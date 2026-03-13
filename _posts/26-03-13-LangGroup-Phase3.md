---
layout: single
title: "[SmartHee] Phase 3 셋업 — Celery 비동기 작업 + 웹훅 + 마켓플레이스 트러블슈팅 정리"
excerpt: "Celery + Redis + FastAPI 환경에서 SmartHee Phase 3를 로컬에서 실행하며 겪은 모듈 경로 오류, Windows PermissionError, Langfuse 인증 실패 등의 오류 해결 방법을 기록."
categories: [Project, SmartHee]
tags: [python, fastapi, celery, redis, langgraph, langfuse, webhook, 비동기, 포트폴리오]
---Q

## 들어가며

멀티에이전트 오케스트레이션 플랫폼 **SmartHee**의 Phase 3를 셋업하면서 겪은 시행착오를 기록한다.  
Phase 3의 핵심은 **Celery 기반 비동기 에이전트 실행과 웹훅 콜백**이다. 에이전트 실행 요청이 들어오면 즉시 `task_id`를 반환하고, 실행이 완료되면 지정한 `callback_url`로 결과를 POST하는 것이 목표다.

Phase 2에서 해결했던 에러들이 Phase 3에도 그대로 이어졌고, 여기에 Celery 고유의 Windows 환경 이슈가 더해졌다.

**환경 정보**
- OS: Windows 11
- Python: 3.13
- 경로: `D:\Project\Multi-Agent\phase3\`
- Phase 3 전용 venv 별도 생성 (`phase3\backend\venv`)

---

## Phase 3에서 추가되는 것

Phase 2 대비 추가 파일은 세 가지다.

```
phase3/backend/
├── services/
│   └── tasks.py          ← Celery 비동기 태스크 핵심
├── models/
│   └── platform.py       ← AgentSchedule, MarketplaceTemplate, Skill 모델
└── api/routes/
    └── platform.py       ← 스케줄링 / 웹훅 / 마켓플레이스 / 스킬 API
```

`requirements.txt`도 Phase 2 것에 `celery`만 추가하면 된다.

```txt
# Phase 2 내용 그대로 +

# Task Queue (Phase 3 신규)
celery
```

> **팁:** Phase 3 원본 `requirements.txt`에는 `langfuse==2.0.0`과 `celery==5.4.0`이 중복 기재되어 있고, 존재하지 않는 버전이 고정되어 있다. Phase 2 기반에 `celery`만 추가하는 방식으로 진행한다.

---

## Langfuse를 선택한 이유

### LLM 애플리케이션 특유의 관측 문제

일반적인 웹 서비스는 응답 시간, 에러율, 처리량 같은 지표만 모니터링하면 충분하다. 그런데 LLM 기반 에이전트는 다르다. 같은 입력을 넣어도 매번 다른 결과가 나오고, 어떤 프롬프트가 어떤 응답을 유발했는지, LLM이 어떤 도구를 몇 번 호출했는지, 비용은 얼마나 나왔는지를 추적하지 않으면 에이전트 동작을 이해하거나 개선하기가 매우 어렵다.

예를 들어 에이전트가 틀린 답을 냈을 때, "어느 단계에서 잘못됐는지"를 파악하려면 다음 정보가 필요하다.

- 어떤 시스템 프롬프트를 사용했는가
- LLM이 어떤 도구를 선택했는가
- 도구 실행 결과는 무엇이었는가
- LLM이 최종 응답을 생성할 때 어떤 컨텍스트를 받았는가

이것을 로그 파일에서 수동으로 추적하는 것은 현실적으로 불가능하다. 바로 이 문제를 해결하기 위한 도구가 **LLM Observability 플랫폼**이다.

### Langfuse를 선택한 구체적인 이유

| 항목 | 내용 |
|------|------|
| **LangChain/LangGraph 네이티브 지원** | `CallbackHandler` 한 줄이면 LangGraph의 모든 노드 실행, LLM 호출, 도구 사용이 자동으로 추적된다. 별도 계측 코드가 거의 필요 없다. |
| **비용 자동 계산** | 모델별 토큰 단가를 내장하고 있어 호출당 비용을 자동으로 계산해준다. gpt-4o 기준 입출력 토큰 비용이 대시보드에 바로 표시된다. |
| **오픈소스 + Self-hosted 가능** | cloud.langfuse.com을 무료로 쓸 수 있고, 데이터를 외부로 보내고 싶지 않다면 Docker로 로컬에 직접 띄울 수 있다. |
| **Trace 단위 디버깅** | 에이전트 실행 한 번을 Trace로 묶어서, 내부 LLM 호출과 도구 실행을 트리 구조로 시각화해준다. 어느 단계에서 지연이 발생했는지 한눈에 파악 가능하다. |
| **A/B 테스트 지원** | 같은 입력에 대해 다른 모델이나 프롬프트를 비교하는 평가 기능을 내장하고 있다. Phase 2의 `evaluator.py`가 이 기능을 활용한다. |

### SmartHee에서의 연동 구조

```
사용자 요청
    ↓
