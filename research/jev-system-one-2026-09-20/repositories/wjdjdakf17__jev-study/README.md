# jev-study

**Jev(TypeSafe AI의 "System One Model")를 공부한 기록 —
한국어 스터디 노트 + 개념의 TypeScript 타이핑 + 목업 워크플로우 실험.**

2026년 9월 15일, ChatGPT 공동 발명자 디오구 알메이다가 2년의 스텔스를
끝내고 내놓은 모델이 Jev다. LLM이 문장을 *생성*하는 것과 달리
Jev는 **판단만 한다** — 미리 정의된 선택지·척도·명제에 대해
**타입으로 보장된 값 + 보정된 확률**을 70~500ms 안에 돌려준다.

> "프론티어 지능을 가진 함수 호출:
> 비정형 state가 들어가고, 타입화된 확률적 결정이 나온다."
> — TypeSafe AI

이 레포는 얼리 액세스 모델이라 실제 API를 호출하는 대신,
**공개된 개념을 코드로 옮겨 이해하는 것**을 목표로 한다.

## 레포 구성

| 위치 | 내용 |
| --- | --- |
| `docs/` | 한국어 스터디 노트 5편 (아래) |
| `src/types.ts` | 질문 3종(Choice/Score/Noul)·결정·confidence를 TypeScript 타입으로 모델링 |
| `src/client.ts` | `DecisionClient` 인터페이스 + 결정론적 목업 구현 |
| `src/workflow.ts` | **confidence-gated routing** — 확률을 소비하는 if문 패턴 |
| `src/calibration.ts` | 보정 측정 도구 — Brier score, 신뢰도 버킷 |
| `tests/` | 26개 테스트 (타입 계산 / 목업 계약 / 정책 / 보정 수학) |

## 빠른 시작

```bash
git clone https://github.com/wjdjdakf17/jev-study && cd jev-study
npm install
npm test        # 26 tests
npm run example # 티켓 3종 라우팅 데모
```

예제 출력(목업) — 애매한 티켓은 confidence 게이트에서 걸려
사람 검토로 넘어가는 모습:

```
===== 2) 애매한 티켓 (라우팅 팀이 갈림) =====
  라우팅: technical (confidence 0.20) [billing 40% · technical 60% · account 0%]
→ 결과: 사람 검토로 에스컬레이션 — 라우팅 confidence 0.20가 임계값 0.5 미만
```

## 스터디 노트

1. [Jev란 무엇인가](docs/01-what-is-jev.md) — 한 줄 정의, 이름의 유래(칸만·제번스), 왜 뜨거운가
2. [작동 방식](docs/02-how-it-works.md) — state/질문/결정 구조, Choice·Score·Noul, 병렬 샘플링, confidence vs calibration
3. [LLM과의 비교](docs/03-llm-vs-system-one.md) — RLHF/RLVR/RLCD, 문자열을 포기한다는 것, 경쟁이 아니라 분업
4. [어디에 쓸까, 한계는](docs/04-use-cases-limits.md) — 스마트 if문·실시간 데모들, 공식 limitations, 비판적으로 읽기
5. [참고자료](docs/05-references.md) — 1차 소스와 코드-개념 대응표

## 핵심 요약 (내 3줄)

1. **문자열 생성을 포기하면 타입 안전·병렬 샘플링·확률 보고가 남는다** — 속도와 비용이 자릿수 단위로 무너지는 대가
2. **structured ≠ correct** — 타입 안전성은 실패의 모양을 좁힐 뿐, 판단 품질은 별도 검증(→ calibration)
3. **확률을 소비하는 건 코드다** — 판단은 모델, 정책은 if문. 이 분업은 Jev 없이도 지금 당장 적용할 수 있는 교훈

## 면책

Jev는 TypeSafe AI의 상표·제품이고 이 레포는 개인 스터디다.
실제 API 명세와 다를 수 있으며, 인용 수치는 전부 벤더/커뮤니티
셀프 리포트다 (비판적 맥락: [docs/04](docs/04-use-cases-limits.md)).

## 라이선스

[MIT](LICENSE)
