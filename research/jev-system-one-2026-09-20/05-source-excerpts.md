# 核心代码摘录（原样、带本地行号）

代码按原许可证保留；不在这里执行。完整源码在 code-snapshots。

## jaredpalmer/kev — branch_mask_batch
来源：https://github.com/jaredpalmer/kev

文件：`kev/model.py`，L75–L101（函数完整终点 L101）。
```text
  75  def branch_mask_batch(segs, device, dtype=torch.float32, opts=None):
  76      """Batched block-causal mask, additive [B,1,L,L], right-padded to the longest sequence.
  77  
  78      Padded key positions are masked for every query; padded query rows keep the diagonal so no row is fully
  79      masked (finfo.min, not -inf, so softmax stays finite either way). Real tokens never see pads because pads sit
  80      after them (causal) and belong to no segment (-1).
  81  
  82      opts (option isolation): within a question, an option-span token may attend to state, the instruction, and its own
  83      span only; <decide> attends to everything in its question. Instruction tokens never see option spans (causal)."""
  84      L = max(len(s) for s in segs)
  85      s = torch.full((len(segs), L), -1, device=device)
  86      for b, seg in enumerate(segs):
  87          s[b, : len(seg)] = torch.tensor(seg, device=device)
  88      causal = torch.tril(torch.ones(L, L, dtype=torch.bool, device=device))
  89      same = (s[:, None, :] == s[:, :, None]) | (s[:, None, :] == 0)
  90      valid_key = (s != -1)[:, None, :]
  91      allow = causal[None] & same & valid_key
  92      if opts is not None:
  93          o = torch.full((len(segs), L), OPT_NONE, device=device)
  94          for b, op in enumerate(opts):
  95              o[b, : len(op)] = torch.tensor(op, device=device)
  96          key_is_option = (o[:, None, :] >= 0)
  97          query_is_decide = (o[:, :, None] == OPT_DECIDE)
  98          same_option = o[:, None, :] == o[:, :, None]
  99          allow = allow & (~key_is_option | query_is_decide | same_option)
 100      allow = allow | torch.eye(L, dtype=torch.bool, device=device)[None]
 101      return torch.zeros(len(segs), L, L, dtype=dtype, device=device).masked_fill(~allow, torch.finfo(dtype).min)[:, None]
```

## jaredpalmer/kev — PointerHead
来源：https://github.com/jaredpalmer/kev

文件：`kev/model.py`，L104–L112（函数完整终点 L112）。
```text
 104  class PointerHead(nn.Module):
 105      def __init__(self, d, dp=256):
 106          """dp = pointer dimension (head capacity knob)."""
 107          super().__init__()
 108          self.q, self.k = nn.Linear(d, dp), nn.Linear(d, dp)
 109          self.scale = 1 / math.sqrt(dp)
 110  
 111      def forward(self, h_decide, h_opts):  # [d], [K,d] -> logits [K]
 112          return (self.k(h_opts) @ self.q(h_decide)) * self.scale
```

## jaredpalmer/kev — question_loss
来源：https://github.com/jaredpalmer/kev

文件：`kev/train.py`，L23–L31（函数完整终点 L31）。
```text
  23  def question_loss(z, q, dev, ord_w):
  24      """Cross-entropy, optionally plus the normalized ranked probability score for ordered levels."""
  25      y = torch.tensor([q["label"]], device=dev)
  26      loss = F.cross_entropy(z[None], y)
  27      if q["qtype"] == "score" and ord_w > 0:
  28          p = F.softmax(z, -1)
  29          observed_cdf = (torch.arange(len(p) - 1, device=dev) >= q["label"]).to(p.dtype)
  30          loss = loss + ord_w * (p.cumsum(-1)[:-1] - observed_cdf).square().mean()
  31      return loss
```

## zhengxuyu/litjev — concentration
来源：https://github.com/zhengxuyu/litjev

