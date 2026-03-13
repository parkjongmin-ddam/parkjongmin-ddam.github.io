---
layout: single
title: "[SmartHee] Phase 4 셋업 — Cost Tracker + React 프론트엔드 트러블슈팅 정리"
excerpt: "SmartHee 마지막 Phase. pytest 테스트 자동화, 비용 추적(Cost Tracker), React + Vite 프론트엔드 연동까지. Phase 1~3에서 반복됐던 에러가 4에서도 동일하게 등장했고, 해결 방법도 동일했다."
date: 2026-03-13
categories: [Project, SmartHee]
tags: [python, fastapi, react, vite, typescript, langgraph, langfuse, celery, cost-tracker, 포트폴리오]
---

## 들어가며

멀티에이전트 오케스트레이션 플랫폼 **SmartHee**의 마지막 Phase다.  
Phase 4의 핵심은 세 가지다.

1. **Cost Tracker** — 에이전트 실행마다 토큰 사용량과 USD 비용을 자동 계산·기록
2. **테스트 자동화** — pytest 기반 테스트 코드
3. **React 프론트엔드** — 에이전트 생성, 실행, 결과 확인을 한 화면에서

Phase 1~3를 거치며 반복됐던 에러들이 Phase 4에서도 그대로 등장했다. 원본 코드가 최신 라이브러리 버전을 반영하지 않기 때문이다.

**환경 정보**
- OS: Windows 11
- Python: 3.13
- Node.js: 설치되어 있어야 함 (npm 사용)

---

## Phase 4에서 추가되는 것

### 백엔드

Phase 3 대비 추가 파일은 세 가지다.

```
phase4/backend/
├── services/
│   └── cost_tracker.py     ← 토큰 비용 계산 및 DB 기록
├── models/
│   └── cost.py             ← CostRecord DB 모델
├── api/routes/
│   └── costs.py            ← 비용 조회 API
└── tests/
    └── test_core.py        ← pytest 테스트 코드 (Phase 4 신규)
```

`requirements.txt`는 Phase 3 기반에 테스트 패키지 3개만 추가한다.

```txt
# Phase 3 내용 그대로 +

# Test (Phase 4 신규)
pytest
pytest-asyncio
pytest-cov
```

### 프론트엔드

Phase 4에서 처음 추가되는 구성이다. React + Vite + TypeScript 기반이며 별도 `frontend/` 폴더에 위치한다.

```
phase4/
├── backend/    ← 기존 그대로 유지
└── frontend/   ← Phase 4 신규
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── api/client.ts
        ├── components/
        │   ├── Header.tsx
        │   ├── BuilderPanel.tsx
        │   ├── RunPanel.tsx
        │   └── ResultPanel.tsx
        ├── pages/Dashboard.tsx
        ├── styles/globals.css
        ├── types/index.ts
        └── App.tsx
```

---

## Cost Tracker를 만든 이유

LLM API는 사용량 기반 과금이다. 에이전트가 실행될 때마다 비용이 발생하는데, 이를 추적하지 않으면 운영 비용을 전혀 파악할 수 없다.

Cost Tracker는 매 에이전트 실행마다 아래 정보를 `cost_records` 테이블에 기록한다.

| 항목 | 내용 |
|------|------|
| `model` | 사용한 LLM 모델명 |
| `prompt_tokens` | 입력 토큰 수 |
| `completion_tokens` | 출력 토큰 수 |
| `cost_usd` | 모델별 단가 기준 자동 계산한 USD 비용 |

모델별 토큰 단가는 `cost_tracker.py`에 하드코딩되어 있다.

```python
MODEL_PRICING = {
    "openai/gpt-4o":      {"input": 5.00,  "output": 15.00},  # USD per 1M tokens
    "openai/gpt-4o-mini": {"input": 0.15,  "output": 0.60},
    "ollama/llama3":      {"input": 0.00,  "output": 0.00},   # 로컬 무료
}
```

비용 계산 공식:

```python
cost = (prompt_tokens / 1_000_000) * pricing["input"]
     + (completion_tokens / 1_000_000) * pricing["output"]
```

`/api/v1/costs/overview`로 전체 에이전트 비용 순위를, `/api/v1/costs/agent/{id}`로 특정 에이전트의 날짜별 비용 분석을 조회할 수 있다.

### 동작 확인 (SQL)

실제로 에이전트 실행 후 `cost_records` 테이블에 비용 데이터가 정상적으로 쌓이는지 확인한 결과다.

