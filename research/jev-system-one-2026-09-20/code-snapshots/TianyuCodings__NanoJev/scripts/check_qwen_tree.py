#!/usr/bin/env python3
"""Check a tiny random Qwen3 shared-prefix tree against independent token paths.

No pretrained weights, datasets, training updates, network calls, or timing claims.
Run only on the explicitly assigned physical CUDA device 7.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

import torch
import torch.nn.functional as F
import transformers
from transformers import Qwen3Config, Qwen3Model


SEED = 1729
READOUT = 3


def fixture():
    return [
        {"id": "s0", "tokens": [5, 6, 7], "questions": [
            {"id": "q0", "tokens": [31, 32], "candidates": [
                {"id": "c0", "tokens": [51, 52]},
                {"id": "c1", "tokens": [53]},
                {"id": "c2", "tokens": [54, 55, 56]}]},
            {"id": "q1", "tokens": [33], "candidates": [
                {"id": "c0", "tokens": [57, 58]},
                {"id": "c1", "tokens": [59]}]}]},
        {"id": "s1", "tokens": [17, 18], "questions": [
            {"id": "q0", "tokens": [34, 35, 36], "candidates": [
                {"id": "c0", "tokens": [61]},
                {"id": "c1", "tokens": [62, 63]}]},
            {"id": "q1", "tokens": [37, 38], "candidates": [
                {"id": "c0", "tokens": [64, 65, 66]},
                {"id": "c1", "tokens": [67]}]}]},
    ]


def token_paths(states):
    return {
        (s["id"], q["id"], c["id"]): s["tokens"] + q["tokens"] + c["tokens"] + [READOUT]
        for s in states for q in s["questions"] for c in q["candidates"]
    }


def make_tree(states, device, dtype, *, wrong_mask=False, wrong_positions=False):
    ids, positions, node_for_token, offsets = [], [], [], []
    nodes, leaves = [], {}

    def add(parent, tokens):
        node_id = len(nodes)
        ancestors = set() if parent is None else nodes[parent]["ancestors"] | {parent}
        depth = 0 if parent is None else nodes[parent]["depth"] + nodes[parent]["length"]
        start = len(ids)
        nodes.append({"ancestors": ancestors, "depth": depth, "length": len(tokens)})
        ids.extend(tokens)
        positions.extend(range(depth, depth + len(tokens)))
        node_for_token.extend([node_id] * len(tokens))
        offsets.extend(range(len(tokens)))
        return node_id, start + len(tokens) - 1

    for state in states:
        sn, _ = add(None, state["tokens"])
        for question in state["questions"]:
            qn, _ = add(sn, question["tokens"])
            for candidate in question["candidates"]:
                _, end = add(qn, candidate["tokens"] + [READOUT])
                leaves[(state["id"], question["id"], candidate["id"])] = end

    n = len(ids)
    allow = torch.tensor([
        [node_for_token[k] in nodes[node_for_token[q]]["ancestors"] or
         (node_for_token[k] == node_for_token[q] and offsets[k] <= offsets[q])
         for k in range(n)] for q in range(n)
    ], dtype=torch.bool, device=device)
    if wrong_mask:
        allow = torch.ones_like(allow).tril()
    if wrong_positions:
        positions = list(range(n))
    mask = torch.zeros((1, 1, n, n), dtype=dtype, device=device)
    mask.masked_fill_(~allow[None, None], float("-inf"))
    keys = sorted(leaves)
    return {
        "input_ids": torch.tensor([ids], dtype=torch.long, device=device),
        "position_ids": torch.tensor([positions], dtype=torch.long, device=device),
        "attention_mask": mask,
        "use_cache": False,
    }, keys, torch.tensor([leaves[k] for k in keys], device=device), n


def make_flat(states, device, dtype):
    paths = token_paths(states)
    keys = sorted(paths)
    lengths = [len(paths[k]) for k in keys]
    width = max(lengths)
    ids, pos = [], []
    allow = torch.zeros((len(keys), width, width), dtype=torch.bool, device=device)
    for row, key in enumerate(keys):
        length = lengths[row]
        ids.append(paths[key] + [0] * (width - length))
        pos.append(list(range(length)) + [0] * (width - length))
        allow[row, :length, :length] = torch.ones(
            length, length, dtype=torch.bool, device=device
        ).tril()
        # Padding queries have only a self-loop; their outputs are never read.
        for pad in range(length, width):
            allow[row, pad, pad] = True
    mask = torch.zeros((len(keys), 1, width, width), dtype=dtype, device=device)
    mask.masked_fill_(~allow[:, None], float("-inf"))
    return {
        "input_ids": torch.tensor(ids, dtype=torch.long, device=device),
        "position_ids": torch.tensor(pos, dtype=torch.long, device=device),
        "attention_mask": mask,
        "use_cache": False,
    }, keys, torch.tensor(lengths, device=device) - 1, sum(lengths)


class Scorer(torch.nn.Module):
    def __init__(self):
        super().__init__()
        config = Qwen3Config(
            vocab_size=128, hidden_size=64, intermediate_size=128,
            num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2,
            head_dim=16, max_position_embeddings=128, attention_dropout=0.0,
            use_sliding_window=False, layer_types=["full_attention"] * 2,
            use_cache=False, pad_token_id=0, bos_token_id=1, eos_token_id=2,
            tie_word_embeddings=False,
        )
        config._attn_implementation = "eager"
        self.backbone = Qwen3Model(config)
        self.head = torch.nn.Linear(64, 1, bias=False)


def leaf_forward(model, states, tree=True, **kwargs):
    parameter = next(model.parameters())
    builder = make_tree if tree else make_flat
    inputs, keys, leaf_idx, tokens = builder(states, parameter.device, parameter.dtype, **kwargs)
    hidden = model.backbone(**inputs).last_hidden_state
    leaf = hidden[0, leaf_idx] if tree else hidden[torch.arange(len(keys), device=hidden.device), leaf_idx]
    logits = model.head(leaf).squeeze(-1).float()
    return keys, leaf, logits, tokens


def decision_loss(keys, logits):
    groups = sorted({key[:2] for key in keys})
    losses = []
    for group_index, group in enumerate(groups):
        indices = [i for i, key in enumerate(keys) if key[:2] == group]
        # Fixed targets derived only from semantic group order, not packing order.
        target = torch.tensor([group_index % len(indices)], device=logits.device)
        losses.append(F.cross_entropy(logits[indices][None], target))
    return torch.stack(losses).mean()


def metrics(a, b):
    a, b = a.detach().double().cpu(), b.detach().double().cpu()
    delta = a - b
    return {
        "max_abs": float(delta.abs().max()),
        "rms_abs": float(delta.square().mean().sqrt()),
        "relative_l2": float(delta.norm() / a.norm().clamp_min(1e-30)),
        "all_finite": bool(torch.isfinite(a).all() and torch.isfinite(b).all()),
    }


def snapshot(model, states, tree):
    model.zero_grad(set_to_none=True)
    keys, leaf, logits, tokens = leaf_forward(model, states, tree)
    loss = decision_loss(keys, logits)
    loss.backward()
    grads = {}
    missing = []
    for name, parameter in model.named_parameters():
        if parameter.grad is None:
            missing.append(name)
        else:
            grads[name] = parameter.grad.detach().float().cpu().clone()
    return {"keys": keys, "leaf": leaf.detach().float().cpu(),
            "logits": logits.detach().cpu(), "loss": float(loss.detach()),
            "grads": grads, "missing_grads": missing, "tokens": tokens}


def run_dtype(master, dtype):
    model = copy.deepcopy(master).to(device="cuda:0", dtype=dtype).eval()
    states = fixture()
    flat = snapshot(model, states, False)
    tree = snapshot(model, states, True)
    assert flat["keys"] == tree["keys"]
    assert not flat["missing_grads"] and not tree["missing_grads"], "Missing parameter gradients"
    assert flat["grads"].keys() == tree["grads"].keys()
    per_parameter = {name: metrics(flat["grads"][name], tree["grads"][name])
                     for name in flat["grads"]}
    gradient_global = metrics(
        torch.cat([g.flatten() for g in flat["grads"].values()]),
        torch.cat([g.flatten() for g in tree["grads"].values()]),
    )
    report = {
        "dtype": str(dtype), "leaf_hidden": metrics(flat["leaf"], tree["leaf"]),
        "logits": metrics(flat["logits"], tree["logits"]),
        "loss_flat": flat["loss"], "loss_tree": tree["loss"],
        "loss_abs_difference": abs(flat["loss"] - tree["loss"]),
        "gradients_global": gradient_global,
        "gradient_parameter_count": len(per_parameter),
        "gradient_element_count": sum(g.numel() for g in flat["grads"].values()),
        "per_parameter_gradients": per_parameter,
        "path_tokens": flat["tokens"], "tree_tokens": tree["tokens"],
        "leaves": len(tree["keys"]),
    }
    with torch.no_grad():
        reordered = copy.deepcopy(states)[::-1]
        for state in reordered:
            state["questions"].reverse()
            for question in state["questions"]:
                question["candidates"].reverse()
        keys, changed, _, _ = leaf_forward(model, reordered)
        assert keys == tree["keys"]
        report["reordering"] = metrics(tree["leaf"], changed)

        other_state = copy.deepcopy(states)
        other_state[1]["tokens"] = [87, 88]
        keys, changed, _, _ = leaf_forward(model, other_state)
        keep = [i for i, key in enumerate(keys) if key[0] == "s0"]
        mutated = [i for i, key in enumerate(keys) if key[0] == "s1"]
        report["cross_state_isolation"] = metrics(tree["leaf"][keep], changed[keep])
        report["mutated_state_response"] = metrics(tree["leaf"][mutated], changed[mutated])

        sibling = copy.deepcopy(states)
        sibling[0]["questions"][0]["candidates"][1]["tokens"] = [89]
        keys, changed, _, _ = leaf_forward(model, sibling)
        keep = [i for i, key in enumerate(keys) if key != ("s0", "q0", "c1")]
        report["candidate_branch_isolation"] = metrics(tree["leaf"][keep], changed[keep])

        _, changed, _, _ = leaf_forward(model, states, wrong_mask=True)
        report["negative_control_plain_causal_mask"] = metrics(tree["leaf"], changed)
        _, changed, _, _ = leaf_forward(model, states, wrong_positions=True)
        report["negative_control_packed_positions"] = metrics(tree["leaf"], changed)

    # FP32 thresholds are declared implementation acceptance checks.
    # BF16 is measured, not asserted to preserve an exact FP32 function.
    if dtype == torch.float32:
        thresholds = {"hidden_max_abs": 3e-5, "loss_abs": 2e-6,
                      "grad_max_abs": 5e-5, "grad_relative_l2": 1e-4,
                      "isolation_max_abs": 3e-5, "negative_control_min_abs": 1e-4}
        report["acceptance_thresholds"] = thresholds
        report["checks"] = {
            "hidden_equivalence": report["leaf_hidden"]["max_abs"] <= thresholds["hidden_max_abs"],
            "loss_equivalence": report["loss_abs_difference"] <= thresholds["loss_abs"],
            "all_parameter_gradient_equivalence": (
                gradient_global["max_abs"] <= thresholds["grad_max_abs"] and
                gradient_global["relative_l2"] <= thresholds["grad_relative_l2"] and
                all(m["all_finite"] for m in per_parameter.values())),
            "reordering": report["reordering"]["max_abs"] <= thresholds["isolation_max_abs"],
            "cross_state_isolation": report["cross_state_isolation"]["max_abs"] <= thresholds["isolation_max_abs"],
            "candidate_branch_isolation": report["candidate_branch_isolation"]["max_abs"] <= thresholds["isolation_max_abs"],
            "mutation_is_nontrivial": report["mutated_state_response"]["max_abs"] > thresholds["negative_control_min_abs"],
            "wrong_mask_detected": report["negative_control_plain_causal_mask"]["max_abs"] > thresholds["negative_control_min_abs"],
            "wrong_positions_detected": report["negative_control_packed_positions"]["max_abs"] > thresholds["negative_control_min_abs"],
        }
        report["passed"] = all(report["checks"].values())
    else:
        report["status"] = "measured_only_no_exact_equivalence_claim"
    del model
    torch.cuda.empty_cache()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--disable-native-triton", action="store_true",
                        help="Use the installed torch 2.14 process-local native DSL fallback; no package edits")
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "7":
        raise RuntimeError("This check is authorized only with CUDA_VISIBLE_DEVICES=7")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("Expected exactly one visible, usable CUDA device")
    if args.disable_native_triton:
        # Optional torch 2.14 eager overrides require Python.h for Triton driver JIT.
        # This fixed-version internal API restores ordinary ATen ops in this process.
        from torch._native import triton_utils
        triton_utils.deregister_op_overrides()
    torch.manual_seed(SEED)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    master = Scorer().eval()
    paths = token_paths(fixture())
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report = {
        "schema": "openjev-qwen3-tree-check-v1",
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "script_sha256": script_hash,
        "scope": "random tiny Qwen3Model, no pretrained weights, no optimizer updates, not a performance benchmark",
        "environment": {"torch": torch.__version__, "transformers": transformers.__version__,
                        "cuda_build": torch.version.cuda, "gpu": torch.cuda.get_device_name(0),
                        "physical_gpu": 7, "visible_gpu_count": torch.cuda.device_count(),
                        "bf16_supported": torch.cuda.is_bf16_supported(), "tf32": False,
                        "native_triton_overrides_disabled": args.disable_native_triton},
        "configuration": master.backbone.config.to_dict(),
        "seed": SEED,
        "fixture_paths": [{"key": list(k), "token_ids": v} for k, v in sorted(paths.items())],
        "float32": run_dtype(master, torch.float32),
    }
    if torch.cuda.is_bf16_supported():
        report["bfloat16"] = run_dtype(master, torch.bfloat16)
    report["passed"] = report["float32"]["passed"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    compact = {"passed": report["passed"], "output": str(args.output)}
    for name in ["float32", "bfloat16"]:
        if name in report:
            r = report[name]
            compact[name] = {"hidden_max_abs": r["leaf_hidden"]["max_abs"],
                             "loss_abs": r["loss_abs_difference"],
                             "gradient_max_abs": r["gradients_global"]["max_abs"],
                             "gradient_relative_l2": r["gradients_global"]["relative_l2"]}
    print(json.dumps(compact))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
