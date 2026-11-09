"""Comparable direct-scoring runs, without exposing evaluation labels to the engine."""

from time import perf_counter

from litjev.decision import DecisionResponse, Evaluation, Usage
from litjev.schema import DecisionSchema

STATE = "Answer each question using its listed options."


def evaluate(engine, schema, sequential=False, synchronize=lambda: None):
    if not sequential:
        return engine.evaluate(STATE, schema), {}
    answers, durations = {}, {}
    input_tokens = forward_calls = 0
    fields = {}
    for name, field in schema.items():
        single = DecisionSchema({name: field})
        synchronize()
        started = perf_counter()
        evaluation = engine.evaluate(STATE, single)
        response = evaluation.result
        synchronize()
        durations[name] = perf_counter() - started
        answers.update(response.answers)
        input_tokens += response.usage.input_tokens
        forward_calls += evaluation.diagnostics["forward_calls"]
        fields.update(evaluation.diagnostics["fields"])
    return Evaluation(
        DecisionResponse(response.model, answers, Usage(input_tokens)),
        {**evaluation.diagnostics, "forward_calls": forward_calls, "fields": fields},
    ), durations