```sql
agentforge=# SELECT model, prompt_tokens, completion_tokens, total_tokens, cost_usd, created_at
FROM cost_records
ORDER BY created_at DESC
LIMIT 5;

     model     | prompt_tokens | completion_tokens | total_tokens | cost_usd |          created_at
---------------+---------------+-------------------+--------------+----------+-------------------------------
 openai/gpt-4o |             3 |               334 |          337 | 0.005025 | 2026-03-13 06:59:24.162214+00
(1 row)
```

---

## 프론트엔드 구성

### 화면 구조

```
┌──────────────────────────────────────────────────┐
│  ⬡ AgentForge  v4.0             ● API 연결됨  ☀  │
├──────────────┬───────────────┬───────────────────┤
│ 01 ─ BUILDER │ 02 ─ EXECUTE  │ 03 ─ RESULT       │
│              │               │                   │
│ 모델 선택    │ 에이전트 배지  │ ✓ SUCCESS         │
│ 설명 입력    │ 태스크 입력   │ OUTPUT            │
│ [에이전트    │ [▶ 실행]      │ 응답 텍스트        │
│  생성]       │               │ [복사]            │
└──────────────┴───────────────┴───────────────────┘
```

세 컬럼이 `1px` 구분선으로 나뉘어 있다. 01에서 에이전트를 생성하면 02로 자동 전달되고, 실행 결과는 03에 표시된다. 우측 상단 버튼으로 다크/라이트 테마를 전환할 수 있으며 선택값은 `localStorage`에 저장된다.

아래는 실제 동작 화면이다. `ADFS에 대해 설명하는 에이전트`를 생성하고, `ADFS란 무엇인가요?`를 입력해 실행했을 때 **✓ SUCCESS** 상태와 함께 결과가 03 RESULT 패널에 출력되는 것을 확인할 수 있다.

![SmartHee Phase 4 프론트엔드 — 에이전트 생성·실행·결과 확인 정상 동작 화면](/assets/images/smarthee-phase4-frontend.png)

### 기술 선택

| 항목 | 선택 |
|------|------|
| 프레임워크 | React 18 |
| 빌드 도구 | Vite |
| 언어 | TypeScript |
| 스타일 | CSS Modules |
| 폰트 | JetBrains Mono + DM Sans |

**React 18을 선택한 이유**

AgentForge 프론트엔드는 에이전트 생성 → 실행 → 결과 표시로 이어지는 흐름에서 여러 컴포넌트가 같은 상태(생성된 에이전트, 실행 결과, 로딩 여부)를 공유해야 한다. React의 `useState`와 Props 전달 구조가 이 흐름을 명확하게 표현하기에 적합하다. Vue나 Svelte도 가능하지만, 포트폴리오 관점에서 가장 범용적으로 통용되는 React를 선택했다.

**Vite를 선택한 이유**

Create React App(CRA)은 내부적으로 Webpack을 사용하는데, 프로젝트 규모가 커질수록 개발 서버 시작과 HMR(Hot Module Replacement) 속도가 느려진다. Vite는 개발 환경에서 번들링 없이 네이티브 ES Module을 브라우저에 직접 제공하기 때문에 서버 시작이 거의 즉각적이다. 또한 `vite.config.ts`의 `proxy` 설정 한 줄로 FastAPI 백엔드로의 API 요청을 프록시할 수 있어 CORS 설정 없이 개발할 수 있다.

**TypeScript를 선택한 이유**

FastAPI는 `/api/v1/agents/run` 응답으로 `{ run_id, output, status }` 구조를 반환한다. TypeScript 없이 JavaScript로 작성하면 `result.output`이 문자열인지 dict인지 런타임에서야 알 수 있다. 실제로 Phase 4에서 `result` dict 전체가 반환되면서 프론트엔드가 빈 화면이 되는 에러가 발생했는데, TypeScript의 타입 정의가 있었다면 컴파일 시점에 바로 잡을 수 있었던 문제다. API 응답 구조를 `types/index.ts`에 명시해두면 어떤 필드가 있는지 자동완성으로 확인할 수 있어 개발 효율도 높아진다.

```typescript
// types/index.ts — API 응답 구조를 타입으로 명시
export interface RunResult {
  run_id: string
  output: string        // ← 문자열임을 명시
  status: 'success' | 'failed'
}
```

**CSS Modules를 선택한 이유**

Tailwind CSS는 유틸리티 클래스 기반으로 빠르게 스타일링할 수 있지만, 프로덕션 빌드를 위해 PostCSS와 컴파일러 설정이 별도로 필요하다. AgentForge 프론트엔드는 Vite CDN 방식이 아닌 로컬 빌드 환경이므로, 별도 설정 없이 바로 사용할 수 있는 CSS Modules를 선택했다. CSS Modules는 파일마다 클래스명이 자동으로 해시되어 컴포넌트 간 스타일 충돌이 없다. `Header.module.css`, `Panel.module.css`처럼 컴포넌트와 1:1로 관리하면 유지보수도 쉽다.

