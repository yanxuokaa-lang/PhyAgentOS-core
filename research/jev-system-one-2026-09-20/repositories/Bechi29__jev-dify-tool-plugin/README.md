# Jev Decision Tool for Dify

依頼 ID: `jev-dify-tool-plugin-20260920` / plugin: `bechi/jev_tool` / version: `0.1.0`

`state` と `questions` を TypeSafe Direct API に送り、Choice・Score・Boolean を JSON で返す **Tool プラグイン**です。Workflow の Tool ノードで利用します。LLM モデルプロバイダーの追加は行いません。

## 実装と現在の検証範囲

- Python **3.12**、`dify-plugin==0.10.2`。通信には標準ライブラリを使用します。
- 送信先は `POST https://api.typesafe.ai/v1/systemone` 固定。モデルは `jev-latest` が既定で、登録画面で Direct API のモデル ID を指定できます。
- API キーは provider の `secret-input`。登録時は形式のみ検証し、課金を伴う呼び出しは行いません。認証・early access の利用権限は合成データの疎通で確認してください。
- 2026-09-20 作業環境は Python 3.9.6 のみ。Dify CLI／Python 3.12／Dify SDK がなく、シェルから GitHub への DNS 解決も失敗しました。**CLI の `dify plugin init` からの生成は未実施**です。公式仕様に沿って手動作成した実装であり、CLI 由来と偽称しません。
- ローカルの標準ライブラリテストは実行済み。実 SDK テスト、CLI 検証、`.difypkg` 生成、実 API 疎通、Dify インストールは未実施です。`VALIDATION.md` に記録しています。
- Gateway バックエンドは実装していません。依頼の「Direct または Gateway」のうち Direct を採用しました。

## データと判断の制限

**形式保証 ≠ 誤判定ゼロ（候補外は出ないが、候補内ミスはあり得る）。** 応答の候補・確率・型を検証し、契約から外れた応答はエラーとして停止します。実業務の正解率はラベル付きデータで別途評価してください。Choice に `other` を設け、低 confidence や曖昧な Boolean 確率は人手確認へ分岐します。

**外向きAPI。ZDR未確認の機密データは本番禁止。PII/秘密は state に載せない／マスク前提。** questions・instructions・criteria にも同じ制限を適用してください。本ツールは自動マスクしません。Dify の実行履歴・監視基盤もデータを保持し得ます。