FastAPI (agents/run)
    ↓
AgentOrchestrator.run()
    ↓
LangGraph 실행  ←── CallbackHandler (자동 추적 시작)
    ├── LLM 호출 1  → Langfuse에 입력/출력/토큰 기록
    ├── Tool 실행   → Langfuse에 도구명/결과 기록
    └── LLM 호출 2  → Langfuse에 최종 응답 기록
    ↓
flush_langfuse()  → 수집 데이터 cloud.langfuse.com으로 전송
```

코드 관점에서는 `get_langfuse_callback()`이 반환하는 핸들러를 LangGraph의 `config={"callbacks": [cb]}`에 넘기는 것만으로 전체 실행 흐름이 추적된다.

```python
cb = get_langfuse_callback(state.get("run_id"))
response = await react_agent.ainvoke(
    {"messages": [HumanMessage(content=state["task_input"])]},
    config={"callbacks": [cb]} if cb else {},  # ← 이 한 줄로 전체 추적
)
```

---

## Celery Worker를 선택한 이유

### 동기 실행의 한계

Phase 1~2의 `/api/v1/agents/run`은 동기 방식이다. 요청이 들어오면 에이전트 실행이 완료될 때까지 HTTP 연결을 유지하고, 완료되면 응답을 반환한다.

```
클라이언트 ──요청──→ FastAPI ──실행 중(6~30초)──→ 응답
          ←────────────────────────────────────────
```

이 방식은 간단하지만 두 가지 문제가 있다.

첫째, **타임아웃 문제**다. 에이전트가 여러 도구를 반복 호출하거나 복잡한 멀티에이전트 워크플로우를 실행하면 수십 초가 걸릴 수 있다. 브라우저나 API 클라이언트의 기본 타임아웃(30~60초)을 초과하면 연결이 끊어진다.

둘째, **스케줄링이 불가능하다**. "매일 오전 9시에 뉴스를 요약해서 슬랙으로 보내줘" 같은 반복 실행은 HTTP 요청 기반으로는 구현할 수 없다.

### Celery가 해결하는 것

Celery는 **분산 태스크 큐(Distributed Task Queue)**다. FastAPI가 태스크를 큐에 넣으면(`delay()`), 별도 프로세스인 Celery Worker가 큐에서 꺼내 실행한다.

```
클라이언트 ──요청──→ FastAPI ──task_id 즉시 반환──→ 클라이언트
                       ↓
                   Redis 큐에 태스크 등록
                       ↓
               Celery Worker (별도 프로세스)
                       ↓
                   에이전트 실행 (6~30초)
                       ↓
               callback_url로 결과 POST  ──→ 클라이언트
```

FastAPI는 요청을 받는 즉시 `task_id`를 반환하고 연결을 끊는다. 실행이 완료되면 Celery Worker가 지정한 `callback_url`로 결과를 POST(웹훅)한다. 클라이언트는 타임아웃 걱정 없이 나중에 결과를 받을 수 있다.

### Redis를 브로커로 선택한 이유

Celery는 브로커(Broker)와 백엔드(Result Backend)가 필요하다. 브로커는 태스크 메시지를 저장하는 큐이고, 백엔드는 태스크 실행 결과를 저장하는 저장소다.

AgentForge는 이미 Phase 1부터 Redis를 인프라에 포함하고 있었다. 별도 인프라 없이 Redis를 그대로 재활용할 수 있어 선택했다.

```env
CELERY_BROKER_URL=redis://localhost:6379/1    # DB 1번 — 태스크 큐
CELERY_RESULT_BACKEND=redis://localhost:6379/2 # DB 2번 — 실행 결과
REDIS_URL=redis://localhost:6379/0             # DB 0번 — 애플리케이션 캐시
```

Redis DB 번호를 분리해서 용도별로 데이터가 섞이지 않도록 구성했다.

### AgentForge Phase 3의 Celery 활용

```python
# 즉시 비동기 실행 (웹훅)
task = run_agent_task.delay(
    agent_id=req.agent_id,
    input_text=req.input_text,
    webhook_url=req.callback_url,  # 완료 시 결과 POST
)
return {"task_id": task.id, "status": "queued"}

