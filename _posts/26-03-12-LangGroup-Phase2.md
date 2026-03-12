---
layout: single
title: "[SmartHee] Phase 2 셋업 — Langfuse 3.x + LangGraph 1.x 연동 트러블슈팅 정리"
excerpt: "Langfuse 3.x + LangGraph 1.x 환경에서 SmartHee Phase 2를 로컬에서 실행하며 겪은 API 변경, 모듈 경로 이동, 콜백 생성 방식 변경 등의 오류 해결 방법을 기록."
categories: [Project, SmartHee]
tags: [python, fastapi, langgraph, langfuse, observability, llm-tracing, 포트폴리오]
---

## 들어가며

멀티에이전트 오케스트레이션 플랫폼 **SmartHee**의 Phase 2를 셋업하면서 겪은 시행착오를 기록한다.  
Phase 2의 핵심은 **Langfuse 기반 LLM 실행 트레이싱**이다. 에이전트가 어떤 프롬프트를 받고, 어떤 LLM을 호출했으며, 응답이 무엇인지, 비용은 얼마인지를 cloud.langfuse.com 대시보드에서 실시간으로 확인하는 것이 목표다.

생각보다 많은 에러가 쏟아졌다. 특히 langfuse 3.x와 LangGraph 1.x 모두 최근에 API가 크게 바뀌었기 때문에 공식 문서보다 실제 설치된 버전이 다른 경우가 많았다.

**환경 정보**
- OS: Windows 10
- Python: 3.13
- 경로: `D:\Project\Multi-Agent\phase2\`
- Phase 2 전용 venv 별도 생성 (`phase2\backend\venv`)

---

## Phase 2에서 추가되는 것

Phase 1 대비 추가 파일은 세 가지다.

```
phase2/backend/
├── core/
│   └── tracing.py        ← Langfuse 연동 핵심
├── agents/
│   └── evaluator/
│       └── evaluator.py  ← LLM Judge 평가
└── api/routes/
    └── evaluation.py     ← 평가 API 라우트
```

`requirements.txt`도 Phase 1 것에 `langfuse` 한 줄만 추가하면 된다.

```txt
# Phase 1 내용 그대로 +

# Observability (Phase 2 신규)
langfuse
```

> **팁:** Phase 1에서 이미 pip가 Python 3.13과 호환되는 버전 조합을 찾아놓은 상태다. Phase 2의 원본 `requirements.txt`를 그대로 쓰면 버전 충돌이 다시 발생할 수 있으므로, Phase 1 기반에 langfuse만 추가하는 방식으로 진행한다.

---

## .env 설정

Phase 2 루트에 `.env.example`이 있다. 복사 후 API 키를 채운다.

```bash
# phase2 루트에서
copy .env.example .env
# 내용 편집 후
copy .env backend\.env
```

### Phase 2 .env 최종 내용

```env
# LLM
OPENAI_API_KEY=sk-...         # 따옴표 없이 입력
DEFAULT_MODEL=openai/gpt-4o

# Database
DATABASE_URL=postgresql+asyncpg://agentforge:<password>@localhost:5432/agentforge
REDIS_URL=redis://localhost:6379/0

# Langfuse (Phase 2 핵심)
LANGFUSE_PUBLIC_KEY=pk-lf-...  # 따옴표 없이 입력
LANGFUSE_SECRET_KEY=sk-lf-...  # 따옴표 없이 입력
LANGFUSE_HOST=https://cloud.langfuse.com

# App
SECRET_KEY=local-dev-secret
DEBUG=true
```

> ⚠️ **보안 주의:** API 키를 Git에 절대 커밋하지 말 것. `.gitignore`에 `.env` 추가 필수. 노출됐다면 즉시 해당 키를 Revoke하고 재발급한다.

---

## 에러 ①  — `ModuleNotFoundError: No module named 'langfuse.callback'`

### 증상

```
from langfuse.callback import CallbackHandler
ModuleNotFoundError: No module named 'langfuse.callback'
```

### 원인

**langfuse 3.x에서 모듈 경로가 변경됐다.**

| 버전 | import 경로 |
|------|------------|
| langfuse 2.x | `from langfuse.callback import CallbackHandler` |
| langfuse 3.x | `from langfuse.langchain import CallbackHandler` |

langfuse 버전이 업데이트되면서 모듈 경로까지 변경된 부분을 미처 알지 못하고 있었다.

### 해결

`tracing.py`의 import 경로 변경:

```python
# 변경 전 (langfuse 2.x)
from langfuse.callback import CallbackHandler

