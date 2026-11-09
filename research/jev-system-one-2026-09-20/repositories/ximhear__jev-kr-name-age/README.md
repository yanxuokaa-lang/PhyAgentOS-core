# 이름으로 보는 나이대 (Jev)

한국·미국·일본·중국 중 나라를 고르고 이름을 입력하면 TypeSafe의 **Jev** 모델(System One API)이 시대별 작명 경향을 바탕으로 나이대와 성별을 추정합니다.

## 데모

https://github.com/ximhear/jev-kr-name-age/raw/main/demo/name-age-demo.mp4

예시 이름 8개를 차례로 눌러 본 화면입니다 ([demo/name-age-demo.mp4](demo/name-age-demo.mp4)).

## 실행

```bash
npm install
cp .env.example .env   # TYPESAFE_API_KEY 입력 (https://console.typesafe.ai/settings/keys)
npm run dev
```

## 구조

- `src/countries.ts` — 나라별 입력 규칙, 작명 경향 힌트, 예시 이름 (UI와 서버가 공유)
- `src/bands.ts` — 나이대별 색상·이모지·태그
- `src/App.tsx` — React UI. `/api/age?country=...&name=...`를 호출하고 나이대별 확률을 막대로 표시
- `server/predict.ts` — `@typesafe-ai/sdk`로 Jev에 `choice` 질문 2개(나이대, 성별)를 보냄
- `server/plugin.ts` — Vite dev/preview 서버에 `/api/age` 엔드포인트를 붙이는 플러그인 (API 키는 서버에만 존재)
