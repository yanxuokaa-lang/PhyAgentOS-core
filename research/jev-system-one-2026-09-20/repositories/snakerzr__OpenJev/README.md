# OpenJev — Decisions API Gateway

Легковесный **System One** шлюз к [vLLM](https://github.com/vllm-project/vllm): модель не генерирует текст (`max_tokens=1`). Шлюз собирает промпт, батчит вопросы, запрашивает logprobs у vLLM и возвращает строго типизированные ответы: `choice`, `score`, `noul`.

```
Client → OpenJev (FastAPI + tokenizer) → vLLM /v1/completions → logprob slice → Decisions
```

PyTorch в проекте **нет** — инференс только на стороне vLLM; локальный `uv sync` ставит FastAPI, httpx и transformers (токенизатор).

## Требования

- [uv](https://docs.astral.sh/uv/) и Python **3.11** (`.python-version`)
- Для полного стека: Docker + NVIDIA GPU (vLLM-контейнер)
- Hugging Face-модель instruct/chat (по умолчанию `Qwen/Qwen2.5-1.5B-Instruct`)

## Быстрый старт (Docker)

```bash
docker compose up --build
```

- Decisions API: http://localhost:8000 (`GET /health` → `backend: "vllm"`)
- vLLM OpenAI API: http://localhost:8001/v1

## Локальная разработка (только шлюз)

```bash
uv sync
uv sync --group dev    # pytest
```

vLLM уже запущен (например, из compose на порту 8001):

```bash
uv run openjev --vllm-url http://127.0.0.1:8001/v1 --model Qwen/Qwen2.5-1.5B-Instruct --prompt-format instruct
```

### CLI

| Флаг | Смысл |
|------|--------|
| `--vllm-url` | Базовый URL OpenAI API vLLM (по умолчанию `http://localhost:8001/v1`) |
| `--model` | ID модели в vLLM и для токенизатора |
| `--prompt-format instruct` | **`instruct`** (рекомендуется для System One), `chatml`, `auto` |
| `--max-length` | Лимит промпта; в vLLM уходит `truncate_prompt_tokens = max_length - 1` |
| `--temperature` | Softmax по кандидатам-буквам |
| `--timeout` | Таймаут HTTP к vLLM (сек.) |

### Переменные окружения

`OPENJEV_VLLM_URL`, `OPENJEV_MODEL`, `OPENJEV_MAX_LENGTH`, `OPENJEV_PROMPT_FORMAT`, `OPENJEV_TEMPERATURE`, `OPENJEV_VLLM_TIMEOUT`, `OPENJEV_TRUST_REMOTE_CODE`.

## Проверка API

```powershell
curl.exe -s http://127.0.0.1:8000/v1/decisions -H "Content-Type: application/json" -d "@examples/request.json"
```

Заголовок `X-Inference-Time-Ms` — время round-trip шлюз + vLLM.

## Контракт

| Тип | Выход |
|-----|--------|
| `choice` | `choice` + `probabilities` по меткам `criteria` |
| `score` | `score` (argmax), `expected` = Σ i·P_i, `probabilities` |
| `noul` | `noul` = P(true) |

Подробнее: [`ARCHITECTURE.md`](ARCHITECTURE.md).

### Формат промпта (System One)

При 0-token решении для малых моделей (1.5B) обычно лучше **`instruct`** (финал `Select single option letter:`), а не ChatML assistant-префикс. В `docker-compose.yml` по умолчанию `OPENJEV_PROMPT_FORMAT=instruct`.

## Бенчмарк

```bash
uv sync --group benchmark
uv run python benchmark/evaluate.py --endpoint http://127.0.0.1:8000/v1/decisions --concurrency 4
```

См. [`benchmark/README.md`](benchmark/README.md).

### Референс (RTX 3050 6 GB, Qwen2.5-1.5B, `instruct`, `c=4`)

| Метрика | Значение |
|--------|----------|
| Schema violations | **0%** (38/38) |
| Choice Top-1 | ~87% |
| Latency P50 | ~85 ms |
| Latency P95 | ~630 ms |

Стек vLLM: образ `v0.8.5`, `--max-model-len 1024`, `--gpu-memory-utilization 0.88`.

## Структура пакета `openjev/`

| Модуль | Роль |
|--------|------|
| `schemas.py` | Pydantic контракт API |
| `prompter.py` | Промпты instruct / ChatML |
| `decoding.py` | logprob → softmax → ответы (без torch) |
| `engine.py` | HTTP-клиент vLLM + токенизатор |
| `server.py` | FastAPI |

## Архитектура

[`ARCHITECTURE.md`](ARCHITECTURE.md) — пайплайн System One, vLLM и калибровка.