# 스케줄 실행 (Celery Beat — cron 방식)
app.conf.beat_schedule = {
    "daily-news": {
        "task": "run_agent",
        "schedule": crontab(hour=9, minute=0),  # 매일 오전 9시
        "args": (agent_id, "오늘의 AI 뉴스를 요약해줘"),
    }
}
```

---

## .env 설정

Phase 2 `.env`에 Celery 항목만 추가한다.

```env
# LLM
OPENAI_API_KEY=sk-...         # 따옴표 없이 입력
DEFAULT_MODEL=openai/gpt-4o

# Database
DATABASE_URL=postgresql+asyncpg://agentforge:your_db_password@localhost:5432/agentforge
REDIS_URL=redis://localhost:6379/0

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-...  # 따옴표 없이 입력
LANGFUSE_SECRET_KEY=sk-lf-...  # 따옴표 없이 입력
LANGFUSE_HOST=https://cloud.langfuse.com

# Celery (Phase 3 신규)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# App
SECRET_KEY=your-local-secret-key
DEBUG=true
```

> ⚠️ **주의:** Langfuse 키를 따옴표(`"`)로 감싸면 따옴표 자체가 키값으로 인식되어 `401 Invalid credentials` 에러가 발생한다. 반드시 따옴표 없이 입력한다.

---

## 에러 ① — Phase 2와 동일: `No module named 'langfuse.callback'`

Phase 3 원본 `tracing.py`가 langfuse 2.x 기준으로 작성되어 있었다.

### 해결

Phase 2에서 수정한 `tracing.py`를 그대로 적용한다. 추가로 Phase 3에서는 Langfuse 3.x에서 제거된 `lf.trace()` 메서드 호출도 제거해야 한다.

```python
# 변경 전 (langfuse 2.x — 두 가지 문제)
from langfuse.callback import CallbackHandler   # ← 경로 오류
...
self._trace = self.lf.trace(...)   # ← 3.x에서 제거된 메서드

# 변경 후 (langfuse 3.x)
from langfuse.langchain import CallbackHandler  # ← 경로 수정
...
# trace() 호출 제거 — 콜백 핸들러가 자동으로 trace 수집
```

`AgentTracer` 클래스를 단순화하여 `lf.trace()` 관련 코드를 전부 제거했다.

단순화한 이유는 **역할 중복** 때문이다. 기존 `AgentTracer`는 `lf.trace()`를 직접 호출해서 trace를 생성하고, 내부 span도 직접 기록하는 방식이었다. 그런데 `CallbackHandler`를 LangGraph의 `config`에 넘기면 LangGraph가 노드 실행, LLM 호출, 도구 사용을 **자동으로** trace에 기록한다. 즉, `AgentTracer`가 손수 trace를 만들어 봤자 `CallbackHandler`가 만든 trace와 별개로 생성되어 **같은 실행이 두 개의 trace로 중복 기록**되는 문제가 생긴다.

따라서 `AgentTracer`의 역할을 "실행 시간 측정 + 종료 시점에 `flush_langfuse()` 호출"로만 좁히고, trace 수집 자체는 `CallbackHandler`에게 온전히 맡기는 방식으로 책임을 분리했다. `span()`과 `update()`는 기존 호출부 코드를 건드리지 않기 위해 아무 동작도 하지 않는 noop으로 대체했다.

```python
class AgentTracer:
    def __init__(self, run_id: str, agent_name: str, input_text: str = ""):
        self.run_id = run_id
        self.agent_name = agent_name
        self.input_text = input_text
        self._start_time = None

    def __enter__(self):
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        flush_langfuse()   # 콜백 핸들러가 trace 자동 수집

    def span(self, name: str, input_data=None):
        return _NoopSpan()

    def update(self, output=None, usage=None, metadata=None):
        pass
```

