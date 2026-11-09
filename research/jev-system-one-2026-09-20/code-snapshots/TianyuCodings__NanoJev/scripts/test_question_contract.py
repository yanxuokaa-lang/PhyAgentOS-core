#!/usr/bin/env python3
"""Offline characterization of question encoding and known API differences.

Run: python3 -m unittest discover -s scripts -p test_question_contract.py -v
The reversible fake tokenizer checks semantic input isolation without importing
PyTorch, downloading a tokenizer, loading weights, or calling a provider.
These are token-input checks, not evidence of numerical output invariance.
"""

import copy
import json
import unittest

from predict_toy_decisions import answer_from_probabilities, prepare_examples, validate_request


class CharacterTokenizer:
    eos_token_id = 0

    def encode(self, text, add_special_tokens=False):
        if add_special_tokens:
            raise AssertionError("The encoder must explicitly disable added special tokens")
        return [ord(char) + 1 for char in text]

    @staticmethod
    def decode(tokens):
        return "".join(chr(token - 1) for token in tokens if token != 0)


def payload(question, state="A customer asks for a refund.", qid="transport_qid_731", identifier="transport_id_924"):
    return {"states": [{"id": identifier, "state": state, "questions": {qid: copy.deepcopy(question)}}]}


def encoded(request):
    return prepare_examples(request, CharacterTokenizer(), max_length=100000)


def boolean_question():
    return {"type": "boolean", "instructions": "Does the customer request a refund?",
            "criteria": {"true": "The customer explicitly asks for money back.",
                         "false": "The customer makes no request for money back."}}


def choice_question():
    return {"type": "choice", "instructions": "Which team should handle the request?",
            "criteria": {"returns": "Handles requests for money back.", "shipping": "Handles delivery tracking."}}


def score_question():
    return {"type": "score", "instructions": "How urgent is the request?",
            "criteria": ["No time limit is mentioned.", "A deadline is mentioned but is not immediate.",
                         "The request needs an immediate response."]}


class TransportAndQuestionIsolationTests(unittest.TestCase):
    def test_renaming_record_and_question_ids_keeps_all_leaf_tokens(self):
        for question in (boolean_question(), choice_question(), score_question()):
            with self.subTest(type=question["type"]):
                original = encoded(payload(question))[0]
                renamed = encoded(payload(question, qid="different_qid", identifier="different_record"))[0]
                self.assertEqual(original["leaf_tokens"], renamed["leaf_tokens"])
                self.assertNotEqual(original["id"], renamed["id"])
                for tokens in original["leaf_tokens"]:
                    text = CharacterTokenizer.decode(tokens)
                    self.assertNotIn("transport_qid_731", text)
                    self.assertNotIn("transport_id_924", text)

    def test_added_reordered_unrelated_questions_do_not_change_existing_leaves(self):
        questions = {"refund": boolean_question(), "department": choice_question(), "urgency": score_question()}
        request = {"states": [{"id": "one", "state": "Please return my money today.", "questions": questions}]}
        original = {ex["qid"]: ex["leaf_tokens"] for ex in encoded(request)}
        expanded = copy.deepcopy(request)
        extra = {"type": "boolean", "instructions": "UNRELATED_SENTINEL: does the state mention a blue bicycle?"}
        expanded["states"][0]["questions"] = {"irrelevant": extra, **dict(reversed(list(questions.items())))}
        after = {ex["qid"]: ex["leaf_tokens"] for ex in encoded(expanded)}
        for qid, leaves in original.items():
            self.assertEqual(leaves, after[qid])
            self.assertTrue(all("UNRELATED_SENTINEL" not in CharacterTokenizer.decode(leaf) for leaf in after[qid]))

    def test_extra_state_does_not_change_existing_example_tokens(self):
        request = payload(choice_question())
        original = encoded(request)[0]
        expanded = copy.deepcopy(request)
        expanded["states"].insert(0, {"id": "different_state", "state": "An unrelated long state. " * 20,
                                      "questions": {"unrelated": score_question()}})
        after = next(ex for ex in encoded(expanded) if ex["state_id"] == original["state_id"])
        self.assertEqual(original["leaf_tokens"], after["leaf_tokens"])

    def test_instructions_carry_question_semantics_and_change_input(self):
        question = boolean_question()
        original = encoded(payload(question))[0]
        question["instructions"] = "Has a refund already been issued to the customer?"
        changed = encoded(payload(question))[0]
        self.assertNotEqual(original["leaf_tokens"], changed["leaf_tokens"])
        self.assertIn(question["instructions"], CharacterTokenizer.decode(changed["leaf_tokens"][0]))


