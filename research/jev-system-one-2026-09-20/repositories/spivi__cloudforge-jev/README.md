# cloudforge + Jev sidecar

A trainer already has [cloudforge](https://github.com/spivi/forge-x-labs): a
local lab generator with a machine-checkable answer key. `cloudforge grade`
matches guessed node ids as a subsequence of the labeled path.

Students also write a paragraph. That text is not a node-id list. This sidecar
sits **outside** cloudforge and uses [TypeSafe Jev](https://docs.typesafe.ai)
to judge whether the paragraph names the same entry, identity hop, and sink.

cloudforge stays hermetic and no TypeSafe dependency lands in the OSS product;
the code here owns the thresholds and Jev returns the probabilities.

## Run it

```bash
git clone https://github.com/spivi/cloudforge-jev.git && cd cloudforge-jev
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
echo 'TYPESAFE_API_KEY=<your key>' > .env
.venv/bin/python judge_lab.py --lab samples/lab --rationale samples/match.txt
```

`samples/lab` is the instructor pack of one `ci_cd_iam_chain` lab written by cloudforge 1.4.0
(seed 7), so the first grade needs nothing but a key. `samples/miss.txt` is the paragraph about
the wrong risk. To grade your own labs, point `--lab` at any pack `cloudforge lab` wrote.

## What Jev is doing

One request, four atomic questions over the same state:

| Question | Primitive | Meaning |
|---|---|---|
| `names_entry` | Noul | Same initial access as the labeled path? Worded for a name when the entry is an identity, for a phrase when it is public access or another account |
| `names_identity_hop` | Noul | Same hop that grants the access: the first identity after the entry, or the misconfigured resource when the path has none (a public bucket, a shared snapshot) |
| `names_sink` | Noul | Names what the attacker reaches, per `ground_truth.sink_kind` (data, secret, key, role, image, queue, snapshot, database, vault) |
| `depth` | Score | How far the writeup walks the chain, four levels |

The three names come from node types, not positions: an owning account as the entry means public, unauthenticated access; an external account is named as such. On a two-node
path (an external account into the trusted role, a developer role into the admin role),
the hop and the sink are the same node; asking about the hop would repeat the sink
question, so it collapses into the resource question instead: the misconfiguration that
opens the access. A semantic hit is all three Nouls at or above 0.7. A Noul between 0.4
and 0.6 flags instructor review. That composition is ordinary Python.

`depth` is a ladder, not a single completeness score:

| Depth | What the writeup does |
| --- | --- |
| 0 | Names a different risk, or none of the critical hops |
| 1 | Names the sink or the entry but not the connecting hop |
| 2 | Names the entry, the hop that grants the access, and what is reached |
| 3 | Also walks the chain between them, in order, with what makes each hop possible |

The top of the ladder is capped by the labeled path itself: a path of three nodes or
fewer has no chain left to walk beyond the hop already required at depth 2, so it caps
at depth 2 of 2; a longer path caps at depth 3 of 3. The printed row always reads
"depth N of M" for that lab's own M.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export CLOUDFORGE_ROOT=/path/to/forge-x-labs
.venv/bin/pip install -e "$CLOUDFORGE_ROOT"   # only needed when the sidecar generates the lab
# TYPESAFE_API_KEY in .env
```

## Run

`--lab` is required unless you pass `--generate`. The sidecar fails closed: no
Jev call, no lab write, until you say which one you want.

Matching writeup, against a pack `cloudforge lab` already wrote:

```bash
.venv/bin/python judge_lab.py \
  --lab out/demo-lab \
  --rationale samples/match.txt
```

Wrong risk:

```bash
.venv/bin/python judge_lab.py \
  --lab out/demo-lab \
  --rationale samples/miss.txt
```

No pack yet:

```bash
.venv/bin/python judge_lab.py \
  --generate \
  --cloudforge-root "$CLOUDFORGE_ROOT" \
  --rationale samples/match.txt
```

`--lab` reuses a pack `cloudforge lab` already wrote. `--generate` writes one
with cloudforge first.

## What comes back

Both samples, run against the same `ci_cd_iam_chain` lab (GitHub Actions OIDC,
`iam:PassRole` to a runtime role, `customer-exports`):

| Signal | `samples/match.txt` | `samples/miss.txt` |
|---|---|---|
| names entry | 0.97 | 0.02 |
| names identity hop | 0.84 | 0.02 |
| names sink | 0.65 | 0.03 |
| depth (0 to 3, this lab's chain is 8 nodes) | 2, entry, hop, and sink | 0, different risk |
| semantic hit | no (sink sat at 0.65, under 0.7) | no |
| instructor review | no | no |

The miss names a public bucket and no IAM chain. Jev did not split the
difference; the numbers went to the rule the code already had.

The numbers are from one run. A second run of the same text moves them by a few
hundredths, and by more on borderline answers; that is what the review band is for.

Without `TYPESAFE_API_KEY` the sidecar exits with an error and the lab is
untouched.

The measurements behind the essay (stress writeups, a local model on the same inputs, wording
sensitivity, repeat runs, the weird inputs, a blind second reader, the depth ladder) are in
[docs/measurements.md](docs/measurements.md).
