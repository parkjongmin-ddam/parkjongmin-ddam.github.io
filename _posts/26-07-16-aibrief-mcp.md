---
layout: single
title: "AI 브리핑을 MCP 서버로 열었다 — aibrief-mcp"
excerpt: "매일 만들던 한국어 AI 브리핑을 에이전트가 직접 읽게 하고 싶어서 읽기 전용 MCP 서버로 열었다. Cloudflare Workers 위에서 도는 7개 툴, 요청당 LLM 비용 0, Smithery로 원클릭 연결. 어떻게 만들었고 어떻게 붙이는지 정리한다."
date: 2026-07-16
categories: [AI, MCP]
tags: [mcp, cloudflare-workers, smithery, ai-news, 오픈소스, 에이전트]
---

<img src="/assets/images/26-07-16-aibrief-mcp/icon.png" alt="aibrief-mcp" width="96" align="right" />

## 배경

AI 소식은 소스가 너무 흩어져 있다. arXiv와 Hugging Face에 논문이 올라오고, OpenAI·Google·Anthropic·Meta가 각자 릴리스를 내고, Hacker News와 커뮤니티에서 토론이 붙고, 유튜브와 블로그에도 볼 게 쌓인다. 매일 이걸 다 따라가려니 감당이 안 돼서, 결국 파이프라인을 하나 만들어 돌리고 있다. `aibrief`다. 소스를 긁어와 점수를 매기고 한국어로 요약해서 매일 브리핑 하나를 뽑아낸다.

그런데 정작 이 브리핑을 **어디서 보느냐**가 계속 애매했다. 웹으로 띄워도 되지만, 요즘 내 작업은 대부분 에이전트(Claude, Cursor 같은) 안에서 이뤄진다. 거기서 바로 "오늘 뭐 나왔어?"라고 물으면 에이전트가 알아서 브리핑을 읽어오는 게 제일 편하겠다 싶었다. 그래서 브리핑을 [MCP](https://modelcontextprotocol.io) 툴로 꺼내주는 서버를 붙였다. 이 글에서 소개하는 [`aibrief-mcp`](https://github.com/parkjongmin-ddam/aibrief-mcp)다.

---

## 툴 7개 (전부 읽기 전용)

MCP는 에이전트가 외부 도구·데이터에 붙는 표준이다. `aibrief-mcp`는 브리핑 아카이브를 읽기 전용 툴 7개로 노출한다. 쓰기는 없다. 아카이브를 조회하고 검색하는 게 전부다.

조회 쪽은 이렇다.

- `list_briefs` — 발행된 날짜 목록
- `get_brief(date="latest")` — 특정일(또는 `latest`) 브리핑 전체
- `get_section(date, section)` — 특정일에서 한 섹션만 (`papers`·`releases`·`community`·`video`·`deepdive`)
- `search_briefs(query, section?, tag?)` — 키워드·섹션·태그로 검색

훑어보기 좋은 툴도 세 개 뒀다.

- `top_items(days=7, section?)` — 최근 며칠간 상위 항목
- `list_tags()` — 태그 목록과 건수
- `get_stats()` — 아카이브 전반 요약(태그·섹션·기간)

응답으로 넘어오는 항목 하나는 이렇게 생겼다.

| 필드 | 뜻 |
|------|----|
| `title_ko` / `title_en` | 한국어 / 원문 제목 |
| `summary_ko` | 2~4문장 한국어 요약 |
| `why_it_matters` | 왜 중요한지 한 줄 |
| `tags` | `LLM`·`RAG`·`에이전트`·`인프라`·`오픈소스` |
| `url` | 원문 링크 |
| `score` | 큐레이션 점수 |

여기서 요약과 "왜 중요한가"가 **이미 다 계산돼 있다**는 게 포인트다. 에이전트는 원문을 다시 읽거나 요약을 새로 만들 필요 없이, 완성된 브리핑을 그대로 가져다 쓴다.

---

## 어떻게 굴러가나

만들 때 신경 쓴 건 하나였다. 수집·랭킹·프롬프트 같은 알맹이는 안 열고, 결과물만 깔끔하게 서빙하는 것. 그래서 층을 이렇게 갈랐다.

```
aibrief (비공개)          →   aibrief-mcp (공개)          →   에이전트
수집·랭킹·요약·프롬프트          정본 JSON 미러 + MCP 서버         MCP 클라이언트
                              (Cloudflare Worker)              (Claude/Cursor/…)
```

`aibrief`가 매일 소스를 긁어 요약까지 끝낸 **정본 JSON**을 만들면, 발행 직후 cron이 그날치를 `aibrief-mcp`의 공개 `data/`로 밀어 넣는다(검색 인덱스도 이때 다시 만든다). 그러면 Cloudflare Worker가 `POST /mcp`로 그 데이터를 읽어 7개 툴로 답한다. 수집 로직이나 랭킹, 프롬프트는 `aibrief`에 그대로 남는다. 밖으로 나가는 건 서빙 코드와 브리핑 콘텐츠(JSON)뿐이다.

이 구조에서 마음에 든 건 세 가지다.

**돈이 안 든다.** 요약이 미리 계산돼 있으니 서버는 JSON을 읽어 돌려주기만 한다. 요청마다 LLM을 부르지 않으니 호출 비용이 0이고, 상태를 들고 있지도 않아서 붙는 사람 쪽 토큰도 안 나간다.

**데이터를 갱신해도 재배포가 필요 없다.** 데이터를 코드에 번들하지 않고 런타임에 raw에서 가져온다(같은 URL은 60초 캐시). cron이 새 날짜를 push하면 Worker를 다시 배포하지 않아도 바로 반영된다. 데이터 커밋에는 `[skip ci]`를 달아 두어서 그 push로 배포가 도는 일도 없다.

**공개 범위가 명확하다.** 이 원칙은 `aibrief`의 ADR-008로 못 박아 뒀다. 서빙 코드와 콘텐츠는 열고, 나머지는 닫는다.

---

## 붙이기

제일 쉬운 길은 [Smithery](https://smithery.ai)다. 서버를 스캔해서 툴 목록이랑 Playground, 클라이언트별 설정까지 만들어 준다.

👉 **[smithery.ai/servers/pjm754/aibrief](https://smithery.ai/servers/pjm754/aibrief)**

페이지에서 **Connect**를 누르면 Claude Desktop이든 Cursor든 VS Code든 쓰는 클라이언트에 맞는 설정을 그대로 복사해 붙이면 된다. 연결하고 나선 이렇게 물어보면 된다.

- "오늘 AI 브리핑 보여줘"
- "이번 주 뜬 논문 top 5"
- "MCP 태그 달린 것만 찾아줘"

직접 굴리고 싶으면 레포를 포크해서 Cloudflare Workers에 올리고(`wrangler deploy`), `DATA_BASE_URL`만 본인 아카이브로 바꾸면 된다. 서버 코드는 MIT다.

---

## 마무리

거창한 백엔드 없이도 됐다. 미리 계산해 둔 정본 JSON에, 상태 없는 Worker 하나, 그리고 표준 MCP. 그게 전부다. 매일 만들던 브리핑을 이제 에이전트가 알아서 읽어 간다.

- 서버 코드: [github.com/parkjongmin-ddam/aibrief-mcp](https://github.com/parkjongmin-ddam/aibrief-mcp)
- 연결: [smithery.ai/servers/pjm754/aibrief](https://smithery.ai/servers/pjm754/aibrief)

써 보고 걸리는 게 있으면 알려주면 좋겠다. 브리핑 품질이랑 툴 스키마는 계속 다듬을 생각이다.
