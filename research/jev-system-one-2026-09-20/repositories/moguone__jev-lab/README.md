# jev-lab

TypeSafe AI の System One モデル **Jev** を、小さなアプリで実際に動かして検証するためのリポジトリ。
検証テーマごとに `apps/` 以下へ独立したアプリを置く。

> 個人による非公式の検証プロジェクトであり、TypeSafe AI とは関係がない。「TypeSafe」「Jev」は同社の名称。

## アプリ

| アプリ | 内容 | 主な検証観点 |
|---|---|---|
| [maze-runner](apps/maze-runner/) | 迷路チェイスゲームの進行方向を Jev に裁定させて自動クリアを目指す | Choice 一括 vs Noul+Score fan-out、リアルタイム進行でのレイテンシの影響、confidence によるフォールバック |
| [twenty-questions](apps/twenty-questions/) | 「20 の質問」形式で、プレイヤーが思い浮かべた動物を Jev の確率だけで当てる | Noul の確率を尤度としてベイズ合成、確率を 0/1 に丸めた場合との比較、キャリブレーション、Score による自由回答の解釈 |

## セットアップ

API キーは [TypeSafe Console](https://console.typesafe.ai) で発行し、リポジトリ直下の `.env` に置く。全アプリがこのファイルを読む。

```sh
cp .env.example .env   # TYPESAFE_API_KEY を記入
```

起動方法は各アプリの README を参照。

## アプリを追加するとき

- `apps/<name>/` に、そのディレクトリだけで完結する形で置く（`package.json` と README を持たせる）。
- そのアプリの README にサンプル画面のスクリーンショットを載せる（このルートの README には載せない）。実測値が写らないよう MOCK などダミー応答の状態で撮る。
- API キーはサーバ側だけで扱い、ブラウザやリポジトリに出さない。
- 起動スクリプトは `--env-file-if-exists=../../.env` でルートの `.env` を読む。

## 計測結果の公開について

TypeSafe AI の利用規約は、サービスのベンチマークや性能情報の公開を禁じている。
このリポジトリには計測結果を含めていない。各アプリで得た数値を公開する場合は、事前に TypeSafe AI の許可を得ること。

## Claude Code 用スキル

`.claude/skills/typesafe-ai/` に TypeSafe AI 公式の Agent skill（MIT License、[typesafe-ai/skills](https://github.com/typesafe-ai/skills)）を同梱している。

## ライセンス

[MIT](LICENSE)。`.claude/skills/typesafe-ai/` は同ディレクトリの LICENSE に従う。
