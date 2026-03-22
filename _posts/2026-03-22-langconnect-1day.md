---
layout: single
title: "[구현기] LangConnect 수동 구현 (Windows + WSL2) — pgvector RAG + Claude Desktop MCP"
excerpt: "FastAPI + PostgreSQL(pgvector) + Next.js + FastMCP 스택을 처음부터 직접 구현한 과정 정리. 벡터 DB GUI 관리 및 Claude Desktop MCP RAG 연동까지."
categories:
  - AI
tags:
  - LangConnect
  - RAG
  - FastAPI
  - pgvector
  - MCP
  - Claude
  - Docker
  - WSL2
---


# LangConnect 프로젝트 수동으로 직접 구현해봄 (Windows + WSL2)

> 벡터 DB 관리 GUI + Claude Desktop MCP RAG 연동  
> FastAPI + PostgreSQL(pgvector) + Next.js + FastMCP 스택을 처음부터 직접 구현한 과정 정리

---

## 프로젝트 개요

[LangConnect](https://github.com/teddynote-lab/langconnect-client)는 pgvector 기반 벡터 DB를 GUI로 관리하고, MCP(Model Context Protocol)를 통해 Claude Desktop에서 RAG를 바로 사용할 수 있게 해주는 오픈소스 프로젝트다.

그냥 clone해서 쓰면 되는 프로젝트지만, 내부 동작을 제대로 이해하고 싶어서 파일 하나하나 직접 구현해봤다. 이 글은 그 과정을 처음부터 끝까지 기록한 구현기다.

### 기술 스택

| 구분 | 기술 |
|------|------|
| 백엔드 | Python 3.11, FastAPI, LangChain |
| 데이터베이스 | PostgreSQL 16 + pgvector |
| 인증 | Supabase JWT |
| 프론트엔드 | Next.js 15, TypeScript |
| MCP 서버 | FastMCP (stdio / SSE) |
| 컨테이너 | Docker Compose |

### 사전 준비

- Windows + WSL2 환경
- Docker Desktop 설치 (WSL2 Integration 활성화)
- Python 3.11+, UV 패키지 매니저
- OpenAI API Key
- Anthropic API Key
- Supabase 계정 (무료로 사용 가능)

---

## Step 1 — 프로젝트 폴더 구조 생성

PowerShell에서 프로젝트 루트 폴더 만들고 Git 초기화함.

```powershell
cd D:\Project
mkdir langconnect-client
cd langconnect-client

# Git 초기화
git init

# 전체 폴더 구조 한번에 생성
mkdir next-connect-ui
mkdir init-scripts
mkdir langconnect
mkdir langconnect\api
mkdir langconnect\database
mkdir langconnect\models
mkdir langconnect\services
mkdir mcpserver
```

`.gitignore`도 같이 만들어줌:

```
__pycache__/
*.pyc
.env
.next/
node_modules/
uv.lock
```

완성된 구조:

```
langconnect-client/
  ├── langconnect/
  │   ├── api/
  │   ├── database/
  │   ├── models/
  │   └── services/
  ├── mcpserver/
  ├── init-scripts/
  └── next-connect-ui/
```

---

## Step 2 — 환경변수 (.env) 설정

루트에 `.env` 파일 생성함.

```env
# OpenAI (임베딩 + multi_query LLM)
OPENAI_API_KEY=sk-proj-여기에입력

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-여기에입력

# Supabase (JWT 인증)
SUPABASE_URL=https://xxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...  # anon public key

# PostgreSQL
POSTGRES_HOST=teddynote
POSTGRES_PORT=5432
POSTGRES_USER=teddynote
POSTGRES_PASSWORD=teddynote
POSTGRES_DB=teddynote_db

# CORS
ALLOW_ORIGINS=["*"]

# Testing mode
IS_TESTING=false

# API URL
API_BASE_URL=http://localhost:8080
NEXT_PUBLIC_API_URL=http://localhost:8080

# NextAuth
NEXTAUTH_SECRET=여기에입력
NEXTAUTH_URL=http://localhost:3000

# MCP
SSE_PORT=8765
SUPABASE_JWT_SECRET=
```

> **Supabase 설정 방법**  
> 1. [supabase.com](https://supabase.com) 접속 → 무료 가입  
> 2. New Project 생성 → 리전: Northeast Asia (Seoul) 선택  
> 3. Project Settings → API 탭에서 **Project URL** 과 **anon public key** 복사하면 됨

`SUPABASE_JWT_SECRET`은 나중에 `make mcp` 실행하면 자동으로 채워짐.

---

## Step 3 — docker-compose.yml

루트에 `docker-compose.yml` 생성함. postgres, api, nextjs 3개 서비스가 하나의 네트워크로 묶이는 구조임.

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: langconnect-postgres
    restart: always
    ports:
      - "5432:5432"
    env_file:
      - .env
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - langconnect-network

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: langconnect-api
    restart: always
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8080:8080"
    env_file:
      - .env
    environment:
      POSTGRES_HOST: postgres   # 컨테이너 내부에선 서비스명으로 접근
      POSTGRES_PORT: ${POSTGRES_PORT}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_SSLMODE: disable
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:${POSTGRES_PORT}/${POSTGRES_DB}
      ALLOW_ORIGINS: '["http://localhost:3000","http://localhost:8080","http://localhost","http://127.0.0.1:3000","http://127.0.0.1:8080"]'
    volumes:
      - ./langconnect:/app/langconnect
    networks:
      - langconnect-network

  nextjs:
    build:
      context: ./next-connect-ui
      dockerfile: Dockerfile
      args:
        NEXT_PUBLIC_API_URL: http://localhost:8080
        NEXTAUTH_URL: http://localhost:3000
        NEXTAUTH_SECRET: ${NEXTAUTH_SECRET}
    container_name: next-connect-ui
    restart: always
    depends_on:
      - api
    ports:
      - "3000:3000"
    env_file:
      - .env
    environment:
      API_URL: http://api:8080   # 내부 통신은 서비스명 사용
      NEXTAUTH_URL: http://localhost:3000
      NEXTAUTH_SECRET: ${NEXTAUTH_SECRET}
      NEXT_PUBLIC_API_URL: http://localhost:8080
      SUPABASE_URL: ${SUPABASE_URL}
      SUPABASE_KEY: ${SUPABASE_KEY}
      SUPABASE_JWT_SECRET: ${SUPABASE_JWT_SECRET}
    networks:
      - langconnect-network

volumes:
  postgres_data:
    driver: local

networks:
  langconnect-network:
    driver: bridge
```

---

## Step 4 — pyproject.toml + requirements.txt + Dockerfile

### pyproject.toml vs requirements.txt 차이

처음엔 왜 두 개가 필요한지 몰랐는데 역할이 다름.

- `pyproject.toml` → `uv pip install -e .` 로컬 개발할 때 사용
- `requirements.txt` → Docker 이미지 빌드할 때 사용

### pyproject.toml

```toml
[project]
name = "langconnect"
version = "0.1.0"
description = "LangConnect - Vector DB RAG API"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.115.6",
    "uvicorn>=0.34.0",
    "langchain>=0.3.20",
    "langchain-openai>=0.3.7",
    "langchain-community>=0.0.20",
    "langchain-core>=0.2.37",
    "langchain-text-splitters>=0.0.1",
    "langchain-postgres>=0.0.2",
    "python-dotenv>=1.0.1",
    "aiohttp>=3.11.13",
    "python-multipart>=0.0.20",
    "httpx>=0.28.1",
    "beautifulsoup4>=4.12.3",
    "pdfminer.six>=20231228",
    "pdfplumber>=0.11.0",
    "asyncpg>=0.30.0",
    "psycopg[binary]>=3.2.6",
    "pillow>=11.2.1",
    "lxml>=5.4.0",
    "unstructured[docx]>=0.17.2",
    "python-docx>=1.1.0",
    "supabase>=2.15.1",
    "requests>=2.31.0",
    "fastmcp>=0.1.0",
    "anthropic>=0.40.0",
    "email-validator>=2.1.0",
]

[project.scripts]
langconnect-server = "langconnect.server:main"
mcp-langconnect = "mcpserver.mcp_server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["langconnect"]
```

### requirements.txt

```txt
fastapi>=0.115.6
uvicorn>=0.34.0
langchain>=0.3.20
langchain-openai>=0.3.7
langchain-community>=0.0.20
langchain-core>=0.2.37
langchain-text-splitters>=0.0.1
langchain-postgres>=0.0.2
python-dotenv>=1.0.1
aiohttp>=3.11.13
python-multipart>=0.0.20
httpx>=0.28.1
beautifulsoup4>=4.12.3
pdfminer.six>=20231228
pdfplumber>=0.11.0
asyncpg>=0.30.0
psycopg[binary]>=3.2.6
pillow>=11.2.1
lxml>=5.4.0
python-docx>=1.1.0
supabase>=2.15.1
requests>=2.31.0
fastmcp>=0.1.0
anthropic>=0.40.0
email-validator>=2.1.0
```

### Dockerfile

Multi-stage build로 구성함. builder 단계에서 의존성 설치하고 최종 이미지에는 런타임만 남기는 방식임.

```dockerfile
FROM python:3.11-slim as builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc python3-dev libpq-dev curl libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY requirements.txt ./
RUN uv venv && \
    uv pip install -r requirements.txt && \
    uv pip install "unstructured[docx]"

# ── 최종 이미지 ──────────────────────────────
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq-dev libxml2 libxslt1.1 libmagic1 \
    poppler-utils tesseract-ocr pandoc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv
RUN groupadd -r langconnect && useradd -r -g langconnect langconnect

WORKDIR /app

RUN mkdir -p /home/langconnect/.cache && \
    chown -R langconnect:langconnect /home/langconnect/.cache

# builder에서 가상환경만 복사
COPY --from=builder --chown=langconnect:langconnect /app/.venv /app/.venv
COPY --chown=langconnect:langconnect . .

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER langconnect

EXPOSE 8080 8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()" || exit 1

CMD ["uvicorn", "langconnect.server:APP", "--host", "0.0.0.0", "--port", "8080"]
```

---

## Step 5 — FastAPI 백엔드 코드

### 전체 파일 목록

```
langconnect/
  ├── __init__.py
  ├── __main__.py
  ├── auth.py
  ├── config.py
  ├── server.py
  ├── api/
  │   ├── __init__.py
  │   ├── auth.py
  │   ├── collections.py
  │   └── documents.py
  ├── database/
  │   ├── __init__.py
  │   ├── collections.py
  │   └── connection.py
  ├── models/
  │   ├── __init__.py
  │   ├── collection.py
  │   └── document.py
  └── services/
      ├── __init__.py
      └── document_processor.py
```

### config.py — 환경변수 로드 및 임베딩 초기화

```python
import json
from langchain_core.embeddings import Embeddings
from starlette.config import Config, undefined

env = Config()

IS_TESTING = env("IS_TESTING", cast=str, default="").lower() == "true"

if IS_TESTING:
    SUPABASE_URL = ""
    SUPABASE_KEY = ""
else:
    SUPABASE_URL = env("SUPABASE_URL", cast=str, default=undefined)
    SUPABASE_KEY = env("SUPABASE_KEY", cast=str, default=undefined)

def get_embeddings() -> Embeddings:
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model="text-embedding-3-small")