---

## 에러 ② — Phase 2와 동일: `state_modifier` 파라미터 제거

Phase 3 원본 `graph.py`에도 LangGraph 0.x 기준 파라미터가 남아 있었다.

### 증상

```json
{
  "detail": "create_react_agent() got unexpected keyword arguments: {'state_modifier': '이 에이전트는...'}"
}
```

### 원인

`graph.py`에 두 가지 문제가 동시에 존재했다.

첫째, `state_modifier` → `prompt` 파라미터명 변경 (LangGraph 1.x).  
둘째, `_build_single_agent_graph` 메서드에서 `system_prompt` 변수가 정의되지 않은 채로 사용되고 있었다.

```python
# 잘못된 코드 — system_prompt가 어디서 왔는지 불명확
react_agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=system_prompt if system_prompt else None,  # ← system_prompt 미정의!
)
```

### 해결

`self.config`에서 가져오도록 명시하고, `build_worker_node`의 `state_modifier`도 함께 수정했다.

```python
# _build_single_agent_graph 수정
def _build_single_agent_graph(self):
    llm = get_llm(self.config["model"], temperature=0.0)
    tools = ToolRegistry.get(self.config.get("tools", []))
    system_prompt = self.config.get("system_prompt", "")   # ← config에서 가져오도록
    react_agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt if system_prompt else None,   # ← state_modifier → prompt
    )

# build_worker_node 수정
role = worker_cfg.get("role", "")
react_agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=role if role else None,   # ← state_modifier → prompt
)
```

---

## 에러 ③ — Phase 2와 동일: `output` 타입 오류

### 증상

```
sqlalchemy.exc.DBAPIError: invalid input for query argument $1:
{'output': '온톨로지 네이티브(Ontology Native)는...'} (expected str, got dict)
```

### 원인 및 해결

`agents.py`에서 `result` dict 전체를 DB의 `output` VARCHAR 컬럼에 저장하려 해서 발생한다.

```python
# 변경 전
run.output = result
return {"run_id": str(run.id), "output": result, "status": "success"}

# 변경 후
run.output = result["output"]   # 문자열만 저장
return {"run_id": str(run.id), "output": result["output"], "status": "success"}
```

---

## 에러 ④ — Langfuse `401 Invalid credentials`

Phase 2에서 정상 동작하던 Langfuse가 Phase 3에서는 인증 실패가 떴다.

### 증상

```
[Langfuse] 초기화 실패: status_code: 401,
body: {'message': "Invalid credentials. Confirm that you've configured the correct host."}
```

### 원인

Phase 2 `.env`에서는 Langfuse 키가 따옴표로 감싸져 있었는데 정상 동작했다. Phase 3에서 키를 새로 입력하는 과정에서 실수로 잘못된 키값이 들어갔다.

### 해결

`cloud.langfuse.com → Settings → API Keys`에서 키를 재확인 후 `.env`에 다시 정확히 입력했다. 따옴표 없이 입력하는 것이 안전하다.

```env
# 잘못된 예 (따옴표 포함)
LANGFUSE_PUBLIC_KEY="pk-lf-abc123"

# 올바른 예 (따옴표 없이)
LANGFUSE_PUBLIC_KEY=pk-lf-abc123
```

---

## 에러 ⑤ — Celery Windows `PermissionError: [WinError 5]`

Phase 3에서 처음 만나는 Celery 고유 에러다.

### 증상

```
PermissionError: [WinError 5] 액세스가 거부되었습니다
billiard\pool.py: self._semlock.__enter__()
Process 'SpawnPoolWorker-7' pid:30056 exited with 'exitcode 1'
```

Worker 프로세스가 계속 죽고 재시작되면서 무한 반복된다.

### 원인

Celery의 기본 멀티프로세싱 방식(`prefork`)은 Windows에서 공유 메모리 세마포어 접근 시 권한 문제가 발생한다. billiard(Celery의 멀티프로세싱 라이브러리)가 Windows의 프로세스 격리 정책과 충돌하는 것이다.

### 해결

