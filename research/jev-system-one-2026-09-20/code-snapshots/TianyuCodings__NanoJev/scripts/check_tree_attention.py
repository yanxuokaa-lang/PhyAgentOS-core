"""纯 Python 算法自检；没有下载模型、调用 API 或执行训练。

两层单头因果注意力/RMSNorm/RoPE/残差前馈的玩具网络，验证共享树
与独立路径的前向及有限差分导数一致性。它不验证 Qwen/HF/CUDA 实现。
"""
import copy
import json
import math
import random
from pathlib import Path

D = 4
LAYERS = 2
RNG = random.Random(17)


def matrix():
    return [[RNG.uniform(-0.6, 0.6) for _ in range(D)] for _ in range(D)]


PARAMS = [{name: matrix() for name in ('q', 'k', 'v', 'o', 'f1', 'f2')}
          for _ in range(LAYERS)]
HEAD = [0.23, -0.31, 0.41, 0.17]
DATA = [
    {'id': 's0', 'tokens': [2, 4, 6], 'questions': [
        {'id': 'q0', 'tokens': [8, 10], 'candidates': [
            {'id': 'a', 'tokens': [12, 14]},
            {'id': 'b', 'tokens': [16]},
            {'id': 'c', 'tokens': [18, 20]}]},
        {'id': 'q1', 'tokens': [22], 'candidates': [
            {'id': 'a', 'tokens': [24]},
            {'id': 'b', 'tokens': [26, 28]}]}]},
    {'id': 's1', 'tokens': [30, 32], 'questions': [
        {'id': 'q0', 'tokens': [34, 36], 'candidates': [
            {'id': 'a', 'tokens': [38]},
            {'id': 'b', 'tokens': [40, 42]}]}]},
]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def linear(x, w):
    return [dot(row, x) for row in w]


def norm(x):
    scale = math.sqrt(sum(v * v for v in x) / len(x) + 1e-6)
    return [v / scale for v in x]


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def rope(x, pos):
    result = []
    for i in range(0, D, 2):
        angle = pos / (10000 ** (i / D))
        c, s = math.cos(angle), math.sin(angle)
        result.extend([x[i] * c - x[i+1] * s, x[i] * s + x[i+1] * c])
    return result


def softmax(xs):
    pivot = max(xs)
    values = [math.exp(x - pivot) for x in xs]
    total = sum(values)
    return [v / total for v in values]


def run(nodes, params):
    hidden = [[math.sin(n['token'] * (i + 1) * 0.31) for i in range(D)]
              for n in nodes]
    for layer in params:
        normalized = [norm(h) for h in hidden]
        qs = [rope(linear(h, layer['q']), n['pos']) for h, n in zip(normalized, nodes)]
        ks = [rope(linear(h, layer['k']), n['pos']) for h, n in zip(normalized, nodes)]
        vs = [linear(h, layer['v']) for h in normalized]
        output = []
        for i, node in enumerate(nodes):
            visible = node['visible']
            weights = softmax([dot(qs[i], ks[j]) / math.sqrt(D) for j in visible])
            attended = [sum(w * vs[j][d] for w, j in zip(weights, visible))
                        for d in range(D)]
            residual = add(hidden[i], linear(attended, layer['o']))
            f = linear(norm(residual), layer['f1'])
            f = [x / (1 + math.exp(-x)) for x in f]
            output.append(add(residual, linear(f, layer['f2'])))
        hidden = output
    return [dot(norm(h), HEAD) for h in hidden]


def pack_tree(data):
    nodes, leaves = [], {}

    def append_segment(tokens, ancestors):
        path = list(ancestors)
        for token in tokens:
            index = len(nodes)
            nodes.append({'token': token, 'pos': len(path), 'visible': path + [index]})
            path.append(index)
        return path

    for state in data:
        state_path = append_segment(state['tokens'], [])
        for question in state['questions']:
            question_path = append_segment(question['tokens'], state_path)
            for candidate in question['candidates']:
                path = append_segment(candidate['tokens'] + [99], question_path)
                leaves[(state['id'], question['id'], candidate['id'])] = path[-1]
    return nodes, leaves