**JetBrains Mono + DM Sans를 선택한 이유**

AgentForge는 에이전트 ID, 모델명, 실행 로그 같은 기술적 데이터를 많이 표시한다. `JetBrains Mono`는 개발 도구에서 널리 쓰이는 모노스페이스 폰트로, 고정폭 특성 덕분에 UUID나 코드 같은 텍스트가 정렬되어 보인다. `DM Sans`는 가독성 높은 sans-serif 폰트로 설명 텍스트와 버튼 레이블에 사용했다. 두 폰트의 조합으로 기술적인 느낌과 읽기 편한 UI를 동시에 달성했다.

### Vite 프록시 설정

프론트(`localhost:5173`)에서 백엔드(`localhost:8000`)로 API 요청 시 CORS 문제가 발생하지 않도록 Vite 개발 서버에 프록시를 설정한다.

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
    },
  },
},
```

이렇게 하면 프론트에서 `/api/v1/...`로 요청하면 자동으로 백엔드로 전달된다.

---

## .env 및 requirements.txt 설정

Phase 3 설정을 그대로 이어받는다.

```bash
# .env 복사
copy phase3\backend\.env phase4\backend\.env

# requirements.txt 복사
copy phase3\backend\requirements.txt phase4\backend\requirements.txt
```

`requirements.txt` 맨 아래에 3줄 추가:

```txt
# Phase 3 신규
celery

# Phase 4 신규
pytest
pytest-asyncio
pytest-cov
```

---

## 에러 ① — Phase 3와 동일: `No module named 'langfuse.callback'`

### 해결

Phase 3에서 수정한 `tracing.py`를 그대로 복사한다.

```bash
copy phase3\backend\core\tracing.py phase4\backend\core\tracing.py
```

---

## 에러 ② — Phase 3와 동일: `state_modifier` 파라미터 제거

### 증상

```json
{
  "detail": "create_react_agent() got unexpected keyword arguments: {'state_modifier': '...'}"
}
```

### 해결

Phase 3에서 수정한 `graph.py`를 그대로 복사한다.

```bash
copy phase3\backend\agents\orchestrator\graph.py phase4\backend\agents\orchestrator\graph.py
```

---

## 에러 ③ — Phase 3와 동일: `output` 타입 오류 (빈 화면)

### 증상

에이전트 실행은 성공하는데 프론트엔드 03 RESULT 패널이 빈 화면으로 바뀐다. 콘솔에 별도 에러 로그는 없다.

### 원인

Phase 4 원본 `agents.py`가 `result` dict 전체를 반환하고 있었다. 프론트엔드는 `result.output` 문자열을 기대하는데 dict가 들어오면 렌더링에 실패하면서 빈 화면이 된다.

### 해결

Phase 3에서 수정한 `agents.py`를 그대로 복사한다.

```bash
copy phase3\backend\api\routes\agents.py phase4\backend\api\routes\agents.py
```

> **참고:** `--reload` 옵션으로 서버를 실행 중이라면 파일을 저장하는 즉시 서버가 자동 재시작된다. 별도 재시작 명령이 필요 없다.

---

## alembic 없이 테이블 자동 생성

Phase 4에는 `alembic.ini`가 없다. 대신 `main.py`의 `lifespan` 이벤트에서 `init_db()`를 호출하여 서버 시작 시 테이블을 자동 생성한다.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()   # ← 서버 시작 시 테이블 자동 생성
    yield
```

Phase 4에서 새로 추가되는 `cost_records` 테이블도 서버 첫 시작 시 자동으로 만들어진다.

```
INFO: CREATE TABLE cost_records (
    id UUID NOT NULL,
    run_id UUID NOT NULL,
    agent_config_id UUID NOT NULL,
    model VARCHAR(100) NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd FLOAT,
    created_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id)
)
INFO: Application startup complete.
```

`alembic upgrade head`를 실행할 필요 없다.

### Docker에서 테이블 생성 확인

서버 시작 후 실제로 테이블이 만들어졌는지 Docker PostgreSQL에 직접 접속해서 확인할 수 있다.

**1단계 — PostgreSQL 컨테이너 접속:**

```bash
docker exec -it agentforge-postgres psql -U agentforge -d agentforge
```

> `agentforge-postgres`는 `docker-compose.yml`의 컨테이너명이다. 다를 경우 `docker ps`로 실제 컨테이너명 확인 후 교체한다.

**2단계 — 테이블 목록 확인:**

```sql
\dt
```

아래처럼 `cost_records`를 포함한 전체 테이블 목록이 출력되면 정상이다.