`--pool=solo` 옵션으로 단일 프로세스 모드로 실행한다. 개발 환경에서는 충분하다.

```bash
# 기존 (실패)
celery -A services.tasks worker --loglevel=info

# 수정 (성공)
celery -A services.tasks worker --loglevel=info --pool=solo
```

정상 실행 시 아래 로그가 뜬다:

```
[tasks]
  . run_agent

[2026-03-13 11:08:56] celery@your-hostname ready.
```

> **참고:** `--pool=solo`는 동시 실행(concurrency)이 없는 단일 스레드 모드다. 운영 환경에서는 Linux/Docker 환경에서 기본 `prefork`나 `gevent`를 사용한다.

---

## 에러 ⑥ — Celery `ModuleNotFoundError: No module named 'models'`

### 증상

```
[Celery] 에이전트 실행 실패: No module named 'models'
Task run_agent[...] retry: Retry in 60s: ModuleNotFoundError("No module named 'models'")
```

### 원인

`tasks.py`의 `_execute_agent` 함수 안에 지연 import가 있다.

```python
async def _execute_agent(agent_id: str, input_text: str) -> dict:
    from models.agent import AgentConfig          # ← 지연 import
    from agents.orchestrator.graph import ...     # ← 지연 import
```

Celery Worker가 `backend/` 경로를 `sys.path`에 추가하지 않은 상태에서 이 import가 실행되면 `models` 패키지를 찾지 못한다. `backend/`에서 실행해도 Celery 내부에서 서브프로세스가 생성될 때 경로가 초기화되기 때문이다.

### 해결

`tasks.py` 상단에 `sys.path`를 명시적으로 추가한다.

```python
from celery import Celery
from celery.schedules import crontab
import sys
import os

# Celery Worker가 backend\ 경로를 인식하도록 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_settings
import asyncio
import httpx
import logging
```

`os.path.abspath(__file__)`은 `tasks.py` 자신의 경로, `dirname` 두 번으로 `services/` → `backend/` 경로를 얻는다.

---

## 최종 확인 — 웹훅 비동기 실행

모든 수정 후 웹훅 API로 Celery가 실제로 동작하는지 확인한다.

**1단계 — 에이전트 생성** (`POST /api/v1/builder/create`):

```json
{
  "request": "ADFS에 대해 설명하는 에이전트 만들어줘",
  "model": "openai/gpt-4o"
}
```

**2단계 — 웹훅으로 비동기 실행** (`POST /api/v1/webhook/run`):

```json
{
  "agent_id": "복사한 agent_id",
  "input_text": "ADFS란 무엇인가요?",
  "callback_url": "https://httpbin.org/post"
}
```

> **`https://httpbin.org/post`는 테스트용 공개 API 서버다.** 받은 HTTP 요청 내용을 그대로 JSON으로 응답해주는 도구로, 웹훅 콜백이 실제로 도착하는지 확인하는 용도로 사용한다. 실제 운영 시에는 슬랙 웹훅, 사내 API 서버, n8n 등 결과를 수신할 실제 URL로 교체하면 된다.

즉시 반환되는 응답:

```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "queued",
  "callback_url": "https://httpbin.org/post",
  "message": "완료 시 callback_url로 결과가 전송됩니다."
}
```

**3단계 — 태스크 상태 조회** (`GET /api/v1/webhook/status/{task_id}`):

```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "SUCCESS",
  "result": {
    "output": "ADFS(Active Directory Federation Services)는...",
    "run_id": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
    "latency_ms": 6081
  }
}
```

`"status": "SUCCESS"`가 나오면 Celery 비동기 실행 완전 동작 확인이다.

동시에 **Celery Worker 터미널(터미널 2)**에도 아래 로그가 찍힌다.

```
[2026-03-13 11:18:54] INFO/MainProcess] [Webhook] 전송 성공: https://httpbin.org/post → 200
[2026-03-13 11:18:54] INFO/MainProcess] Task run_agent[xxxxxxxx-...] succeeded in 11.67s: {
    'output': 'ADFS(Active Directory Federation Services)는 Microsoft에서 개발한...',
    'run_id': 'yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy',
    'latency_ms': 6081
}
```

세 가지를 동시에 확인할 수 있다.

