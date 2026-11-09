# jev-mcp

[TypeSafe AI](https://docs.typesafe.ai/introduction) の判断モデル **Jev** を、Codex から利用するための軽量な MCP サーバーです。Rust で実装し、標準入出力（stdio）で MCP クライアントと通信します。

Codex が要件の理解、コードの調査・編集、テストの実行を担い、その途中で必要になる分類、関連性の判定、候補の選択、評価を Jev に渡します。

```text
Codex：調査・計画
  ↓ 判断に必要な情報と質問
Jev：分類・選択・評価
  ↓ 型付きの回答と確率分布
Codex：編集・テスト・次の行動
```

## できること

次の4つの MCP ツールを提供します。

| ツール | 用途 | 主な回答 |
| --- | --- | --- |
| `jev.noul` | 条件が成立するかを判定する | Yes の確率 `noul`（0〜1） |
| `jev.choice` | 名前付きの選択肢から1つ選ぶ | `choice`、`probabilities`、`confidence` |
| `jev.score` | 順序のある評価基準に沿って採点する | `score`、`legend`、`probabilities`、`confidence` |
| `jev.batch` | 同じ情報に対する複数の質問をまとめて評価する | 質問 ID ごとの回答 |

たとえば、次のような判断に利用できます。

- ファイルの内容が現在の不具合に関係しているか
- テスト失敗が直前の変更に起因するか
- どのサブシステムを先に調べるべきか
- 変更に追加のレビューやテストが必要か
- 提供した実行履歴から、作業が進んでいるか、同じ試行を繰り返しているか

サーバー自身はリポジトリのファイルを読んだり、実行履歴を収集したりしません。判断材料は呼び出し側が `state` として渡します。

## 必要なもの

- Rust 1.88 以上
- TypeSafe API キー
- Codex など、stdio 接続に対応した MCP クライアント

API キーは [TypeSafe のコンソール](https://console.typesafe.ai/) で取得します。評価時には TypeSafe API を呼び出すため、利用に応じた料金が発生する場合があります。

## ビルド

```sh
cargo build --release --locked
```

実行ファイルは `target/release/jev-mcp` に生成されます。

通常は MCP クライアントがこの実行ファイルを起動します。ターミナルから直接起動した場合は、標準入力から MCP メッセージが届くまで待機します。

## Codex に接続する

`~/.codex/config.toml` に次の設定を追加します。`command` は、ビルドした実行ファイルの絶対パスに置き換えてください。すでに `[mcp_servers.jev]` がある場合は、既存の設定を更新します。

```toml
[mcp_servers.jev]
command = "/absolute/path/to/jev-mcp/target/release/jev-mcp"
tool_timeout_sec = 70

[mcp_servers.jev.env]
TYPESAFE_API_KEY = "your_typesafe_api_key"
```

`your_typesafe_api_key` を実際の API キーに置き換えて保存し、Codex を再起動してください。キーを記載した設定ファイルは Git にコミットしないでください。

環境変数として管理する場合は、上の設定の代わりに次を使えます。

```toml
[mcp_servers.jev]
command = "/absolute/path/to/jev-mcp/target/release/jev-mcp"
env_vars = ["TYPESAFE_API_KEY", "TYPESAFE_MODEL"]
tool_timeout_sec = 70
```

この場合、Codex を起動するプロセスの環境に `TYPESAFE_API_KEY` を設定します。GUI アプリはターミナルの環境変数を引き継がない場合があります。

サーバーは起動時に環境変数を読み込みます。**`.env` ファイルの自動読み込みには対応していません。** 設定方法の詳細は [Codex の公式 MCP ドキュメント](https://developers.openai.com/codex/mcp/) を参照してください。

### 環境変数

| 名前 | 説明 |
| --- | --- |
| `TYPESAFE_API_KEY` | API 認証に使う Bearer トークン。未設定・空でもツール一覧は取得できますが、評価時にエラーを返します。 |
| `TYPESAFE_MODEL` | 既定のモデル。省略時は `jev-latest`。各ツールの `model` 引数で上書きできます。 |

## ツールの使い方

### Codex スキルから使う

[jev-decisions スキル](skills/jev-decisions/SKILL.md) を同梱しています。Jev に渡す判断の選び方、バッチ化、回答の解釈、追加調査へのつなげ方を Codex に伝えます。

`skills/jev-decisions` フォルダーを個人用のスキルディレクトリ（通常は `~/.codex/skills/`）に配置すると、次のように呼び出せます。`CODEX_HOME` を設定している場合は、その配下の `skills/` を使います。

```text
$jev-decisions このテスト失敗と差分の関連性を評価して、次に調べる箇所を絞って。
```

スキルと MCP サーバーは別です。事前に上記の MCP 接続と API キーの設定を済ませてください。

### 共通仕様

- `state`：評価する情報。文字列、オブジェクト、配列を指定できます。
- `instructions`：質問または判定したい条件。文字列、オブジェクト、配列を指定できます。
- `model`：任意のモデル指定。省略時はサーバーの既定値を使います。
- `criteria`：Choice では選択肢のマップ、Score では順序付きの評価基準、Noul では任意の Yes／No の説明です。

未定義の引数はエラーになります。入力形式は [TypeSafe API リファレンス](https://docs.typesafe.ai/api) に基づきます。

成功時は `model`、`answers`、`usage` を含む API 応答を返します。MCP の `structuredContent` に加え、`content` にも同じ内容を JSON 文字列で含めます。

単発ツールの回答は `answers.result` に入ります。`jev.batch` は呼び出し側が指定した質問 ID を維持します。

以下の JSON はツールの引数です。MCP の `tools/call` メッセージへの組み込みはクライアントが行います。

### Yes／No の判定：`jev.noul`

```json
{
  "state": "テストは成功しました。",
  "instructions": "テストが成功したと明記されていますか？"
}
```

回答の `noul` は Yes の確率です。

- 1 に近い：強い Yes
- 0 に近い：強い No
- 0.5 に近い：判断が不確か

Noul に独立した `confidence` はありません。必要に応じて `criteria` に `true` と `false` の説明を指定できます。

### 選択肢から選ぶ：`jev.choice`

`criteria` は1〜255個の選択肢を持つマップです。説明には文字列、オブジェクト、配列を使えます。説明が不要な場合は `null` を指定します。

```json
{
  "state": "ワーカーの再試行回数を変更した後、ジョブの再試行テストが失敗しました。",
  "instructions": "最初に調べるべきサブシステムはどれですか？",
  "criteria": {
    "worker": "ジョブの実行と再試行を担当する部分",
    "api": "HTTP リクエストを処理する部分",
    "unknown": "判断に必要な情報が不足している"
  }
}
```

返却形式の例です。数値は説明用であり、実測値ではありません。

```json
{
  "model": "jev-example",
  "answers": {
    "result": {
      "type": "choice",
      "choice": "worker",
      "probabilities": {
        "worker": 0.9,
        "api": 0.05,
        "unknown": 0.05
      },
      "confidence": 0.75
    }
  },
  "usage": { "input_tokens": 200, "output_tokens": 30 }
}
```

選択肢だけではすべての状況を扱えない場合は、`unknown` や `other` に相当する選択肢を含めてください。

### 評価基準に沿って採点する：`jev.score`

`criteria` に、低い段階から高い段階への順で2〜10個の評価基準を指定します。各段階は文字列、オブジェクト、配列で記述できます。

```json
{
  "state": "CSV 出力が失敗します。JSON 出力は利用できます。",
  "instructions": "報告された不具合の深刻度を評価してください。",
  "criteria": [
    "表示上の問題のみで、機能への影響はない",
    "機能の一部が使えないが、代替手段がある",
    "主要な作業ができず、代替手段もない"
  ]
}
```

`score` は各段階の番号を確率で重み付けした値です。番号は0から始まるため、3段階なら0〜2の範囲となり、小数も返ります。常に0〜1の確率を返すわけではありません。

回答には、段階番号と説明を対応させる `legend`、各段階の `probabilities`、分布から算出した `confidence` も含まれます。

### 複数の質問をまとめる：`jev.batch`

同じ `state` に対する独立した質問は、`jev.batch` にまとめてください。Noul、Choice、Score を1回の API リクエストに混在させられます。`questions` には少なくとも1件の質問が必要です。

```json
{
  "state": {
    "diff": "ワーカーの再試行上限を3回から0回に変更した。",
    "test_failure": "worker_retries_transient_failure: expected 3 attempts, got 1"
  },
  "questions": {
    "related": {
      "type": "noul",
      "instructions": "`test_failure` は `diff` に関係していますか？"
    },
    "subsystem": {
      "type": "choice",
      "instructions": "最初に調べるべきサブシステムはどれですか？",
      "criteria": {
        "worker": "バックグラウンド実行と再試行",
        "api": "HTTP リクエストの処理",
        "unknown": "判断材料が不足している"
      }
    },
    "impact": {
      "type": "score",
      "instructions": "`diff` が再試行の動作に与える影響を評価してください。",
      "criteria": [
        "再試行の動作は変わらない",
        "一部の条件で再試行に失敗するが、再試行自体は行われる",
        "再試行が完全に無効になる"
      ]
    }
  }
}
```

回答は `answers.related`、`answers.subsystem`、`answers.impact` に入ります。

バッチ内の質問は互いの回答を参照できません。前の回答が次の判断に必要な場合は、その回答を新しい `state` に含めて別の呼び出しを行います。

## 不確かな結果の扱い

Choice と Score の `confidence` は、回答の確率分布から算出される指標です。正解を保証する値ではありません。

呼び出し側では、たとえば次のような分岐を設けられます。

```text
confidence >= 0.90
    → Jev の判断を採用する

0.60 <= confidence < 0.90
    → Codex が結果を確認する

confidence < 0.60
    → 判断材料を追加して再評価する
```

このしきい値は設計例です。サーバーは自動採用や再評価を強制しません。用途と実際の評価データに合わせて調整してください。Noul では Yes の確率に基づく別の基準が必要です。

詳しくは [TypeSafe の Confidence ドキュメント](https://docs.typesafe.ai/confidence) を参照してください。

## 通信とエラー処理

すべてのツールは、渡された情報と質問を次のエンドポイントへ送信します。

```text
POST https://api.typesafe.ai/v1/systemone
```

| 項目 | 動作 |
| --- | --- |
| 接続タイムアウト | 10秒 |
| 1回のリクエストのタイムアウト | 30秒 |
| 再試行を含む全体の制限時間 | 60秒 |
| HTTP 429／529 | 最大2回再試行。通常は0.5秒、1秒と待機時間を増やす。秒数形式の `Retry-After` があれば従う。全体の制限時間は維持する。 |
| その他の HTTP エラー・通信エラー | 再試行せずにエラーを返す |
| リダイレクト | 追従しない |
| 応答サイズ | 最大8 MiB |

入力の不備、キーの未設定、API エラー、不正な回答は `isError: true` の MCP ツール結果として返します。未知のツール名には JSON-RPC エラーを返します。

API のエラー本文や認証情報はエラーメッセージに含めません。標準出力は MCP メッセージ専用です。

## 開発とテスト

```sh
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked
```

テストではローカルのモック HTTP サーバーと、実際の stdio 子プロセスを使用します。TypeSafe の API キーや有料 API 呼び出しは不要です。

確認対象には、各ツールのリクエスト形式、混合バッチの MCP 通信、入力検証、認証エラー、再試行、タイムアウト、不正・過大な応答、stdio の初期化と終了が含まれます。

実モデルの判断品質、費用、応答時間は、実際の API キーと用途に合ったデータで別途評価する必要があります。

## 設計方針と実装状況

Codex は調査・実装・検証を進め、Jev はその途中の小さな判断を担当します。質問は1つの判断に絞り、複数の観点が必要なら分けて評価し、呼び出し側のコードで結果を組み合わせます。

現在は実験段階です。4つの stdio MCP ツール、TypeSafe API との接続、入力・応答の検証、再試行とタイムアウト、モックおよびプロトコルのテストを実装しています。

リポジトリの自動調査やエージェントの実行履歴収集は未実装です。また、Jev を組み込むことでトークン使用量、不要なファイル読み込み、重複した推論、待ち時間がどれだけ減るかは、今後の検証対象です。最終的なタスクの達成品質を維持できるかも含めて評価します。
