---
title: "aibrief — 매일 한국어 AI 브리핑 MCP 서버"
excerpt: "매일 큐레이션된 한국어 AI 브리핑을 읽기 전용 MCP 툴로 제공하는 원격 서버. 요청당 LLM 호출·과금 0."
permalink: /aibrief/
layout: single
toc: true
toc_label: "목차"
toc_sticky: true
author_profile: true
---

**aibrief**는 매일 큐레이션된 **한국어 AI 브리핑**을 읽기 전용 [MCP](https://modelcontextprotocol.io)(Model
Context Protocol) 툴로 노출하는 **원격 서버**입니다. AI 에이전트나 Claude 같은 MCP 클라이언트가
그날의 AI 소식을 한국어 요약·태그·출처와 함께 바로 조회할 수 있습니다.

- 🔗 **Smithery**: [smithery.ai/server/pjm754/aibrief](https://smithery.ai/server/pjm754/aibrief)
- 🛰️ **MCP 엔드포인트**: `https://aibrief-mcp.jongminoov.workers.dev/mcp`
- 💻 **소스**: [github.com/parkjongmin-ddam/aibrief-mcp](https://github.com/parkjongmin-ddam/aibrief-mcp)

## 무엇을 하나

매일 상위 파이프라인이 논문·릴리스·커뮤니티·영상 등에서 AI 소식을 **수집 → 랭킹 → 한국어 요약**한
정본 JSON을 만들고, 이 서버가 그것을 런타임에 읽어 MCP 툴로 제공합니다. 요약이 **미리 계산돼**
있어 요청할 때마다 LLM을 호출하지 않습니다 — 즉 **요청당 LLM 과금 0**, 완전 **stateless · read-only**.

각 항목은 다음 정보를 담습니다:

| 필드 | 설명 |
|------|------|
| `title_ko` | 한국어 제목 |
| `summary_ko` | 한국어 요약 |
| `why_it_matters` | 왜 중요한지 |
| `tags` | 주제 태그 |
| `url` | 원문 링크 |
| `score` | 큐레이션 점수 |

## 제공 툴 (7개, 전부 읽기 전용)

**조회**

- `list_briefs` — 발행된 일자 목록(최신순)과 각 일자 섹션별 건수
- `get_brief(date="latest")` — 특정 일자의 브리핑 전체 (`"latest"`/`"today"` 지원)
- `get_section(date, section)` — 특정 일자의 특정 섹션(papers·releases·community·video·deepdive)
- `search_briefs(query, section?, tag?)` — 아카이브 전체 키워드 검색

**발견**

- `top_items(days=7, section?)` — 최근 N일 상위 항목
- `list_tags()` — 태그 목록
- `get_stats()` — 통계

## 어떻게 쓰나

MCP 클라이언트(Claude Desktop, Smithery Toolbox, 또는 직접 연결)에서 아래 원격 URL을 등록하면
됩니다. 인증·설정이 필요 없습니다.

```
https://aibrief-mcp.jongminoov.workers.dev/mcp
```

Smithery를 통해 쓰면 Telegram·Slack 설치나 Toolbox 추가도 한 번에 가능합니다 →
[Smithery 서버 페이지](https://smithery.ai/server/pjm754/aibrief).

### 예시 호출

```jsonc
// 오늘자 브리핑 전체
{ "tool": "get_brief", "arguments": { "date": "latest" } }

// "에이전트" 키워드로 아카이브 검색
{ "tool": "search_briefs", "arguments": { "query": "에이전트" } }

// 최근 7일 상위 항목
{ "tool": "top_items", "arguments": { "days": 7 } }
```

## 구조

```
Cloudflare Worker (stateless createMcpHandler, POST /mcp)
        │  런타임에 raw JSON fetch (60초 캐시)
        ▼
data/daily/*.json  ← 상위 aibrief 파이프라인이 매일 push (공개 아카이브)
```

- 데이터는 번들이 아니라 **런타임에 원격 raw에서 fetch** → cron이 새 일자를 push하면 **재배포 없이 반영**
- 배포: [Cloudflare Workers](https://workers.cloudflare.com) → 엔드포인트를 [Smithery](https://smithery.ai)에 등록

공개되는 것은 **① 서빙 코드**와 **② 브리핑 콘텐츠(JSON)** 뿐입니다. 수집 로직·랭킹·프롬프트는
비공개 상위 파이프라인에 남습니다.

## 라이선스

서버 코드는 MIT. 브리핑 콘텐츠는 3rd-party 소스의 요약을 포함합니다.
