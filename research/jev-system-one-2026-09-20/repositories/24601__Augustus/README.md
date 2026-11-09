# Augustus

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/github/v/release/24601/Augustus)](https://github.com/24601/Augustus/releases)
[![Claude Code](https://img.shields.io/badge/Claude_Code-marketplace-purple.svg)](.claude-plugin/marketplace.json)
[![Skills.sh](https://img.shields.io/badge/skills.sh-compatible-green.svg)](https://www.skills.sh/)

Agent skill for placing TypeSafe Jev Choice/Score/Noul with classical
decision methods, composition algebra, and a validation gate.

**Augustus** — named for Augustus De Morgan (1806–1871), mentor and professor
of William Stanley Jevons — is the design-judgment skill for **where** typed
probabilistic judgment belongs (the Jev-class of System One models), using
mathematical, logical, and algorithmic mental models. It applies across
**AI, software, business, knowledge work, and life** — not only SWE.
[TypeSafe](https://docs.typesafe.ai/) Jev is the documented exemplar
(Choice, Score, Noul), not the monopoly. Formal methods are one pillar.
Exact work stays in code or policy; the model owns narrow judgment;
never launder a Noul as a proof.

> Companion, not replacement, to the official
> [`typesafe-ai` skill](https://github.com/typesafe-ai/skills). That skill
> owns Jev integration contracts; Augustus owns the **design judgment**:
> which *pillar*, *family*, and classical method map, what the objective
> implies for fail-open vs fail-closed, and what experiment would prove a
> design wrong. Not a TypeSafe-only how-to.

## The skill

- `.agents/skills/augustus/SKILL.md` — working protocol + decision-design card
- `.agents/skills/augustus/references/mental-models.md` — cross-domain
  frames (EU, abstention, VOI, MCDA, SDT, search/control, Leveson,
  NATM/snap-fit/Norman); not SWE-only. Extractable-from-state boundary
  map (self-contained vs needs outside knowledge)
- `.agents/skills/augustus/references/judgment-class.md` — the class (Jev
  exemplar, not monopoly): open heads (Laya, kev, encoder DeBERTa, LoRA
  distill, domain specialist on independent gold), constrained-AR (TypeAR, pcdServer), announced decision-model (Watch),
  open multimodal RLCD (blackwood-rlcd; not Archer), Laya ONNX port,
  contract-compatible local `/v1/systemone` (stub until hf scorer; also kev pointer / von §49 Needle SAN snapshot ≠ this-pass 395M / n=78 — not replicas; **jevify** CUDA/PyTorch packed-logprob cousin — uncalibrated likelihoods ≠ Noul; **jeff** GLiFormer-400M encoder drop-in — not a Jev replica; **sysone** loopback gateway routes hosted + local, not a model; **githubnext/localjev** prompted JSON ≠ structured-read logits — ≠ kunchenguid/local-jev),
  GLiNER/GLiClass species (locate vs categorize vs local multi-head;
  GLiNER2.5 extractive compaction as a named job, not a new species;
  GLiNER code-graph indexer + escalate-S2, 10–50× unfilled;
  GLiNER2 observe→score-among-candidates computer-use as a *different*
  named job, not GLiNER2.5; typesafe-computer-use OCR+AX desktop hosted Jev
  of the same hole, never screenshot-to-frontier for the decision;
  **gliner-native-runtime** unofficial Swift/Core ML GLiNER 2.5-small on ANE — entity spans + confidence, not Choice/Score/Noul, not TypeSafe),
  **Decision Graph Protocol** (numerous-com/dgp; Jev-first assessor-neutral; app retains permissions/effects; guarded commit / receipt/next frame; not an official TypeSafe spec),
  **kev family** (Archer-arch fidelity; OOD 0.76–0.77 vs Jev 0.86; `/v1/systemone` drop-in is not a Noul; replica honesty),
  **OpenJev** local `/v1/decide` (not TypeSafe drop-in; distinct from
  hraness/sysone OpenJev runners), **semif-serve** SemIf `/v1/systemone`
  runoff (wire-compat ≠ replica),
  listwise vs decision objectives, vision scoring, when-to-use axes
  (including decision-model vs constrained LLM),
  agent-architecture portents
- `.agents/skills/augustus/references/formal-methods.md` — judgment vs
  proof ownership; Alloy Analyzer vs Apalache (finder ≠ BMC ≠
  inductiveness); TLA+/Quint/P/NuSMV/PRISM/Event-B/mCRL2/KeYmaera;
  Dafny/JML/Frama-C/SPARK/ITP; DST trio (Antithesis hypervisor, Resonate
  HQ durable-async Lean+oracle+SDK, PufferLib env+seed); TOCTOU-of-Noul,
  soundness theater, AI×FM harms (Hillel, Cauli); NATM/snap-fit/Norman/
  Leveson/Kent/Shirky
- `.agents/skills/augustus/references/formal-semi-formal.md` — one-screen
  alias of the FM pillar
- `.agents/skills/augustus/references/mixed-architecture.md` — default
  placement: judgment-class model + LLM + code; preference lint; provider
  (Jev default / other family with self-eval); dual-process S1 decide / S2
  generate; component node; DOM-as-text + fan-out; shadow-mode compaction rollout;
  fail-open wake vs fail-closed merge-gate; Harbor on/off routing;
  hybrid local decide + remote fill; `DONE` ≠ verified success;
  evidence-preserving stdout prune (hard envelope then Noul;
  OpenCode host-port indiejoseph/opencode-jev-pruner, jev-zen /
  jev-1.13-free, zen-chat ≠ Noul);
  Decision Graph Protocol envelope (numerous-com/dgp;
  frame→assess→commit; app retains permissions/effects;
  Jev-first assessor-neutral; assessment batching;
  hard-gating DGP as safety theater);
  calibrated meaning-grep live tree (can1357/jegrep;
  path+range Nouls; no embeddings/index/daemon;
  ~$0.01–0.03 typical; agent --json);
  cost-derived YES/NO/UNSURE overlay (Kungie/gut;
  thresholds from costs not hard-coded; auto-batch
  same-object; overlay not species);
  typed-callback control flow (Illusion47586/judge;
  exactly one app-owned callback; explicit uncertain);
  variable-N option scoring (zwliJay/jev-forge;
  dynamic candidate bags; not a sixth species);
  open NAR replica late-catch (wfzyx/von; Needle
  snapshot ≠ 395M table; replica honesty);
  specialist S1 computer-use (Cua-S1 form-v0; plan ≠ execute; not TypeSafe Jev);
  judgment as a language primitive (hunch); decision-native RAG
  (retrieve wide → decide → evidence set); classify-first MCP
  (jev-sift); draft-gate heartbeat; living class-pattern atlas;
  public judgment wall; PR attention ≠ correctness; session-sticky
  first-prompt route; capability kernel (secrets never in agent;
  Jev SENSOR); typed control plane around DSPy; engine owns truth /
  Jev owns judgment; human-confirmed kill; decide→policy→LLM leftover
  cascade; wire-compat encoder backend; loopback gateway;
  closed-vote computer-use (no planner LLM); host-owned handlers ×
  System One; active-learning triage (do not distill Jev as teacher);
  evidence-packet explorer; meaning-grep AND/OR/NOT; OMP prompt
  suppression (permission vs probability; operator owns the bar);
  judgment ≠ permission (skill-broker outline, not a recipe);
  constrained optimizer + S1 features (slo-router; never sole
  hot-path gate); effect-based shell gate (privilege ≠ verdict);
  attention filter / VOI (jev-lens; never blocks; never green unless sure);
  measurement owns endorsement (jev-packs evidence-gated + jevassert record/replay CI);
  Jev supplies evidence / code owns authority (actiongate-jev);
  ranking ≠ calibration (never hard-threshold raw p as frequency);
  hot-click CU (ego-jev; indexed table; S1 on click path);
  Jev judges relevance / code decides structure (jev-compactor);
  local rules first / never auto-train on own hides (x-reply-filter);
  control-plane combinators (not chat turns); skill VOI / abstention
  (skillranker hook fail-open); receipts not leaderboard (atlas);
  OOD / AUC ≠ ECE (sign flips by type); thinking-budget bake-off
  (frontier-100); turnstile evidence≠authority + replay; MLX
  one-pass replica economics (jevmlx; softmax ≠ Noul);
  never confidently wrong / TLA+ compose (jev-labs);
  no seal no advance / coverage ledger (seal; mint ≠ product
  brain); sureness bands (how-sure-is-jev; max_prob is generous);
  JevBench Harbor practice (calibration not in Main Score);
  CI typed gate before expensive review (ci-gatekeeper);
  Codex MCP host adapter (jev-in-codex);
  judgment as attention redirect (jev-preflight; not a merge blocker);
  compress-before-first-send (dizk/jev-lens; 79% fewer tokens);
  tools≠use / SessionStart over hoping (carryforward 0/4);
  observational memory (pi-om keep/kind verbatim);
  open-Jev class (openvons; JevPick; wire-compat ≠ replica);
  physical-world S1 (HA-Jev; not for locks);
  judgment outside the store (jevql CLI);
  landed-script trust / headless≠auto-approve (construct);
  digital-design combinators (jev-combinators rename + extended five);
  VOI cache admission (jevcache 0 FP/100);
  decision-ledger memoization (hyperspaceai/jevcache; fingerprint after redact; recall vs decide; Cache hit ≠ correctness; ≠ kushals256/jevcache);
  GEPA alignment loop (sutro-sh/jev-align; human labels only; score never auto-accepts; production capture flywheel; ≠ caiovicentino/jev-align);
  worth-your-attention VOI (ThinkyMiner/Winnow ≠ kevinpita/winnow);
  Jev WHETHER / Python HOW / LLM WHAT (hermes-jev-router);
  typed escalate/continue/abort baton (jev-handoff; gate never grants);
  Playwright executes, Jev chooses (browser-jev);
  OpenJev `/v1/decide` ≠ drop-in + SemIf runoff wire;
  conflict ≠ ignorance (named Choice escape);
  decision-as-memory flywheel (DGUI_HYPERMEM-JEV);
  record/replay CI (jevassert LANDED);
  measurement owns endorsement now has a runner (jev-packs
  2,990-case matrix; calibration+cost first-class);
  failure-finding arena (jevarena ≠ jev-arena);
  BBQ stereotype/uncertainty/cost (not a bias cert);
  decider≠executor (jeffrey; pick ≠ fill);
  sentence-as-rule lint (mizchi/jev-lint is jevlint rename ≠ huntedman/JevLint);
  VOI hunk prune (prune-review ~20% cost target);
  whole-repo intent VERIFIED/VIOLATION/UNKNOWN;
  GLiNER2 System One spec ≠ replica;
  open replica substrates (grande / laya-jolt / JEV-CPU /
  local-jev measured not equivalent);
  githubnext/localjev prompted JSON ≠ structured-read logits;
  persist constraints across compaction (pi-heed);
  Harbor SGR-judge contract (jev-judge-bench; canaries ≠ quality;
  no headline yet; ≠ jevarena/jevbench);
  hand no-text steps (jev-use; Vercel drops confidence);
  Pi System-One control plane (pi-jev-control; GUI never force-click);
  never free-generates (jev-gpt tree of Choices);
  OpenRouter recipe atlas (jev-cookbook; samples not benches);
  personal-history feed (jevfeed; no social graph);
  competing NAR claim-audit (openJev-verdict-2.0; PR #1; ≠ OpenJev);
  empty compaction-proxy skip (IPECTER);
  1-token logprob endpoint ≠ Noul (chakuho; coverage ≠ correctness);
  open replica engine (jevinf; argmax-parity ≠ ECE);
  unofficial Elixir SDK ≠ OTP peer;
  jevex n=16 files-to-read VOI;
  commit pre-review attention≠verdict (middle band);
  Hermes plugin is Agnes not TypeSafe;
  pi-jev-compact ≠ pi-jev-compaction;
  decision-native inbox (mailordinal);
  unofficial jev-cli not ready (≠ jevql);
  laya-multilingual English checkpoint confident-wrong OOD;
  schema-scorer peaked ranking ≠ calibration;
  productized System One HTTP (classifier.dev; label+confidence; batch ~1000);
  escalate-under-threshold (smart single-label <0.7; multi-label ignores);
  silent FALLBACK (granite 0.546 vs advertised 0.800; rh-guard owns the gate);
  systematic-review pointer (choxos/jev-reviewer ≠ egma-ai; two-pass Choice+Noul; human tick is the product);
  wire-compat ≠ logit-equiv (githubnext/localjev ≠ kunchenguid/local-jev; prompted JSON ≠ structured-read logits);
  Laya packaging ≠ new species (NandhaKishorM/laya; Router script-before-p; post-T ECE ≠ raw ECE; 0.85 still soft);
  external openjev census ≠ scored bake-off (@airesearch12; GLiNER2+routers class-boundary; incomplete vs watch; Harbor honesty watch);
  JevBench v1.2 geometric-mean I/C/S/K (cal ON rank; Jev 75.3 / SemIf 74.6 *theirs*; Luna I=96.8 rank #7; option-order 72→21; ×2/est. Harbor honesty; Laya absent gap; Qwen3.8 27B ≠ Archer);
  hourly 0842 already-folded recipe (wire≠logit · FALLBACK · packaging honesty · pointer-not-generator · leaderboard VOI; skip thin noise; hard-gate Noul as PR/quality = soundness theater);
  S1 never stalls / S2 one-use advisory (khordoo/jev-reflex-autonomy-lab delta; purple = consumed; Local controller ≠ githubnext/localjev; seed = geometry; 20% still soft; no pixels; S2 never grants);
  OCR+AX desktop observe→score→act (typesafe-computer-use; never screenshot-to-frontier for the decision; overlapping options = doubt; 155× *theirs* one screenshot; 0.4/0.5 still soft; **≠** jev-ultrafast **≠** cua-s1);
  ASR voice-browser observe→score→act (jev-voice-browser; never waveform-to-Jev; partial-speech VOI; spoken confirm ≠ auth; numbered overlay; 27/27 *theirs* fixtures; **≠** jev-voice-control **≠** nikolas-j **≠** OCR desktop);
  wrap-as-execution ALLOW/ASK/DENY (AgentGhost; wrap *is* the tool function; rules first; ASK throws; fail-closed; **≠** actiongate **≠** jev-use; rh-guard owns the gate cousin);
  JP genre atlas (@studio_yebisu; stars research-time ≠ eval; **≠** class census **≠** v1.2);
  external pedagogy / how-to-apply (@akshay_pachaar “Jev Clearly Explained”; LLM hammer; schema-safe ≠ correct; 200×/400× TypeSafe ceiling; shadow + questions-as-code; **≠** official docs **≠** Flavio);
  meaning-grep dedicated (jev-semgrep; proposition ≠ embedding; AND/OR/NOT after threshold; Semgrep.dev collision; not a gate; contrast-set refund);
  decision-validated UI (gram-render never authors text; jev2ui Jev decides / Gemini writes; valid ≠ good);
  decision-as-assert (jevtest ambiguous band; 0.85 still soft; record/replay);
  hybrid S1 (anima3 closed verb menu + hard safety; Qwen logprob; jeff confidently flat; do not invent Laya);
  pointer search (JevFind path then window);
  Harbor bake-off trio (jev-frontier-bench ≠ frontier-100; GLiClass product bakeoff; four engines / majority floor / calibration ≠ discrimination);
  authorship named escape (not evidence);
  non-SWE (ha-switchboard HA remains execution ≠ HA-Jev; n8n Low Confidence);
  compaction delta (fast-jev-compaction-pi ≠ pi-jev-compact ≠ pi-jev-compaction);
  full-distribution optimizer (jevloop UCB1+CEM; no LLM in the loop; mock default);
  deferred class (laya-vision SmolVLM `score` untrained ≠ blackwood ≠ Archer; Cerebellum-2B `/v1/decide` ≠ TypeSafe / wire-compat vs agent-routing; laya-grounded not drop-in / Platt not temperature);
  open LoRA replica (GestaltLabs/Jeff-1 ≠ logan-markewich/jeff; acc/ECE tradeoff n=9730 *theirs*);
  Jev-first bounded agent (stanley-code; empty ≠ approve; human promote);
  NL memory → beam-search FS (findme ≠ JevFind);
  price workers not the conversation (jevsubrouter; fail-open; counts ≠ dollars);
  Typed if (feelings `.feels()` default 0.5 is Noul-0.5-never-rounded; **≠** hunch **≠** Probably);
  Shadow then honor (apa-agent-harness ≠ AntonioCoppe/jev-harness; grok-bot-jev skill honor / A/B proxies ≠ tokens);
  Human every action (Essentiel-Jev never authority);
  Atom then sense (enzo-mcp independently falsifiable claims; ≠ jev-sift);
  File by Choice (pigeonhole OTHER skip; HF playground static ≠ classifier.dev);
  Question preflight (jev-reliability Nothing about accuracy; clduab11/jev-test bars ≠ scores; jev-rag-benchmark “Jev wins” is not an assumption; dairui1/jev-lab ≠ BrendanH18/jev-lab);
  Inbox read-only vs write (jevmail `gmail.readonly`; mailjay archive/trash after review; ≠ mailordinal)
- `.agents/skills/augustus/references/applied-mappings.md` — context sieve,
  exact-text keep/drop (extractive / pointer-not-generator; char-offset compaction; observed a11y/DOM controls; Bash stdout prune; verbatim session ledger / carryforward 0/4 tools≠use; classify-first MCP / jev-sift; Stagehand extract pick-and-copy; jevcumber meaning-as-spec; closed-vote JevOnly; host-owned waymode; jev-compactor framework-agnostic compact+gate 73% product-arm; dizk/jev-lens pre-send views; pi-om observational keep/kind), env triage (OpenSmoke + latch merge-gate; ci-gatekeeper pre-review typed gate; jev-preflight Stop-hook attention redirect, not a merge blocker), moderation/ranking (decision-native RAG evidence set; living class-pattern atlas; meaning-search without embeddings / jevgrep; meaning-grep jev-semgrep; evidence-packet jevex; measured RAG rerank vs generative rerank; sift ~$0.00003/post; ThinkyMiner/Winnow worth-your-attention VOI ≠ kevinpita/winnow), skill routing (route ≠ memory; session-sticky first-prompt lock; OMP/pi fail-open jev_route; OMP prompt suppression / omp-greenlight; skill-broker outline — Jev never grants access; slo-router constrained optimizer + S1 features; skillranker VOI / hook fail-open; jev-in-codex Codex MCP adapter; pi-jev-skill-bench Harbor roster-size harness; pi-jev-skill-suggestion strip-roster), capability kernel / human-confirmed gate (interlock vs toolgate; port-cleanup; permission vs probability; spoken confirm ≠ auth / jev-voice-browser; wrap-as-execution ALLOW/ASK/DENY / AgentGhost — wrap *is* execution; ASK throws; fail-closed; rh-guard owns the gate cousin; construct-auto-classifier privilege ≠ verdict + landed-script / headless≠auto-approve; actiongate-jev — Jev supplies evidence, code owns authority; turnstile — policy first, replay; seal — no seal no advance / coverage ledger; jev-labs — never confidently wrong; jev-handoff typed baton — gate never grants), decide→policy→LLM leftover cascade (jav-email-cascade), closed-vote computer-use (applied-mappings §9; ego-jev hot-click cousin; browser-jev Playwright executes Jev chooses; jeffrey decider≠executor; jev-use hand no-text steps; jev-gpt never free-generates; typesafe-computer-use OCR+AX desktop cousin; jev-voice-browser ASR voice-browser cousin), VOI hunk prune / whole-repo intent (prune-review / jev-intent-review), persist constraints (pi-heed; Jev never writes policy), Pi control plane (pi-jev-control), personal-history ranking (jevfeed; ≠ Winnow), OpenRouter recipe atlas (jev-cookbook), empty compaction-proxy skip (IPECTER), Pi verbatim summarizer replacement (pi-jev-compact ≠ pi-jev-compaction), decision-native inbox (mailordinal), commit pre-review (commitjev), jevex n=16 files-to-read, productized classification API (classifier.dev; spam/inbox/feedback), systematic-review pointer (choxos/jev-reviewer ≠ egma-ai; two-pass; human check never overwritten), prompted-JSON local `/v1/systemone` (githubnext/localjev ≠ kunchenguid/local-jev; wire-compat ≠ logit-equiv),
  Laya packaging (NandhaKishorM/laya Router over Hub ckpts; not a TypeSafe drop-in),
  external openjev census (@airesearch12 / Benchmark Heaven; tweet ≠ v1.1 ≠ live ranks),
  JevBench v1.2 scored board (geo-mean I/C/S/K; cal ON; 534 decisions; ≠ v1.1 87.6),
  hourly 0842 apply-the-five (already §73–§78; skip thin; soundness-theater PR gate),
  continuous-control S1/S2 (khordoo delta §80; escalate without stall; Local ≠ localjev),
  OCR+AX desktop CU (typesafe-computer-use §81; exclusive actions; split kind/item/site; writer/decider; 155× *theirs* one screenshot),
  ASR voice-browser CU (jev-voice-browser §82; partial-speech VOI; pointer spans; spoken confirm ≠ auth; 27/27 *theirs* fixtures),
  wrap-as-execution ALLOW/ASK/DENY (AgentGhost §83; wrap *is* execution; ASK throws; fail-closed; rh-guard owns the gate cousin),
  JP genre atlas (@studio_yebisu §84; stars research-time; not verified evals; **≠** class census **≠** v1.2),
  external pedagogy (@akshay_pachaar §85; schema-safe ≠ correct; 200×/400× TypeSafe ceiling; questions-as-code),
  meaning-grep dedicated (jev-semgrep §86; proposition ≠ embedding; boolean composition after threshold; Semgrep.dev collision; not a gate),
  hourly 1047 + deferred 0945 (`notes.md` §87; decision-validated UI; decision-as-assert; hybrid S1; pointer search; Harbor trio; authorship; ha-switchboard ≠ HA-Jev; n8n; compaction-pi namesake lock; jevloop; laya-vision / Cerebellum / laya-grounded),
  queued SIGNALs + jevsubrouter (`notes.md` §88; GestaltLabs/Jeff-1 ≠ logan-markewich/jeff; stanley empty ≠ approve; findme beam ≠ JevFind; jevsubrouter prices workers),
  hourly 1144 (`notes.md` §89; feelings typed if; apa-agent-harness ≠ jev-harness; grok-bot-jev skill honor; Essentiel-Jev never authority; enzo-mcp ≠ jev-sift; pigeonhole OTHER skip; playground static; jev-reliability Nothing about accuracy; clduab11/jev-test ≠ jevtest; jev-rag-benchmark “Jev wins” is not an assumption; dairui1/jev-lab ≠ BrendanH18; jevmail readonly / mailjay writes after review),
  hourly 1241 (`notes.md` §90; ZHUBoer/ego-jev reserved `__none__` / runWorkflow completed ≠ success ≠ jiangkoumo; jsort scores are relative / Noul not Choice for scale; groundedness-judge-bench native vs schema-guided / implicit_true included in yes; jev_playground 0 promotions / routing-backtest 0.0447%; yuyang2230/jev-agent-skill jev-1.13-free; jev-techstack-classifier stack_config.json; s1_ruby collapse late / `undecided?` abstain; 2389-research/judgement license null / confidence ≠ winner p; typesafeai-sdk-community not a new species; tpellet/hunch exit 3 / never-execute list; jev-file-search scores not calibrated accuracy; jev-linkmap Jev never sees S2 prose; muhammedilyasy/jev-mail metadata only; tidy none-of-folders stay; tab-bouncer pinned/audio/current never closed; lkclean Show fail-open; jev-yt-time-saver Show anyway; ORIGIN pause-if-no-Jev / validResponse sums-to-1; jev-crawlers risk bands never raw boolean; jevbrain AUTO_ACT is not a Noul),
  hourly 1347 (`notes.md` §91; judgekit YAML classify/score/route/verify; typed-judge-kit verdict-in-code; alsoleg89/decide packing VOI / 0.8 ≠ 80% accuracy ≠ jev-sift; Jev-Calibration Platt ECE 0.117→0.052; jev-calibration-arena never acts ≠ jev-arena; ctmx/openrouter-jev-mcp Decision-as-Plugin; cyrusasco/typesafe-mcp noul deadband 0.35–0.65; FrancoisChastel/jev-code ≠ npm jev-code; claudecode-jev-marketplace fail-open not hot path; pedroknigge/mcp_jev packs not ask_jev; codaaiteam/jev-skill jevtypesafeai.com ≠ TypeSafe; hermes-switchyard ≠ hermes-jev-router ≠ hermes-plugin-jev; nanoprune 2.8MB ECE 2.58%; smartdio/jev-browser-agent ≠ ZHUBoer/ego-jev; Dakai/omp-jev-web DONE ≠ proof; hari007sh/jev ≠ dannote/jev; 0thernet/system-one-skills deterministic verify; typed-gate band [0.40,0.60] is refusal; pi-jev-gate fail-closed; choice is the verdict),
  hourly 1441 (`notes.md` §92; Foq ~25ms/2.2GB local; rev prefill-only + HF jev-0.5b; robfrase/jev planning memo; typesafe_agent_gates 27/27 / 31/31; EpicEric/safe-sh static remainder; pastepilot Confirm before act; Jev-Reranker live Jev not yet measured; sessionwise opt-in relevance; jev-search pointer sieve; 400ms Salesforce WebMCP; typesafe-scheduler-diagnostics advisory; droidjev screenshot-free; Tewoto1 jevcu planner still writes; ha-conversation-jev Jev→Grok; dsh-jev can only gate; jev-classification-benchmark specified not run; jev-luna-pagerduty p≥0.50; meldltd/meldecision laya-go ONNX; laya-doom never pixels; logixism/laya-api empty README; akpsahan/laya ≠ Archer; choxos/jevchess engine owns truth; jev-drive sim not AV; story-arc Jev never authors; jev-hs-assistant HS6; golergka/jev-plays-starcraft-2 UI-verified ≠ API Victory; awesome-jev-use-cases catalog; Nibir1/typesafe-go ≠ official; rh-guard owns gates; Soft Noul ≠ hard safety),
  SIGNAL jevcache/jev-align (`notes.md` §93; fingerprint after redact; recall vs decide; publish fingerprints+answers; CI replay as Harbor cousin; Cache hit ≠ correctness; hyperspaceai/jevcache ≠ kushals256/jevcache; human labels only; score never auto-accepts; production capture flywheel; sutro-sh/jev-align ≠ caiovicentino/jev-align; memoize typed decisions; VOI of cache hit; GEPA + System One; Soft Noul ≠ hard safety),
  SIGNAL enzyme/JA ModernBERT/Gemma (`notes.md` §94; guidance ≠ hook; catalysts ≠ summaries; compile-time System One; unofficial ≠ TypeSafe; format_version modernbert-jev/1; Argos1111/jev_local ≠ us/jev-local ≠ kunchenguid/local-jev; LFM default ≠ ModernBERT backend; Nemotron ≠ TypeSafe Jev; not a calibrated replacement; djev-dev complements djev-spark; images as Choice options; Laya essay numbers *theirs*; Router/OOD confidence; hosted bootstrap ≠ silent TypeSafe; Soft Noul ≠ hard safety),
  hourly 1541 (`notes.md` §95; difficulty + policy thresholds + JSONL trace; jev-codex-pilot model + reasoning depth; keep/shadow/hybrid/reject; quarry evidence projection; Frank-ZY-Dou/awesome-jev robotics/3D/control; one-dollar-tahoe TypeSafe Jev defense eval; jevguard calibrator/cache/escape; jev-ci-selector CI shadow mode; llama-jev llama.cpp replica; petercr/jev-orchestrator ≠ FleeexCorp/jev-orchestrator; seb4ez/jevguard ≠ AseemPrasad/JevGuard ≠ pablozr/JevGuard; webNeat/llama-jev ≠ WiktorB2004/llama-index-jev; rh-guard owns gates; Soft Noul ≠ hard safety),
  hourly 1639 (`notes.md` §96; OpenCode jev-pruner context sieve; observe→score-candidates→prune; jev-zen / jev-1.13-free; zen-chat ≠ Noul; fail-open original; keepScore >0.1 floor; host port of tamaratran/jev-pruner; indiejoseph/opencode-jev-pruner ≠ nrdz-labs/fast-jev-opencode; jev-webagent-bench empty stub; Kiln-AI/jev_jsonschema noul_threshold 0.5; NSStudent/JevSwiftSDK unofficial; Soft Noul ≠ hard safety),
  SIGNAL gliner-native-runtime (`notes.md` §97; GLiNER2 native Apple path; unofficial Swift/Core ML GLiNER 2.5-small; entity spans + confidence; not Choice/Score/Noul; not TypeSafe; label descriptions as schema; on-device ANE economics; honesty locks; shershah1024/gliner-native-runtime ≠ Fastino; ≠ gliner25-compaction ≠ gliner2-ultrafast ≠ Eran-BA/Jev_from_GLiNER2 ≠ NSStudent/JevSwiftSDK ≠ jevmlx; default threshold 0.1 still soft; Soft Noul ≠ hard safety),
  hourly 1740 (`notes.md` §98; Decision Graph Protocol frame→assess→commit; app retains permissions/effects; Jev-first assessor-neutral; guarded commit / receipt/next frame; assessment batching; hard-gating DGP as safety theater; numerous-com/dgp ≠ TypeSafe official; jegrep calibrated path+range Nouls; no embeddings/index/daemon; ~$0.01–0.03 typical; agent --json; can1357/jegrep ≠ Bentlybro/jevgrep ≠ uehaj/jev-semgrep; Archer-arch fidelity; kev family OOD 0.76–0.77 vs Jev 0.86; block-causal isolation; pointer/readout CE-trained; /v1/systemone drop-in; replica honesty; Soft Noul ≠ hard safety),
  hourly 2145 (`notes.md` §102; question-linting of Jev questions themselves; nine jaggedness rules, no API key, no labelled data; static lint ≠ measured separation; yodablocks/jevq ≠ tenbin ≠ JevLint ≠ commitjev; open-weights Laya as class exemplar (binding); Nx/Bumblebee runtime; host chooses backend; ChristianAlexander/laya_ex ≠ system_one_sdk ≠ dannote/jev ≠ NandhaKishorM/laya; on-chain/edge Laya deploy; parity_verified stays false; model output never grants Tx; humandebri/IC-Laya ≠ laya_ex; auditable weekend replica; Jev outputs never used for training; unpaired 0.577 vs 0.727; agilabs-ai/jev48 ≠ JevBench ≠ Mapika/decider; adversarial dual-judge / framing attack surface; comparative framing is the usable judgment; prior injection crowds out evidence; copyleftdev/ember ≠ ember.js; Laya specialist fine-tune pipeline; training still GPU-pending; PIXELZX0/XERON ≠ convaiinnovations/laya; Hub Laya replica drop; daliborsb/laya ≠ convaiinnovations/laya ≠ NandhaKishorM/laya; System One student distillation corpus; gold is programmatic; teacher is closed-API clone; do not distill Jev as teacher of record; MagaBitmex/jev-4b-distill-data ≠ missing student checkpoint; non-LLM VIN System One; planning depth not chat; lewislululu/jevon ≠ douglance/jevon; source-bound evidence checks; local quote mismatch needs no API; exit 0 ≠ claim truth; WaynezProg/jev-kit ≠ jonathanavis96/jev-kit (Airlock) ≠ jev-use ≠ jev-mcp; Soft Noul ≠ hard safety),
  hourly 2246 (`notes.md` §103; independent System One evidence catalog; 19 reviewed records; scores not one leaderboard; no external record currently reproduced; TokenTrim no-Jev matched hybrid 62.4%; reachjalil/system-one-bench ≠ mallahyari/system-one-benchmark; 21 tasks · 134 items · 208 questions; scenes from public GitHub contracts, not production logs; SivletLabs/jev-eval ≠ willkelly/jev-evaluation ≠ 4esv/jev-eval ≠ xxkuboxx/jev-eval ≠ onlyoneaman/jev-eval ≠ dayhaysoos/jevals; option isolation (sibling-blind); permutation-equivariant; Hub OWNER not published; nafisazizir/hev ≠ jaredpalmer/kev; frozen local LLM logits, no trained decision head; residual-head 9,222-param decreased 73/96→67/96; confidence = 1−normalized entropy, not P(correct); yuki-oshio/mini-jev ≠ r-ms/mini-jev; Jev classifier as autoregressive next-token predictor; ChatJev-style soundness theater; erik-dunteman/ChatJev ≠ dannote/jev ≠ jev-gpt; calibrated decision head × AlphaProof value head; implementation-layer isomorphism, semantic difference; timeout = censoring; do not launder Noul as proof; parallel rank-prediction vs serial selection; independent questions can conflict; zzzzzec/jevsort ≠ keltokhy/jsort; curated open System One ecosystem catalog; rupeshpoojary9/awesome-open-system-one ≠ AnotiaWang/awesome-jev; arXiv paper radar with Jev relevance scoring; ranking ≠ calibration / 0.5 still soft; fail-open failed evals not marked seen; Soft Noul ≠ hard safety),
  hourly 2340 (`notes.md` §104; train calibrated ~27M from scratch; typed Q→prob dist / one forward pass / no LLM decode; hyusi2003/MiniSystemOne ≠ Colvin0315/MiniSystemOne; description-only stub / size 5; ESCI hard probe fails four of six; jev_bool ECE 0.242 inversion 0.255; do not re-fold §60 six-gates as new; jobbyjev one-request-per-company from batch-size result; find/design/evaluate TypeSafe Jev decision loops; karanb192/jev-architect ≠ samtay32/jev-system-architect; Jairik/jev-distiller size 1; distill-Jev UI stub / do not distill Jev as teacher of record; post-launch scored use-case map / Jev self-scores then human curation; licensedsaucer9-web/jev-opportunities; Jev-inize a use case into classifier/router; gavinHuang/jevinize → simple-jev not TypeSafe; featherless-ai/simple-jev; compare saved decisions / same label can still change the branch; VihaanAgarwal/jev-diff ≠ Saik0s/diffusiongemma-jev-macos; not tested with a live Jev API key; constrained logprob + temp/Platt ≠ Noul; OpenJevPro pastes openjev-sglang JevBench as own; zhangcy122/OpenJevPro ≠ IamBusy/OpenJev ≠ ekzhang/openjev-sglang; PolyForm Noncommercial; SmolLM-135M / sub-70ms / 0 output tokens; demo P(True) 0.5052 / Choice conf 0.2872 / Score conf 0.0055; README claims MIT / GitHub license null / no LICENSE file; patelvishwa112/jev-system-one-rlcd ≠ arnabgho/rlcd-lite ≠ blackwood-rlcd; source-backed Awesome Jev radar / 306+ commit-pinned; logicrw/awesome-jev-projects ≠ AnotiaWang/awesome-jev ≠ yibie/awesome-jev ≠ cobanov/awesome-jev ≠ rupeshpoojary9/awesome-open-system-one; auto GitHub sync / Issue-only submissions; hashed n-gram encoder / rival-aware attention; olanotolu/jevbetter vs jevlike starter; synthetic hard menus top-1 0.916 vs 0.873 / ECE 0.0182 vs 0.0367 / 40 vs 4608 menus/sec; shuffled-context control 0.335; Soft Noul ≠ hard safety),
  hourly 0042 (`notes.md` §105; structured probability readouts; distribution > argmax; Noul 0.5 midpoint; score is expectation not integer; bare HTTP not SDK; Arohtea/jev-readout; Jev-style Choice/Score/Noul from ordinary models; optional DSH plugin; schema-valid ≠ calibrated; gulagala001/jevify ≠ Mintzs/jevify; Laya RLCD benchmark; 40.3% below constant-answer; open-weight measurement; mourad-ghafiri/laya-rlcd-benchmark ≠ yibie/laya-jev-lab; cheap fail-open semantic edge; second signal not sole; FastLoopError catch; SupremeDreamZ/jev-fastloop ≠ jev-ultrafast; asking more questions in one call; 0.980 at every N; nearly not fully deterministic; TheWebDevel/jev-fanout; Qwen3-VL perception + Jev decisions train RL; 0 model calls at deployment; VLM alone 1.7 vs +Jev 4.4; harneet2512/reflexrl ≠ khordoo/jev-reflex-autonomy-lab; independent Jev API vs Laya; cascade 0.60 matches 78% at 1.8×; noul facts not judgements; yibie/laya-jev-lab ≠ dairui1/jev-lab ≠ BrendanH18/jev-lab; GLiNER vs GLiFormer vs Laya vs Jev; extractors ≠ decision engines; Laya dict-instructions collapse 58.3%; umstek/zero-shot-ie-bench; decisions-per-minute & cost; 204 moves vs 73; throughput not intelligence; angelgalvisc/snake-arena-jev-vs-llms ≠ vtrivedy/jev-plays-games; behavioral contracts; pin expectations eval upgrades; raw 0.94 is not a release; sathariels/jevcheck ≠ dayhaysoos/jevals ≠ SivletLabs/jev-eval; evidence-linked dependency upgrade; Jev never generates filenames; no_direct_evidence ≠ safe to merge; GaneshVG18/upgrade-radar ≠ LYchoon/paper-radar-jev; discography theme/mood/complexity; five atomic questions one call; lirantal/discoprint; Soft Noul ≠ hard safety),
  hourly 0243 (`notes.md` §107; Benchmark-driven Jev router and judge; cheap alone is not success; Jev does not write, sum prices, or claim accuracy %; Sol 94.2 / Luna 83.9 / Jev path 89.7; 19.2% Sol / 62.3% cost save / 4.5pp miss of 2pp non-inferiority; p50 latency worse than Sol due to routing overhead; erendikmenn/jev-llm-router-benchmark ≠ jev-rag-benchmark ≠ ryantsai/jev-llm-router; Express + node:sqlite; mock and Jev decision engines; previous_ticket_count >= 3 is code; MIN_CONFIDENCE 0.6 still soft; substring false positives; aesaganda/jev-ticket-router ≠ SarathChandraBellam/jev-vs-llm-ticket-router; Universal Figure & Diagram Router; confidence ≥ 0.85 hard-gate is theater; generative AI banned from scientific plots; six visual branches; hoangngochuong24947-gif/jev-figure-router; human-labeled (state, question, label); 166,054 rows / 22 configs; soft_label for human uncertainty; Praveenrajus/jev-bench ≠ fstandhartinger/jevbench; ternary bonsai System One GGUF; openjev's mechanism, Bonsai's weights; Hub does not ship weights; 100/100 easy T/F is not Harbor; label_mass ≠ correctness; stock llama.cpp Q2_0 silently gibberish; NicolaiMTLassen/open-bonzi-jev ≠ NicolaiLassen; transformers.js DeBERTa ONNX; source:com-kotobalabs/open-jev-deberta-v3-large; temperature 1.05; AutoModel from_pretrained works; onnx-community/open-jev-deberta-v3-large-ONNX ≠ system-one-qwen3.5-4b-scorer-ONNX; 107★ densify; GH 151M vs README 149.6M; PR #1 now closed unmerged; do not re-fold §71 claim-audit as a beat; typed decisions, RLCD, confidence-gated routing; structured ≠ correct; mock not live API; 26 tests; wjdjdakf17/jev-study ≠ baekenough/jev-study; do not reopen or amend PR #23 or #24; Soft Noul ≠ hard safety),
  hourly 0145 (`notes.md` §106; Turn any open LLM into System-One Jev; uspraveen/Jevify ≠ Mintzs/jevify ≠ gulagala001/jevify; Jevify-any-LLM architecture probe; description-only stub / size 0; Train encoder-only calibrated decision models from a task sentence; Exu is a toolkit, not a method; strictly proper scoring rule; Pre-alpha; Ruivalim/exu-base; scratch-trained calibrated decision model; typed Q → probability dists; Colvin0315/MiniSystemOne ≠ hyusi2003/MiniSystemOne; no published weights download URL; 90.5 seconds / 29.2% pipeline evidence; p_i/p_j independent of other candidates; Recipe for calibrated decision models — small model out; init → synth → train → eval → serve; 91.1 % / ECE 0.022 *theirs*; Jev zero-shot 75.1; scienthoon/luce; Put Jev's three headline claims on trial; 0.5B local GPU; 46x speedup / accuracy identical; ECE 0.624 sentiment catastrophe; bigger model worse calibration; RichardoMrMu/jev-mini ≠ yuki-oshio/mini-jev ≠ r-ms/mini-jev; System-1 decision engine for local LLMs; structured choices only; JSON parse of generated text ≠ Noul; TypefAI JEV / Journal Entry Voucher; tapsin/jev-local ≠ us/jev-local ≠ Argos1111/jev_local; Jev 1.13 reward-model eval across 8 benchmark tracks; 40,940 examples / 0 API errors; RewardBench v1 92.58%; Precise IF 50.63%; goya4140/jev-reward-model-evaluation; Scaffolding in progress; Jev vs LLM support-ticket routing; static + live decision bench; TypeSafe's own published benchmark; illustrative simulations, not live API calls; JevBench v1 — smart/cheap/fast/reliable; I/C/S/K 25% geometric mean; classifier.dev fast tier 84.8 is Jev behind its own API; do not re-fold §78 v1.2 board as new; Laya (421M) 70.1 now on board; Zero-shot/few-shot LLM routing; hard budget filter before Jev; Jev never asked to perform budget arithmetic; Jev judges the next state, XState enforces transitions; simulation uses synthetic keyword fixtures; catalog gravity; v-modal/awesome-jev-tools; ★339 live REST; curation is not endorsement; crawler-maintained directory; Daily GitHub + npm sweep, human-merged; RadRebelSam/awesome-jev ≠ AnotiaWang ≠ yibie ≠ cobanov ≠ logicrw ≠ v-modal; HF peft SPLADE/BGE reranker; rdxtremity/jev-reranking ≠ carlaiau/jev-reranking; query-side encoders, not a Jev replica; ONNX System One Qwen3.5-4B scorer; source:pngwn/system-one-qwen3.5-4b-scorer; CC-BY-NC-4.0; temperature 1.75; transformers.js AutoModel cannot load this graph; Consistency benchmark Space; This Space contains no benchmark result yet; 12-case plumbing fixture; do not reopen or amend PR #23; Soft Noul ≠ hard safety),
  hourly 2041 (`notes.md` §101; resume-screening bias audit methodology; name×resume factorial independent Nouls; callback determined by resume quality; mean-probability name gaps operationally negligible; natemoo-re/bias-bench ≠ BBQ; Plan/PRD panel → code-owned pass|review|block; cheerleading out of scope; austindixson/planalyzer ≠ single-goodness Noul; cost-aware multi-model routing/escalation; decide vs do; successful-task cost; cannacre8ive/switchboard-ai ≠ ha-switchboard ≠ hermes-switchyard; frozen-protocol zero-shot bench; TypeSafe Jev vs PrismNLI vs Laya; contamination caveat; elcronos/jev-vs-open-decision-models ≠ JevBench ≠ DMB; context-window admission control; VOI gate which tokens are worth the expensive model; fail polarity per lens; on small inputs lenses lose money; cvsgireesh/jevusher ≠ jev-sift ≠ winnow; typed decision control plane; receipt ≠ authorization; historical-v0 zero retained cases; MokiMeow/jev-fabric ≠ jev-forge ≠ dgp; live 15-dim typed rubric re-score per pause; scoring economics exemplar; OpenJev/Codiv ≠ TypeSafe hosted; jose-troche/live-rubric ~$0.000004 desc / ~$0.000006 README; adversarial pre-registered Jev eval; 28 predictions before data; 123,805 requests; confidence does not track ignorance; polite injection 65% / crude 0%; willkelly/jev-evaluation ≠ jevals ≠ jev-baselines-eval; provider-neutral Elixir/BEAM Noul/Choice/Score SDK; class infrastructure; nshkrdotcom/system_one_sdk ≠ typesafe_sdk ≠ dannote/jev; Soft Noul ≠ hard safety),
  hourly 1943 (`notes.md` §100; Jev IS the if-statement; judgments/probabilities drive branches; text model only writes prose; interpreter owns variables/loops/budgets/replay; otherwise maybe / confidence gate; chaos samples after the gate; southpolesteve/probably ≠ carldaws/hunch ≠ feelings ≠ Kungie/gut ≠ Illusion47586/judge ≠ tidymodels/probably; 133★ / forks 10 live; build calibrated classifiers from human feedback; retrieve by relevance not resemblance; one calibrated yes/no per memory in one request; pointer mode 17/18 19/20 *theirs*; embedding resemblance misses the allergy; samdotmak/jev-recall ≠ jev-search ≠ jev-sift ≠ carryforward ≠ chopratejas/invalidate; memory leases ended by new evidence; six Nouls then fixed rules in code; 0 of 157 false invalidations; questions/plans/directives are not evidence; unsure → review queue; host keeps the store; name↔body / comment truth / test-claims; mizchi/jev-lint is mizchi/jevlint rename; no shipped rule has severity error; ~1 in 5 findings wrong *theirs*; mizchi/jev-lint ≠ huntedman/JevLint ≠ MichitoSugawara/jev-lint; JSON Schema → typed JSON via Jev; noul_threshold 0.5 decoder not a proof; IncompatibleSchemaError lists every bad property; on-device Laya CoreML ANE; ~5 ms P50 short decisions; 189/189 FP16 checkpoint parity; 10× not achieved; mizorewww/laya-coreml ≠ gliner-native-runtime ≠ jevmlx ≠ NandhaKishorM/laya; softmax over allowed tokens ≠ Noul; question-first cache; Micha0827/snapjudge ≠ githubnext/localjev ≠ jevmlx ≠ cendress/SnapJudge; Jev-first Pi agent loop; slow-LLM fallback; explicit action menu / CandidateSource unimplemented; 62 tests wiring not quality; direwolfiy/JevPi ≠ standardagents/jevpilot ≠ pi-jev-control; probably is a language not an overlay; Soft Noul ≠ hard safety),
  hourly 1843 (`notes.md` §99; cost-sensitive decision theory × System One probabilities → control flow; thresholds derived from costs not hard-coded; YES / NO / UNSURE from cost_false_yes / cost_false_no / cost_human; auto-batching same-object questions; Kungie/gut ≠ tpellet/hunch ≠ carldaws/hunch; judgment vs generation; deterministic execution after probabilistic judgment; exactly one app-owned callback; explicit uncertain branch; Illusion47586/judge ≠ lexingtonhibiki/judgekit ≠ Ascurse/typed-judge-kit; variable-N option scoring as the trainable object; dynamic candidate bags not fixed label sets; zwliJay/jev-forge ≠ NanoJev; NAR local drop-in; open replica economics / latency vs closed Jev; wfzyx/von late-catch HIGH; competing NAR claims / replica honesty; typed judgments vs chat judges on guardrailing; ishaannk/llm-vs-jev cross-note only; deeper integrity fold is rh-guard; nothing wins outright; can be argued out of guarding; overlays not species; Soft Noul ≠ hard safety)
- `.agents/skills/augustus/references/faq.md` — "just classification",
  stack replacement, Jev vs open head vs encoder vs LoRA vs constrained AR vs kev vs blackwood,
  wait-for-Archer, missing-other confident-wrong, soft project rules vs linter (Abide), extractive/pointer-not-generator, compaction summarize vs pointer, encoder vs Jev compaction, fail-closed keep_full, shadow-mode rollout, fail-open vs fail-closed wake vs CI gate, observe→score→act backend-agnostic, hybrid local decide + remote fill, DONE ≠ verified success, stdout prune vs session compaction, Cua-S1 vs TypeSafe Jev, plan ≠ execute / dry-run, local drop-in vs stub scorer, route ≠ memory, when-it-holds / extractable-from-state, decision-model vs constrained LLM, dual-process S1/S2, S2 never flies / Local controller ≠ localjev / purple = consumed, combinatorial grid ≠ extractive, GLiNER vs GLiClass vs CLIP, LLM-as-judge, in-engine vs CLI store,
  hard envelope (bitrate / planner), not-another-how-to,
  uncalibrated local likelihoods ≠ Noul, decision-native RAG, classify-first MCP, living applied-mappings atlas / class patterns, draft-gate silence ≠ safer, robotics text-state vs pixels, Stagehand extract pick-and-copy / fast-path not replacement, public judgment wall / six parallel questions, meaning-search without embeddings, attention≠correctness PR review, skills→oxlint not a hard gate, session-sticky fail-closed routing, measured RAG rerank vs generative rerank, cascade
  sign-flip / calibration theater, Precision PDF honest negative,
  type-safe ≠ correct / Jev is SENSOR not policy, Ax/DSPy knobs vs
  typed control plane, native vs verbalized confidence, engine owns
  truth / Jev owns judgment, train specialist vs few-shot hosted,
  Noul 0.5 cannot-tell never rounded, calibration ≠ sortable,
  local `/v1/systemone` ≠ Jev (GLiFormer / gateway),
  do not distill Jev as teacher of record, PCD O(1) ≠ calibrated Noul,
  closed-vote CU vs Stagehand pick, OMP/pi fail-open vs pi-jev-approver,
  permission vs probability / operator owns the safety bar, judgment ≠
  permission / Jev never grants access, eval integrity / instrument not
  score, Jev not sole hot-path gate / constrained optimizer + S1 features,
  privilege ≠ verdict / effect contracts, attention filter not permission,
  measurement owns endorsement / evidence-gated packs, Jev supplies
  evidence / code owns authority, ranking ≠ calibration / never
  hard-threshold raw p as frequency, Jev `done` ≠ browser success,
  never auto-train on the model's own hides, pointer compact ≠
  LLM summarize, combinators not a new model, AUC ≠ ECE / sign
  by type, thinking-budget bake-off, local MLX one-pass ≠ Noul, never confidently wrong / TLA+ compose, no seal no advance, sureness vs max_prob, JevBench calibration not in Main Score, CI typed gate before expensive review, Codex MCP adapter, two jev-lens products, Stop-hook not merge blocker, tools≠use, openvons not TypeSafe, Noul not for locks/heaters, two Winnow products, OpenJev `/v1/decide` not drop-in, SemIf runoff ≠ replica, combinators rename + extended five, Noul conflict≠ignorance, jevcache fail-open, typed baton never grants, jevassert record/replay CI, jevarena≠jev-arena, BBQ not a bias cert, jeffrey pick≠fill, jev-lint is jevlint rename ≠ JevLint, local-jev not equivalent, constraints survive compaction (pi-heed), jev-judge-bench≠jevarena≠jevbench (no quality headline yet), jev-use≠ultrafast / Vercel drops confidence, pi-jev-control GUI never force-click, jev-gpt never generates, cookbook samples not benches, jevfeed no social graph, openJev-verdict claims ≠ OpenJev / not endorsement, 1-token logprob ≠ Noul / coverage ≠ correctness, jevinf replica ≠ TypeSafe, elixir-sdk ≠ dannote/jev, jevex n=16 rename, commitjev middle band, hermes-plugin-jev is Agnes, pi-jev-compact ≠ pi-jev-compaction, IPECTER runway empty, mailordinal inbox, jev-cli not ready ≠ jevql, laya-multilingual confident-wrong OOD, schema-scorer peaked ranking, HF 401 / GitHub 404 Hub-only, classifier.dev productized HTTP / escalate-under-threshold / silent FALLBACK / vs_jev tracked JSON, choxos/jev-reviewer ≠ egma-ai / two-pass Choice+Noul / not-found / human tick is the product, githubnext/localjev ≠ kunchenguid/local-jev / wire-compat ≠ logit-equiv / prompted JSON ≠ structured read / 1200-req bake-off caveats, NandhaKishorM/laya packaging ≠ Hub-only / Router script-before-p / post-T ECE ≠ raw / Banking77 token-budget / 0.85 still soft / vs-Jev unpublished-here, @airesearch12 census ≠ jevbench v1.1 / GLiNER2+routers class-boundary / incomplete vs Laya-localjev-kev / likes ephemeral, JevBench v1.2 geo-mean I/C/S/K / cal ON rank / 75.3 vs 87.6 not a drop / Luna I=97 rank #7 / option-order 72→21 / ×2 latency assumption / Laya absent gap / Qwen3.8 27B ≠ Archer, hourly 0842 already-folded / apply-the-five / skip thin noise / hard-gate Noul as PR gate is soundness theater, screenshot-to-Jev for CU / 155× Harbor score (typesafe-computer-use: no, and no), waveform-to-Jev / 27/27 Harbor score (jev-voice-browser: no, and no; spoken confirm ≠ auth), AgentGhost sidecar / ASK skip (no, and no; wrap *is* execution; ASK throws; fail-closed), JP genre atlas bake-off / live ★ (studio_yebisu: no, and no; stars research-time; not verified evals), Akshay how-to / 200× Harbor (no, and no; TypeSafe ceiling; schema-safe ≠ correct), jev-semgrep Semgrep.dev / embedding tricks / a gate (no, no, and no; proposition ≠ embedding; boolean after threshold; ranking fail-open), Jev writes UI text / valid GramSpec is good (no, and no), jevtest 0.85 as product proof (no), anima3 default jeff / invent Laya (no), Jev 72.5% class ceiling (no), GLiClass architecture duel (no), skip majority floor (no), authorship as evidence (no), ha-switchboard replaces HA-Jev (no), n8n official TypeSafe (no), compaction-pi = compact (no), jevloop mock quality (no), laya-vision is Archer (no), Cerebellum typesafe-sdk drop-in / endorse 94.92% (no), laya-grounded drop-in / temperature (no), Jeff-1 is logan-markewich/jeff / better ECE than Jev (no, and no; n=9730 *theirs*; set reused), empty stanley findings as approval / auto-promote (no; `notChecked`; Soft Noul ≠ hard safety), findme is JevFind / beam proves the file (no), swap conversation model / quote jevsubrouter dollars (no; counts ≠ dollars), `.feels()` a new language / default 0.5 a bool if (no, and no), apa-agent-harness is jev-harness / copy `@aipersona` (no, and no), grok-bot-jev 13.0× as token savings / skill forces the bot (no, and no), Essentiel Jev send mail / 0.75 calibrated (no, and no), enzo-mcp is jev-sift / skip UNKNOWN (no, and no), pigeonhole OTHER as a move / 0.6 Harbor τ (no, and no), HF playground live Jev / classifier.dev (no, and no), jev-reliability measures accuracy (no), clduab11/jev-test is jevtest / D already passed (no, and no), jev-rag-benchmark showed Jev wins (no), dairui1/jev-lab is BrendanH18 / re-card jev-desktop (no, and no), jevmail is mailordinal / mailjay read-only (no, and no), ZHUBoer/ego-jev is jiangkoumo / `completed` is success (no, and no), jsort scores are frequencies / Choice for scale (no, and no), groundedness-judge-bench showed Jev wins quality (no), jev_playground 83% is quality (no), copy `jev-latest` on Zen (no), techstack classifier generates a stack (no), s1_ruby is hunch / `is?` is a proof (no, and no), judgement is jevql / confidence is winner p (no, and no), Rust community SDK is official / a new species (no, and no), tpellet/hunch is carldaws/hunch (no), file-search 15 matches is recall (no), linkmap referee is gold / Jev sees S2 prose (no, and no), jev-mail is jevmail / tidy OTHER moves / close pinned tabs (no), ORIGIN LLM decides / continue without Jev (no, and no), crawlers raw `bug_likely` as a gate (no), jevbrain is TypeSafe Jev / 95.2% class number (no, and no), judgekit is JudgeBench / 97.7% class ceiling (no, and no), openrouter-jev-mcp is TypeSafe first-party (no), Gemini self-confidence as a threshold (no), decide 0.8 is 80% accuracy (no), calibration arena acts / is jev-arena (no, and no), raw Choice 50–95% is accuracy (no), FrancoisChastel/jev-code is stanley npm (no), marketplace Jev on the hot path / fail-closed missing key (no, and no), mcp_jev invents ask_jev (no), jevtypesafeai.com is TypeSafe (no), ts_safety is a Noul (no), hermes-switchyard is hermes-jev-router / Agnes / loads skills (no), nanoprune is hosted Jev / 0 hallucination (no, and no), jev-browser-agent is ZHUBoer / omp DONE is proof (no, and no), hari007sh/jev is dannote/jev (no), system-one-skills is a judge / 8,026 class ceiling (no, and no), typed-gate 0.51 is a yes (no), pi-jev-gate is fail-closed (no), Foq 100%/ECE 0.2% class ceiling / 25 ms Harbor (no, and no), rev measured replica / quote 32.4 (no), robfrase/jev running local / collapse into dannote (no, and no), typesafe_agent_gates 27/27 Harbor / Noul as hard deny (no), safe-sh pre-exec allow/block (no), pastepilot act without Confirm / clipboard watch (no, and no), Jev-Reranker 0.1667 live Jev / confidence scales value (no, and no), sessionwise required sieve / fail-closed down (no, and no), jev-search scores as truth (no), 400 ms Salesforce SLA (no), scheduler plugin places Pods / demo agreement as accuracy (no, and no), Android screenshot-to-frontier / collapse droidjev into ultrafast (no, and no), jevcu closed-vote / Jev writes the plan (no, and no), ha-conversation-jev is HA-Jev / copy OAuth client_id (no, and no), dsh-jev widen tools / live Jev default (no, and no), classification-benchmark $0.46 measured (no), luna-pagerduty 1.000 production paging (no), meldecision new Laya species (no), laya-doom sees pixels / is Archer (no, and no), quote laya-api README (no), akpsahan vs-Jev as new measure / Qwen3.8-27B Archer (no, and no), Jev owns chess truth (no), jev-drive is AV (no), Jev authors story-arc (no), auto-file HS6 (no), SC2 API Victory as UI win (no), awesome-jev-use-cases likes as eval (no), typesafe-go official (no), enzyme `when asked` as PreToolUse deny / catalysts as summaries (no, and no), enzyme hosted bootstrap as silent TypeSafe (no), unofficial JA ModernBERT is TypeSafe / skip format_version / collapse Argos1111/jev_local into us/jev-local (no), LFM default is JA ModernBERT (no), Nemotron_Jev is a calibrated Jev replacement (no), djev-dev is djev-spark / ships pixels as TypeSafe CU (no, and no), Laya essay vs-Jev is a new bake-off / Khmer 0.952 conf is competence (no, and no), OpenCode jev-pruner is tamaratran or fast-jev-opencode (no, and no), zen-chat is a Noul / paste 24/24 onto OpenCode (no, and no), fail-closed the OpenCode turn / keepThreshold 0.5 as proof (no, and no), jev-webagent-bench scores / JSON Schema boolean as a proof / JevSwiftSDK official (no, no, and no), gliner-native-runtime is TypeSafe Jev / Fastino official / Choice/Score/Noul (no, no, and no), collapse it into gliner25-compaction / gliner2-ultrafast / Eran-BA / JevSwiftSDK / jevmlx (no), README 0.99 as Harbor / hard-gate 0.1 as NER quality / invent ANE ms (no, no, and no), file it as keep/drop / position 4 Selector (no, and no), numerous-com/dgp is official TypeSafe / assessment p grants an effect / a receipt proves the decision was right (no, no, and no), hard-gate DGP as a safety proof / collapse ThreadDesk mocks into live Jev (no, and no), can1357/jegrep is Bentlybro/jevgrep / uehaj/jev-semgrep / paste 79% (no, no, and no), hard-gate 0.4/0.2 as concept absent / paste $0.01–0.03 as a class ceiling (no, and no), kev OOD 0.76 is Jev / isolation 4e-6 proves identity / `/v1/systemone` wire is a Noul / Archer landed (no, no, no, and no), Jev IS the if-statement / playground recordings (southpolesteve/probably: no, and no), re-dump jev-align / 133★ identity (no; SHA unchanged), retrieve by resemblance / 17/18 Harbor (no, and no), hard-gate 0 of 157 / questions as evidence (no, and no), jev-lint is a second product / fail CI on a shipped warning (no, and no), boolean @ 0.5 is a proof (no), ANE 4.98 ms beats Jev / claim 10× (no, and no), snapjudge softmax is a Noul / is localjev (no, and no), JevPi 62 tests are quality / is jevpilot (no, and no)

- `.agents/skills/augustus/references/mappings.md` — classical-method
  mappings with boundaries, counterexamples, acceptance tests (including
  Hypothesis cards §6–§19 — promote only with a test that ran)
- `.agents/skills/augustus/references/validation.md` — design gate, eval
  recipes, Jev-for-skills (routing, self-monitoring, testing, modularity,
  frontmatter), and Eval & hill-climb (jevals hygiene + Harbor taskset;
  open-jev-laya-bench as ECE/NLL/Brier bake-off exemplar; DMB as
  Harbor-style frozen protocol vs constrained LLMs; jevals-data as
  CC-BY-4.0 recompute-from-logs feedstock; Abide replay as
  Harbor-adjacent soft-rule measurement; solari-reflex Harbor-style
  computer-use; gliner2-ultrafast encoder-backend cousin (`DONE` ≠
  success; demo is not a bake-off); Cua-S1 specialist form source-only
  (metric names, no checkpoint scores; not TypeSafe Jev); Stagehand
  extract pick-and-copy 37/75 no-LLM ~0.5s vs 4.37s (*their* card;
  pick ≠ replacement; draft #2951–#2955); jevgrep 79% top-5 vs BM25
  / grep on stripped repos; Jev-RAG one-run vs Spark rerank
  (full-context Spark still faster); jev-oxlint Phoenix answer-key;
  native-probability calibration arena (jev-arena live Brier 0.0059 /
  ECE 0.0620 *theirs*); typed control-plane bake-off shape
  (jev-dspy-control-plane; offline stubs ≠ quality); jev-testbench collab arms; ARC-AGI Direct Jev as
  combinatorial-≠-extractive negative; jev-gateway-bench Harbor on/off
  routing one-run signal; jev-pruner Harbor needle/noise + Terminal-Bench
  integration pilot, not a full bench; jev-baselines-eval pre-registered
  **AMBIGUOUS** + cascade sign-flip; explore-typesafe-ai synthetic FHIR
  Harbor-shaped, not clinically validated; databricks-jev-pdf-lab honest
  negative; Domain-jev-maker specialist vs few-shot (KL/r/McNemar);
  jav-email-cascade compare arms; jev-orderby-bench ORDER BY gates
  (calibration ≠ sortable); jeff GLiFormer cost/accuracy;
  system-one-benchmark Jev vs MLX PCD vs AR JSON n=50 (Brier 0.1096 vs
  0.3884); jevex 1/8→6/8 SWE finish n=8; jev-semgrep 0.94/0.98 (10×51 *theirs*; dedicated §86; **51★** ephemeral);
  omp-greenlight 1,013/10 default 40.9% / 0 of 94; dinostomp jev-as-if
  ECE 0.062 *theirs* / FINDINGS 189; slo-router p95 77.93→490.38 same
  routes; construct-auto-classifier Jev 0 dangerous / 975; INSTRUCT_JEV
  119-row instruct seed; jev-packs nine verified packs on pinned
  jev-1.13 + **jevassert LANDED** (2,990-case matrix; Jev/Sonnet 5
  accuracy tie, Jev better calibrated 7/9, ~250× cheaper;
  sms-spam 0.953/0.040); BBQ 58,492 / 97.28% / $0.3429 *theirs*;
  jev-lint (jevlint rename) 13/15 1.00/1.00; grande JGLUE 0.614/0.853; local-jev
  done 30%/shape 57%; pi-heed 98.5%/0 false block; does-jev-confidence 8,000 judgments
  AUC ~0.91 / stated ~75% vs human ~10% / ~96% ECE removed;
  ego-jev n=3 medians ~2× vs per-step LLM; jev-compactor 64.5%/
  366ms/0 invented paths vs Sonnet summary, one session;
  jev-frontier-100 Jev 77.0% vs Qwen3.5 4B/2048 96.7%
  (exploratory); jev-ood-calibration 900 tickets ECE 0.107 =
  4.4× floor / sign flips by type; jev-labs 1,080 golden 0
  wrong under chaos (escalate; not a proof of zero);
  jevbench v1.1 Jev 1.13.0 Main 87.6 (calibration not scored);
  how-sure-is-jev Choice confidence = max_prob; ci-gatekeeper
  504–629 ms own-repo; dizk/jev-lens 79% / 500 trajectories;
  jev-compactor product-arm 73%/350ms/4 of 4; carryforward
  0/4 recall; openvons JevPick 3.2–4.8×; HA-Jev 17★ not for
  locks; jev-preflight fail-open 8 axes; jevcache 0 FP/100;
  zeroshot-vs-bert +0.05–+0.13 / DiD; ThinkyMiner/Winnow
  80%/90%; OpenJev 45/60; semif-serve 1164 vs 178 ms;
  typed-evaluation-collapse Noul vs named Choice;
  jev-judge-bench SLA-150 contract / canaries ≠ quality / no headline
  yet; jev-use 220 ms p50 / 12/12 / Vercel 0.4 *theirs*; jev-cookbook
  425/$0.015 samples not benches; openJev-verdict-2.0 77.10%/0.0636/
  0.0144 *theirs* unverified + PR #1 claim-audit;
  chakuho GUI 336 27B 95%/92% vs Jev 89%/82% *theirs*;
  jevinf 2.57×/2.27× 100% argmax; jevex n=16 160s→69s /
  $8.74→$3.13; commitjev 0 false on 5 clean *theirs*;
  laya-multilingual MASSIVE 0.366/0.387 vs 0.227/0.733;
  schema-scorer v2 Choice 0.841; HF 401 this pass;
  classifier.dev 400/650 ms; F1 0.887 / 230 ms vs 0.799;
  AG News 87.7%; granite 0.546 vs advertised 0.800 *theirs*;
  NandhaKishorM/laya T4 32.8 ms / post-T ECE 0.081 vs
  Jev 0.246; Banking77 0.425 vs 0.870; 0.766 fine-tune
  *theirs*;
  @airesearch12 census tweet (engagement ephemeral; not a scored bake-off);
  JevBench v1.2 Jev 75.3 / SemIf 74.6 *theirs*; Luna I=96.8 rank #7; cal ON; ≠ v1.1 87.6;
  hourly 0842 recipe already §73–§78 / skip thin / soundness-theater PR gate;
  khordoo/jev-reflex-autonomy-lab Local-vs-Live A/B, not a scored bake-off;
  AgentGhost wrap-as-execution, not a quality bench (MIT **2★**; ASK throws);
  @studio_yebisu JP genre atlas tweet (engagement ephemeral; stars research-time; not verified evals);
  @akshay_pachaar “Jev Clearly Explained” (engagement ephemeral; 200×/400× TypeSafe ceiling; schema-safe ≠ correct);
  uehaj/jev-semgrep meaning-grep dedicated (51★ ephemeral; 0.94/0.98 *theirs* 10×51; Semgrep.dev collision; not a gate);
  hourly 1047 + deferred 0945 (gram-render / jevtest / jev2ui / anima3 / JevFind / jev-frontier-bench 72.5% ECE 0.161 vs Fable 84% ECE 0.064 *theirs* / jev-gliclass-bench 78/40/49 / job-posting-triage floor 0.947 / authorship / ha-switchboard ≠ HA-Jev / n8n-nodes-jev / fast-jev-compaction-pi ~50× *theirs* / jevloop mock / laya-vision 75.2% ECE cal 0.034 / Cerebellum competing NAR not endorsement / laya-grounded phishing regress);
  queued SIGNALs + jevsubrouter (`notes.md` §88; GestaltLabs/Jeff-1 acc 0.8183 ECE 0.0807 vs Jev 0.8283/0.0932 n=9730 *theirs* ≠ logan-markewich/jeff / stanley empty ≠ approve / findme ≠ JevFind / jevsubrouter counts ≠ dollars / Soft Noul ≠ hard safety);
  hourly 1144 (`notes.md` §89; jev-reliability noul-gate 0.0%/12.5%/3.6% *theirs* Nothing about accuracy; clduab11/jev-test Nothing runs yet; jev-rag-benchmark “Jev wins” is not an assumption; dairui1/jev-lab urgent 91% vs Haiku 79% *theirs* synthetic; grok-bot-jev A/B proxies not tokens);
  hourly 1241 (`notes.md` §90; groundedness-judge-bench native vs schema-guided Jev 0.6667 vs GLM 0.7661 *theirs*; jev_playground 0 promotions / routing-backtest 0.0447%; jsort CommonLit r=0.824 / ρ=0.841 *theirs*; tpellet/hunch NL2Bash 36/120 *theirs*; jev-file-search scores not calibrated accuracy; jev-linkmap v1→v3 45%→65% *theirs*; ORIGIN pause-if-no-Jev; jevbrain AUTO_ACT is not a Noul);
  hourly 1347 (`notes.md` §91; judgekit 97.7% n=130 *theirs*; typed-judge-kit 7.0× / MIN_LABELS=20; decide 500 issues $0.0203 *theirs* / 0.8 ≠ 80% accuracy; Jev-Calibration Platt ECE 0.117→0.052; jev-calibration-arena never acts; FrancoisChastel/jev-code **1★** ≠ npm jev-code; hermes-switchyard ≠ hermes-jev-router ≠ hermes-plugin-jev; nanoprune 2.8MB ECE 2.58%; omp-jev-web 5.9s/0 vs 47.6s/27 *theirs*; typed-gate 0 wrong/0 omit/117 review *theirs*);
  hourly 1441 (`notes.md` §92; Foq 25 ms P50 / 2.2 GB / ECE 0.2% / 100% 150-case *theirs*; rev sample 32.4 not a bench; robfrase/jev 85–114 ms p50 *theirs* planning memo; typesafe_agent_gates 27/27 / 31/31 *theirs*; Jev-Reranker r@1 0.1667 offline not live Jev; jev-search 24p $0.01/7.4s *theirs*; 400ms Salesforce WebMCP demo timestamps ≠ Harbor; droidjev find ~0.6s/iter *theirs*; jevcu smoke 12s / 324–380 ms *theirs*; ha-conversation-jev FAST_MIN 0.80 *theirs*; classification-benchmark specified not run; luna-pagerduty p≥0.50 1.000/$0.062 *theirs* n=3000; meldecision tokenize 6.9 / infer 312.4 ms *theirs*; jevchess ~300 ms / game <1¢ *theirs*; SC2 UI-verified Liberation Day 3:44 / Outlaws 27:57 *theirs* ≠ API Victory; akpsahan/laya ≠ Archer / do not re-paste Nandha vs-Jev),
  SIGNAL jevcache/jev-align (`notes.md` §93; Cache hit ≠ correctness; score never auto-accepts; hyperspaceai/jevcache ≠ kushals256/jevcache; sutro-sh/jev-align ≠ caiovicentino/jev-align),
  SIGNAL enzyme/JA ModernBERT/Gemma (`notes.md` §94; guidance ≠ hook; unofficial ≠ TypeSafe; Nemotron ≠ TypeSafe Jev; not a calibrated replacement; JGLUE JNLI 92.62% / JComQA 92.40% *theirs*; Gemma ~0.2s *theirs*; Laya essay numbers *theirs*),
  hourly 1541 (`notes.md` §95; orchestrator finish 0.95 / test 0.8 *theirs* sensors; replacement 20-case acc 0.90→1.00 F1 0.9028→1.0000 p50 675.66→253.13 ms cost 1.52× *theirs* failed cost gate; quarry 5 s fail-open / p&lt;0.5 drop / top 3; OpenRoboto apple-to-plate 113 cycles $0.018825 vs Astra $5.933624 *theirs* one seed-0 not a rate; one-dollar-tahoe ~74 demo no ASR/FPR; llama-jev 80 ms cold / 40 ms cache *theirs* softmax ≠ Noul),
  hourly 1639 (`notes.md` §96; OpenCode jev-pruner unit tests ≠ Harbor; do not copy tamaratran 24/24 / 83%; jev-webagent-bench empty stub),
  SIGNAL gliner-native-runtime (`notes.md` §97; README 0.99 fixture; no Harbor; default threshold 0.1 still soft),
  hourly 1740 (`notes.md` §98; DGP 106 tests ≠ Harbor; mock resolver ≠ Jev; jegrep no published Harbor do not copy 79%; OpenRouter/TypeSafe auto-failover is silent FALLBACK; kev family OOD 0.76–0.77 vs Jev 0.86 *theirs*; replica honesty; Score confidence is a stand-in),
  hourly 1843 (`notes.md` §99; von n=78 / 93.0% *theirs* ≠ Harbor; do not merge Needle 52.6%; llm-vs-jev RESULTS generated from summary.json ≠ Harbor; nothing wins outright; competing NAR claims / replica honesty; jev-forge 0.579/0.637 *theirs* not Harbor),
  hourly 1943 (`notes.md` §100; pointer mode 17/18 19/20 *theirs* ≠ Harbor; 0 of 157 false invalidations tuned on same set; 189/189 FP16 checkpoint parity ≠ task accuracy; 62 tests wiring not quality; 10× not achieved; softmax over allowed tokens ≠ Noul),
  hourly 2041 (`notes.md` §101; 1824 independent Nouls / callback 25.0% *theirs* ≠ Harbor; Jev 0.587 / PrismNLI 0.725 / Laya 0.587 *theirs* ≠ JevBench; contamination caveat; 123,805 requests / ECE 0.075 / 47% unanswerable @≥0.95 *theirs* ≠ jevals; historical-v0 zero retained cases; on small inputs lenses lose money; quote both $0.000004 and $0.000006),
  hourly 2145 (`notes.md` §102; 0.75 vs 0.81 *theirs* ≠ measured separation; 62 cargo PASS ≠ Laya parity; unpaired 0.577 vs 0.727 ≠ JevBench; AUROC 0.769 vs acc 50.1; +0.199 / +26,744 / 0 of 2,816 *theirs* ≠ Harbor; maze 1.0000 n=141 research artefact; exit 0 ≠ claim truth; MagaBitmex/jev-4b-distill model not found),
  hourly 2246 (`notes.md` §103; TokenTrim no-Jev matched hybrid 62.4% *theirs* ≠ bake-off; 21 tasks · 134 items · 208 questions constructed ≠ production; Hev 80.00%/ECE 0.020 *theirs* development-only; mini-jev 93.25% self-authored ≠ family-disjoint; residual-head 9,222-param decreased 73/96→67/96; ChatJev-style soundness theater; timeout = censoring; ranking ≠ calibration / 0.5 still soft),
  hourly 2340 (`notes.md` §104; description-only stub / size 5 ≠ trained checkpoint; ESCI hard probe fails four of six *theirs* ≠ Harbor; jev_bool ECE 0.242 inversion 0.255; do not re-fold §60 six-gates as new; Jairik/jev-distiller size 1; not tested with a live Jev API key; OpenJevPro pastes openjev-sglang JevBench as own; constrained logprob + temp/Platt ≠ Noul; demo P(True) 0.5052 / Choice conf 0.2872 / Score conf 0.0055; synthetic hard menus top-1 0.916 vs 0.873 / ECE 0.0182 vs 0.0367 / 40 vs 4608 menus/sec))
  hourly 0042 (`notes.md` §105; 40.3% below constant-answer *theirs* ≠ class ceiling; 0.980 at every N / 22 of 24 *theirs* ≠ universal determinism; VLM alone 1.7 vs +Jev 4.4 / 2.95× *theirs* ≠ Harbor; cascade 0.60 matches 78% at 1.8× *theirs* not a hard gate; Laya dict-instructions collapse 58.3%; 204 moves vs 73 throughput not intelligence; raw 0.94 is not a release; no_direct_evidence ≠ safe to merge),
  hourly 0243 (`notes.md` §107; size **0** with contents llm-router/ticket-router/GH bonzi; license **null** ticket-router; figure **1★**; verdict **107★** was 0; Sol 94.2 / Luna 83.9 / Jev path 89.7; 19.2% Sol / 62.3% cost save / 4.5pp miss of 2pp non-inferiority; p50 latency worse than Sol due to routing overhead; confidence ≥ 0.85 hard-gate is theater; 100/100 easy T/F is not Harbor; label_mass ≠ correctness; stock llama.cpp Q2_0 silently gibberish; temperature 1.05 AutoModel from_pretrained works vs T=1.75 cannot load; 166,054 rows / 22 configs; GH 151M vs README 149.6M; PR #1 now closed unmerged; do not re-fold §71 claim-audit as a beat; SemIf **2094★** vs §106 **2074**; jevlike **1023★**; TypeAR **12★** flat; AnotiaWang **93★**; tracker likes **59** lastModified UNCHANGED; do not reopen or amend PR #23 or #24))
  hourly 0145 (`notes.md` §106; description-only stub / size 0 ≠ checkpoint; Colvin HEAD `d7f9f803` / README SHA `a5b0d2fd` vs §104; size **0** with contents; ★339 live REST vs watch 337; jevbench **6★** HEAD `c7ab99f5`; logicrw **146★** vs §104 **136★**; SemIf **2074★** vs §104 **2047**; tracker likes **59** lastModified UNCHANGED; 0★ HIGH still get real cards; JSON parse of generated text ≠ Noul; 46x speedup / accuracy identical; ECE 0.624 sentiment catastrophe; 91.1 % / ECE 0.022 *theirs*; RewardBench v1 92.58%; Precise IF 50.63%; classifier.dev fast tier 84.8 is Jev behind its own API; do not re-fold §78 v1.2 board as new; This Space contains no benchmark result yet; do not reopen or amend PR #23))
- `.agents/skills/augustus/references/boundary-audit.md` — existing-system
  insertion: fit test, opportunity map, smallest boundary, red flags
- `.agents/skills/augustus/scripts/evaluate_decisions.py` — offline evaluator
  for selective binary decisions (Brier, reliability, threshold/cost sweep)

Plus `research/` — the living evidence archive behind the skill, refreshed
hourly (see `research/README.md`).

## Install

**Claude Code** (plugin marketplace, mirrors the official TypeSafe layout):

```bash
claude plugin marketplace add 24601/Augustus
claude plugin install augustus@augustus
```

**Any skills-compatible agent** (Amp, Codex, Cursor, …):

```bash
npx skills add 24601/Augustus --skill augustus
```

**ChatGPT**: skills are not a native ChatGPT primitive — paste
`.agents/skills/augustus/SKILL.md` plus the `references/` files into a
GPT's instructions or a Project's knowledge and it will follow the protocol.

**Amp**: repo-local `.agents/skills/` are discovered automatically.

## GitHub topics

`jev` `typesafe` `typesafe-ai` `system-one` `system-one-models`
`structured-output` `calibrated-confidence` `ai-agents` `agent-skills`
`decision-systems` `reranking` `beam-search` `claude-code` `python` `llm`
`decision-theory` `semantic-search` `agent-workflows` `mixed-architecture`
`tool-routing` `skill-routing` `semantic-lint` `classification` `gliclass`
`listwise-ranking` `vision-scoring` `open-weights` `formal-methods`
`model-checking` `deterministic-simulation` `decision-theory`
`value-of-information` `signal-detection` `mcda` `calibration`
`alloy` `apalache` `pufferlib` `stamp-stpa`

## Versioning

See [CHANGELOG.md](CHANGELOG.md) and
[releases](https://github.com/24601/Augustus/releases). Current: **0.3.0**,
written against [`typesafe-ai/skills` v0.5.7](https://github.com/typesafe-ai/skills/tree/v0.5.7)
(`65a39f3`). Re-read live TypeSafe docs before treating that pin as current
API behavior.

## License

MIT — see [LICENSE](LICENSE).
