"""Offline checks for shared Snake planning, input isolation, and actual choices."""
import copy
import unittest
from unittest.mock import patch

import evaluate_composed_snake as runner
import snake_game as snake


def episode(state, identifier="snake"):
    return {"id": identifier, "game": "snake", "split": "test", "size": state["size"], "initial_state": state}


class DirectionChooser(runner.UniformChoice):
    def __init__(self, last=False):
        self.last = last

    def predict(self, payload, **kwargs):
        response = super().predict(payload, **kwargs)
        for row in response["states"]:
            probabilities = row["answers"]["action"]["probabilities"]
            selected = list(probabilities)[-1 if self.last else 0]
            row["answers"]["action"]["probabilities"] = {a: float(a == selected) for a in probabilities}
        response["states"].reverse()
        return response


class ComposedSnakeTests(unittest.TestCase):
    def state(self):
        state = snake.make_snake(6, 17)
        state.update(body=[[3, 3], [3, 2], [3, 1]], direction="east", food=[1, 5])
        snake.validate_state(state)
        return state

    def test_planner_safe_food_distance_and_model_changes_real_action(self):
        state = self.state()
        plan = runner.plan_candidates(state)
        self.assertEqual(plan["offered_actions"], ["north", "east"])
        self.assertEqual(plan["static_total_distances"]["north"], 4)
        self.assertEqual(plan["static_total_distances"]["east"], 4)
        results = [runner.run_composed_snake([episode(state)], DirectionChooser(last), max_steps=1) for last in (False, True)]
        self.assertEqual([r["episodes"][0]["steps"][0]["action"] for r in results], ["north", "east"])
        self.assertNotEqual(results[0]["episodes"][0]["final_state"]["body"], results[1]["episodes"][0]["final_state"]["body"])

    def test_rng_future_food_and_planner_metadata_do_not_enter_input(self):
        state = self.state()
        state["food"] = [3, 4]
        changed = copy.deepcopy(state)
        changed.update(rng_state=(state["rng_state"] + 999) & snake.MASK64, seed=888, oracle="forbidden")
        self.assertEqual(runner.plan_candidates(state), runner.plan_candidates(changed))
        public = runner.render_composed_request(state, ["north", "east"])
        self.assertEqual(public, runner.render_composed_request(changed, ["north", "east"]))
        self.assertEqual(set(public["questions"]), {"action"})
        self.assertEqual(runner.plan_candidates(state)["static_total_distances"]["east"], 1)

    def test_forced_move_never_calls_model_and_trapped_is_not_win(self):
        state = self.state()
        state["food"] = [3, 4]
        engine = runner.UniformChoice()
        with patch.object(engine, "predict", side_effect=AssertionError("Forced move called model")):
            result = runner.run_composed_snake([episode(state)], engine, max_steps=1)
        self.assertEqual(result["summary"]["forced_moves"], 1)
        self.assertEqual(result["summary"]["food_collected"], 1)
        trapped = snake.make_snake(3, 8)
        trapped.update(body=[[0, 0], [0, 1], [1, 1], [1, 0], [2, 0]], direction="west", food=[2, 2])
        snake.validate_state(trapped)
        result = runner.run_composed_snake([episode(trapped)], engine, max_steps=4)
        self.assertEqual(result["episodes"][0]["outcome"], "trapped")
        self.assertFalse(result["episodes"][0]["full_board_win"])

    def test_tail_vacancy_and_full_board_win_are_safe(self):
        state = snake.make_snake(3, 1)
        state.update(body=[[1, 1], [1, 0], [0, 0], [0, 1]], direction="east", food=[2, 2])
        self.assertIn("north", runner.plan_candidates(state)["safe_actions"])
        full = snake.make_snake(2, 1)
        full.update(body=[[0, 0], [1, 0], [1, 1]], direction="north", food=[0, 1])
        result = runner.run_composed_snake([episode(full)], runner.UniformChoice(), max_steps=2)
        self.assertTrue(result["episodes"][0]["full_board_win"])
        self.assertEqual(result["episodes"][0]["survival_steps"], 1)

    def test_sampling_and_batching_are_reproducible_and_actions_replay(self):
        rows = [episode(self.state(), "one"), episode(snake.make_snake(8, 44), "two")]
        first = runner.run_composed_snake(rows, runner.UniformChoice(), "sample", 30, 1)
        second = runner.run_composed_snake(rows, runner.UniformChoice(), "sample", 30, 2)
        for a, b in zip(first["episodes"], second["episodes"]):
            self.assertEqual(a["steps"], b["steps"])
            state = a["initial_state"]
            for trace in a["steps"]:
                self.assertEqual(trace["state"], runner.physical_state(state))
                state = snake.step(state, trace["action"])
                self.assertEqual(trace["next_state"], runner.physical_state(state))
                if trace["actor"] != "forced_move":
                    self.assertTrue(0 <= trace["controller_draw"] < 1)

    def test_invalid_probability_and_empty_candidate_schema_rejected(self):
        for probabilities in ({"north": .8}, {"north": .5, "east": float("nan")}, {"north": .8, "east": .8}):
            with self.assertRaises(ValueError):
                runner.validate_choice({"type": "choice", "probabilities": probabilities}, ["north", "east"])
        with self.assertRaises(ValueError):
            runner.render_composed_request(self.state(), ["north"])


if __name__ == "__main__":
    unittest.main()