文件：`src/litjev/decision.py`，L67–L72（函数完整终点 L72）。
```text
  67  def concentration(probabilities):
  68      """LitJev statistic, not a reproduction of Jev's unpublished formula."""
  69      count = len(probabilities)
  70      if count == 1:
  71          return 1.0
  72      return float(np.clip((count * sum(p * p for p in probabilities) - 1) / (count - 1), 0, 1))
```

## ekzhang/openjev-sglang — parse_generation
来源：https://github.com/ekzhang/openjev-sglang

文件：`src/openjev/backend.py`，L93–L123（函数完整终点 L123）。
```text
  93  def parse_generation(data: dict, label_ids: list[int]) -> Generation:
  94      meta = data["meta_info"]
  95      reason = meta.get("finish_reason") or {}
  96      if reason.get("type") == "abort":
  97          raise ValueError("generation was aborted")
  98      output_tokens = meta["completion_tokens"]
  99      if output_tokens != 1:
 100          raise ValueError(f"expected exactly one output token, got {output_tokens}")
 101      logprobs = []
 102      if label_ids:
 103          positions = meta["output_token_ids_logprobs"]
 104          if len(positions) != 1:
 105              raise ValueError("expected one position of selected-token logprobs")
 106          by_id = {}
 107          for entry in positions[0]:
 108              value, token_id = entry[:2]
 109              if token_id in by_id:
 110                  raise ValueError("duplicate token ID in logprobs")
 111              if value is None or math.isnan(value) or value == math.inf:
 112                  raise ValueError("non-numeric or invalid logprob")
 113              by_id[token_id] = float(value)
 114          logprobs = [by_id[token_id] for token_id in label_ids]
 115          if not any(math.isfinite(value) for value in logprobs):
 116              raise ValueError("all label probabilities are zero")
 117      return Generation(
 118          logprobs=logprobs,
 119          input_tokens=int(meta["prompt_tokens"]),
 120          output_tokens=int(output_tokens),
 121          # The Rust frontend currently omits this field even when radix hits occur.
 122          cached_tokens=int(meta["cached_tokens"]) if meta.get("cached_tokens") is not None else None,
 123      )
```

## zeredy879/minojev — DecisionHead
来源：https://github.com/zeredy879/minojev

