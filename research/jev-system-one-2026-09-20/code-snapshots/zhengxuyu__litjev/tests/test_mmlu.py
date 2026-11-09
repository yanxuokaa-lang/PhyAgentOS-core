from litjev.mmlu import convert_rows, ten_question_batches


def test_real_mcq_only_and_gold_never_in_request():
    rows = [
        {
            "question_id": i,
            "question": f"Question {i}",
            "options": ["one", "two"],
            "answer_index": i % 2,
            "cot_content": "SECRET SOLUTION",
        }
        for i in range(11)
    ]
    rows.append({"question_id": 100, "question": "Not multiple choice"})
    questions, labels, skipped = convert_rows(rows)
    batches = list(ten_question_batches(questions))
    assert len(skipped) == 1
    assert len(batches) == 2
    assert all(len(batch.questions) == 10 for batch, _ in batches)
    assert sum(len(ids) for _, ids in batches) == 11
    assert "SECRET" not in batches[0][0].model_dump_json()
    assert "answer_index" not in batches[0][0].model_dump_json()
    assert labels["1"] == "B"
