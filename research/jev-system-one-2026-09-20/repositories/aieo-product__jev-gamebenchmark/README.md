# Jev Game Benchmark

落ち物パズル（連鎖パズル Blobs・ライン消しパズル Blocks）の 2P 対戦で、[Jev](https://typesafe.ai)（TypeSafe の System One モデル）と LLM（Claude / GPT）を同じ土俵で比べるベンチマーク。
そして、**Jev への「問いの立て方」を誰でも書き換えて試せるサンドボックス**です。

> A sandbox for optimizing how you ask [Jev](https://typesafe.ai) (TypeSafe's System One model) to play falling-block games, benchmarked head-to-head against LLMs (Claude / GPT). Game logic is fixed; you only edit one small strategy file. Docs are in Japanese; the code and strategy files are short enough to read directly. → [English quick start](#english-quick-start)

```
┌─ ゲームロジック（触らない）────────────┐      ┌─ 戦略（ここだけ書き換える）──────────┐
│ arena/games/blobs.py  blocks.py        │      │ strategies/blobs/build-big-chains.py          │
│  ・置ける場所の列挙                     │ 候補  │  ・モデルに見せる特徴量 features()    │
│  ・結果のシミュレーション（連鎖・消去）   │ ───▶ │  ・評価基準の文言 LEVELS             │
│  ・おじゃま／勝敗／リアルタイム進行      │      │  ・同点の扱い tie_break()            │
│ arena/server.py  agents.py            │ ◀─── │  （上級: 問いの構成そのもの）         │
│  ・Jev / Claude / GPT との通信・計測    │  手   └────────────────────────────────────┘
└───────────────────────────────────────┘
```

考えている間もピースは落ち続けます。**速く、かつ良い判断をした方が勝つ**ので、判断の質・速度・費用がまとめて画面に出ます。左側を「人間（キーボード）」にすれば、自分で Jev や LLM と対戦することもできます。

## 起動

```bash
git clone https://github.com/aieo-product/jev-gamebenchmark && cd jev-gamebenchmark
./run.sh                           # → http://localhost:8770
```

初回は `run.sh` が `.venv` を作って依存を入れ（Python 3.10+。`uv` があれば使います）、**API キーの渡し方**を聞きます。

| 渡し方 | やること |
|---|---|
| `env`（環境変数） | 起動前に `export TYPESAFE_API_KEY=...`（必須。https://console.typesafe.ai で発行）、`export ANTHROPIC_API_KEY=...` / `export OPENAI_API_KEY=...`（任意） |
| `akc`（macOS キーチェーン） | [akc](https://github.com/aieo-product/AIkeychain)（`npm i -g aikeychain`）に同じ名前で登録しておく: `akc set TYPESAFE_API_KEY` など。`run.sh` が `akc run` でサーバーの子プロセスにだけ渡します |

選択は `.arena-keys` に保存されます（変更は `ARENA_KEYS=env ./run.sh` / `ARENA_KEYS=akc ./run.sh`）。キーの名前はどちらの方式でも `TYPESAFE_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` です。

対戦相手ごとに必要なもの:

| 対戦相手 | 必要なもの |
|---|---|
| Claude — API 直結 | `ANTHROPIC_API_KEY` |
| GPT — OpenAI API 直結 | `OPENAI_API_KEY` |
| Jev — 戦略どうしの対戦 | `TYPESAFE_API_KEY` だけ |
| Claude — Agent SDK | [Claude Code](https://claude.com/claude-code) にログイン済みであること（サブスク。API キー不要） |
| GPT — Codex app-server | [Codex CLI](https://github.com/openai/codex)（`npm i -g @openai/codex`）で `codex login` 済みであること（ChatGPT のサブスク。API キー不要） |

ログイン（サブスク）で動かす2つは請求がないので、画面の費用は「API 換算額」です。速度の比較は API 直結が本筋です（ログイン経由は CLI のプロセスを挟みます）。
- 費用の目安: Jev は入力 $0.042 / 100万トークン（出力無料）。1手 約 $0.0002〜0.0004、3分の試合で $0.1 前後。LLM 側は各社の定価どおり。

## 戦略を書き換える（3ステップ）

1. コピーする: `cp strategies/blobs/build-big-chains.py strategies/blobs/mine.py`
2. `mine.py` を編集する（下の表）。
3. 試す。サーバーの再起動は不要です（試合を始めるたびに読み込み直します）。
   - まず単独プレイで質を測る（速くて安い）: `python -m arena.solo blobs -s mine,build-big-chains`
   - 画面で対戦: ゲーム＝Blobs、対戦相手＝「Jev — 戦略どうしの対戦」、左＝`mine`、右＝`build-big-chains`

同梱の戦略（画面の選択肢には `DESCRIPTION` の一言が並びます）:

| ゲーム | 戦略 | 内容 |
|---|---|---|
| Blobs | `build-big-chains`（推奨） | 連鎖を育ててから打つ。最大8連鎖 |
| Blobs | `pop-early` | 最初に書いた基準。小さい連鎖をすぐ打ってしまう |
| Blocks | `keep-flat`（推奨） | 穴を避けつつ低く平らに積む |
| Blocks | `avoid-holes-first` | 最初に書いた基準。穴を避けて高く積みがち |

| 戦略ファイルに書くもの | 役割 |
|---|---|
| `DESCRIPTION` / `RECOMMENDED` | 選択肢に出る一言。`RECOMMENDED = True` で先頭に出る（`arena.solo` や `arena.bench` で戦略を省略したときの既定にもなる） |
| `LEVELS` | Score の評価基準（悪い→良い、2〜10段階）。**Jev は各段を別々に、字義どおりに読みます** |
| `features(cand, view)` | 候補1つぶんの、モデルに見せる特徴量（dict）。`cand` にはシミュレーション結果（置く前後の盤面、連鎖の各段など）が入っています |
| `context(view)` | 全候補に共通の状況（いまのピース、予告おじゃま、相手の高さ など） |
| `TIE_EPS` / `tie_break(f)` | スコアが同点の候補から、コードがどれを選ぶか |
| `QUESTION` / `INSTRUCTIONS` | 問いの文 |
| `questions()` / `pick()`（任意） | 問いの構成そのものを変える（観点ごとに Score を分けて重み付けで合成する、Noul で足切りする、など） |

詳しくは [strategies/README.md](strategies/README.md)。LLM（Claude / GPT）と対戦するときは、公平のため**同じ戦略**（同じ特徴量・同じ基準）を LLM にも渡します。

### 最適化でどれだけ変わるか（同梱の2つの戦略）

Blobs・Jev 単独 100手（`python -m arena.solo blobs -s build-big-chains,pop-early -a jev,code`、2026-09-18）:

| 戦略 | 最大連鎖 | 作れたおじゃま（seed 1001 / 2002） |
|---|---|---|
| `pop-early`（最初に書いた基準。小さい連鎖をすぐ打つ） | 3 | 100個 / 96個 |
| `build-big-chains`（書き直した基準。育ててから打つ） | **8** | **452個 / 675個** |
| 参考: コードだけの評価関数（`-a code`） | 7 | 541個 / 715個 |

モデルは同じで、変えたのは戦略ファイルだけです。`pop-early` は「3連鎖以上＝最上位」と書いていたので、Jev は基準どおり小さい連鎖をすぐ打っていました。効いた変更は次の3つ:

- 「盤面に余裕があるうちの発火は無駄打ち」と低い段に明記した
- 条件の掛け合わせ（連鎖数 × 盤面の余裕 × 予告おじゃま）を、コードが `pop_timing` という1つの言葉にまとめて渡した（モデルに AND 条件を解かせない）
- 「狙える連鎖数」を、同色ブロブをあと2個足すところまで見るようにした

まだ伸ばせます（アイデア: NEXT まで読む2手読み、連鎖の形の特徴量、観点別 Score の合成、発火判断を Noul に分ける）。**もっと良い戦略ができたら PR を送ってください。**

## ベンチマーク結果

**[docs/benchmarks.md](docs/benchmarks.md)** に、全モデルとの対戦結果（勝敗・回答時間・置いた数・費用）と、戦略ごとの単独プレイの結果を載せています。2026-09-18 の計測の要約:

| | Jev | Claude Haiku 4.5 | GPT-5.6 luna | Claude Opus 5 |
|---|---|---|---|---|
| 回答時間の中央値（Blocks） | 約 280ms | 720ms | 1,035ms | 2,720ms |
| 1手の費用（Blocks） | $0.00022 | 9.8倍 | 1.7倍 | 58倍 |
| 対戦成績（両ゲーム・全7モデル計 30試合） | Jev の 29勝 1敗 | | | |

取り直す: `./run.sh` → `python -m arena.bench blobs` → `python -m arena.report`。

## 画面で見られるもの

各回答の実時間（ms）、トークン、費用（累計・1手あたり・攻撃1単位あたり）、どんな出力で操作したか（行をクリックでリクエスト／レスポンス全文）、間に合わなかった回数、形式逸脱。すべて `logs/*.jsonl` に保存されます（戦略ファイルの全文も記録）。

対戦相手は5通り: Claude（API 直結）／GPT（OpenAI API 直結）／Jev（戦略どうし）／Claude（Agent SDK、Claude Code のログイン）／GPT（Codex app-server、ChatGPT のログイン）。

### 自分で対戦する（キー設定）

「左側」を **人間（キーボード）** にして対戦開始。画面のどこかをクリックしてからキーを押します。

| キー | 操作 |
|---|---|
| <kbd>←</kbd> <kbd>→</kbd> | 左右に移動 |
| <kbd>↑</kbd> または <kbd>X</kbd> | 回転（時計回り） |
| <kbd>Z</kbd> | 逆回転 |
| <kbd>↓</kbd> | 1段落とす |
| <kbd>Space</kbd> | 一気に落として固定 |

- 着地してから 0.5秒は動かせます（その間に動かして再び落ちられる状態になれば、固定は延びます）。
- Blobs の回転は軸を中心に子が 上→右→下→左 と回ります。壁や床にぶつかるときは軸を1マスずらして入れます。
- キーを変えるには `static/index.html` 先頭の `KEYMAP` を編集します。
- 回答ログには押したキーが、回答時間の欄には「ピースが出てから固定するまでの時間」が出るので、自分の手の速さをモデルと比べられます。相手の LLM に渡す戦略は「戦略」で選びます。

## ルールと公平性

- **共通**: 両者同じピースの並び。落下は 20秒ごとに 15% 速くなる。回答が届いた瞬間にその置き方へ移して落とす（横移動・回転は瞬間移動）。着地までに間に合わなければ出現位置のまま固定。回答時間はサーバー側で計った実時間（ネットワーク往復込み）。試合前に両者ウォームアップ済み。
- **Blobs**: 6×12、4色、4つで消える。得点は定番の連鎖ボーナス式、70点でおじゃま1個（画面で変更可）、相殺あり、一度に降るのは5段まで。左から3列目の最上段が埋まったら負け。連鎖の演出中（1段 約0.4秒）は操作不可。
- **Blocks**: 10×20、7種のピースを1巡ずつ引く方式。2ライン→1段、3→2段、4→4段の邪魔ブロック、相殺あり。ホールドや回転ボーナスはなし。
- どちらのゲームも、コードの評価関数だけで十分強く打てます。これは実用例ではなく、**Jev と LLM を同じ条件で比べ、問いの立て方を練習するための題材**です。

## コマンド

```bash
python -m arena                     # サーバー（run.sh と同じ）
python -m arena.solo blobs -s mine,build-big-chains -a jev -n 100      # 単独プレイで戦略の質を測る（-a code / random は API 不要）
python -m arena.headless blobs claude-api claude-haiku-4-5 --seconds 60   # ブラウザなしで1試合（サーバー起動中に）
python -m arena.bench blobs          # 全モデルと順番に対戦して docs/results/ に保存（サーバー起動中に。LLM の費用がかかる）
python -m arena.report               # docs/results/*.json → docs/benchmarks.md
python -m tests.test_rules          # ルールと全戦略ファイルの確認（API 不要）
```

## 構成

```
arena/games/*.py   ゲームのルール（1ゲーム1ファイル。足すときは games/__init__.py に登録し、static/index.html の RENDER に描画を足す）
arena/strategy.py  戦略ファイルの読み込みと既定の動作
arena/agents.py    Jev / Claude / GPT との通信・計測・費用計算
arena/server.py    対戦の進行と WebSocket 配信
arena/solo.py      単独プレイの計測     arena/headless.py  ブラウザなしの対戦
arena/bench.py     全モデルとの連続対戦   arena/report.py    docs/benchmarks.md の生成
docs/              ベンチマーク結果（benchmarks.md と元データ results/*.json）
strategies/        ★ 書き換える場所
static/index.html  画面（描画とログ表示だけ）
```

## English quick start

```bash
export TYPESAFE_API_KEY=...   # required; ANTHROPIC_API_KEY / OPENAI_API_KEY optional (or keep them in macOS Keychain via akc)
./run.sh                      # → http://localhost:8770 — asks once whether keys come from env or akc
cp strategies/blobs/build-big-chains.py strategies/blobs/mine.py     # edit LEVELS / features() / tie_break()
python -m arena.solo blobs -s mine,build-big-chains                 # measure quality cheaply, no opponent
```

Code enumerates and simulates every legal placement; your strategy file decides which facts the model sees, how the Score rubric is worded, and how ties are broken. Jev scores every candidate in one request; the LLM receives the same facts and rubric and must answer `{"pick": "pNN"}`. Pieces keep falling while a model thinks, so latency matters as much as judgment. Strategies are reloaded at every match start.

## 注意

- 本プロジェクトは TypeSafe、Anthropic、OpenAI の公式プロジェクトではありません。ゲームは、広く知られた落ち物パズルの形式に着想を得た独自実装で、特定の商品とは関係ありません。
- ライセンス: MIT
