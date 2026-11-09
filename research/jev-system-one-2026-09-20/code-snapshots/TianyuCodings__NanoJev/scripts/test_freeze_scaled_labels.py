import copy
import hashlib
import json
import unittest

from freeze_scaled_labels import restore_raw_rng_metadata, json_value_equal
from snake_game import make_snake, make_record


class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.raw = make_record(make_snake(8, 9), "train")
        self.label = copy.deepcopy(self.raw)
        public = {key: self.raw[key] for key in ("state", "questions")}
        self.label["input_sha256"] = hashlib.sha256(json.dumps(public, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()

    def test_known_uint64_roundtrip_preserves_raw(self):
        original = self.raw["metadata"]["environment_state"]["rng_state"]
        self.label["metadata"]["environment_state"]["rng_state"] = int(float(original))
        result, changed = restore_raw_rng_metadata(self.raw, self.label)
        self.assertEqual(result["metadata"], self.raw["metadata"])
        self.assertEqual(result["questions"], self.raw["questions"])

    def test_no_boolean_numeric_alias_or_unrelated_change(self):
        self.label["metadata"]["environment_state"]["steps"] = False
        with self.assertRaises(ValueError):
            restore_raw_rng_metadata(self.raw, self.label)
        self.assertFalse(json_value_equal(0, False))
        self.assertTrue(json_value_equal(1, 1.0))

    def test_input_and_probability_changes_are_rejected(self):
        for key in ("state", "questions", "gold_probs"):
            label = copy.deepcopy(self.label)
            label[key] = "changed"
            with self.assertRaises(ValueError):
                restore_raw_rng_metadata(self.raw, label)
        label = copy.deepcopy(self.label)
        label["input_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            restore_raw_rng_metadata(self.raw, label)


if __name__ == "__main__":
    unittest.main()