文件：`src/minojev/heads.py`，L43–L104（函数完整终点 L104）。
```text
  43  class DecisionHead(nn.Module):
  44      def __init__(self, hidden_size: int, attention_dim: int = 128, num_heads: int = 4) -> None:
  45          super().__init__()
  46          self.norm = nn.LayerNorm(hidden_size)
  47          self.scalar = nn.Linear(hidden_size, 1)
  48          self.set_input = nn.Linear(hidden_size + 1, attention_dim)
  49          self.set_attention = nn.MultiheadAttention(attention_dim, num_heads, dropout=0.0, batch_first=True)
  50          self.set_output = nn.Linear(attention_dim, 1)
  51          nn.init.normal_(self.scalar.weight, std=0.02)
  52          nn.init.zeros_(self.scalar.bias)
  53          nn.init.zeros_(self.set_output.weight)
  54          nn.init.zeros_(self.set_output.bias)
  55  
  56      def forward(self, hidden: torch.Tensor, groups, group_kinds: list[str]) -> list[GroupOutput]:
  57          normalized = self.norm(hidden)
  58          base = self.scalar(normalized).squeeze(-1).float()
  59          scores = base
  60          comparative = [index for index, kind in enumerate(group_kinds) if kind in (CHOICE, BOOLEAN)]
  61          if comparative:
  62              delta = self._set_correction(normalized, groups, comparative)
  63              scores = base.index_add(0, self._choice_path_indices(groups, comparative), delta)
  64          outputs = []
  65          for group, kind in zip(groups, group_kinds):
  66              logits = scores[group.path_indices]
  67              if kind == BOOLEAN:
  68                  probabilities = torch.softmax(logits, dim=-1)
  69                  outputs.append(GroupOutput(probabilities=probabilities, logits=logits))
  70              elif kind == SCORE:
  71                  probabilities = torch.softmax(logits, dim=-1)
  72                  indices = torch.arange(len(group.path_indices), device=hidden.device, dtype=probabilities.dtype)
  73                  expected = torch.sum(indices * probabilities)
  74                  outputs.append(GroupOutput(probabilities=probabilities, logits=logits, expected=expected))
  75              else:
  76                  probabilities = torch.softmax(logits, dim=-1)
  77                  outputs.append(GroupOutput(probabilities=probabilities, logits=logits))
  78          return outputs
  79  
  80      def _choice_path_indices(self, groups, choice_rows: list[int]) -> torch.Tensor:
  81          flat = []
  82          for row in choice_rows:
  83              flat.extend(groups[row].path_indices)
  84          return torch.tensor(flat, dtype=torch.long, device=self.scalar.weight.device)
  85  
  86      def _set_correction(self, hidden: torch.Tensor, groups, choice_rows: list[int]) -> torch.Tensor:
  87          device = hidden.device
  88          candidates = [groups[row].path_indices for row in choice_rows]
  89          width = max(len(paths) for paths in candidates)
  90          batch = len(candidates)
  91          pooled = hidden.new_zeros((batch, width, hidden.shape[-1]))
  92          valid = torch.zeros((batch, width), dtype=torch.bool, device=device)
  93          for row, paths in enumerate(candidates):
  94              pooled[row, : len(paths)] = hidden[paths]
  95              valid[row, : len(paths)] = True
  96          count = valid.sum(-1).float()
  97          size_feature = torch.where(valid, torch.log(count)[:, None], torch.zeros_like(count)[:, None])
  98          features = self.set_input(torch.cat([pooled, size_feature.unsqueeze(-1)], dim=-1))
  99          mixed, _ = self.set_attention(features, features, features, key_padding_mask=~valid, need_weights=False)
 100          delta = self.set_output(torch.tanh(features + mixed)).squeeze(-1).float()
 101          flat = []
 102          for row, paths in enumerate(candidates):
 103              flat.extend(paths)
 104          return delta[valid]
```

## zeredy879/minojev — apply_calibration
来源：https://github.com/zeredy879/minojev

文件：`src/minojev/calibrate.py`，L44–L56（函数完整终点 L56）。
```text
  44  def apply_calibration(output: GroupOutput, kind: str, calibration: Calibration | None) -> GroupOutput:
  45      if calibration is None:
  46          return output
  47      temperature = calibration.temperature(kind)
  48      if abs(temperature - 1.0) < 1e-9:
  49          return output
  50      logits = output.logits / temperature
  51      probabilities = torch.softmax(logits, dim=-1)
  52      expected = None
  53      if kind == SCORE:
  54          indices = torch.arange(len(logits), device=logits.device, dtype=probabilities.dtype)
  55          expected = torch.sum(indices * probabilities)
  56      return GroupOutput(probabilities=probabilities, logits=logits, expected=expected)
```

## zeredy879/minojev — _fit_one
来源：https://github.com/zeredy879/minojev

文件：`src/minojev/calibrate.py`，L122–L135（函数完整终点 L135）。
```text
 122  def _fit_one(pairs: list[tuple[torch.Tensor, torch.Tensor]]) -> float:
 123      if not pairs:
 124          return 1.0
 125      low, high, steps = math.log(0.1), math.log(4.0), 64
 126      grid = [math.exp(low + index * (high - low) / (steps - 1)) for index in range(steps)]
 127      grid.append(1.0)
 128      best_temperature = 1.0
 129      best_loss = float("inf")
 130      for temperature in grid:
 131          loss = sum(_nll(logits, target, temperature) for logits, target in pairs)
 132          if loss < best_loss:
 133              best_loss = loss
 134              best_temperature = temperature
 135      return round(best_temperature, 4)
```

## logan-markewich/jeff — normalize
来源：https://github.com/logan-markewich/jeff

