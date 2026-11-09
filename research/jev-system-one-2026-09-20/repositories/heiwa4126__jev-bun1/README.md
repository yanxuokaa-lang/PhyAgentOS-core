# jev-bun1

[TypeSafe の Jev](https://docs.typesafe.ai/introduction)
を
[TypeScript SDK](https://docs.typesafe.ai/sdk/javascript)
で使ってみる最初の 1 歩。

## 開発

初期設定:

```bash
# 依存パッケージをインストール
bun ci
# APIキーを設定
cp .env.example .env
## で .env を編集
```

最初の実行:

```bash
# https://docs.typesafe.ai/sdk/javascript にあるサンプルそのまま
bun run ex0
```

上記の実行例:

```console
$ bun run ex0
billing
```

### さらなるサンプル

```sh
# Playground の Noul のサンプル「ホットドックはサンドイッチか?」を API で
bun run noul1
bun run noul2 # placefolder 使用
bun run noul3 # 並列問い合わせ
# noul1 を改造して、日本語のテスト「バナナはおやつに入りますか?」
bun run j-noul1 # おやつ判定されたけど、ちゃんと理解してるかわからん...
```

This project was created using `bun init` in bun v1.4.2.
[Bun](https://bun.com) is a fast all-in-one JavaScript runtime.
