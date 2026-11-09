"""Build the Phase 1 calibration corpus from 20 Newsgroups.

Why this corpus, in the order the constraints mattered:

1. Human-labeled by provenance, not by us. Each document's label is the
   newsgroup its author posted it to. We are measuring Jev against human
   behaviour, not against a Claude-generated answer key. Self-labeling
   would measure Jev's agreement with Claude and produce an authoritative
   looking number worth nothing.
2. Freely redistributed for research. Note it carries no explicit
   license; see the Corpus licensing section of the README.
3. Single-factor labels. "Is this about X" is one judgment, matching the
   build spec's rule that questions must be single-factor.
4. Clear of Jev's documented failure modes. The jaggedness page for
   jev-1.13 lists math/counting, date comparison and hex/RGB numeric
   representation as known-weak. Topic membership touches none of them,
   so a miscalibration we measure is not silently a counting failure.
5. Labels can be made to span the probability range. See below.

The spread requirement is the subtle one. If every row is an obvious yes
or an obvious no, Jev's probabilities pile up at 0 and 1, ECE comes out
tiny, the Phase 1 gate passes vacuously and we have learned nothing. So
the sampler deliberately mixes three difficulty strata per question.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass, asdict
from pathlib import Path

CORPUS_ROOT = Path.home() / "scikit_learn_data" / "20news_home" / "20news-bydate-train"

# Each probe is one single-factor yes/no judgment.
#
#   positive  -> newsgroups where the human label says yes
#   near_miss -> newsgroups that are topically adjacent. These are the rows
#                that should land mid-range. A model that answers 0/1 here
#                is overconfident and ECE will say so.
#   far       -> plainly unrelated newsgroups, the easy noes
PROBES = {
    "space": {
        "question": "Is this message about spaceflight, astronomy, or space exploration?",
        "positive": ["sci.space"],
        "near_miss": ["sci.electronics", "sci.crypt"],
        "far": ["rec.sport.hockey", "misc.forsale"],
    },
    "medical": {
        "question": "Is this message about medicine, health, or medical treatment?",
        "positive": ["sci.med"],
        "near_miss": ["sci.space", "talk.politics.misc"],
        "far": ["comp.graphics", "rec.autos"],
    },
    "forsale": {
        "question": "Is this message offering an item for sale?",
        "positive": ["misc.forsale"],
        "near_miss": ["rec.autos", "comp.sys.mac.hardware"],
        "far": ["talk.religion.misc", "sci.med"],
    },
}

# Choice and Score reuse the same documents, so one paid pass over a row can
# answer all three primitive types. The build spec asks for the metrics to be
# reported separately because they may calibrate differently; it does not ask
# for three separate corpora.
CHOICE_GROUPS = {
    "sci.space": "space",
    "sci.med": "medicine",
    "misc.forsale": "for_sale",
    "rec.autos": "cars",
    "comp.graphics": "computer_graphics",
}


# Per-ROW ambiguity detection, not per-group.
#
# The problem: the author picking a different newsgroup does not entail
# "not about X". A rec.autos post selling a part really is offering an
# item for sale; a talk.politics.misc post on healthcare reform really is
# about health. Scoring a correct 0.6 against a wrong False reads as
# miscalibration and can fail the gate on label error alone.
#
# The first fix was to ban whole groups, which was wrong twice over.
# Measured contamination is only 2-5% per group, so banning a group throws
# away ~95% of good rows; and it removed BOTH of forsale's near-miss
# groups, collapsing that probe to clear positives plus clear negatives.
# That is exactly the vacuous-gate failure the stratified sampler exists
# to prevent, reintroduced by the fix.
#
# So: flag the individual rows whose negative label is actually doubtful,
# and keep the rest. Flagged rows stay in the corpus for ranking (they are
# the hard cases where sort order matters) and are held out of calibration.
AMBIGUITY_PATTERNS = {
    "forsale": re.compile(
        r"\b(for ?sale|selling|i'?m selling|asking \$|best offer|\bobo\b|"
        r"shipped conus|price:|\$\d{2,}|make (me )?an offer|want to sell|"
        r"\bwtb\b|\bfs\b:)\b",
        re.I,
    ),
    "medical": re.compile(
        r"\b(health ?care|medical|disease|patient|doctor|physician|"
        r"treatment|cancer|diagnos\w+|symptom|prescription|therapy|"
        r"clinical|medicine)\b",
        re.I,
    ),
    "space": re.compile(
        r"\b(nasa|orbit\w*|spacecraft|satellite|space shuttle|astronaut|"
        r"launch vehicle|payload|interplanetary|space station)\b",
        re.I,
    ),
}


def is_ambiguous_negative(probe: str, text: str) -> bool:
    """True if a row labeled False plausibly deserves True.

    Deliberately over-inclusive: a false positive here costs one row of
    calibration sample, while a false negative puts a wrong label straight
    into the ECE that gates Phase 2.
    """
    pat = AMBIGUITY_PATTERNS.get(probe)
    return bool(pat and pat.search(text))


@dataclass
class Row:
    row_id: str
    probe: str
    text: str
    newsgroup: str
    label: bool          # ground truth from the human-assigned newsgroup
    stratum: str         # positive | near_miss | far
    choice_label: str | None
    label_confident: bool = True   # False = "no" is arguable, exclude from ECE


def _clean(raw: str) -> str:
    """Strip headers, quoted replies and signatures.

    Equivalent to sklearn's remove=('headers','footers','quotes'), and it
    matters more than it looks. A leftover `Newsgroups:` or `Subject:`
    header hands the model the answer directly, and an `Organization:
    Memorial Sloan-Kettering Cancer Center` line makes an unrelated post
    look medical. Either way we would be measuring header parsing rather
    than semantic judgment.
    """
    # RFC822 headers run until the first blank line.
    parts = raw.split("\n\n", 1)
    body = parts[1] if len(parts) > 1 else raw

    # Any stragglers that survived, plus attribution lines.
    lines = []
    for ln in body.splitlines():
        s = ln.strip()
        if s.startswith((">", "|")):
            continue
        if re.match(r"^[A-Za-z-]{2,20}:\s", ln) and re.match(
            r"^(From|Subject|Organization|Lines|NNTP-Posting-Host|Reply-To|"
            r"Distribution|Newsgroups|X-[\w-]+|In-article|Keywords|Summary|"
            r"Nntp-Posting-Host|Article-I\.D|References|Sender|Followup-To|"
            r"Expires|Originator|Date|Message-ID|Path|Xref)\b",
            ln, re.I,
        ):
            continue
        if re.match(r"^In article <.*>.*writes:\s*$", s):
            continue
        if re.match(r"^.{0,80}\bwrites:\s*$", s) and "@" in s:
            continue
        lines.append(ln)

    text = "\n".join(lines)
    text = re.split(r"^-- ?$", text, flags=re.MULTILINE)[0]
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _load_group(group: str) -> list[tuple[str, str]]:
    d = CORPUS_ROOT / group
    if not d.is_dir():
        raise FileNotFoundError(
            f"Corpus not found at {d}. See README.md for the "
            "one-time download step."
        )
    out = []
    for f in sorted(d.iterdir()):
        if not f.is_file():
            continue
        text = _clean(f.read_text(errors="replace"))
        # Very short documents carry no evidence; very long ones become a
        # distractor, which the jaggedness page flags as accuracy-reducing
        # irrelevant context. Keep the middle.
        if 200 <= len(text) <= 4000:
            out.append((f"{group}/{f.name}", text))
    return out


def build(n_per_probe: int = 120, seed: int = 20260918) -> list[Row]:
    """Sample a stratified corpus.

    Default 3 probes x 120 = 360 rows, inside the spec's 300-500 band.
    The split is deliberately not 50/50: near_miss rows are the ones that
    carry calibration information, so they get the largest share.
    """
    rng = random.Random(seed)
    rows: list[Row] = []

    for probe_name, probe in PROBES.items():
        # 1/3 clear yes, 5/12 near miss, 1/4 clear no.
        quota = {
            "positive": round(n_per_probe * 0.34),
            "near_miss": round(n_per_probe * 0.41),
            "far": round(n_per_probe * 0.25),
        }
        for stratum, groups in (
            ("positive", probe["positive"]),
            ("near_miss", probe["near_miss"]),
            ("far", probe["far"]),
        ):
            pool: list[tuple[str, str]] = []
            for g in groups:
                pool.extend((doc_id, text, g) for doc_id, text in _load_group(g))
            rng.shuffle(pool)
            for doc_id, text, group in pool[: quota[stratum]]:
                rows.append(
                    Row(
                        row_id=hashlib.sha256(
                            f"{probe_name}:{doc_id}".encode()
                        ).hexdigest()[:16],
                        probe=probe_name,
                        text=text,
                        newsgroup=group,
                        label=(stratum == "positive"),
                        stratum=stratum,
                        # Groups outside CHOICE_GROUPS map to "other" rather
                        # than None. Dropping them would mean no scored row
                        # ever exercises the no-match path, and the whole
                        # point of offering "other" is that the model can
                        # decline instead of being forced into a wrong bucket.
                        choice_label=CHOICE_GROUPS.get(group, "other"),
                        # Positives are safe: the author chose the group.
                        # Only negatives can be doubtful.
                        label_confident=(
                            stratum == "positive"
                            or not is_ambiguous_negative(probe_name, text)
                        ),
                    )
                )

    rng.shuffle(rows)
    return rows


def write(path: Path, rows: list[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(asdict(r)) + "\n")


if __name__ == "__main__":
    import sys

    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("corpus.jsonl")
    rows = build()
    write(dest, rows)

    from collections import Counter

    print(f"{len(rows)} rows -> {dest}")
    print("by probe   :", dict(Counter(r.probe for r in rows)))
    print("by stratum :", dict(Counter(r.stratum for r in rows)))
    print("label yes  :", sum(r.label for r in rows))
    print("choice-able:", sum(r.choice_label is not None for r in rows))