# 변경 후 (langfuse 3.x)
from langfuse.langchain import CallbackHandler
```

---

## 에러 ② — `CallbackHandler.__init__() got an unexpected keyword argument 'secret_key'`

import 경로를 고친 후에도 또 다른 에러가 발생했다.

### 증상

```
WARNING:core.tracing:Langfuse 콜백 생성 실패:
LangchainCallbackHandler.__init__() got an unexpected keyword argument 'secret_key'
```

### 원인

langfuse 3.x에서 `CallbackHandler` 생성 방식이 완전히 바뀌었다.

| 버전 | 생성 방식 |
|------|----------|
| langfuse 2.x | `CallbackHandler(public_key=..., secret_key=..., host=...)` — 직접 전달 |
| langfuse 3.x | 먼저 `Langfuse()` 클라이언트 초기화 후 `CallbackHandler()` 인수 없이 생성 |

기존 코드는 2.x 방식으로 파라미터를 직접 전달하고 있었다.

### 해결 — `tracing.py` 전면 수정

langfuse 3.x 공식 패턴:

```python
# 1. 앱 시작 시 Langfuse 클라이언트 초기화
from langfuse import Langfuse
Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_HOST,
)

# 2. CallbackHandler는 인수 없이 생성 (위에서 초기화한 클라이언트를 자동 참조)
from langfuse.langchain import CallbackHandler
handler = CallbackHandler()
```

최종 `tracing.py` 핵심 구조:

```python
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from core.config import get_settings
import logging, time

logger = logging.getLogger(__name__)
settings = get_settings()

_langfuse_client = None

def _init_langfuse():
    """앱 시작 시 1회 Langfuse 클라이언트 초기화"""
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client
    if not settings.LANGFUSE_PUBLIC_KEY:
        return None
    try:
        _langfuse_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
        logger.info(f"[Langfuse] 초기화 성공 / auth: {_langfuse_client.auth_check()}")
    except Exception as e:
        logger.warning(f"[Langfuse] 초기화 실패: {e}")
        _langfuse_client = None
    return _langfuse_client

# 앱 로드 시 즉시 초기화
_init_langfuse()


def get_langfuse_callback(trace_id: str = None):
    """LangGraph 콜백 핸들러 반환 (langfuse 3.x 방식)"""
    client = _init_langfuse()
    if client is None:
        return None
    try:
        handler = CallbackHandler()   # 인수 없이 생성
        logger.info(f"[Langfuse] 콜백 생성 결과: {handler}")
        return handler
    except Exception as e:
        logger.warning(f"[Langfuse] 콜백 생성 실패: {e}")
        return None


def flush_langfuse():
    """LLM 호출 후 데이터를 Langfuse로 즉시 전송"""
    client = _init_langfuse()
    if client:
        try:
            client.flush()
        except Exception as e:
            logger.warning(f"[Langfuse] flush 실패: {e}")
```

서버 재시작 시 아래 로그가 뜨면 정상이다:

```
INFO - [Langfuse] 초기화 성공 / auth: True
```

---

## 에러 ③ — LangGraph 1.x: `state_modifier` 파라미터 제거

### 증상

```
TypeError: create_react_agent() got an unexpected keyword argument 'state_modifier'
```

### 원인

LangGraph 0.x와 1.x 사이에 `create_react_agent` 파라미터명이 변경됐다.

| 버전 | 파라미터 |
|------|---------|
| LangGraph 0.x | `state_modifier=system_prompt` |
| LangGraph 1.x | `prompt=system_prompt` |

### 해결

```python
# 변경 전 (0.x)
react_agent = create_react_agent(
    model=llm,
    tools=tools,
    state_modifier=system_prompt,
)