Gateway ZDR は **per-request オプション** `providerOptions.gateway.zeroDataRetention: true` で指定できます。本プラグインは Gateway を呼ばないため、この保証は適用されません。[Vercel 公式 Jev 発表](https://vercel.com/changelog/typesafe-ai-jev-now-available-on-ai-gateway)

直APIのZDRは enterprise 案内が強い、という依頼時情報はありますが、今回確認できた [TypeSafe 公式サイト](https://typesafe.ai/) には Enterprise 導線がある一方、直APIの公開仕様で ZDR の契約条件やリクエスト指定方法までは確認できませんでした。「Enterprise 契約で提供される」という読みは**推測・要問い合わせ**です。デフォルト ZDR を保証しません。

TypeSafe 公式サイトには Waitlist 導線があります。**early access／アカウント承認が必要となる可能性を前提**に、利用権限・モデル・課金条件を確認してください。依頼メモの入力 `$0.042 / 1M tokens`・出力課金なしは見積参考値で、直APIの料金確約ではありません。[Gateway のモデルページ](https://vercel.com/ai-gateway/models/jev) は確認時 `$0.04 / 1M` 表示でした。価格・課金トークンの扱いは契約先に確認してください。API の `output_tokens` が返ることと出力課金の有無は別です。

## 入力

| パラメーター | 型 | 内容 |
|---|---|---|
| state | string | マスク済みテキスト、または JSON 文字列 |
| state_format | select | `text`（既定）または `json`。json は string/object/array のみ |
| questions | string | 質問 ID をキーとした JSON オブジェクト |
| boolean_threshold | number | 0〜1、既定 0.5。`probability >= threshold` を true にする |

`questions` の各値に `type` と `instructions` が必須です。instructions は文字列・オブジェクト・配列。質問 ID 自体はモデルへの指示になりません。

| type | criteria / options |
|---|---|
| choice | 候補名 → 説明（string/object/array/null）のオブジェクト。1〜255 候補 |
| score | 低→高の説明配列。2〜10 段階。index は 0 始まり |
| boolean / noul | 省略可。`true` / `false` の説明オブジェクト |

`options` は `criteria` の別名です。同時指定はエラーです。Boolean は Direct API へ送る際 `noul` に変換します。

```json
{
  "department": {
    "type": "choice",
    "instructions": "Which team handles this request?",
    "options": {"billing": "Payments/refunds", "technical": "Bugs/outages", "other": "None of the above"}
  },
  "severity": {
    "type": "score",
    "instructions": "Rate service impact.",
    "criteria": ["No impact", "Workaround exists", "Service blocked"]
  },
  "urgent": {"type": "boolean", "instructions": "Does the message explicitly request urgent action?"}
}
```

ローカル保護上限は 64 質問・ID/候補名 200 文字・送信 JSON 1,000,000 bytes・受信 2,000,000 bytes です。これらはベンダー上限の主張ではありません。未知フィールド、重複 JSON キー、NaN/Infinity、曖昧な型は拒否します。実 API がさらに制限する場合は 422 エラーになります。

## 出力

Tool の標準 `json` 出力へ正規化したオブジェクトを 1 件返します。加えてカスタム出力 `answers`（object）、`model`（string）、`result_json`（string）を返すため、WF から参照できます。

```json
{
  "schema_version": "1.0",
  "backend": "typesafe_direct",
  "model": "jev-1.13.0",
  "answers": {
    "department": {"type": "choice", "choice": "billing", "probabilities": {"billing": 0.85, "technical": 0.1, "other": 0.05}, "confidence": 0.7, "confidence_source": "api"},
    "severity": {"type": "score", "score": 1.3, "probabilities": {"0": 0.1, "1": 0.5, "2": 0.4}, "legend": {"0": "No impact", "1": "Workaround exists", "2": "Service blocked"}, "confidence": 0.2, "confidence_source": "api"},
    "urgent": {"type": "boolean", "value": true, "probability": 0.9, "probabilities": {"true": 0.9, "false": 0.1}, "threshold": 0.5, "confidence": null, "confidence_source": "not_provided_by_api"}
  },
  "usage": {"input_tokens": 100, "output_tokens": 20}
}
```

これは説明用 fixture です。Choice/Score の confidence は API 値を保持します。**Noul は confidence を返さないため Boolean confidence は null**。確率から擬似 confidence を作りません。Boolean の 0.5 は不確実で、true 値だけを根拠に自動実行しないでください。

接続・読み取りはソケット操作あたり 30 秒 timeout。全処理の厳密な総時間上限ではありません。TLS 証明書を検証し、HTTP redirect を追跡しません。自動再試行は行わず、429/5xx は WF のエラー分岐から backoff と回数制限付きで再試行してください。timeout 後の再試行は二重課金となる可能性があります。エラーは成功 JSON と混ぜず Tool エラーとして停止します。応答本文・API キー・state をエラーメッセージに含めません。

## セットアップとキー不要テスト

以下は納品フォルダ `jev-dify-tool-plugin-20260920` をカレントにし、**ネットワーク取得が許可された別のビルド環境**で実行します。この Slack サンドボックスの制限変更は行いません。

Python 3.12 と [Dify Plugin CLI](https://docs.dify.ai/en/develop-plugin/getting-started/cli)、RTK を用意してください。CLI は `difyctl` とは異なります。CLI バージョンを検証記録に残します。

```sh
rtk proxy dify version
rtk proxy python3.12 -m venv .venv
rtk proxy .venv/bin/python -m pip install -r jev_tool/requirements.txt
rtk proxy .venv/bin/python -m unittest discover -s tests -v
```

全テストが成功し、SDK テストが skip されないことを確認します。依存の直接バージョンは固定していますが推移依存は未ロックです。リリース時は検証環境の依存一覧と CLI version を保存してください。

### 必須 CLI スキャフォールドを再現する手順

今回の環境では実行できていないため、完了に向けて以下が残っています。既存ファイルの上書きを避けるため、納品フォルダ外の**新しい空の検証用ディレクトリ**で実行します。

```sh
rtk proxy dify plugin init
```

対話入力は name=`jev_tool`、author=`bechi`、description=`Typed decisions via TypeSafe System One Direct API`、language=`python`、type=`Tool`。逆呼び出し・storage・endpoint 権限は不要なので有効化しません。

CLI が生成した `jev_tool` の構成を納品物と比較します。納品物の `manifest.yaml`、`main.py`、`requirements.txt`、`jev_client.py`、`provider/jev.*`、`tools/evaluate.*`、`_assets/icon.svg`、`privacy.md`、`README.md` を移植し、manifest の provider 参照と provider の tool 参照を一致させます。テンプレートの未使用 Tool は登録しません。CLI 生成物で SDK テスト・パッケージ検証を行い、差分があれば納品ソースへ反映してください。`scripts/package.py` は納品ソースを梱包するので、反映前に最終成果物としないでください。

## パッケージ生成

```sh
rtk proxy .venv/bin/python scripts/package.py
```

実体は `dify plugin package <staging>/jev_tool`。レビュー対象ファイルだけを allowlist で一時ディレクトリにコピーするため、`.env`、キー、テスト、venv、Git 情報が紛れ込みません。生成先は `dist/jev_tool.difypkg` と `dist/SHA256SUMS`。既存成果物があれば停止します。ZIP を単にリネームする代替は実装していません。

CLI を直接使う場合は、キーや `.env` が存在しないクリーンなソースから以下でも生成できます。

```sh
rtk proxy dify plugin package ./jev_tool
```

この手順自体は現環境では未検証です。配布前に CLI エラーがないこととアーカイブ内容を確認してください。

## 実 API のローカル疎通

**人が明示して実行する任意の有料テスト**です。API キーはシークレット管理から `TYPESAFE_API_KEY` 環境変数へ安全に設定してください。コマンド行に実値を貼る、shell trace (`set -x`)、`env` の出力、コミットは禁止です。CLI オプションによるキー受け取りは提供しません。

```sh
rtk proxy .venv/bin/python scripts/smoke.py --live
```

合成データだけを送信し、3 種類の応答契約を検証します。標準出力は成功メッセージのみ。`TYPESAFE_MODEL` は任意です。ローカル環境変数は Dify の provider 登録とは別管理です。キー未設定なら送信せず失敗します。

## Dify へのインストール → キー登録 → WF 接続

1. ステージング用 Dify の Plugins → ローカルファイルからインストールで `.difypkg` を選択します。署名ポリシーに従い、拒否される場合は管理者が承認した配布方法を利用します。署名検証設定を勝手に無効化しないでください。
2. Jev Decision Tool の認証設定で TypeSafe API キーを secret 欄に入力し、model は `jev-latest` または利用可能な固定モデル ID を設定します。登録成功だけでは API 認証成功とは限りません。
3. Workflow の Start にマスク済み文字列入力を用意し、Tool → Jev → Evaluate decisions を追加します。
4. `state` を Start の入力にバインドし、`state_format=text`、`questions` に上の JSON、`boolean_threshold=0.5` を設定します。
5. 続く Code ノードに `examples/workflow_code.py` の内容を貼り、入力 `result_json` を Tool の同名出力に接続します。Code 出力は `department:string`、`severity:number`、`urgent:boolean`、`needs_review:boolean` と定義します。
6. IF/ELSE は先に `needs_review == true` を人手確認へ分岐。残りを `department == billing` 等で分岐します。例の閾値は仮値で、業務データで校正してください。動的な質問 ID を直接選べない Dify UI でもこの Code ノードで値を取り出せます。
7. Tool のエラー分岐を有効化し、認証エラー・429・timeout・不正応答を成功経路へ接続しないようにします。まず合成データで確認し、低 confidence、Boolean 中間確率、通信失敗の経路も検証します。

本番 Dify へのインストールは行っていません。

## Gateway を後から追加する場合

Vercel の `typesafe-ai/jev` は AI SDK の `experimental_evaluate` 経路です。OpenAI 互換 Chat Completions に URL を差し替える構成にはしません。Gateway の評価対応、ZDR、confidence の格納場所は Direct と異なるため、専用の実装・試験が必要です。現プラグインへ Gateway キーや `typesafe-ai/jev` を設定しないでください。

## 参照（2026-09-20 確認、一次資料）

- [TypeSafe HTTP API](https://docs.typesafe.ai/api)
- [TypeSafe Choice](https://docs.typesafe.ai/primitives/choice)、[Score](https://docs.typesafe.ai/primitives/score)、[Noul](https://docs.typesafe.ai/primitives/noul)
- [Dify Tool 開発](https://docs.dify.ai/en/develop-plugin/dev-guides-and-walkthroughs/tool-plugin)
- [Dify Manifest](https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/plugin-info-by-manifest)
- [Dify Tool 出力](https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/tool)
- [Dify SDK 0.10.2](https://pypi.org/project/dify-plugin/0.10.2/)

GitHub リポジトリ・PR は作成していません。外部サービスへの書き込み禁止という本実行環境の制約に従い、ローカル成果物を納品します。