class BooleanCriteriaTests(unittest.TestCase):
    def test_both_criteria_enter_one_semantic_path_in_fixed_order(self):
        question = boolean_question()
        example = encoded(payload(question))[0]
        self.assertEqual(example["candidate_ids"], ["false", "true"])
        self.assertEqual(len(example["leaf_tokens"]), 1)
        text = CharacterTokenizer.decode(example["leaf_tokens"][0])
        self.assertIn("False criterion: " + question["criteria"]["false"], text)
        self.assertIn("True criterion: " + question["criteria"]["true"], text)
        self.assertLess(text.index("False criterion:"), text.index("True criterion:"))
        self.assertIn("Candidate:\nThe proposition is true.\nDecision:", text)
        reordered = copy.deepcopy(question)
        reordered["criteria"] = dict(reversed(list(question["criteria"].items())))
        self.assertEqual(example["leaf_tokens"], encoded(payload(reordered))[0]["leaf_tokens"])

    def test_changing_either_truth_boundary_changes_the_encoded_question(self):
        original = boolean_question()
        baseline = encoded(payload(original))[0]["leaf_tokens"]
        for key in ("false", "true"):
            with self.subTest(key=key):
                changed = copy.deepcopy(original)
                changed["criteria"][key] += " Only confirmed transactions qualify."
                self.assertNotEqual(baseline, encoded(payload(changed))[0]["leaf_tokens"])

    def test_optional_and_one_sided_criteria_are_supported_without_invented_text(self):
        question = {"type": "boolean", "instructions": "Is there a refund request?"}
        absent = encoded(payload(question))[0]
        self.assertNotIn("criterion:", CharacterTokenizer.decode(absent["leaf_tokens"][0]))
        for key, label in (("false", "False"), ("true", "True")):
            changed = {**question, "criteria": {key: "Only an explicit request counts."}}
            text = CharacterTokenizer.decode(encoded(payload(changed))[0]["leaf_tokens"][0])
            self.assertIn(label + " criterion:", text)
            self.assertNotIn(("True" if key == "false" else "False") + " criterion:", text)


