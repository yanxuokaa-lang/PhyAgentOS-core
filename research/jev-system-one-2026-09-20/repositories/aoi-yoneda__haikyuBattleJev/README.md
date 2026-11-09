# haikyuBattleJev

Jev（TypeSafe AI System One）が打者のリアクションを判断する、配球バトル野球シミュレーション。

## 遊び方（HTML版・推奨）

`index.html` をブラウザで開くだけ（依存なし・9回制・パワプロ風能力表示）。

デフォルトはモック Jev。実 API を使う場合は画面上部で「実 API」を選び、`TYPESAFE_API_KEY` を入力。

## Streamlit版

```bash
pip install streamlit
streamlit run app.py
```

## Jev 連携

- リクエスト: `POST https://api.typesafe.ai/v1/systemone`（`state` + Choice 質問）
- レスポンス: `choice` / `confidence` / `probabilities` を正規化して打撃判定に使用
- API キーなしでもモックで同じ形式のレスポンスを返す
