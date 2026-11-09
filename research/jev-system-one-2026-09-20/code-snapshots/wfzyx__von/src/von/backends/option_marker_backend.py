"""Option-Marker Backend for Von.

Executes single-pass non-autoregressive decision evaluation:
- Choice: Pack all K options into 1 sequence with [MASK] markers.
- Noul: Single-pass binary verification against dual affirmative/negative options.
- Score: Single-pass ordinal rating over all levels simultaneously.
"""

import json
import os
import threading
from typing import Any, Dict, List, Optional, Union

import torch
from ..types import (
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Question,
    Score,
    ScoreAnswer,
    SystemOneResponse,
    Usage,
)
from .base import BaseBackend
from ..models.option_marker import OptionMarkerModel


def _format_state(state: Any) -> str:
    if isinstance(state, str):
        return state
    if isinstance(state, dict):
        parts = []
        for k, v in state.items():
            parts.append(f"{k}: {v}")
        return "\n".join(parts)
    return str(state)


class OptionMarkerBackend(BaseBackend):
    """Native System One decision backend powered by Option-Marker joint attention."""

    def __init__(
        self,
        checkpoint_dir: str = "checkpoints/von-option-marker",
        device: Optional[str] = None,
    ):
        self.checkpoint_dir = checkpoint_dir
        self.device = torch.device(
            device
            if device
            else ("cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"))
        )
        self._model = None
        self._default_temp = 1.0
        self._lock = threading.Lock()

    def _get_model(self) -> OptionMarkerModel:
        with self._lock:
            if self._model is None:
                pt_path = os.path.join(self.checkpoint_dir, "option_marker.pt")
                if os.path.exists(pt_path):
                    # Load trained OptionMarkerModel
                    model = OptionMarkerModel(base_model_id=self.checkpoint_dir)
                    state_dict = torch.load(pt_path, map_location=self.device, weights_only=True)
                    model.load_state_dict(state_dict)
                else:
                    # Fallback to base model
                    base_id = "checkpoints/von-modernbert-rlcd" if os.path.exists("checkpoints/von-modernbert-rlcd") else "wfzyx/von-1.0"
                    model = OptionMarkerModel(base_model_id=base_id)

                model = model.to(self.device).eval()

                # Load fitted temperature if present
                calib_path = os.path.join(self.checkpoint_dir, "marker_calibration.json")
                if os.path.exists(calib_path):
                    try:
                        with open(calib_path, "r", encoding="utf-8") as f:
                            cdata = json.load(f)
                            self._default_temp = float(cdata.get("temperature", 1.0))
                    except Exception:
                        self._default_temp = 1.0
                else:
                    self._default_temp = 1.0

                self._model = model
            return self._model

    def evaluate_choice(
        self,
        q_id: str,
        state_text: str,
        q: Choice,
        temperature: float = 1.0,
        **kwargs,
    ) -> ChoiceAnswer:
        options = list(q.criteria.keys())
        if not options:
            return ChoiceAnswer(choice="", probabilities={}, confidence=0.0)

        model = self._get_model()
        tok = model.tokenizer

        descriptions = []
        for opt in options:
            desc = q.criteria.get(opt)
            descriptions.append(desc.strip() if desc else opt.strip())

        packed_text = model.pack_sequence(state_text, q.instructions, descriptions)

        inputs = tok(packed_text, return_tensors="pt").to(self.device)
        input_ids = inputs["input_ids"][0]
        pos_list = (input_ids == model.mask_token_id).nonzero(as_tuple=True)[0].tolist()

        with torch.no_grad():
            batch_logits = model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                mask_positions=[pos_list],
            )
            logits = batch_logits[0]  # (K,)
            scaled = logits / max(temperature, 1e-4)
            probs = torch.softmax(scaled, dim=-1).cpu().tolist()

        best_idx = int(torch.argmax(logits).item())
        best_choice = options[best_idx]
        prob_dict = {opt: round(float(p), 4) for opt, p in zip(options, probs)}

        sorted_p = sorted(probs, reverse=True)
        conf = round(max(0.0, min(1.0, sorted_p[0] - (sorted_p[1] if len(sorted_p) > 1 else 0.0))), 3)

        return ChoiceAnswer(choice=best_choice, probabilities=prob_dict, confidence=conf)

    def evaluate_noul(
        self,
        q_id: str,
        state_text: str,
        q: Noul,
        temperature: float = 1.0,
        **kwargs,
    ) -> NoulAnswer:
        model = self._get_model()
        tok = model.tokenizer

        crit = q.criteria or {}
        pos_desc = crit.get("true", "Yes, condition holds true.")
        neg_desc = crit.get("false", "No, condition is false.")

        descriptions = [
            f"{q.instructions} {pos_desc}".strip(),
            f"{q.instructions} {neg_desc}".strip(),
        ]

        mask = tok.mask_token
        sep = tok.sep_token
        packed_text = f"{state_text} {sep} {mask} {descriptions[0]} {mask} {descriptions[1]}"

        inputs = tok(packed_text, return_tensors="pt").to(self.device)
        input_ids = inputs["input_ids"][0]
        pos_list = (input_ids == model.mask_token_id).nonzero(as_tuple=True)[0].tolist()

        with torch.no_grad():
            batch_logits = model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                mask_positions=[pos_list],
            )
            logits = batch_logits[0]
            scaled = logits / max(temperature, 1e-4)
            probs = torch.softmax(scaled, dim=-1).cpu().tolist()

        prob_true = round(max(0.0, min(1.0, probs[0])), 4)
        return NoulAnswer(noul=prob_true)

    def evaluate_score(
        self,
        q_id: str,
        state_text: str,
        q: Score,
        temperature: float = 1.0,
        **kwargs,
    ) -> ScoreAnswer:
        levels = q.criteria
        if not levels:
            return ScoreAnswer(score=0.0, confidence=0.0, legend={}, probabilities={})

        model = self._get_model()
        tok = model.tokenizer

        legend: Dict[str, str] = {}
        descriptions = []
        inst_clean = q.instructions.strip() if q.instructions else ""

        for i, item in enumerate(levels):
            idx_str = str(i)
            if isinstance(item, dict):
                what = item.get("what", "")
                examples = item.get("examples", [])
                ex_str = f" Examples: {', '.join(examples)}" if examples else ""
                desc = f"{what}{ex_str}".strip()
            else:
                desc = str(item).strip()
            legend[idx_str] = desc
            descriptions.append(f"The condition is {desc}")

        mask = tok.mask_token
        sep = tok.sep_token
        prefix = f"{inst_clean} {state_text}".strip() if inst_clean else state_text
        packed_text = f"{prefix} {sep} " + " ".join(f"{mask} {d}" for d in descriptions)

        inputs = tok(packed_text, return_tensors="pt").to(self.device)
        input_ids = inputs["input_ids"][0]
        pos_list = (input_ids == model.mask_token_id).nonzero(as_tuple=True)[0].tolist()

        with torch.no_grad():
            batch_logits = model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                mask_positions=[pos_list],
            )
            logits = batch_logits[0]
            scaled = logits / max(temperature, 1e-4)
            probs = torch.softmax(scaled, dim=-1).cpu().tolist()

        prob_dict = {str(i): round(float(p), 4) for i, p in enumerate(probs)}
        weighted_score = round(sum(i * p for i, p in enumerate(probs)), 2)

        sorted_p = sorted(probs, reverse=True)
        conf = round(max(0.0, min(1.0, sorted_p[0] - (sorted_p[1] if len(sorted_p) > 1 else 0.0))), 3)

        return ScoreAnswer(
            score=weighted_score,
            confidence=conf,
            legend=legend,
            probabilities=prob_dict,
        )

    def evaluate(
        self,
        state: Any,
        questions: Dict[str, Union[Question, Dict[str, Any]]],
        model: str = "von-option-marker",
    ) -> SystemOneResponse:
        state_str = _format_state(state)
        answers: Dict[str, Union[NoulAnswer, ChoiceAnswer, ScoreAnswer]] = {}
        total_q_chars = 0

        for q_id, q_data in questions.items():
            if isinstance(q_data, dict):
                q_type = q_data.get("type", "choice")
                if q_type == "choice":
                    q_obj = Choice(**q_data)
                elif q_type == "noul":
                    q_obj = Noul(**q_data)
                elif q_type == "score":
                    q_obj = Score(**q_data)
                else:
                    raise ValueError(f"Unknown question type '{q_type}'")
            else:
                q_obj = q_data

            if isinstance(q_obj, Choice):
                answers[q_id] = self.evaluate_choice(q_id, state_str, q_obj, temperature=self._default_temp)
                total_q_chars += len(q_obj.instructions or "")
            elif isinstance(q_obj, Noul):
                answers[q_id] = self.evaluate_noul(q_id, state_str, q_obj, temperature=self._default_temp)
                total_q_chars += len(q_obj.instructions or "")
            elif isinstance(q_obj, Score):
                answers[q_id] = self.evaluate_score(q_id, state_str, q_obj, temperature=self._default_temp)
                total_q_chars += len(q_obj.instructions or "")

        resolved_model = "von-option-marker"
        state_tokens = max(1, len(state_str) // 4)
        q_tokens = max(1, total_q_chars // 4)

        usage = Usage(
            state_tokens=state_tokens,
            question_tokens=q_tokens,
            total_tokens=state_tokens + q_tokens,
        )

        return SystemOneResponse(
            model=resolved_model,
            answers=answers,
            usage=usage,
        )