DEFAULT_EMBEDDINGS = get_embeddings()
DEFAULT_COLLECTION_NAME = "default_collection"

POSTGRES_HOST = env("POSTGRES_HOST", cast=str, default="localhost")
POSTGRES_PORT = env("POSTGRES_PORT", cast=int, default="5432")
POSTGRES_USER = env("POSTGRES_USER", cast=str, default="langchain")
POSTGRES_PASSWORD = env("POSTGRES_PASSWORD", cast=str, default="langchain")
POSTGRES_DB = env("POSTGRES_DB", cast=str, default="langchain_test")

ALLOW_ORIGINS_JSON = env("ALLOW_ORIGINS", cast=str, default="")
ALLOWED_ORIGINS = json.loads(ALLOW_ORIGINS_JSON.strip()) if ALLOW_ORIGINS_JSON else ["http://localhost:3000"]
```

### auth.py — Supabase JWT 검증

모든 API 엔드포인트에 `Depends(resolve_user)`로 주입해서 인증 처리함.

```python
from typing import Annotated
from fastapi import Depends
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.authentication import BaseUser
from supabase import create_client
from langconnect import config

security = HTTPBearer()

class AuthenticatedUser(BaseUser):
    def __init__(self, user_id: str, display_name: str):
        self.user_id = user_id
        self._display_name = display_name

    @property
    def is_authenticated(self): return True

    @property
    def display_name(self): return self._display_name

    @property
    def identity(self): return self.user_id  # DB 쿼리에서 owner_id로 사용