class CandidateSemanticsTests(unittest.TestCase):
    def test_choice_encodes_both_option_name_and_description(self):
        question = choice_question()
        example = encoded(payload(question))[0]
        for name, tokens in zip(example["candidate_ids"], example["leaf_tokens"]):
            self.assertIn("Candidate:\n" + name + ": " + question["criteria"][name], CharacterTokenizer.decode(tokens))
        renamed = copy.deepcopy(question)
        renamed["criteria"] = {"refund_team": renamed["criteria"]["returns"], "shipping": renamed["criteria"]["shipping"]}
        self.assertNotEqual(example["leaf_tokens"][0], encoded(payload(renamed))[0]["leaf_tokens"][0])
        revised = copy.deepcopy(question)
        revised["criteria"]["returns"] = "Handles exchanges only; never refunds."
        self.assertNotEqual(example["leaf_tokens"][0], encoded(payload(revised))[0]["leaf_tokens"][0])

    def test_choice_permutation_preserves_each_named_leaf(self):
        question = choice_question()
        first = encoded(payload(question))[0]
        question["criteria"] = dict(reversed(list(question["criteria"].items())))
        reordered = encoded(payload(question))[0]
        self.assertEqual(dict(zip(first["candidate_ids"], first["leaf_tokens"])),
                         dict(zip(reordered["candidate_ids"], reordered["leaf_tokens"])))

    def test_score_level_moving_index_or_changing_neighbors_preserves_its_leaf(self):
        question = score_question()
        first = encoded(payload(question))[0]
        focus = question["criteria"][1]
        changed = copy.deepcopy(question)
        changed["criteria"] = ["An entirely different lower boundary.",
                               "Another new description absent from the original.", focus,
                               "An entirely different upper boundary."]
        after = encoded(payload(changed))[0]
        self.assertEqual(first["leaf_tokens"][1], after["leaf_tokens"][2])
        self.assertEqual(first["candidate_ids"][1], "1")
        self.assertEqual(after["candidate_ids"][2], "2")
        text = CharacterTokenizer.decode(after["leaf_tokens"][2])
        self.assertIn("Candidate:\n" + focus + "\nDecision:", text)
        self.assertNotIn("Another new description", text)
        self.assertNotIn("entirely different", text)

    def test_changing_score_level_description_changes_only_its_leaf(self):
        question = score_question()
        first = encoded(payload(question))[0]
        question["criteria"][1] = "The customer explicitly permits a response next week."
        after = encoded(payload(question))[0]
        self.assertEqual(first["leaf_tokens"][0], after["leaf_tokens"][0])
        self.assertNotEqual(first["leaf_tokens"][1], after["leaf_tokens"][1])
        self.assertEqual(first["leaf_tokens"][2], after["leaf_tokens"][2])

    def test_duplicate_score_descriptions_have_no_hidden_index_feature(self):
        question = score_question()
        question["criteria"] = ["The same complete description."] * 3
        example = encoded(payload(question))[0]
        self.assertEqual(example["leaf_tokens"][0], example["leaf_tokens"][1])
        self.assertEqual(example["leaf_tokens"][1], example["leaf_tokens"][2])

    def test_score_answer_uses_expected_index_not_argmax_level(self):
        example = encoded(payload(score_question()))[0]
        answer = answer_from_probabilities(example, [0.2, 0.3, 0.5])
        self.assertAlmostEqual(answer["score"], 1.3)
        self.assertEqual(answer["level"], 2)


class KnownContractGapTests(unittest.TestCase):
    """Characterize current gaps explicitly; revise these when formats are versioned."""

    def test_official_noul_name_requires_an_adapter(self):
        question = boolean_question()
        question["type"] = "noul"
        with self.assertRaises(ValueError):
            validate_request(payload(question))

    def test_structured_and_null_instructions_are_not_local_inputs_yet(self):
        for instructions in ({"question": "Does the customer request a refund?"}, ["Check the refund request."], None):
            with self.subTest(instructions=instructions), self.assertRaises(ValueError):
                encoded(payload({**boolean_question(), "instructions": instructions}))

    def test_structured_and_null_criteria_are_not_local_inputs_yet(self):
        for value in ({"definition": "An explicit refund request."}, ["A refund request."], None):
            for question, replacement in (
                (boolean_question(), {"true": value}),
                (choice_question(), {"returns": value, "shipping": "Delivery only."}),
                (score_question(), [value, "A complete upper level."]),
            ):
                with self.subTest(value=value, type=question["type"]), self.assertRaises(ValueError):
                    encoded(payload({**question, "criteria": replacement}))

    def test_object_state_is_python_repr_and_key_order_changes_tokens(self):
        state = {"approved": True, "refund": None, "messages": ["A refund was requested."]}
        first = encoded(payload(boolean_question(), state=state))[0]
        reordered = encoded(payload(boolean_question(), state=dict(reversed(list(state.items())))))[0]
        text = CharacterTokenizer.decode(first["leaf_tokens"][0])
        self.assertIn("State:\n" + str(state) + "\n", text)
        self.assertIn("'approved': True", text)
        self.assertIn("'refund': None", text)
        self.assertNotIn("State:\n" + json.dumps(state, sort_keys=True) + "\n", text)
        self.assertNotEqual(first["leaf_tokens"], reordered["leaf_tokens"])


if __name__ == "__main__":
    unittest.main()
