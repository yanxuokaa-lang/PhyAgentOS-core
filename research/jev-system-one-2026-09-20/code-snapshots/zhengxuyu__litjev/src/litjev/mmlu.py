"""Gold labels stay outside model requests."""

from pydantic import BaseModel

from litjev.schema import Choice, SystemOneRequest

DATASET_ID = "TIGER-Lab/MMLU-Pro"
LABELS = "ABCDEFGHIJ"


class McqQuestion(BaseModel):
    """Dataset preparation record, not an HTTP request schema."""

    question_id: str
    prompt: str
    options: dict[str, str]


def convert_rows(rows):
    questions, labels, skipped = [], {}, []
    for row in rows:
        question_id = str(row.get("question_id", ""))
        options = row.get("options")
        answer = row.get("answer_index")
        valid = (
            isinstance(options, list)
            and 2 <= len(options) <= 10
            and all(isinstance(text, str) and text.strip() for text in options)
            and type(answer) is int
            and 0 <= answer < len(options)
            and isinstance(row.get("question"), str)
            and row["question"].strip()
        )
        if not valid:
            skipped.append({"id": question_id, "reason": "invalid MCQ or missing label"})
            continue
        if question_id in labels:
            raise ValueError(f"Duplicate question ID: {question_id}")
        questions.append(
            McqQuestion(
                question_id=question_id, prompt=row["question"], options=dict(zip(LABELS, options))
            )
        )
        labels[question_id] = LABELS[answer]
    return questions, labels, skipped


def ten_question_batches(questions):
    """Pad the final batch by repeating real questions with distinct request IDs."""
    for start in range(0, len(questions), 10):
        group = questions[start : start + 10]
        valid_ids = [q.question_id for q in group]
        while len(group) < 10:
            padding_id = f"__padding_{start}_{len(group)}"
            if any(q.question_id == padding_id for q in questions):
                raise ValueError("Question ID collides with padding namespace")
            group.append(group[0].model_copy(update={"question_id": padding_id}))
        yield (
            SystemOneRequest(
                model="litjev",
                state="Answer each question using its listed options.",
                questions={
                    q.question_id: Choice(instructions=q.prompt, criteria=q.options) for q in group
                },
            ),
            valid_ids,
        )