def resolve_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
):
    if config.IS_TESTING:
        if credentials.credentials in {"user1", "user2"}:
            return AuthenticatedUser(credentials.credentials, credentials.credentials)
        raise HTTPException(status_code=401)

    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    response = supabase.auth.get_user(credentials.credentials)
    user = response.user
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return AuthenticatedUser(user.id, user.user_metadata.get("name", "User"))
```

### database/connection.py — asyncpg 풀 + PGVector

```python
import asyncpg
from langchain_postgres.vectorstores import PGVector
from sqlalchemy import create_engine
from langconnect import config

_pool = None

async def get_db_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            user=config.POSTGRES_USER, password=config.POSTGRES_PASSWORD,
            host=config.POSTGRES_HOST, port=config.POSTGRES_PORT,
            database=config.POSTGRES_DB,
        )
    return _pool

@asynccontextmanager
async def get_db_connection():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        yield conn

def get_vectorstore(collection_name=config.DEFAULT_COLLECTION_NAME,
                    embeddings=config.DEFAULT_EMBEDDINGS,
                    collection_metadata=None):
    engine = create_engine(
        f"postgresql+psycopg://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}"
        f"@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"
    )
    return PGVector(embeddings=embeddings, collection_name=collection_name,
                    connection=engine, use_jsonb=True,
                    collection_metadata=collection_metadata)
