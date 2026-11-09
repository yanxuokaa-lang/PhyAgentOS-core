"""High-level composable decision patterns built on top of VonEngine."""

from typing import Any, Callable, Dict, List, Optional
from .api import system_one
from .types import Choice, Noul, Score


def confidence_gate(
    state: Any,
    questions: Dict[str, Any],
    threshold: float = 0.80,
    backend: Optional[str] = None,
) -> Dict[str, Any]:
    """Selective automation pattern: split answers into automatic vs human escalation.

    Evaluates the questions via Von and partitions the results based on the calibrated
    confidence metric. Answers meeting or exceeding `threshold` are routed to `automatic`,
    while ambiguous answers below `threshold` are routed to `escalate`.
    """
    if not (0.0 <= threshold <= 1.0):
        raise ValueError(f"threshold must be in [0.0, 1.0], got {threshold}")

    if backend:
        from .api import set_backend
        set_backend(backend)

    resp = system_one(state, questions)
    automatic = {}
    escalate = {}

    for q_id, ans in resp.answers.items():
        conf = getattr(ans, "confidence", 1.0)
        # For Noul (float probability), confidence is distance from uncertainty (0.5)
        if isinstance(ans, float):
            conf = abs(ans - 0.5) * 2.0

        if conf >= threshold:
            automatic[q_id] = ans
        else:
            escalate[q_id] = ans

    return {
        "automatic": automatic,
        "escalate": escalate,
        "response": resp,
    }


def route(
    state: Any,
    question: Choice,
    routes: Dict[str, Callable[[Any], Any]],
    default: Optional[Callable[[Any], Any]] = None,
    min_confidence: float = 0.0,
    backend: Optional[str] = None,
) -> Any:
    """Run a Choice decision and dispatch immediately to the matching route handler.

    If the winning choice has no matching handler in `routes`, or if the confidence is
    below `min_confidence`, falls back to `default(ans)` if provided.
    """
    if not isinstance(question, Choice):
        raise TypeError("question must be an instance of von.Choice")

    if backend:
        from .api import set_backend
        set_backend(backend)

    resp = system_one(state, {"route_question": question})
    ans = resp["route_question"]
    chosen_id = ans.choice
    confidence = ans.confidence

    handler = routes.get(chosen_id)
    if handler is None or confidence < min_confidence:
        if default is not None:
            return default(ans)
        return ans

    return handler(ans)


def composite_score(
    state: Any,
    questions: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
    normalize: bool = True,
    backend: Optional[str] = None,
) -> Dict[str, Any]:
    """Combine multiple Score and Noul questions into a unified normalized risk index in [0, 1].

    - Score answers are normalized by their max level index: `score / (num_levels - 1)`.
    - Noul answers directly use their probability: `P(true)`.
    - Choice answers are excluded from the numeric average.
    """
    if backend:
        from .api import set_backend
        set_backend(backend)

    resp = system_one(state, questions)
    w_map = weights or {}

    total_weighted_sum = 0.0
    total_weights = 0.0
    breakdown = {}

    for q_id, ans in resp.answers.items():
        normalized_val = None
        if hasattr(ans, "score") and hasattr(ans, "legend"):
            max_level = max(1, len(ans.legend) - 1)
            normalized_val = float(ans.score) / max_level
        elif hasattr(ans, "noul"):
            normalized_val = float(ans.noul)
        elif isinstance(ans, float):
            normalized_val = ans

        if normalized_val is not None:
            w = float(w_map.get(q_id, 1.0))
            total_weighted_sum += normalized_val * w
            total_weights += w
            breakdown[q_id] = {
                "raw": getattr(ans, "score", getattr(ans, "noul", ans)),
                "normalized": round(normalized_val, 4),
                "weight": w,
            }

    final_score = (
        (total_weighted_sum / total_weights)
        if (normalize and total_weights > 0)
        else total_weighted_sum
    )

    return {
        "score": round(final_score, 4),
        "breakdown": breakdown,
        "response": resp,
    }


def two_stage_choice(
    state: Any,
    taxonomy: Dict[str, Dict[str, str]],
    instructions_category: str = "Which broad category best matches the state?",
    instructions_option: str = "Which specific sub-option applies within {category}?",
    backend: Optional[str] = None,
) -> Dict[str, Any]:
    """Hierarchical two-stage routing for high-cardinality taxonomies (>20 options).

    Stage 1: Classifies into one of the top-level categories.
    Stage 2: Classifies into the specific option under that chosen category.
    Avoids single-pass option saturation while maintaining sub-50ms execution.
    """
    if backend:
        from .api import set_backend
        set_backend(backend)

    # Stage 1: Top-level category choice
    cat_criteria = {cat: f"Category for {cat} operations and topics" for cat in taxonomy.keys()}
    cat_q = Choice(instructions=instructions_category, criteria=cat_criteria)

    cat_resp = system_one(state, {"category": cat_q})
    top_cat = cat_resp["category"].choice
    cat_conf = cat_resp["category"].confidence

    # Stage 2: Sub-options under top category
    sub_criteria = taxonomy.get(top_cat, {})
    opt_q = Choice(
        instructions=instructions_option.format(category=top_cat),
        criteria=sub_criteria,
    )

    opt_resp = system_one(state, {"option": opt_q})
    chosen_opt = opt_resp["option"].choice
    opt_conf = opt_resp["option"].confidence

    return {
        "category": top_cat,
        "category_confidence": cat_conf,
        "choice": chosen_opt,
        "choice_confidence": opt_conf,
        "combined_confidence": round(cat_conf * opt_conf, 4),
    }
