# TypeSafe docs (local)

Local markdown mirror of [docs.typesafe.ai](https://docs.typesafe.ai/), crawled with grub-crawler on 2026-09-17.
Starting page: [Intent routing](docs/patterns/intent-routing.md).

Official index: [llms.txt](llms.txt).

## Search this corpus with Lume

Lume lives in `lume/`. It builds a BM25 index plus a semantic knowledge graph from `dict/typesafe.csv`, then search walks that graph (intent routing → handler, confidence-gated routing, fan-out, …).

Run these from the `typesafe-arena` directory. Verified on 2026-09-17: 46 files, 664 sections, graph search for `intent routing` ranked `docs/patterns/intent-routing.md` first.

### 1. Build Lume

Needs [Rust/Cargo](https://rustup.rs/) (1.75+).

```powershell
cd lume
cargo build --release
cd ..
```

Binary: `lume\target\release\lume.exe` (Windows) or `lume/target/release/lume` (Unix).

### 2. Build the graph index

```powershell
.\lume\target\release\lume.exe index --db .lume-index --tag-dict dict\typesafe.csv docs
```

Unix:

```bash
./lume/target/release/lume index --db .lume-index --tag-dict dict/typesafe.csv docs
```

That writes `.lume-index/` (`bm25.json`, `entity_graph.json`, `spelling.json`, `state.json`). The tag dictionary is `dict/typesafe.csv` — phrases like `intent routing`, `Choice`, `Noul`, `confidence` become graph nodes.

Re-index after doc changes:

```powershell
.\lume\target\release\lume.exe index update --db .lume-index
```

Force a full rebuild:

```powershell
.\lume\target\release\lume.exe index -f --db .lume-index --tag-dict dict\typesafe.csv docs
```

### 3. Search

```powershell
.\lume\target\release\lume.exe search --db .lume-index "intent routing"
```

Graph boost is on by default (`-g 0.4`). Disable it with `-g 0`. More hits: `-l 20`.

Optional extras (not required for lexical + graph search):

- `-s` dense vectors (needs a NUTS token and Shivvr)
- `-o` LLM entity extraction via Ollama

## Patterns

- [Patterns](docs/patterns.md)
- [Composite scoring](docs/patterns/composite-scoring.md)
- [Confidence-gated routing](docs/patterns/confidence-routing.md)
- [Speculative fan-out](docs/patterns/fan-out.md)
- [Intent routing](docs/patterns/intent-routing.md)

## Primitives

- [Primitives (Questions)](docs/primitives.md)
- [Advanced: structure](docs/primitives/advanced.md)
- [Choice](docs/primitives/choice.md)
- [Noul](docs/primitives/noul.md)
- [Score](docs/primitives/score.md)

## Concepts

- [How to build with TypeSafe](docs/concepts/how-to-build-with-system-one.md)
- [State](docs/concepts/state.md)
- [System One](docs/concepts/system-one.md)
- [Example use cases](docs/concepts/use-case-map.md)

## Introduction

- [Introduction](docs/introduction.md)
- [AI primer](docs/introduction/machine-learning-primer.md)
- [Quick start](docs/introduction/quickstart.md)

## Confidence

- [Confidence](docs/confidence.md)

## Cookbooks

- [Cookbooks](docs/cookbooks.md)
- [Structure recovery](docs/cookbooks/autoformat.md)
- [Autoresearch feature discovery](docs/cookbooks/autoresearch_feature_discovery.md)
- [Double-checking citations](docs/cookbooks/citation_check.md)
- [Classification using confidence](docs/cookbooks/classification_using_confidence.md)
- [Classifying RAG passages](docs/cookbooks/classifying_rag_passages.md)
- [Self-consistency: choices](docs/cookbooks/consistency_choice_cookbook.md)
- [Self-consistency: nouls](docs/cookbooks/consistency_noul_cookbook.md)
- [Date extraction](docs/cookbooks/date_extraction_cookbook.md)
- [Knowledge graph entity alignment](docs/cookbooks/entity_alignment.md)
- [Function calling](docs/cookbooks/function_calling.md)
- [Hierarchical classification](docs/cookbooks/hierarchical_classification.md)
- [Guardrails for LLMs](docs/cookbooks/llm_guardrails.md)
- [Parallel questions](docs/cookbooks/parallel_questions.md)
- [Pre-parsed value extraction](docs/cookbooks/pre_parsed_value_extraction_cookbook.md)
- [Re-ranking](docs/cookbooks/rerank_typesafe.md)
- [SDE cascade](docs/cookbooks/sde_cascade.md)
- [Line-by-line search](docs/cookbooks/semantic_find.md)
- [Skill suggestion](docs/cookbooks/skill_suggestion.md)

## Demos

- [Demos](docs/demos.md)
- [Smart home assistant demo](docs/demos/smart-home.md)

## SDKs and API

- [Agent skill](docs/agent-skill.md)
- [API reference](docs/api.md)
- [Client SDKs](docs/sdk.md)
- [JavaScript SDK](docs/sdk/javascript.md)
- [TypeSafe Python SDK](docs/sdk/python.md)
- [Usage](docs/sdk/python/usage.md)