文件：`src/jeff/core/answers.py`，L24–L35（函数完整终点 L35）。
```text
  24  def normalize(scores: Sequence[float], temperature: float = 1.0) -> list[float]:
  25      """Normalize independent sigmoids; temperature > 1 flattens the distribution.
  26  
  27      This is score renormalization, not a calibrated posterior.
  28      """
  29      s = [max(float(x), 0.0) for x in scores]
  30      if temperature != 1.0:
  31          s = [x ** (1.0 / temperature) for x in s]
  32      total = sum(s)
  33      if total <= EPS:
  34          return [1.0 / len(s)] * len(s)
  35      return [x / total for x in s]
```

## logan-markewich/jeff — decode
来源：https://github.com/logan-markewich/jeff

文件：`src/jeff/core/answers.py`，L47–L75（函数完整终点 L75）。
```text
  47  def decode(q: Question, scores: Sequence[float], temperature: float = DEFAULT_TEMPERATURE) -> Answer:
  48      if isinstance(q, NoulQuestion):
  49          if len(scores) == 1:  # single-label mode: raw sigmoid is P(yes)
  50              p = min(max(scores[0], 0.0), 1.0)
  51              if temperature != 1.0:
  52                  p = normalize([p, 1.0 - p], temperature)[0]
  53              return NoulAnswer(noul=_r(p))
  54          p = normalize([scores[0], scores[1]], temperature)[0]
  55          return NoulAnswer(noul=_r(p))
  56      if isinstance(q, ChoiceQuestion):
  57          keys = [k for k, _ in q.options()]
  58          probs = normalize(scores, temperature)
  59          best = max(range(len(keys)), key=lambda i: probs[i])
  60          return ChoiceAnswer(
  61              choice=keys[best],
  62              confidence=confidence(probs),
  63              probabilities={k: _r(p) for k, p in zip(keys, probs)},
  64          )
  65      if isinstance(q, ScoreQuestion):
  66          probs = normalize(scores, temperature)
  67          # Tempering increases score MAE; keep the raw expectation (matches probabilities only at T=1).
  68          score = sum(i * p for i, p in enumerate(normalize(scores)))
  69          return ScoreAnswer(
  70              score=_r(score),
  71              confidence=confidence(probs),
  72              legend=q.legend(),
  73              probabilities={str(i): _r(p) for i, p in enumerate(probs)},
  74          )
  75      raise TypeError(type(q))
```

## wfzyx/von — compute_marker_rlcd_loss
来源：https://github.com/wfzyx/von

文件：`training/train_option_marker.py`，L83–L114（函数完整终点 L114）。
```text
  83  def compute_marker_rlcd_loss(
  84      batch_logits: List[torch.Tensor],
  85      labels: torch.Tensor,
  86      brier_weight: float = 0.5,
  87  ) -> Tuple[torch.Tensor, torch.Tensor, float]:
  88      ce_losses = []
  89      brier_losses = []
  90      correct = 0
  91      total = len(labels)
  92  
  93      for i, logits in enumerate(batch_logits):
  94          target_idx = labels[i].item()
  95          probs = torch.softmax(logits, dim=-1)
  96  
  97          safe_target = min(target_idx, probs.size(0) - 1)
  98          ce = -torch.log(probs[safe_target] + 1e-8)
  99          ce_losses.append(ce)
 100  
 101          one_hot = torch.zeros_like(probs)
 102          one_hot[safe_target] = 1.0
 103          brier = torch.sum((probs - one_hot) ** 2)
 104          brier_losses.append(brier)
 105  
 106          if torch.argmax(probs).item() == safe_target:
 107              correct += 1
 108  
 109      mean_ce = torch.stack(ce_losses).mean()
 110      mean_brier = torch.stack(brier_losses).mean()
 111      total_loss = mean_ce + brier_weight * mean_brier
 112      accuracy = correct / max(total, 1)
 113  
 114      return total_loss, mean_ce, accuracy
```

