"""Snake transition, reproducibility, observable-input and training-row checks."""
import copy
import json
import random
import unittest
from unittest.mock import patch

import snake_game as game


def fixture(size, body, direction, food):
    state = game.make_snake(size, 41)
    state.update(body=copy.deepcopy(body), direction=direction, food=list(food))
    game.validate_state(state)
    return state


class SnakeTests(unittest.TestCase):
    def test_seed_sizes_and_global_random(self):
        before = random.getstate()
        for n in (8, 16, 32, 50):
            for seed in (0, 1, -17, 2**70):
                a, b = game.make_snake(n, seed), game.make_snake(n, seed)
                self.assertEqual(a, b)
                self.assertEqual(json.loads(json.dumps(a)), a)
                self.assertNotIn(a['food'], a['body'])
        self.assertEqual(before, random.getstate())
        a = game.make_record(game.make_snake(8, 0), 'train')
        b = game.make_record(game.make_snake(8, 2**70), 'train')
        self.assertEqual(a['id'], b['id'])
        self.assertEqual(a['metadata']['source_group_id'], b['metadata']['source_group_id'])

    def test_actions_reverse_wall_terminal_and_immutability(self):
        s = fixture(8, [[0, 7], [0, 6], [0, 5]], 'east', [2, 2])
        before = copy.deepcopy(s)
        self.assertEqual(set(game.valid_actions(s)), {'north', 'east', 'south'})
        self.assertFalse(game.one_step_safe(s, 'east'))
        for a in ('west', 'invalid', None):
            with self.assertRaises(ValueError): game.step(s, a)
        end = game.step(s, 'east')
        self.assertEqual(s, before)
        self.assertEqual(end['body'], s['body'])
        self.assertEqual(end['outcome'], 'wall_collision')
        self.assertEqual(end['steps'], 1)
        self.assertEqual(game.valid_actions(end), [])
        for fn in (game.step, game.one_step_safe):
            with self.assertRaises(ValueError): fn(end, 'south')
        with self.assertRaises(ValueError): game.render_request(end)
        end['body'][0][0] = 3
        self.assertEqual(s, before)

    def test_self_collision_and_vacating_tail(self):
        loop = fixture(8, [[1, 1], [1, 2], [2, 2], [2, 1]], 'west', [0, 0])
        self.assertTrue(game.one_step_safe(loop, 'south'))
        moved = game.step(loop, 'south')
        self.assertEqual(moved['body'], [[2, 1], [1, 1], [1, 2], [2, 2]])
        self.assertFalse(moved['done'])
        # Occupancy differs on growth; food on the old tail is not a legal state.
        self.assertEqual(game._collision(loop, loop['body'][-1], True), 'self_collision')
        invalid = copy.deepcopy(loop); invalid['food'] = invalid['body'][-1][:]
        with self.assertRaises(ValueError): game.validate_state(invalid)
        bent = fixture(8, [[2, 2], [2, 1], [1, 1], [1, 2], [1, 3], [2, 3], [3, 3]], 'east', [0, 0])
        self.assertIn('north', game.valid_actions(bent))
        self.assertFalse(game.one_step_safe(bent, 'north'))
        self.assertEqual(game.step(bent, 'north')['outcome'], 'self_collision')

    def test_growth_food_roundtrip_and_full_board(self):
        s = fixture(8, [[3, 3], [3, 2], [3, 1]], 'east', [3, 4])
        old = copy.deepcopy(s)
        a = game.step(s, 'east'); b = game.step(json.loads(json.dumps(s)), 'east')
        self.assertEqual(a, b); self.assertEqual(s, old)
        self.assertEqual(len(a['body']), 4); self.assertEqual(a['score'], 1)
        self.assertNotIn(a['food'], a['body'])
        self.assertNotEqual(a['rng_state'], s['rng_state'])
        for _ in range(15):
            offered = game.valid_actions(a)
            safe = [x for x in offered if game.one_step_safe(a, x)]
            if not safe: break
            a, b = game.step(a, safe[0]), game.step(json.loads(json.dumps(b)), safe[0])
            self.assertEqual(a, b)
        almost = fixture(3, [[0, 1], [0, 0], [1, 0], [2, 0], [2, 1], [1, 1], [1, 2], [2, 2]], 'east', [0, 2])
        self.assertTrue(game.one_step_safe(almost, 'east'))
        win = game.step(almost, 'east')
        self.assertEqual((win['done'], win['outcome'], win['food']), (True, 'win', None))
        self.assertEqual(len(win['body']), 9)
        self.assertEqual(win['rng_state'], almost['rng_state'])

    def test_renderer_visibility_and_training_contract(self):
        s = fixture(8, [[0, 7], [0, 6], [0, 5]], 'east', [2, 2])
        baseline = game.render_request(s)
        changed = copy.deepcopy(s); changed.update(seed=987654321, rng_state=123, oracle={'best': 'south'})
        self.assertEqual(game.render_request(changed), baseline)
        with patch.object(game, 'one_step_safe', side_effect=AssertionError('oracle')), patch.object(game, 'step', side_effect=AssertionError('step')), patch.object(game, '_random64', side_effect=AssertionError('rng')):
            self.assertEqual(game.render_request(s), baseline)
        for forbidden in ('rng_state', 'seed', 'oracle', 'next_food'):
            self.assertNotIn(forbidden, baseline['state'])
        row = game.make_record(s, 'train')
        self.assertEqual(row['state'], baseline['state']); self.assertEqual(row['questions'], baseline['questions'])
        self.assertEqual(row['gold_probs']['action'], {'north': 0., 'east': 0., 'south': 1.})
        for action in game.valid_actions(s):
            question = row['questions']['safe_' + action]
            self.assertIn(action, question['instructions'])
            self.assertEqual(set(question['criteria']), {'true', 'false'})
            actual = game.step(s, action)
            expected = not actual['done'] or actual['outcome'] == 'win'
            self.assertEqual(row['gold']['safe_' + action], expected)
            self.assertEqual(row['metadata']['outcomes']['safe_' + action], expected)
        from train_pipeline_decisions import validate_training_row
        targets = validate_training_row(row)
        for action in game.valid_actions(s):
            value = row['gold']['safe_' + action]
            self.assertEqual(targets['safe_' + action]['gold_distribution_probs'], [float(not value), float(value)])
        child = game.step(s, 'south')
        self.assertEqual(game.make_record(child, 'train')['metadata']['source_group_id'], row['metadata']['source_group_id'])
        self.assertEqual(game.make_record(changed, 'train')['id'], row['id'])

    def test_local_food_progress_ties_and_all_dangerous(self):
        s = fixture(8, [[3, 3], [3, 2], [3, 1]], 'east', [1, 3])
        row = game.make_record(s, 'train')
        self.assertEqual(row['gold_probs']['action'], {'north': 1., 'east': 0., 'south': 0.})
        first = game.step(s, row['gold']['action'])
        second = game.step(first, game.make_record(first, 'train')['gold']['action'])
        self.assertEqual(second['score'], s['score'] + 1)
        self.assertEqual(second['body'][0], s['food'])
        tied = copy.deepcopy(s); tied['food'] = [1, 5]
        self.assertEqual(game.make_record(tied, 'train')['gold_probs']['action'], {'north': .5, 'east': .5, 'south': 0.})
        trapped = fixture(8, [[2, 2], [2, 1], [1, 1], [1, 2], [1, 3], [2, 3], [3, 3], [3, 2], [3, 1], [4, 1]], 'east', [0, 0])
        self.assertTrue(all(not game.one_step_safe(trapped, a) for a in game.valid_actions(trapped)))
        self.assertEqual(game.make_record(trapped, 'train')['gold_probs']['action'], {'north': 1/3, 'east': 1/3, 'south': 1/3})
        self.assertEqual(row['gold_probs_kind']['action'], 'optimal_action_policy')

    def test_malformed(self):
        for n, seed in [(True, 0), (1, 0), (3., 0), (8, False), (8, '1')]:
            with self.assertRaises(ValueError): game.make_snake(n, seed)
        original = game.make_snake(8, 2)
        for changes in ({'rng_state': -1}, {'body': [[0, 0], [0, 0]]}, {'body': [[0, 0], [2, 0]]}, {'done': 1}, {'score': -1}, {'food': original['body'][0]}, {'direction': 'up'}, {'direction': []}, {'outcome': 'win'}, {'done': True, 'outcome': {}}, {'food': None}):
            invalid = copy.deepcopy(original); invalid.update(changes)
            with self.assertRaises(ValueError): game.validate_state(invalid)
        with self.assertRaises(ValueError): game.make_record(original, 'unknown')


if __name__ == '__main__':
    unittest.main()
