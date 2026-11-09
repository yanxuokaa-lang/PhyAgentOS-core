"""Von Engine orchestrator with pluggable backends (Needle 3, Laya 421M, and Berta Encoders)."""

import os
import threading
from typing import Any, Dict, List, Optional, Union

from .backends import (
    BaseBackend,
    BertaBackend,
)
from .types import (
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Question,
    Score,
    ScoreAnswer,
    SystemOneResponse,
)


class VonEngine:
    """System One inference engine orchestrator."""

    _instance: Optional["VonEngine"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, backend_name: str = "von-1.0", device: Optional[str] = None):
        self.backend_name = backend_name.lower().strip()
        self.device = device or os.environ.get("VON_DEVICE")
        if self.backend_name in ("option-marker", "von-marker", "marker", "option_marker"):
            from .backends.option_marker_backend import OptionMarkerBackend
            self.backend = OptionMarkerBackend(device=self.device)
        elif self.backend_name in ("von-1.0", "von", "modernbert", "default", "berta-modern", "modernbert-nli"):
            self.backend: BaseBackend = BertaBackend(variant="von-1.0", device=self.device)
        else:
            # Check for local benchmark backends if installed
            try:
                if self.backend_name in ("needle", "cactus-needle", "needle-json", "needle_json"):
                    from .local_backends.needle_backend import NeedleBackend
                    self.backend = NeedleBackend()
                elif self.backend_name in ("laya", "laya-421m", "convaiinnovations/laya"):
                    from .local_backends.laya_backend import LayaBackend
                    self.backend = LayaBackend(device=self.device)
                elif self.backend_name in ("berta", "berta-v3", "deberta", "deberta-v3"):
                    self.backend = BertaBackend(variant="deberta-v3", device=self.device)
                else:
                    raise ValueError(f"Unknown backend '{self.backend_name}'.")
            except (ImportError, ModuleNotFoundError) as e:
                raise ValueError(
                    f"Backend '{self.backend_name}' is not available in public release. "
                    f"Von runs natively on 'von-1.0'."
                ) from e

    @classmethod
    def get_instance(cls, backend: Optional[str] = None, device: Optional[str] = None) -> "VonEngine":
        with cls._lock:
            if cls._instance is None:
                b = backend or os.environ.get("VON_BACKEND", "von-1.0")
                d = device or os.environ.get("VON_DEVICE")
                cls._instance = cls(backend_name=b, device=d)
            return cls._instance

    @classmethod
    def set_backend(cls, backend: str, device: Optional[str] = None):
        """Switch active engine backend."""
        with cls._lock:
            d = device or os.environ.get("VON_DEVICE")
            cls._instance = cls(backend_name=backend, device=d)

    def embed(self, text: str) -> List[float]:
        if hasattr(self.backend, "embed"):
            return getattr(self.backend, "embed")(text)
        try:
            from .local_backends.needle_backend import NeedleBackend
            return NeedleBackend().embed(text)
        except Exception:
            # Fallback representation
            return [0.0] * 768

    def evaluate_choice(self, *args, **kwargs) -> ChoiceAnswer:
        return self.backend.evaluate_choice(*args, **kwargs)

    def evaluate_score(self, *args, **kwargs) -> ScoreAnswer:
        return self.backend.evaluate_score(*args, **kwargs)

    def evaluate_noul(self, *args, **kwargs) -> NoulAnswer:
        return self.backend.evaluate_noul(*args, **kwargs)

    def evaluate(
        self,
        state: Any,
        questions: Dict[str, Union[Question, Dict[str, Any]]],
        model: Optional[str] = None,
    ) -> SystemOneResponse:
        if model in ("von-latest", "von-preview", "jev-latest", "jev-preview", None):
            resolved_model = "von-1.0.0"
        else:
            resolved_model = model
        return self.backend.evaluate(state=state, questions=questions, model=resolved_model)