## rupeshpoojary9/poorjev — fit_abstention_threshold
来源：https://github.com/rupeshpoojary9/poorjev

文件：`src/poorjev/calibration.py`，L126–L148（函数完整终点 L148）。
```text
 126  def fit_abstention_threshold(records: list[DecisionRecord], target_risk: float = 0.1):
 127      """Pick the lowest confidence threshold that keeps error rate on accepted
 128      decisions at or below ``target_risk`` on this set.
 129  
 130      Returns (threshold, coverage, realized_risk). Accept a decision at inference
 131      when its confidence >= threshold; otherwise abstain and escalate.
 132      """
 133      if not records:
 134          return 1.0, 0.0, 0.0
 135      ordered = sorted(records, key=lambda r: r.confidence, reverse=True)
 136      n = len(ordered)
 137      best = None  # (threshold, coverage, risk) with the largest coverage under risk
 138      errors = 0
 139      for i, r in enumerate(ordered, start=1):
 140          if not r.correct:
 141              errors += 1
 142          risk = errors / i
 143          if risk <= target_risk:
 144              best = (r.confidence, i / n, risk)
 145      if best is None:
 146          # even the single most-confident decision is wrong; abstain on everything
 147          return 1.01, 0.0, 0.0
 148      return best
```

## TheoLeeCJ/SemIf — score_shared
来源：https://github.com/TheoLeeCJ/SemIf

文件：`src/semif_phase1/shared.py`，L53–L146（函数完整终点 L146）。
```text
  53  def score_shared(model, tokenizer, rows: list[dict], metadata: dict, max_tokens: int = 4096):
  54      """Return all option distributions together after one state prefill."""
  55      import torch
  56  
  57      if not rows or any(row["state"] != rows[0]["state"] for row in rows[1:]):
  58          raise ValueError("Shared scoring requires one nonempty exact state")
  59      if len({row["id"] for row in rows}) != len(rows):
  60          raise ValueError("Decision IDs must be unique")
  61      started = time.perf_counter()
  62      encoded = [encode_prompt(tokenizer, row, max_tokens) for row in rows]
  63      prefix = _state_prefix(tokenizer, rows[0]["state"])
  64      if not prefix or any(ids[: len(prefix)] != prefix or len(ids) <= len(prefix) for ids, _, _ in encoded):
  65          raise ValueError("The fixed state prefix does not match every full prompt")
  66      pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
  67      if pad is None:
  68          raise ValueError("Tokenizer requires a padding or EOS token")
  69      layout, ends = _suffix_layout([ids[len(prefix) :] for ids, _, _ in encoded], len(prefix), pad)
  70      selected_positions = sorted(set(ends))
  71      encode_seconds = time.perf_counter() - started
  72      device = next(model.parameters()).device
  73      sync = lambda: torch.cuda.synchronize(device) if device.type == "cuda" else None
  74      parameters = inspect.signature(model.forward).parameters
  75      if "logits_to_keep" not in parameters and hasattr(model, "get_base_model"):
  76          parameters = inspect.signature(model.get_base_model().forward).parameters
  77      if "logits_to_keep" not in parameters:
  78          raise RuntimeError("Model lacks selective-position logits needed by shared scoring")
  79      model.eval()
  80      with torch.inference_mode():
  81          sync()
  82          mark = time.perf_counter()
  83          output = model(
  84              input_ids=torch.tensor([prefix], dtype=torch.long, device=device),
  85              attention_mask=torch.ones((1, len(prefix)), dtype=torch.long, device=device),
  86              use_cache=True,
  87              return_dict=True,
  88              logits_to_keep=1,
  89          )
  90          cache = output.past_key_values
  91          del output
  92          sync()
  93          prefill_seconds = time.perf_counter() - mark
  94          if cache is None or cache.get_seq_length() != len(prefix):
  95              raise RuntimeError("Invalid native prefix cache")
  96          if not callable(getattr(cache, "reorder_cache", None)):
  97              raise RuntimeError("Native cache does not support duplicate branch selection")
  98          sync()
  99          mark = time.perf_counter()
 100          cache.reorder_cache(torch.zeros(len(rows), dtype=torch.long, device=device))
 101          sync()
 102          replicate_seconds = time.perf_counter() - mark
 103          inputs = {key: torch.tensor(value, dtype=torch.long, device=device) for key, value in layout.items()}
 104          sync()
 105          mark = time.perf_counter()
 106          output = model(
 107              **inputs,
 108              past_key_values=cache,
 109              use_cache=True,
 110              return_dict=True,
 111              logits_to_keep=torch.tensor(selected_positions, dtype=torch.long, device=device),
 112          )
 113          sync()
 114          suffix_seconds = time.perf_counter() - mark
 115          results = []
 116          for index, (row, (ids, slots, prompt_hash)) in enumerate(zip(rows, encoded)):
 117              vocabulary = output.logits[index, selected_positions.index(ends[index]), :].float()
 118              selected = vocabulary[slots].cpu().tolist()
 119              results.append(
 120                  {
 121                      "id": row["id"],
 122                      "option_ids": [option["id"] for option in row["options"]],
 123                      "probabilities": softmax(selected),
 124                      "option_logits": selected,
 125                      "input_tokens": len(ids),
 126                      "prompt_sha256": prompt_hash,
 127                      "prompt_version": PROMPT_VERSION,
 128                      "model": {**metadata, "serving_config": "native-state-prefix-parallel-v1"},
 129                      "readout": "native selected suffix-position logits",
 130                      "probability_status": "conditional option score; uncalibrated as decision confidence",
 131                  }
 132              )
 133          del output, cache
 134      sync()
 135      timing = {
 136          "total_seconds": time.perf_counter() - started,
 137          "encode_seconds": encode_seconds,
 138          "prefix_tokens": len(prefix),
 139          "prefill_seconds": prefill_seconds,
 140          "replicate_seconds": replicate_seconds,
 141          "suffix_forward_seconds": suffix_seconds,
 142          "batch_size": len(rows),
 143          "true_suffix_tokens": sum(len(ids) - len(prefix) for ids, _, _ in encoded),
 144          "padded_suffix_tokens": len(rows) * len(layout["input_ids"][0]),
 145      }
 146      return results, timing
```