```
              List of relations
 Schema |         Name          | Type  |  Owner
--------+-----------------------+-------+------------
 public | ab_test_results       | table | agentforge
 public | agent_configs         | table | agentforge
 public | agent_runs            | table | agentforge
 public | agent_schedules       | table | agentforge
 public | cost_records          | table | agentforge  ← Phase 4 신규
 public | evaluation_results    | table | agentforge
 public | marketplace_templates | table | agentforge
 public | skills                | table | agentforge
```

**3단계 — 컬럼 구조 확인:**

```sql
\d cost_records
```

```
                        Table "public.cost_records"
       Column        |            Type             | Nullable
---------------------+-----------------------------+----------
 id                  | uuid                        | not null
 run_id              | uuid                        | not null
 agent_config_id     | uuid                        | not null
 model               | character varying(100)      | not null
 prompt_tokens       | integer                     |
 completion_tokens   | integer                     |
 total_tokens        | integer                     |
 cost_usd            | double precision            |
 created_at          | timestamp with time zone    |
```

**4단계 — psql 종료:**

```sql
\q
```

---

## 최종 실행 순서 (Phase 4)

```bash
# 1. Docker 컨테이너 확인
docker ps
# postgres, redis 가 Up 상태가 아니면:
docker-compose up -d postgres redis

# 2. 터미널 1 — FastAPI 서버 (backend\ 에서)
cd phase4\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 3. 터미널 2 — Celery Worker (backend\ 에서)
venv\Scripts\activate
celery -A services.tasks worker --loglevel=info --pool=solo

# 4. 터미널 3 — 프론트엔드 (frontend\ 에서, venv 불필요)
cd phase4\frontend
npm install
npm run dev
```

**접속:**
- API 문서: `http://127.0.0.1:8000/docs`
- 프론트엔드: `http://localhost:5173`

> **주의:** 프론트엔드는 Python venv와 무관하다. `npm run dev`는 별도 터미널에서 venv 활성화 없이 실행한다.

---

## 수정 파일 요약

| 파일 | 수정 내용 | 방법 |
|------|----------|------|
| `requirements.txt` | pytest 3종 추가 | Phase 3 복사 후 추가 |
| `core/tracing.py` | langfuse 3.x 호환 | Phase 3 복사 |
| `agents/orchestrator/graph.py` | `state_modifier` → `prompt` | Phase 3 복사 |
| `api/routes/agents.py` | `result["output"]` 문자열만 반환 | Phase 3 복사 |

---

## 트러블 슈팅 및 교훈

| 에러 | 원인 | 해결 |
|------|------|------|
| `No module named 'langfuse.callback'` | langfuse 3.x 모듈 경로 변경 | `langfuse.langchain`으로 변경 (Phase 3 복사) |
| `unexpected keyword argument 'state_modifier'` | LangGraph 1.x 파라미터명 변경 | `prompt=`으로 변경 (Phase 3 복사) |
| 프론트엔드 빈 화면 | `result` dict 전체 반환 → 렌더링 실패 | `result["output"]` 문자열만 반환 (Phase 3 복사) |
| `alembic upgrade head` 실패 | `alembic.ini` 없음 | `init_db()`가 자동 처리, 불필요 |

> **핵심 교훈:** Phase를 올릴 때마다 `tracing.py`, `graph.py`, `agents.py`는 이전 Phase에서 수정한 버전을 그대로 복사해서 시작하는 것이 맞다. 원본 코드는 langfuse 2.x, LangGraph 0.x 기준으로 작성되어 있어 최신 버전과 맞지 않는다.

---

## SmartHee 전체 여정 마무리

| Phase | 핵심 기능 | 주요 에러 |
|-------|----------|----------|
| Phase 1 | FastAPI + PostgreSQL + Redis 기반 구축 | numpy 호환, requirements 버전 충돌 |
| Phase 2 | LangGraph + Langfuse 트레이싱 | langfuse 3.x API 변경, LangGraph 1.x 파라미터 변경 |
| Phase 3 | Celery 비동기 + 웹훅 + 마켓플레이스 | Windows PermissionError, 모듈 경로 문제 |
| Phase 4 | Cost Tracker + 테스트 + React 프론트엔드 | Phase 2~3 에러 반복, 빈 화면 렌더링 실패 |

Phase 1부터 Phase 4까지 총 4개 Phase에 걸쳐 에이전트 생성 → 실행 → 트레이싱 → 비동기 처리 → 비용 추적 → 프론트엔드 시각화까지 구현했다. 매 Phase에서 라이브러리 버전 불일치로 인한 에러가 반복됐고, 이를 해결하는 과정이 오히려 각 라이브러리의 변경 이력을 이해하는 좋은 계기가 됐다.