```

### 하이브리드 검색 핵심 로직

Semantic 70% + Keyword 30% 가중치로 결합하는 부분이 핵심임.

```python
# Semantic 결과 정규화 후 70% 가중치 적용
max_s = max((s for _, s in semantic_results), default=1.0)
for doc, score in semantic_results:
    norm = score / max_s if max_s > 0 else 0
    combined[doc.id] = {"score": norm * 0.7, ...}

# Keyword 결과 정규화 후 30% 추가
max_k = max((float(r["score"]) for r in keyword_rows), default=1.0)
for r in keyword_rows:
    norm = float(r["score"]) / max_k
    if doc_id in combined:
        combined[doc_id]["score"] += norm * 0.3   # 두 검색 모두에 있으면 합산
    else:
        combined[doc_id] = {"score": norm * 0.3}  # keyword에만 있으면 30%만

# combined_score 내림차순 정렬 후 반환
return sorted(combined.values(), key=lambda x: x["score"], reverse=True)[:limit]
```

### server.py — FastAPI 앱 진입점

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langconnect.api import auth_router, collections_router, documents_router
from langconnect.config import ALLOWED_ORIGINS
from langconnect.database.collections import CollectionsManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await CollectionsManager.setup()  # 앱 시작 시 PGVector 테이블 초기화
    yield

APP = FastAPI(title="LangConnect API", version="0.1.0", lifespan=lifespan)

APP.add_middleware(CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])

APP.include_router(auth_router)        # /auth
APP.include_router(collections_router) # /collections
APP.include_router(documents_router)   # /collections/{id}/documents

@APP.get("/health")
async def health_check():
    return {"status": "ok"}
```

---

## Step 6 — init-scripts/01-init-extensions.sql

Docker 컨테이너 최초 실행 시 자동으로 실행되는 SQL임. pgvector 확장 활성화만 해주면 됨.

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Step 7 — MCP 서버 구성

### 파일 목록

```
mcpserver/
  ├── __init__.py
  ├── mcp_server.py        # stdio 모드 → Claude Desktop 연동용
  ├── mcp_sse_server.py    # SSE 모드
  ├── create_mcp_json.py   # 로그인 → 토큰 발급 → mcp_config.json 자동 생성
  └── get_access_token.py  # JWT 토큰 발급 헬퍼
```

### mcp_server.py 핵심 부분

FastMCP 라이브러리로 `@mcp.tool` 데코레이터만 붙이면 도구로 등록됨. LangConnect API를 httpx로 호출하는 구조임.

```python
from fastmcp import FastMCP
import httpx

mcp = FastMCP(name="langconnect-rag-mcp")

@mcp.tool
async def search_documents(collection_id: str, query: str,
                           limit: int = 5, search_type: str = "semantic") -> str:
    """시맨틱 / 키워드 / 하이브리드 검색"""
    results = await client.request("POST",
        f"/collections/{collection_id}/documents/search",
        json={"query": query, "limit": limit, "search_type": search_type})

    output = f'<search_results type="{search_type}">\n'
    for r in results:
        output += f"  <document>\n    <content>{r['page_content']}</content>\n"
        output += f"    <score>{r['score']:.4f}</score>\n  </document>\n"
    return output + "</search_results>"

@mcp.tool
async def multi_query(question: str) -> str:
    """OpenAI LLM으로 질문 변형 3~5개 생성해서 검색 품질 향상"""
    llm = ChatOpenAI(temperature=0, api_key=OPENAI_API_KEY)
    chain = prompt | llm | LineListOutputParser()
    queries = await chain.ainvoke({"question": question})
    return json.dumps(queries, ensure_ascii=False)

def main():
    mcp.run()  # stdin/stdout JSON-RPC로 Claude Desktop과 통신

if __name__ == "__main__":
    main()
```

