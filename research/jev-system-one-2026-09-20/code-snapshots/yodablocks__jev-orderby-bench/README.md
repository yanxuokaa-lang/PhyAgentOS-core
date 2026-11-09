# jev-orderby-bench

Does `ORDER BY` over a Jev probability put rows in a defensible order?
An independent measurement of TypeSafe AI's Jev (`jev-1.13.0`) on the
properties a semantic sort actually depends on: pairwise inversion rate,
Score ordinality against a graded target, and whether the probabilities
move with evidence or with wording. Calibration (ECE, Brier) is reported
too, but it is not the gate on its own: a model can be well calibrated in
aggregate and still invert the pairs a sorted page shows.

**Headline (2026-09-18): `jev-1.13.0` passes all six pre-registered gate
conditions on 360 human-labeled rows.** Boolean inversion rate 0.036;
Score ordinal inversion 0.143 against a 0.15 threshold, the weak link and
the sort key; negation asymmetry 0.016 but indistinguishable from plain
paraphrase sensitivity; underconfident in 8 of 10 bins. And the sort
key itself is coarse: probabilities come back at two decimals, 360 rows
produced 45 distinct values, and 53 rows tie at 0.99, so
`ORDER BY prob DESC LIMIT 20` returns 20 of those 53 in whatever order
the engine left them. And the integration changes the numbers: the same
rows sent through recodelabs' default 40-row batching **fail the ranking
gate** (inversion 0.171 against 0.15) that they pass one row per
request. See [Results](#results) and [Request shape](#request-shape-the-integration-changes-the-numbers).

**Headline 2 (2026-09-19): on the hard probe it fails.** Amazon ESCI, 306
human-graded query-product pairs over 30 hard shopping queries:
`jev_bool` ECE 0.242 and inversion 0.255; `jev_score` inversion 0.254
against the 4-level human grade, 0.244 inside a single query's result
list, 23 of 30 queries over the threshold; choice confidence ECE 0.279.
Negation symmetry still holds (0.023) while a plain paraphrase moves the
answer by 0.164 on average. Four of six gate conditions fail. See
[Hard probe](#hard-probe-graded-product-relevance-esci).

Run: 360 rows, 350 fresh requests, 359,013 tokens (~999/row), about $0.013.

## Where this sits

Three DuckDB integrations for Jev shipped in the week of its release:
[colliber/duckdb-jev](https://github.com/colliber/duckdb-jev),
[recodelabs/duckdb-jev](https://github.com/recodelabs/duckdb-jev) and
[Query-farm/vgi-typesafe](https://github.com/Query-farm/vgi-typesafe),
plus [pg-jev](https://github.com/realZachi/pg-jev) for Postgres. All
expose `ORDER BY` over a Jev probability; none ships a measurement of
whether that order is defensible. The vendor's
[evals](https://evals.typesafe.ai/) publish accuracy, cost and time
against labels averaged from two frontier models, and no calibration
figure. This repo is the measurement, not a fourth extension.
`harness/udf.py` is a reference for consuming the numbers at the SQL
boundary, gated on the results; use one of the extensions above for real
work, with the batch-size caveat measured below.

Jev's SDK had its first public release on 2026-09-14 and the only figure
its vendor publishes is 67.8% agreement against averaged frontier
judgments, self-run and unreproduced.
Agreement with other models is not calibration, so these are independent
numbers rather than a reproduction of that one. Every method choice is in
the repo and the run is reproducible, so disagree with the numbers by
re-running rather than by taking anyone's word for it, including mine.

[commitjev](https://github.com/yodablocks/commitjev) is a tool built on
the measured model, and it is mine too, so read it as an application of
these numbers rather than independent corroboration of them. Two results
below decide its shape: it sends one commit per request rather than
batching, because batched rows fail the ranking gate that one-per-request
passes, and it thresholds individual probabilities rather than sorting by
them, because the scale is coarse enough that a sorted page is partly
arbitrary. It also ships its own labeled cases, on the argument made here
that a thing built on Jev should say what it catches.

[jobbyjev](https://github.com/yodablocks/jobbyjev) is mine too, and is the
clearest case of a measurement here changing a design. It ranks companies for
one candidate, and it sends one request per company rather than batching them,
because the batch-size result below is the difference between passing the
ranking gate and failing it. Ranking is the whole product there, so it pays
the extra requests.

[jevq](https://github.com/yodablocks/jevq) is the other end of the same
problem, and also mine. Where this repo asks whether Jev's probabilities
can be trusted, jevq asks whether the question put to it was well formed,
by checking a question's text against the failure modes TypeSafe documents.
It needs no API call and no labelled data, so it catches a strict subset:
the mistakes visible by reading. Whether a question actually separates the
cases you care about still takes a measured run like this one.

**Reproduce:** `python3 harness/run_calibration.py` with a key. At the
published price of $0.042 per million input tokens (output is free), the
full run costs about **$0.013**. Responses are cached locally, so once
you have run it, `--analyze-only` recomputes everything for nothing.

## License

Code: MIT (see `LICENSE`). This covers the harness only, **not** the
corpus (see [Corpus licensing](#corpus-licensing)) and not Jev's outputs,
which are governed by TypeSafe AI's terms.

## Results

`model: jev-1.13.0`, question set `60658e143af92016`.

| Primitive | Metric | Value | Gate |
|---|---|---|---|
| `jev_bool` | Brier | **0.0524** | |
| | ECE (adaptive, 10 bins) | **0.0453** | ≤ 0.10 ✓ |
| | ECE (fixed-width, 10 bins) | 0.0454 | |
| | resolution | 0.1820 | > 0 ✓ |
| | AUC | 0.9637 | |
| | inversion rate | **0.0363** | ≤ 0.15 ✓ |
| | distinct values / tied pairs | 45 / **21.6%** | |
| | rows tied at the top (0.99) | **53** | |
| `jev_choice` | accuracy | 0.8754 | |
| | confidence ECE | 0.0769 | ≤ 0.10 ✓ |
| `jev_score` | ordinal inversion | **0.1433** | ≤ 0.15 ✓ |
| | binary inversion | 0.0370 | |
| | distinct values / tied pairs | 88 / 15.0% | |
| | rows tied at the top (3.0) | 54 | |
| Invariant | negation \|P(q)+P(¬q)−1\| | 0.0161 | ≤ 0.15 ✓ |
| | rubric mirror error | 0.0223 (0.74% of scale) | |

Per probe (`jev_bool` ECE): medical 0.030, forsale 0.042, space 0.062.

### Four things the headline number hides

**1. The negation result is not about negation.** The jaggedness page
disclaims `P(q) = 1 - P(not q)`, and the identity in fact holds well:
median violation 0.010, only 2.8% of rows above 0.10. But the paraphrase
control measures 0.0159 against negation's 0.0161, a ratio of **1.01x**.
A semantically equivalent rewording disagrees just as much as a negation
does. So this is general wording stability, not a negation-specific
property, and the negation figure carries no information beyond the
control. Publishing it alone would have overclaimed. This is precisely
what the control was added to catch, and it fired.

**2. The model is systematically underconfident.** 8 of 10 reliability
bins sit above the diagonal, mean signed gap **+0.042**. That one-
directional consistency rules out noise. It is the benign direction for
ranking (ordering is preserved), but it means a `WHERE prob > 0.9`
threshold is stricter than it reads: the true rate at a predicted 0.855
is 0.914. Calibrate thresholds against this table, not against intuition.
MCE 0.126 is ~3x ECE, and the two mid-range bins (predicted 0.029 and
0.188) contribute over half the total error, so the miscalibration is
concentrated where the model is genuinely uncertain.

**3. `jev_score` is the weak link, and it is the sort key.** Ordinal
inversion 0.1433 against a 0.15 threshold is the only condition that
nearly failed, and it passes on a coarse proxy (the 3-level sampling
stratum, not human relevance grades). `jev_score_val` is what semantic
`ORDER BY` sorts on, so this is the number to re-measure on real data
before trusting production sorting. The binary figure of 0.0370 looks
far healthier and should not be quoted in its place: it cannot see
mis-ordering within the positives, which is the graded ordering that
`ORDER BY` actually exploits.

**4. The sort key is quantized to two decimals, and the top of the
ranking is one big tie.** Jev returns probabilities at two decimal
places. Over 360 rows `jev_bool` produced 45 distinct values; 21.6% of
all row pairs tie exactly, 154 rows sit at 0.01 and 53 at 0.99. Score
has the same shape: 88 distinct values, 54 rows tied at the maximum of
3.0. SQL does not define the order of rows that tie on the sort key, so
`ORDER BY prob DESC LIMIT 10`, `LIMIT 20` and `LIMIT 50` all cut inside
the 53-way tie at 0.99 and return an engine-dependent sample of it, not
a ranking. The inversion rate above cannot see this: it scores a tie as
half-discordant, and the rows tied at 0.99 mostly share a label, so
they are not comparable pairs. This is a property of the API's output,
so it applies to every extension identically, including the
`ORDER BY jev_prob(...) DESC LIMIT 20` pattern their READMEs show.
Mitigations, in order of how much they help: treat `LIMIT k` as a
filter (`WHERE prob >= 0.99`) and accept the whole group; break ties
with a second, more specific question or a Score's confidence; at
minimum add a deterministic secondary key (`ORDER BY prob DESC, id`) so
the result is at least reproducible. `sort_key_resolution` in
`results.json` reports the tie group at each cut.

The corpus, client, metrics, gate and notebook all run without a key;
only the scoring pass needs one. See [Running it](#running-it).

---

## Request shape: the integration changes the numbers

The same row and the same question reach the API in a different shape
depending on which integration sends them. Three shapes were measured
on the same 360 rows against the cached baseline (`harness/run_shapes.py`,
aggregates in `results/shapes.json`):

| | State | Question | Rows per request |
|---|---|---|---|
| **A** this harness | the text | instructions + criteria | 1 |
| **B** colliber | the text | criteria only; its client never sends `instructions` | 1 (replayed through our client: its binary is built for DuckDB 1.5.4) |
| **C** recodelabs | `{condition, rows[≤40]}` | one generic noul per `rows[i]` | 40 (its default `jev_batch_size`), run through the extension itself |
| **C1** recodelabs | as C | as C | 1 (`SET jev_batch_size = 1`) |

`jev_bool` against A, 360 rows:

| vs A | mean \|Δp\| | rows moved > 0.20 | decisions flipped at 0.5 | Spearman | ECE | Brier | inversion | gate |
|---|---|---|---|---|---|---|---|---|
| **B** criteria only | 0.041 | 0% | 1 | 0.915 | 0.068 | 0.056 | 0.035 | pass |
| **C** batch 40 | **0.264** | **51%** | **77** | **0.579** | 0.089 | **0.159** | **0.171** | **fail** |
| **C1** batch 1 | 0.027 | 3% | 6 | 0.932 | 0.047 | 0.053 | 0.038 | pass |

`jev_score` follows the same pattern: Spearman against A of 0.950 (B),
**0.506** (C), 0.974 (C1); inversion 0.037, **0.193**, 0.038.

**Batching 40 rows into one state is what breaks it, not the wording.**
C1 sends the identical question text and state layout as C and tracks
the baseline; only the number of rows sharing a state differs. The
damage is a position effect: rows in slots 0 to 7 of the batch move by
0.049 on average, slots 16 to 23 by 0.31, slots 24 to 39 by about 0.42.
It is not a row-to-answer mapping error (the best circular shift of C
against C1 is zero on every probe) and it is not noise: positives are
pulled down by 0.17 and negatives up by 0.27, so 159 of 360 rows land in
the 0.3 to 0.7 band where the baseline has 11. The model stops
discriminating for rows deep in a state of about 12,600 input tokens,
well under the documented 32k limit. recodelabs' README does say that
"the same city can score differently in a different table"; the
magnitude is what is new.

**Dropping `instructions` costs calibration, not ranking.** B keeps the
order (inversion 0.035) but ECE rises from 0.045 to 0.068, and the top
of the ranking changes character: one row at the maximum of 0.96 and 58
distinct values instead of 53 rows tied at 0.99. The two integrations
therefore disagree about *which rows tie*, which decides what
`LIMIT k` returns.

**Cost and cache, as measured through the extension.** C: 18 requests,
226,537 input tokens, $0.0095. C1: 720 requests, 417,994 input tokens,
$0.0176. Batching halves the token bill and pays for it in ranking
quality. A forced replay of every row made no new requests in either
mode, so the per-row cache works as described; its `cache_hits` counter
stayed at 0 throughout, so that field counts something other than
replay hits.

**Mitigation.** With recodelabs, `SET jev_batch_size = 1` (or a small
value; the shift is under 0.05 for the first eight slots, and the shape
of the curve between 1 and 40 is not measured here). With any
integration that packs rows into one state, measure the position effect
on your own data before sorting on the result. colliber sends one row
per request and does not have this problem; Query-farm/vgi-typesafe
was not measured.

## Hard probe: graded product relevance (ESCI)

The 20 Newsgroups result is topic membership, an easy judgment, and its
graded-ranking figure was measured against a 3-level sampling stratum.
The [Amazon Shopping Queries Dataset](https://github.com/amazon-science/esci-data)
(ESCI, Apache 2.0) removes both weaknesses: every query-product pair
carries one of four human grades, Exact > Substitute > Complement >
Irrelevant (the KDD Cup 2022 gain order), Amazon filtered the easy
queries out of the `small_version`, and product search is what a
semantic `ORDER BY` will actually be run on.

Corpus: US locale, test split, 30 queries drawn at random from the 1,148
that carry all four grades, up to 4 E, 4 S, 2 C, 2 I products per query:
**306 rows** (E 111, S 94, C 45, I 56). State is the JSON object
`{query, product{title, brand, colour, bullet_points, description}}`;
text fields are cut at 600 characters. Same questions in kind as before
(a noul, its mechanical negation, a paraphrase, a 4-way choice, a 4-level
score and its reversed twin), same pre-registered gate. 296 requests,
355,682 tokens, about $0.015. `harness/run_esci.py`, results in
`results/esci.json`.

| | 20 Newsgroups | **ESCI** | Gate |
|---|---|---|---|
| `jev_bool` ECE | 0.045 | **0.242** | ≤ 0.10 **✗** |
| `jev_bool` inversion (E vs rest) | 0.036 | **0.255** | ≤ 0.15 **✗** |
| `jev_bool` AUC | 0.964 | 0.745 | |
| `jev_bool` resolution | 0.182 | 0.043 | > 0 ✓ |
| `jev_score` inversion vs graded target | 0.143 (3-level proxy) | **0.254** (4-level human) | ≤ 0.15 **✗** |
| `jev_score` inversion, C rows removed | | 0.265 | |
| `jev_score` Spearman vs grade | 0.744 | 0.538 | |
| `jev_score` within-query inversion | | 0.244; 23 of 30 queries > 0.15 | |
| `jev_choice` accuracy | 0.875 (6-way) | 0.490 (4-way) | |
| `jev_choice` confidence ECE | 0.077 | **0.279** | ≤ 0.10 **✗** |
| negation asymmetry | 0.016 | 0.023 | ≤ 0.15 ✓ |
| paraphrase sensitivity | 0.016 | **0.164** | |

**1. Underconfidence stops being benign.** Every one of the ten
reliability bins sits above the diagonal: a predicted 0.43 is observed
at 0.80, a predicted 0.013 at 0.23. The mean P(exact) on true exact
matches is 0.195; the highest probability in the corpus is 0.75. On the
newsgroups the same bias was harmless because the ordering survived it;
here resolution is 0.043 and AUC 0.745, so the model is barely
separating the classes, and `WHERE p >= 0.5` keeps a handful of rows out
of 111 exact matches.

**2. The sort key fails inside a query, not just across the corpus.**
Inversion against the human grade is 0.254 over all pairs and 0.244
averaged within each query's own result list, which is the `ORDER BY` a
shopper sees; 23 of 30 queries exceed 0.15. Removing Complement rows,
whose place in the order is debatable, gives 0.265, so the failure is
not an artefact of that grade. Mean score by grade: I 1.21, **C 1.14**,
S 1.78, E 2.09. Complements are ranked below irrelevant products: the
rubric's second level is not recognised. And yet the reversed-rubric
mirror check still passes (correlation 0.99, mean error 2% of scale).
The scale is ordinal to the model and wrong. The invariants section
below says passing an invariant does not imply correctness; this is
what that looks like.

**3. Choice collapses onto Substitute.** 168 of 306 rows are predicted
Substitute; 63 of the 111 true Exacts among them. Stated confidence
carries no information: at confidence 1.0, 53% of picks are right.

**4. Wording moves the answer seven times more than negation does.**
Negation symmetry holds as well as it did on the newsgroups (0.023).
The paraphrase control, two questions we consider equivalent, disagrees
by 0.164 on average and by 0.52 at the 95th percentile. On the easy
corpus the two were equal (ratio 1.01); here the ratio is 0.14. The
negation invariant is not evidence of stability; the paraphrase control
is the number that matters, and on hard judgments it is large.

**5. The ties are gone.** 170 distinct score values over 306 rows, 0.9%
of pairs tied (15% on the newsgroups); 47 distinct probabilities, one
row at the maximum. The tie problem in finding 4 above was
corpus-driven, as stated there; the two-decimal cap is not.

**What this does and does not say.** On a realistic `ORDER BY` workload,
`jev-1.13.0` zero-shot with these questions does not pass a gate it
cleared comfortably on topic membership. That is one hard task, one
question set, one seed, 30 queries; trained cross-encoders reach far
higher on ESCI and were not compared. It does not say every hard task
fails. It says the easy result was the upper bound the README called it,
and that the measurement has to be made on your data, which is what the
harness is for. Caveats specific to this probe: the E/S boundary is
subtle even for the human annotators; the question wording is strict
("including every attribute the query states") and the paraphrase
result shows wording matters; product text was truncated; and the
product fields came from a Hugging Face re-encoding of Amazon's file
(`spacemanidol/ESCI-product-dataset-corpus-us`, same product IDs)
because the 1.1 GB original downloads at 60 KB/s from here. The source
is recorded in every corpus row, and once the original had downloaded,
`harness/verify_esci_products.py` compared all 306 products against it:
title, brand, bullet points and description identical on every row;
colour differs on one row (product B07WZVBDY9, "Blue/1Set" in the
re-encoding, "Brown/1set" in the original). One field of one row, so
the results stand as published; rebuilding from the original would
change that one state string.

## Why the measurement comes before the SQL

The product is `ORDER BY` over a semantic score. If the probabilities are
not calibrated, the sort key is a meaningless number and every query fails
*silently*: rows come back in an order, just not a defensible one. Nothing
errors, nothing looks wrong, and the result is wrong. So the calibration
harness is the first deliverable and the gate on everything after it.

`udf.register()` enforces this in code: it refuses to register the SQL
functions unless `results/results.json` records a passing gate.

## What is measured

Two families, because a gate on calibration alone is the wrong gate.

**Calibration** (Brier + Murphy decomposition, ECE, MCE) asks: is a stated
0.7 really 70%?

**Ranking** (Spearman, Kendall, AUC, pairwise inversion rate) asks: does
sorting by this put rows in the right order?

They come apart in both directions. Probabilities squashed into
[0.48, 0.52] but perfectly ordered give an ECE of 0.485 with zero
inversions: terrible calibration, flawless sort. (That exact case is a
test in `test_metrics.py`.) Conversely a model calibrated in aggregate can
still invert many individual pairs and produce a visibly wrong page of
results. `ORDER BY` depends on the second family; the original spec's gate
named only the first.

**Invariants** are the third thing measured, and the most defensible,
because they need **no ground-truth labels at all**:

| Invariant | What it catches |
|---|---|
| Negation symmetry: `P(q)` vs `1 - P(not q)` | Probabilities that move with phrasing rather than evidence. The `jev-1.13` jaggedness page explicitly disclaims this identity, which is what makes it worth measuring. |
| Paraphrase control: `P(q)` vs `P(reworded q)` | The confound in the line above. A semantically equivalent rewording *should* agree, so this is the floor for general wording sensitivity. If it is as large as the negation violation, the asymmetry is not about negation at all, and the headline invariant has to be reported that way. Paraphrases preserve the **predicate**, not just the topic ("is this an offer to sell" not "does this concern selling"), because a drifted paraphrase inflates the control and would push the headline toward "not negation-specific" for the wrong reason. Reported per probe as well as aggregate, so one bad string cannot move the conclusion. |
| Score rubric ordinality: reversed rubric should mirror | Levels are scored independently and the model never sees level numbers, so ordinality is imposed entirely by *our* array order. If `score_reversed != scale_max - score`, the rubric is not ordinal to the model and every sort key built from it is noise. |

The negation question is derived **mechanically** from the positive one
rather than hand-written, so that a large measured asymmetry cannot be
explained away by the two strings not having been true complements.

All three ride along in a request already being paid for: one row costs
one request carrying six questions, not six requests.

Because these compare the model against itself, they are immune to the
label-provenance problem below. They are necessary, not sufficient:
passing negation symmetry does not imply calibration, but failing it means
the probabilities cannot be thresholded reliably, which kills
`WHERE prob > x` independently of calibration.

## Label provenance

This decides whether any of the numbers mean anything.

The corpus is **20 Newsgroups**, and each document's label is the
newsgroup its author chose to post it to: a human judgment, recorded by a
human, independent of this project. Hand-labeling the corpus ourselves
would have measured Jev's agreement with Claude and published it as
calibration, producing an authoritative-looking number worth nothing.

Selection constraints, in the order they bound the result:

1. Human-labeled by provenance, and freely redistributed for research
   (see [Corpus licensing](#corpus-licensing) for what that does and does
   not mean).
2. Single-factor labels, matching the spec's rule for questions.
3. Clear of Jev's documented weak spots. The jaggedness page for
   `jev-1.13` names math/counting, date comparison, and hex/RGB numeric
   representations. Topic membership touches none of them, so a
   miscalibration we measure is not secretly a counting failure.
4. **Labels span the probability range.** Sampling only obvious cases pins
   every prediction at 0 or 1, ECE comes out tiny, the gate passes
   vacuously, and nothing is learned.

Constraint 4 drives the stratified sampler: each probe draws clear
positives, topically adjacent **near misses**, and plainly unrelated
negatives, weighted toward the near misses. Default corpus is 360 rows
across 3 probes, inside the spec's 300-500 band.

### The near-miss labels are not all sound, and that is handled explicitly

The positive labels are safe: the author chose `sci.med`, so "is this
about medicine" is yes. **The negative labels are weaker.** A
`talk.politics.misc` post about healthcare reform genuinely *is* about
health; a `rec.autos` post selling a part genuinely *is* offering an item
for sale. The author picking a different newsgroup does not entail "not
about X."

This is sharper than generic label noise, because the sampler
deliberately concentrates the least reliable labels in the largest
stratum *and* in the mid-probability region where ECE is decided. A
correct 0.6 scored against a wrong `False` reads as miscalibration and
could fail a 0.10 gate on label error alone.

So doubtful rows are detected **per row, not per group**
(`is_ambiguous_negative`) and flagged `label_confident=False`: 7 of 360
rows. They are **excluded from every gated calibration metric** and
**kept for ranking**, because ranking only needs the pairs the labels do
order, and those hard rows are exactly where sort order matters.
`results.json` reports the all-rows figure alongside each gated one, so
it is visible how much work the exclusion is doing.

Banning whole groups was the first attempt and was wrong twice over.
Measured contamination is only 2-5% per group, so a ban discards ~95% of
usable rows; worse, it removed *both* of `forsale`'s near-miss groups,
collapsing that probe to clear positives plus clear negatives. That is
precisely the vacuous-gate failure constraint 4 exists to prevent,
reintroduced by the fix. Per-row filtering keeps all three strata on all
three probes (47 near-misses each).

Document headers are stripped before scoring. A leftover `Newsgroups:` or
`Subject:` line hands the model the answer, and an `Organization: Memorial
Sloan-Kettering Cancer Center` line makes an unrelated post look medical:
either way the run would be measuring header parsing, not judgment.

The vendor's self-reported 67.8% agreement against averaged frontier
judgments is not used as a baseline anywhere here. Agreement with other
models is not calibration.

### Corpus licensing

**20 Newsgroups carries no explicit license.** Neither the original
distribution page nor scikit-learn's documentation states one. It has
been redistributed for research since the 1990s and ships inside
scikit-learn, so research use is well established by convention, but
"conventionally redistributed" is not the same as "licensed", and this
README previously said "licensed for research use", which overstated
what can be verified. Corrected here rather than quietly.

Practical consequences:

- **No corpus text is committed to this repo.** Only aggregate metrics
  are (`results/results.json`). The corpus and the raw response cache are
  gitignored build artifacts you regenerate locally.
- The documents are public Usenet posts from the 1990s written by
  identifiable people. If you republish any of it, that is your call to
  make, not one this repo makes for you.
- **Content warning:** the corpus includes `talk.politics.*` and
  `talk.religion.*` posts, and scikit-learn explicitly warns that it
  "contains data which may be inappropriate for certain NLP
  applications" and that inflammatory or culturally biased text will
  propagate biases. The probe questions here are about topic membership,
  which does not surface that content in the metrics, but you will see it
  if you read the raw rows.

## Gate

Thresholds were fixed **before** any results were seen.

The spec asks for the three primitives to be *reported* separately because
they may calibrate differently. They are therefore *gated* separately too:
gating only `jev_bool` would let a Score that inverts a third of its pairs
through, and `jev_score_val` is the accessor `ORDER BY` actually sorts on.

| Condition | Threshold | Rationale |
|---|---|---|
| `jev_bool` ECE | ≤ 0.10 | A stated 0.8 that is really 0.7 is tolerable for ranking; wider and the probability is decorative. |
| `jev_bool` inversion rate | ≤ 0.15 | Past roughly one bad pair in six, a sorted page looks visibly wrong. |
| `jev_bool` resolution | > 0 | At or below zero, the model is not separating classes at all. A model predicting the base rate every time scores a respectable Brier and is useless for `ORDER BY`. |
| **`jev_score` inversion rate** | ≤ 0.15 | Graded ranking, scored against the 3-level ordinal stratum rather than the binary label, so it can detect mis-ordering *within* the positives. A necessary condition for semantic `ORDER BY`, gated on its own merits. |
| `jev_choice` confidence ECE | ≤ 0.10 | Does stated confidence predict whether the pick was right? |
| Negation asymmetry | ≤ 0.15 | Beyond this, phrasing moves the answer as much as evidence does. |

## Running it

The harness needs **no new packages**: numpy, scipy, sklearn, matplotlib
and requests are already present. `duckdb` is needed only by
`harness/udf.py`.

### The API key

Put it in a `.env` file rather than pasting it anywhere it could be
logged. `.env` is gitignored (and `test_pipeline.py` asserts that, so the
protection cannot rot silently):

```sh
cp .env.example .env
$EDITOR .env          # TYPESAFE_AI_API_KEY=your-key-here
```

The harness looks for `.env` at the repo root and accepts either
`TYPESAFE_AI_API_KEY` or `TYPESAFE_API_KEY` (the build spec names the
first, the published SDK page the second). An already exported shell
variable always wins, so a stale `.env` cannot silently override a key
you set deliberately.

`export TYPESAFE_AI_API_KEY=...` also works if you prefer not to have the
key on disk.

```sh
# one-time corpus download (~14MB, human-labeled; see Corpus licensing)
mkdir -p ~/scikit_learn_data/20news_home
curl -L -A "Mozilla/5.0" -o /tmp/20news.tar.gz \
  http://qwone.com/~jason/20Newsgroups/20news-bydate.tar.gz
tar xzf /tmp/20news.tar.gz -C ~/scikit_learn_data/20news_home

# build the corpus
python3 harness/corpus.py .data/jev-calibration/corpus.jsonl

# verify the harness with no API key and no spend
python3 harness/test_metrics.py     # 29 known-answer metric tests
python3 harness/test_pipeline.py    # end-to-end against a mock Jev server

# then, with a key in .env (or exported):
python3 harness/run_calibration.py --pilot   # 10 rows + cost extrapolation
python3 harness/run_calibration.py           # full run
python3 harness/run_calibration.py --analyze-only   # recompute, no spend

# hard probe: ESCI (examples file from github.com/amazon-science/esci-data,
# products from the original file or the Hugging Face US re-encoding)
python3 harness/corpus_esci.py            # 30 queries, ~306 rows
python3 harness/test_esci.py              # offline, mock server
python3 harness/run_esci.py --pilot       # 10 rows + cost estimate
python3 harness/run_esci.py               # full run, ~$0.015
```

`harness/udf.py` additionally needs `pip install duckdb` (run it yourself; this
repo does not install packages autonomously).

## Execution layer

Built into the harness rather than retrofitted later, because all four
are cheaper to build now and the calibration run needs them anyway.

- **Batching.** Every question for a row goes in one request. Jev answers
  independent questions against one state in a single parallel pass, so
  the calibration run issues 1 request per row instead of 4, and pays for
  the state tokens once instead of six times. Verified by test: 60 rows →
  60 requests, 6 questions each.
- **Cache.** Content hash of `(model, state, questions)` → SQLite (WAL,
  thread-local connections). Verified: a replay run makes 0 requests and
  spends 0 tokens.
- **Cost ceiling.** Hard token budget that raises `BudgetExceeded` rather
  than degrading. `ORDER BY` over a large table is an easy way to spend
  real money by accident, so the failure mode is a loud stop.
- **Concurrency.** Bounded pool, exponential backoff with jitter,
  honouring `retry-after`. Retries 429/529/5xx; does not retry 401/422,
  which will not improve. Partial failures are collected and surfaced, not
  silently nulled.

Token usage is recorded per call from the first request. TypeSafe
publishes pricing ($0.042 per million input tokens, output free) and rate
limits (250k tokens/s, 1,200 requests/min, 64k context with 32k for state
plus the longest question) at docs.typesafe.ai/models, but the limits are
stated to adjust with demand, so a production cost ceiling is calibrated
from usage we measure ourselves rather than from the published figures.

## Consuming the numbers in SQL (reference only)

`harness/udf.py` registers these as DuckDB Python scalar functions. It
exists to show the shape the numbers should take at the SQL boundary,
not to compete with the native extensions above; the design points
below apply to any of them.

```
jev_bool(text, question)      -> STRUCT(value BOOLEAN, prob DOUBLE)
jev_choice(text, options[])   -> STRUCT(value VARCHAR, prob DOUBLE, confidence DOUBLE)
jev_score(text, rubric[])     -> STRUCT(score DOUBLE, confidence DOUBLE)
jev_score_val(text, rubric[]) -> DOUBLE
```

Structs, not bare values: returning NULL on low confidence poisons
`ORDER BY` unpredictably (DuckDB sorts NULLs last regardless of direction,
so low-confidence rows silently clump at one end), and a bare score hides
the uncertainty the caller needs. `jev_score_val` covers the case where
the caller has already decided to trust the score.

`jev_bool` exposes `prob` with no separate confidence because Noul returns
a probability and has no confidence field: `value` is `prob >= 0.5`.

### Score scale: the sharp edge

Score returns a probability-weighted mean over level **indices**, so an
`n`-level rubric spans `0..n-1`, **not** `0..1`. Therefore:

- `jev_score_val` output is **not comparable across different rubrics**.
- `ORDER BY` mixing rubrics is meaningless, and nothing in SQL will warn.

## Limitations

- **One corpus, one domain.** English newsgroup posts. Calibration is a
  property of model *and* domain; these numbers will not transfer to
  contracts, tickets or governance proposals without re-running.
- **Topic membership is an easy judgment**, so treat the results as an
  upper bound on harder ORDER BY workloads. The ESCI probe confirms it:
  the same gate fails there.
- **~120 rows per probe.** Ten-bin ECE is noisy at that size. Bins carry
  Wilson intervals and adaptive (equal-mass) binning is the default; read
  the intervals, not the third decimal.
- **Adaptive ECE is sensitive to tie handling at the ±0.003 level.** Jev
  returns two-decimal probabilities and 154 of 360 rows sit at exactly
  0.01, so five of the ten equal-mass bins contain that one tied value
  (three consist of nothing else) and which tied rows fall on which
  side of a bin edge is arbitrary. An
  earlier draft of this table reported 0.0427 from the same responses in
  a different row order; the code now sorts rows canonically so the
  number is reproducible, but the fixed-width ECE (0.0454), which has no
  tie problem, is the one to quote if the third decimal matters.
- **20 Newsgroups labels are themselves noisy** (cross-posting, imperfect
  group choice), which inflates apparent miscalibration. The worst cases
  are held out of ECE (see above), but the remaining negatives are still
  "the author posted elsewhere", not "a human judged this not-about-X".
- **The tie statistics are corpus-dependent; the quantization is not.**
  Topic membership is easy, which crowds rows at 0.01 and 0.99. A harder
  corpus would spread values across the range and shrink the top tie
  group. Two-decimal output is a property of the API and caps the sort
  key at 101 distinct values whatever the corpus.
- **Invariants bound wording sensitivity, not correctness.** A model can
  be perfectly self-consistent and consistently wrong.
- **Graded ranking is proxied, not measured directly.** The ordinal target
  is the 3-level sampling stratum, not a human-assigned relevance grade.
  It detects gross mis-ordering within the positives; it cannot certify
  fine-grained rank quality.
- **`jev-latest` is a moving target.** The `model` field from each
  response is recorded; these numbers attach to one version.

## Layout

```
harness/corpus.py           stratified corpus builder, provenance notes
harness/client.py           batching, cache, budget, retries, metering
harness/metrics.py          calibration + ranking + invariants + gate
harness/run_calibration.py  scoring run, analysis, reliability diagram
harness/udf.py              reference DuckDB functions (gated on results.json)
harness/run_shapes.py       request-shape comparison across integrations
harness/corpus_esci.py      hard-probe corpus from Amazon ESCI
harness/run_esci.py         hard-probe run: graded ranking, within-query
harness/test_esci.py        offline test of the ESCI runner
harness/verify_esci_products.py  corpus products vs Amazon's original file
harness/test_metrics.py     known-answer tests for every metric
harness/test_pipeline.py    end-to-end test against a mock Jev server,
                            plus secret-hygiene assertions
.env.example                copy to .env and add your key (.env is ignored)
notebook/calibration.ipynb  the publishable artifact
results/                    results.json + reliability.png (after a run)
                            shapes.json (after run_shapes.py)
                            esci.json + reliability_esci.png (after run_esci.py)
```

Corpus and cached responses live in `.data/jev-calibration/` (gitignored):
raw response bodies can contain corpus text, and the cache is a build
artifact.