def tree_scores(data, params, wrong_mask=False, wrong_positions=False):
    nodes, leaves = pack_tree(data)
    for i, node in enumerate(nodes):
        if wrong_mask:
            node['visible'] = list(range(i + 1))
        if wrong_positions:
            node['pos'] = i
    output = run(nodes, params)
    return {key: output[index] for key, index in leaves.items()}


def independent_scores(data, params):
    result = {}
    for state in data:
        for question in state['questions']:
            for candidate in question['candidates']:
                tokens = state['tokens'] + question['tokens'] + candidate['tokens'] + [99]
                nodes = [{'token': token, 'pos': i, 'visible': list(range(i + 1))}
                         for i, token in enumerate(tokens)]
                result[(state['id'], question['id'], candidate['id'])] = run(nodes, params)[-1]
    return result


def difference(a, b):
    return max(abs(a[key] - b[key]) for key in a)


def objective(scores):
    groups = {}
    for key, value in sorted(scores.items()):
        groups.setdefault(key[:2], []).append(value)
    return sum(-math.log(softmax(values)[0]) for values in groups.values()) / len(groups)


def derivative(fn, parameter, delta=1e-5):
    layer, name, row, col = parameter
    positive, negative = copy.deepcopy(PARAMS), copy.deepcopy(PARAMS)
    positive[layer][name][row][col] += delta
    negative[layer][name][row][col] -= delta
    return (objective(fn(DATA, positive)) - objective(fn(DATA, negative))) / (2 * delta)


def main():
    reference = independent_scores(DATA, PARAMS)
    packed = tree_scores(DATA, PARAMS)
    reordered = copy.deepcopy(DATA)[::-1]
    for state in reordered:
        state['questions'].reverse()
        for question in state['questions']:
            question['candidates'].reverse()
    changed = copy.deepcopy(DATA)
    changed[0]['questions'][1]['tokens'] = [103, 107, 109]
    changed[1]['tokens'] = [113, 127]
    changed_scores = tree_scores(changed, PARAMS)
    unaffected = [key for key in packed if key[:2] == ('s0', 'q0')]
    tested_params = [(layer, name, 0, 1)
                     for layer in range(LAYERS) for name in ('q', 'k', 'v', 'o', 'f1', 'f2')]
    grad_error = max(abs(derivative(tree_scores, key) - derivative(independent_scores, key))
                     for key in tested_params)
    result = {
        'kind': 'pure_python_toy_attention_not_training',
        'layers': LAYERS, 'hidden_size': D, 'dropout': 0,
        'forward_max_abs_error': difference(reference, packed),
        'finite_difference_parameter_checks': len(tested_params),
        'finite_difference_derivative_max_abs_error': grad_error,
        'reorder_max_abs_error': difference(packed, tree_scores(reordered, PARAMS)),
        'unrelated_question_and_state_mutation_max_abs_error': max(
            abs(packed[key] - changed_scores[key]) for key in unaffected),
        'wrong_global_causal_mask_detected_error': difference(
            packed, tree_scores(DATA, PARAMS, wrong_mask=True)),
        'wrong_global_rope_positions_detected_error': difference(
            packed, tree_scores(DATA, PARAMS, wrong_positions=True)),
        'limits': '玩具网络前向与数值导数；不是Qwen、自动微分、混合精度或GPU吞吐验证。',
    }
    assert result['forward_max_abs_error'] < 1e-12
    assert result['finite_difference_derivative_max_abs_error'] < 1e-8
    assert result['reorder_max_abs_error'] < 1e-12
    assert result['unrelated_question_and_state_mutation_max_abs_error'] < 1e-12
    assert result['wrong_global_causal_mask_detected_error'] > 1e-5
    assert result['wrong_global_rope_positions_detected_error'] > 1e-5
    path = Path(__file__).resolve().parents[1] / 'research' / 'tree_attention_check.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