### 사용 가능한 MCP 도구 (10개)

| 도구 | 설명 |
|------|------|
| `search_documents` | 시맨틱 / 키워드 / 하이브리드 검색 |
| `list_collections` | 전체 컬렉션 목록 조회 |
| `get_collection` | 특정 컬렉션 상세 정보 |
| `create_collection` | 새 컬렉션 생성 |
| `delete_collection` | 컬렉션 삭제 |
| `list_documents` | 문서 목록 조회 |
| `add_documents` | 텍스트 문서 추가 |
| `delete_document` | 문서 삭제 |
| `get_health_status` | API 헬스체크 |
| `multi_query` | 다중 서브쿼리 생성 |

---

## Step 8 — Makefile

> ⚠️ 명령어 앞 들여쓰기는 반드시 **TAB**이어야 함. 스페이스로 하면 오류남.

```makefile
.PHONY: build up down restart logs logs-api logs-db ps mcp

build:
	@echo "🔨 Building Docker images..."
	@docker compose build
	@echo "✅ Docker build completed!"
	@echo "📌 Run 'make up' to start the server"

up:
	@echo "🚀 Starting LangConnect server..."
	@docker compose up -d
	@echo "✅ Server started!"
	@echo "📌 Access points:"
	@echo "   - API Server : http://localhost:8080"
	@echo "   - API Docs   : http://localhost:8080/docs"
	@echo "   - Next.js UI : http://localhost:3000"
	@echo "   - PostgreSQL : localhost:5432"

down:
	@echo "🛑 Stopping LangConnect server..."
	@docker compose down
	@echo "✅ Server stopped!"

restart:
	@echo "🔄 Restarting LangConnect server..."
	@docker compose down
	@docker compose up -d
	@echo "✅ Server restarted!"

logs:
	@docker compose logs -f

logs-api:
	@docker compose logs -f api

logs-db:
	@docker compose logs -f postgres

ps:
	@docker compose ps

mcp:
	@echo "🔧 Creating MCP configuration..."
	@uv run python mcpserver/create_mcp_json.py
	@echo "✅ MCP configuration created!"
```

---

## 최종 파일 구조

```
langconnect-client/
  ├── .dockerignore
  ├── .env
  ├── .gitignore
  ├── Dockerfile
  ├── docker-compose.yml
  ├── Makefile
  ├── pyproject.toml
  ├── requirements.txt
  ├── init-scripts/
  │   └── 01-init-extensions.sql
  ├── langconnect/
  │   ├── __init__.py
  │   ├── __main__.py
  │   ├── auth.py
  │   ├── config.py
  │   ├── server.py
  │   ├── api/
  │   │   ├── __init__.py
  │   │   ├── auth.py
  │   │   ├── collections.py
  │   │   └── documents.py
  │   ├── database/
  │   │   ├── __init__.py
  │   │   ├── collections.py
  │   │   └── connection.py
  │   ├── models/
  │   │   ├── __init__.py
  │   │   ├── collection.py
  │   │   └── document.py
  │   └── services/
  │       ├── __init__.py
  │       └── document_processor.py
  ├── mcpserver/
  │   ├── __init__.py
  │   ├── create_mcp_json.py
  │   ├── get_access_token.py
  │   ├── mcp_server.py
  │   └── mcp_sse_server.py
  └── next-connect-ui/
```

---

## 다음

파일 구성 완료. 이제 WSL2 터미널에서 빌드 시작함.

```bash
cd /mnt/d/Project/langconnect-client
make build
```

빌드 완료 후 순서:

```bash
make up      # 서비스 시작
make ps      # 컨테이너 상태 확인
make mcp     # Claude Desktop MCP 설정 생성
```

---

*참고: [teddynote-lab/langconnect-client](https://github.com/teddynote-lab/langconnect-client)*