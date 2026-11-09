from typesafe_sdk import ChoiceModel, NoulModel, Question, ScoreModel

choice: ChoiceModel = {"type": "noul", "instructions": "?", "criteria": {"a": None}}  # E: is not assignable to TypedDict key `type`
noul: NoulModel = {"type": "choice", "instructions": "?"}  # E: is not assignable to TypedDict key `type`
score: ScoreModel = {"type": "choice", "instructions": "?", "criteria": ["a"]}  # E: is not assignable to TypedDict key `type`

missing_type: NoulModel = {"instructions": "?"}  # E: Missing required key `type`
missing_choice_criteria: ChoiceModel = {"type": "choice"}  # E: Missing required key `criteria`
missing_score_criteria: ScoreModel = {"type": "score"}  # E: Missing required key `criteria`
bad_extra: NoulModel = {"type": "noul", "extra": "future"}  # E: is not defined
bad_criteria: ChoiceModel = {"type": "choice", "criteria": ["a"]}  # E: is not assignable
bad_score_criteria: ScoreModel = {"type": "score", "criteria": {0: "a"}}  # E: is not assignable
bad_question: Question = {"unrelated": "value"}  # E: is not assignable
bad_question_type: Question = {"type": 123}  # E: is not assignable
