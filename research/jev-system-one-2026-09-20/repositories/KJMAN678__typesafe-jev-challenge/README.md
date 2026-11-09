### TypeSafe の Jev を触ってみた

- サンプルコード
  - [Choice のみ](https://github.com/typesafe-ai/typesafe-sdk-python)
  - [Noul / Choice / Score](https://docs.typesafe.ai/sdk/python/usage#calling-the-system-one-api)

- 手順
  - .env.example をコピーして .env を作成し、TYPESAFE_API_KEY="your-typesafe_api_key" を更新
  - コマンド
```python
$ uv run main.py
```

- 参考 [(英語)TypeSafe Jev — プロジェクト知識リソース](https://gist.github.com/pjburnhill/adf8d28efcad9df037bfdece178ef965)

### Choice のみ

- コード
```python
response = client.system_one(
    state={"document": "GitHub に issueを作成しました。レビューをお願いします"},
    questions={
        "category": Choice(
            instructions="このチケットは何に関するものですか？",
            criteria={"billing": None, "technical": None, "other": None},
        ),
    },
)
```

- 出力
```bash
print(response.choices["category"].choice)
>> technical

print(response.choices["category"].confidence)
>> 0.46

print(response.choices["category"].probabilities)
>> {'technical': 0.64, 'other': 0.36, 'billing': 0.0}

print(response.usage)
>> Usage(input_tokens=336, output_tokens=38)
```
- [モデルの料金](https://docs.typesafe.ai/models)
  - $0.042 / 1Mトークン (2026/9/19時点)

### Noul / Choice / Score
- [参考: Noul / Choice / Score とは](Noul / Choice / Score)
- コード
```python
response = await client.system_one(
    state={"document": "二重に請求されました。至急修正してください。"},
    questions={
        "billing": Noul(instructions="このチケットは請求に関するものですか？"),
        "tone": Choice(
            instructions="顧客の口調はどのようなものですか？",
            criteria={"calm": None, "frustrated": None, "angry": None},
        ),
        "urgency": Score(
            instructions="このチケットの緊急度はどの程度ですか？",
            criteria=["待てる", "今週中", "今日中"],
        ),
    },
)
```
- 出力
```bash
print(response.nouls["billing"].noul)
>> 0.97

print(response.choices["tone"].choice)
>> rustrated
print(response.choices["tone"].confidence)
>> 0.72
print(response.choices["tone"].probabilities)
>> {'frustrated': 0.81, 'calm': 0.01, 'angry': 0.18}

print(response.scores["urgency"].score)
>> 1.99
print(response.scores["urgency"].confidence)
>> 0.99
print(response.scores["urgency"].legend)
>> {0: '待てる', 1: '今週中', 2: '今日中'}
print(response.scores["urgency"].probabilities)
>> {0: 0.0, 1: 0.0, 2: 1.0}
```