# 변경 후 (1.x)
react_agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=system_prompt if system_prompt else None,
)
```

---

## 에러 ④ — `agents.py` 응답 중첩: `output.output` 구조

### 증상

API 응답은 정상(200 OK)이었지만, `output` 안에 또 `output`이 중첩되어 있었다. 명백한 휴먼에러였다. 코드 작성하는 과정에서 발생한 실수다. 손으로 코딩하는 연습을 조금 더 해야겠다는 반성을 하게 된 부분이다.

```json
{
  "run_id": "...",
  "output": {
    "output": "실제 텍스트 응답",
    "run_id": "...",
    "latency_ms": 5895
  },
  "status": "success"
}
```

### 원인

`agents.py` 라우트에서 `result` 전체를 그대로 반환하고 있었다. `graph.py`의 `run()` 메서드는 `{"output": str, "run_id": str, "latency_ms": int}`를 반환하는데, 이걸 `output` 필드에 통째로 담아버린 것이다.

```python
# agents.py — 잘못된 코드
run.output = result           # result 전체 저장 (dict)
return {"run_id": ..., "output": result, "status": "success"}  # 또 중첩
```

### 해결

```python
# agents.py — 수정된 코드
run.output = result["output"]   # 문자열만 저장
return {"run_id": str(run.id), "output": result["output"], "status": "success"}
```

---

## 에러 ⑤ — 들여쓰기 오류: `'AgentOrchestrator' object has no attribute '_build_single_agent_graph'`

### 증상

```json
{"detail": "'AgentOrchestrator' object has no attribute '_build_single_agent_graph'"}
```

### 원인

`graph.py`를 텍스트 에디터에서 편집하다가 들여쓰기가 깨져서 `_build_single_agent_graph` 메서드가 클래스 밖으로 나갔다.

이것 역시 휴먼에러였다. Python에서 들여쓰기 하나가 얼마나 중요한지 다시금 체감했다. 코드를 직접 작성할 때 IDE의 문법 강조(syntax highlighting)를 믿지 말고 줄마다 들여쓰기를 꼼꼼하게 확인하는 습관을 들여야겠다는 반성이 들었다.

Python에서 클래스 메서드는 반드시 클래스 블록 안에서 들여쓰기가 맞아야 한다. `def` 앞의 들여쓰기가 `class` 수준으로 내려가면 독립 함수가 되어버린다.

### 예시 (잘못된 경우)

```python
class AgentOrchestrator:
    def __init__(self, ...):
        ...

    def _build_graph(self):   # 이건 OK
        ...

def _build_single_agent_graph(self):   # ← 들여쓰기가 클래스 밖!
    ...
```

### 해결

들여쓰기가 깨진 부분만 AI의 도움을 받아 수정했다. 부분 편집을 계속 시도했지만 들여쓰기 실수가 반복되어 해당 메서드 블록 단위로 AI를 활용해 교정했다. 앞으로는 AI를 전체 작성 도구가 아닌, 내가 직접 작성한 코드를 검수하고 부분적으로 보완하는 방향으로 활용하는 습관을 들여야겠다.

---

## 에러 ⑥ — `ValueError: Token was created in a different Context`

### 증상

```
ValueError: <Token var=<ContextVar name='current_context' ...> at ...>
was created in a different Context
```

### 원인과 결론

Langfuse가 백그라운드에서 asyncio 컨텍스트를 넘나들며 데이터를 전송하는 과정에서 발생하는 내부 에러다. **에이전트 실행 자체는 정상(200 OK)**이었고 DB 저장도 문제없었다.

이 에러는 Langfuse 3.x + Python 3.13 + uvicorn의 asyncio 이벤트 루프 조합에서 나타나는 알려진 이슈다. 실제 Traces 수집에는 영향이 없었다.

```bash
# 서버 로그에서 이게 보여도
ValueError: <Token ...> was created in a different Context

# 동시에 이게 있으면 정상
INFO - 127.0.0.1 - "POST /api/v1/agents/run HTTP/1.1" 200 OK
```

---

## 🐳 Docker 내 PostgreSQL DB 데이터 적재 확인

API 호출이 정상적으로 완료된 후, 실제로 Docker 내부의 PostgreSQL에 데이터가 저장되었는지 직접 확인했다.

### 확인 방법

```bash
# 실행 중인 컨테이너 이름 확인
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

# PostgreSQL 컨테이너 접속 (psql 인터랙티브 모드)
docker exec -it phase1-postgres-1 psql -U agentforge -d agentforge
```

> Phase 2를 별도 컨테이너로 분리하지 않고 Phase 1의 컨테이너(`phase1-postgres-1`)를 그대로 재사용했다.

### 적재 확인 쿼리

psql 프롬프트 없이 CMD에서 바로 결과를 확인하려면 `-c` 옵션을 사용한다:

```bash
docker exec phase1-postgres-1 psql -U agentforge -d agentforge -c \
  "SELECT id, status, output, token_used, cost_usd, started_at, finished_at FROM agent_runs ORDER BY started_at DESC LIMIT 5;"
```

### agent_runs 테이블 전체 컬럼 구조

```
id              | uuid
agent_config_id | uuid
input           | text
output          | text
status          | character varying
token_used      | integer
cost_usd        | numeric
trace_id        | character varying
started_at      | timestamp with time zone
finished_at     | timestamp with time zone
error           | text
```

### 확인 결과

```
               id                | status  | output             | token_used | cost_usd