| 확인 항목 | 로그 내용 |
|----------|----------|
| 웹훅 콜백 성공 | `[Webhook] 전송 성공: https://httpbin.org/post → 200` |
| 태스크 정상 완료 | `Task run_agent[...] succeeded in 11.67s` |
| 에이전트 실행 결과 | `output`, `run_id`, `latency_ms` 포함된 dict |

> **참고:** `succeeded in 11.67s`는 Celery가 태스크를 큐에서 꺼낸 시점부터 완료까지의 전체 시간이다. `latency_ms: 6081`은 LangGraph 내부 실행 시간으로, 차이만큼은 DB 조회, 오케스트레이터 초기화 등에 소요된 시간이다.

---

## 전체 실행 순서 (Phase 3)

```bash
# 1. Docker 컨테이너 확인 (phase3 루트에서)
docker ps
# postgres, redis 가 Up 상태가 아니면:
docker-compose up -d postgres redis

# 2. 터미널 1 — FastAPI 서버 (backend\ 에서)
cd backend
venv\Scripts\activate
uvicorn main:app --reload --port 8000

# 3. 터미널 2 — Celery Worker (backend\ 에서)
venv\Scripts\activate
celery -A services.tasks worker --loglevel=info --pool=solo

# 4. 서버 정상 시작 확인
# INFO:     Application startup complete.
# INFO - [Langfuse] 초기화 성공 / auth: True
# celery@your-hostname ready.

# 5. API 테스트
# http://127.0.0.1:8000/docs 접속
```

---

## 수정 파일 요약

Phase 3에서 원본 코드 대비 수정이 필요했던 파일들:

| 파일 | 수정 내용 |
|------|----------|
| `requirements.txt` | 버전 고정 제거, 중복 제거, `celery`만 추가 |
| `core/config.py` | `DATABASE_URL` 기본값 수정, `extra = "ignore"` 추가 |
| `core/tracing.py` | `langfuse.langchain` 경로 수정, `lf.trace()` 제거 (3.x 미지원) |
| `agents/orchestrator/graph.py` | `state_modifier` → `prompt`, `system_prompt` 미정의 변수 수정 |
| `api/routes/agents.py` | `run.output = result["output"]`으로 수정 |
| `services/tasks.py` | `sys.path.insert` 추가 (모듈 경로 문제 해결) |
| Celery 실행 옵션 | `--pool=solo` 추가 (Windows PermissionError 해결) |

---

## 삽질 요약 및 교훈

| 에러 | 원인 | 해결 |
|------|------|------|
| `No module named 'langfuse.callback'` | langfuse 3.x 모듈 경로 변경 | `langfuse.langchain`으로 변경 |
| `'Langfuse' object has no attribute 'trace'` | langfuse 3.x에서 `trace()` 제거 | `AgentTracer`에서 `lf.trace()` 코드 제거 |
| `unexpected keyword argument 'state_modifier'` | LangGraph 1.x 파라미터명 변경 | `state_modifier=` → `prompt=` |
| `system_prompt` 미정의 변수 | `_build_single_agent_graph`에서 변수 미선언 | `self.config.get("system_prompt", "")` 으로 수정 |
| `expected str, got dict` | `result` 전체를 VARCHAR 컬럼에 저장 시도 | `result["output"]` 문자열만 저장 |
| Langfuse `401 Invalid credentials` | `.env` 키값 오입력 | 키 재확인 후 따옴표 없이 재입력 |
| Celery `PermissionError: [WinError 5]` | Windows에서 billiard 멀티프로세싱 권한 충돌 | `--pool=solo` 옵션으로 단일 프로세스 실행 |
| `No module named 'models'` | Celery 서브프로세스에서 `backend/` 경로 미인식 | `sys.path.insert`로 명시적 경로 추가 |

> **핵심 교훈:** Phase 2에서 수정했던 에러들이 Phase 3에도 그대로 반복됐다. 각 Phase의 원본 코드가 최신 라이브러리 버전을 반영하지 않은 상태이기 때문이다. Phase를 올릴 때마다 `tracing.py`, `graph.py`, `agents.py`는 이전 Phase에서 수정한 버전을 기반으로 이어가는 것이 맞다.

---

## 다음 단계

Phase 4에서는 **비용 추적(Cost Tracker)**, **테스트 자동화**, **CI/CD** 파이프라인을 추가할 예정이다.