## browser-use/jev-ultrafast — choose
来源：https://github.com/browser-use/jev-ultrafast

文件：`jev_ultrafast/model.py`，L81–L148（函数完整终点 L148）。
```text
  81  def choose(state, goal, history):
  82      elements, targets, controls = action_space(state["actions"])
  83      labels = {
  84          "CLICK": "Click an element, button, menu option, autocomplete suggestion, or calendar day.",
  85          "TYPE_TEXT": "Enter or replace text in an editable field. A small LLM will supply the value from the goal.",
  86          "SELECT": "Select an observed dropdown value.",
  87      }
  88      operations = {key: labels[key] for key in targets}
  89      operations.update({key: value["label"] for key, value in controls.items()})
  90      operations.update(DONE="Every requirement is visibly satisfied.", BLOCKED="No supported operation can progress.")
  91      questions = {
  92          "operation": {"type": "choice", "criteria": operations, "instructions": {"goal": goal, "rules": NEXT_ACTION}}
  93      }
  94      for operation, candidates in targets.items():
  95          questions[operation.lower() + "_target"] = {
  96              "type": "choice",
  97              "criteria": {
  98                  index: {
  99                      "element": f"[{index}] {a['label']}",
 100                      "current_value": a.get("current_value", a.get("value", "")),
 101                      **{k: a[k] for k in ("role", "checked", "selected", "expanded") if k in a},
 102                  }
 103                  for index, a in candidates.items()
 104              },
 105              "instructions": {"goal": goal, "operation": operation, "rules": [NEXT_ACTION, TARGET]},
 106          }
 107      body = {
 108          "model": os.environ.get("TYPESAFE_MODEL", "jev-latest"),
 109          "state": {
 110              "page": {k: state[k] for k in ("url", "title", "text")},
 111              "elements": elements,
 112              "recent_actions": [
 113                  {k: h.get(k) for k in ("action", "kind", "text", "page_changed")} for h in history[-10:]
 114              ],
 115          },
 116          "questions": questions,
 117      }
 118      started = time.perf_counter()
 119      result = post_json("https://api.typesafe.ai/v1/systemone", os.environ["TYPESAFE_API_KEY"], body)
 120      operation_answer = validate_choice(result["answers"].get("operation", {}), operations)
 121      operation = operation_answer["choice"]
 122      target = None
 123      target_answer = None
 124      probabilities = {}
 125      if operation in targets:
 126          # Unused target heads cannot cause an action. Validate the head selected by the operation.
 127          target_answer = validate_choice(result["answers"].get(operation.lower() + "_target", {}), targets[operation])
 128          target = target_answer["choice"]
 129          choice = targets[operation][target]["id"]
 130          probabilities = {a["id"]: target_answer["probabilities"][index] for index, a in targets[operation].items()}
 131      else:
 132          choice = controls[operation]["id"] if operation in controls else operation
 133          probabilities[choice] = operation_answer["probabilities"][operation]
 134      return {
 135          "choice": choice,
 136          "operation": operation,
 137          "target": target,
 138          "confidence": operation_answer["confidence"],
 139          "probabilities": probabilities,
 140          "operation_probabilities": operation_answer["probabilities"],
 141          "target_probabilities": target_answer["probabilities"] if target_answer else {},
 142          "target_confidence": target_answer["confidence"] if target_answer else None,
 143          "raw_answers": result["answers"],
 144          "model": result["model"],
 145          "usage": result.get("usage", {}),
 146          "latency_ms": round((time.perf_counter() - started) * 1000),
 147          "request": body,
 148      }
```