---------------------------------+---------+--------------------+------------+---------
 35529c8c-38b7-4fbc-be47-...     | success | (LLM 응답 텍스트) |       1580 | 0.01402
 ...
(5 rows)
```

API 호출 결과가 `agent_runs` 테이블에 정상적으로 저장된 것을 확인했다. `status: success`, `output`에 실제 LLM 응답, `token_used`와 `cost_usd`에 토큰 사용량과 비용까지 기록된다.

> **팁:** Docker Desktop GUI를 사용한다면 해당 컨테이너 → **Exec** 탭에서 위 명령어를 바로 실행할 수 있어 편리하다.

---

## 최종 확인 — Langfuse 대시보드

모든 수정 후 `agents/run` API를 호출하자 cloud.langfuse.com에서 Traces가 잡혔다.

**확인 경로:** cloud.langfuse.com → 프로젝트 선택 → Traces 메뉴

| 항목 | 내용 |
|------|------|
| Traces | 3 Total traces tracked |
| Source | LangGraph |
| Model costs | gpt-4o $0.014035 |
| Tokens | 1.58K |

![Langfuse 대시보드 요약](/assets/images/langfuse_dashboard_summary.png)

![Traces 시간대별 차트 & Model Usage](/assets/images/langfuse_traces_usage.png)

![User consumption](/assets/images/langfuse_user_consumption.png)

![Model latencies](/assets/images/langfuse_model_latencies.png)

실제 호출이 이루어진 3/12 오후 2시 직후에 Traces, 비용, 지연시간 모두 대시보드에 정확하게 찍혔다.

---

## 전체 실행 순서 (Phase 2)

```bash
# 1. Docker 컨테이너 확인 (phase2 루트에서)
docker ps
# postgres, redis 가 Up 상태가 아니면:
docker-compose up -d postgres redis

# 2. 가상환경 활성화 후 서버 실행 (backend/ 에서)
cd backend
venv\Scripts\activate
uvicorn main:app --reload --port 8000

# 3. 서버 정상 시작 확인
# INFO:     Application startup complete.
# INFO - [Langfuse] 초기화 성공 / auth: True

# 4. API 테스트
# http://127.0.0.1:8000/docs 접속
```

---

## 수정 파일 요약

Phase 2에서 원본 코드 대비 수정이 필요했던 파일들:

| 파일 | 수정 내용 |
|------|----------|
| `core/config.py` | `DATABASE_URL` 기본값 수정, `extra = "ignore"` 추가 |
| `core/tracing.py` | langfuse 3.x 초기화 패턴으로 전면 재작성 |
| `agents/orchestrator/graph.py` | LangGraph 1.x `prompt=` 파라미터로 변경 |
| `api/routes/agents.py` | `run.output = result["output"]`으로 수정, 반환값 중첩 제거 |
| `backend/.env` | LANGFUSE 키 따옴표 없이 입력, `LANGFUSE_BASE_URL` 중복 제거 |

---

## 💡 트러블슈팅 요약

| 에러 | 원인 | 해결 |
|------|------|------|
| `No module named 'langfuse.callback'` | langfuse 3.x 모듈 경로 변경 | `langfuse.langchain` 으로 변경 |
| `unexpected keyword argument 'secret_key'` | langfuse 3.x CallbackHandler 생성 방식 변경 | `Langfuse()` 먼저 초기화 후 `CallbackHandler()` 인수 없이 생성 |
| `unexpected keyword argument 'state_modifier'` | LangGraph 1.x 파라미터명 변경 | `state_modifier=` → `prompt=` |
| 응답 `output.output` 중첩 | `result` 전체를 `output` 필드에 저장 | `result["output"]`으로 수정 |
| `object has no attribute` | 들여쓰기 오류로 메서드가 클래스 밖으로 | 전체 파일 재작성 후 교체 |
| `Token was created in a different Context` | langfuse 3.x + Python 3.13 asyncio 이슈 | 무시해도 됨 (기능 정상) |

> **핵심 교훈:** langfuse와 LangGraph 모두 최근에 메이저 버전이 올라가면서 API가 크게 바뀌었다. 라이브러리 버전을 고정하지 않으면 이전 문서가 그대로 맞지 않는 경우가 많다. 설치 후 `pip show langfuse`, `pip show langgraph`로 실제 설치된 버전을 반드시 확인하자.

---

## 다음 단계

Phase 3에서는 **Celery 비동기 작업**, **웹훅**, **마켓플레이스**를 추가할 예정이다.