## sutro-sh/jev-align — select_batch
来源：https://github.com/sutro-sh/jev-align

文件：`src/jev_align/acquisition.py`，L34–L61（函数完整终点 L61）。
```text
  34  def select_batch(
  35      predictions: list[Prediction],
  36      *,
  37      batch_size: int = 5,
  38      exploration_count: int = 1,
  39      seed: int = 0,
  40  ) -> list[Acquisition]:
  41      if batch_size < 1:
  42          raise ValueError("batch_size must be positive")
  43      if not 0 <= exploration_count <= batch_size:
  44          raise ValueError("exploration_count must be between zero and batch_size")
  45      if len(predictions) < batch_size:
  46          raise ValueError("not enough unlabeled rows for an acquisition batch")
  47  
  48      ambiguous_count = batch_size - exploration_count
  49      ranked = sorted(
  50          predictions,
  51          key=lambda item: (-prediction_ambiguity(item), item.story_id),
  52      )
  53      ambiguous = ranked[:ambiguous_count]
  54      chosen = {item.story_id for item in ambiguous}
  55      remainder = [item for item in predictions if item.story_id not in chosen]
  56      rng = random.Random(seed)
  57      exploration = rng.sample(remainder, exploration_count)
  58      return [
  59          *(Acquisition(item, "ambiguous") for item in ambiguous),
  60          *(Acquisition(item, "exploration") for item in exploration),
  61      ]
```

## RomanSlack/jev-drone — decision_needed
来源：https://github.com/RomanSlack/jev-drone

文件：`tactics.py`，L91–L96（函数完整终点 L96）。
```text
  91  def decision_needed(scene):
  92      """Code decides WHEN there is a judgment worth paying for. On an empty corridor
  93      with the target in view there is nothing to decide, so we do not ask."""
  94      return (scene["nearest_obstacle_m"] < THRESHOLDS["consult_within_m"]
  95              or scene["sectors_blocked"] >= 1
  96              or (scene["target"]["unseen_for_s"] or 0.0) >= THRESHOLDS["consult_lost_s"])
```
