---
title: "AI 에이전트를 Role 사다리에 얹기 — NHI Top 10과 OWASP Agentic Top 10이 만나는 곳"
categories: [Security, IAM, RAG]
tags: [OWASP, NHI, Agentic, IAM, least-agency, RAG, permission-aware-rag, ASI03, ABAC]
description: "지난 편의 Role 사다리는 '자격증명을 어떻게 보관하느냐'의 축이었다. AI 에이전트는 거기에 '얼마나 스스로 판단하느냐'는 두 번째 축을 추가한다. least agency라는 새 변수, ASI 위험의 Stage별 증폭, 그리고 권한 인식 RAG가 검색 단계에서 권한을 강제해 ASI03·NHI5·ASI06 교집합을 푸는 방법."

---

> **이 글을 읽기 전에 — NHI Top 10이 처음이라면**
> NHI(Non-Human Identity, 비인간 식별자)는 사람이 아닌 주체 — 애플리케이션·서비스·봇·AI 에이전트 — 가 시스템에 인증할 때 쓰는 정체성이다. API 키·토큰·서비스 계정·인증서가 모두 NHI다. OWASP는 2024년 말 이 영역의 대표 위험 10가지를 [NHI Top 10 (2025)](https://owasp.org/www-project-non-human-identities-top-10/2025/)으로 정리했다. 이 글에 자주 나오는 항목만 추리면: **NHI2**(시크릿 유출), **NHI5**(과대권한 — 필요 이상의 권한), **NHI8**(환경 격리 실패 — dev/prod 자격증명 공유), **NHI9**(NHI 재사용 — 여러 곳이 같은 자격증명 공유), **NHI10**(NHI의 인간 사용 — 사람이 서비스 계정으로 직접 로그인). 더 깊은 배경은 [지난 편](/nhi-top10-role-based-guide/)에 있다. ASI는 뒤에서 설명한다.

[지난 편](/nhi-top10-role-based-guide/)에서 OWASP NHI Top 10을 8개 Role 타입별로 재배치하고, 그걸 *Legacy SA → gMSA → Managed Identity → Federation/SPIFFE* 라는 4단계 마이그레이션 사다리로 정리했다. 핵심은 "한 단계 위로 올라가면 통제로 막던 위험 1~2개가 구조적으로 사라진다"는 것이었다.

그런데 2025년 말, 그 사다리 위에 완전히 새로운 워크로드 유형이 올라왔다 — **AI 에이전트**다. 이 글은 OWASP가 발표한 [Top 10 for Agentic Applications (2026)](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)을 지난 편의 사다리 위에 얹어, 세 가지를 다룬다: ① 에이전트가 사다리에 추가하는 새 축, ② ASI 위험이 Stage별로 어떻게 달라지는지, ③ 권한 인식 RAG가 그 교집합을 어떻게 푸는지.

---

## ① 에이전트는 사다리에 새 축을 추가한다 — least agency

지난 편 사다리의 축은 단 하나였다: **"자격증명을 어떻게 보관하고 회전하는가."** Legacy SA는 사람이 아는 비밀번호, gMSA는 AD가 관리하는 비밀번호, Managed Identity는 단기 토큰, Federation은 정적 시크릿 자체의 부재 — 위로 갈수록 자격증명이 단기화·자동화됐다.

하지만 이 사다리의 모든 단계에는 공통점이 있다. **행동이 결정론적(deterministic)이라는 것.** gMSA로 동작하는 SQL Server는 미리 짜인 쿼리만 실행한다. Managed Identity로 동작하는 Lambda는 코드에 적힌 경로만 탄다. 자격증명이 단기화됐을 뿐, *무엇을 할지*는 개발자가 사전에 결정해뒀다.

AI 에이전트는 이 전제를 깬다. 같은 자격증명을 들고도 **런타임에 무엇을 할지 스스로 정한다.** 도구를 호출할지, 어떤 순서로 호출할지, 어떤 데이터를 읽을지를 모델이 추론으로 결정한다. 앞서 언급한 OWASP Agentic Top 10은 이 새로운 위험 10가지를 ASI01~ASI10(Agentic Security Initiative의 약자)으로 번호 매긴 목록이다. 그중 ASI03(Identity & Privilege Abuse)이 OWASP 문서에서 <q>Excessive Agency(LLM06:2025)의 에이전트 진화형</q>으로 정의되는 이유가 여기 있다.[^asi03-evolution] 위험의 본질이 "권한을 너무 많이 줬다"에서 "재량을 너무 많이 줬다"로 옮겨간 것이다.

그래서 OWASP Agentic Top 10은 전통적 최소권한(least privilege)에 더해 **최소 자율성(least agency)** 이라는 새 변수를 도입한다. 빌더 입장에서 이것은 <q>비즈니스 문제가 정당화하는 것 이상의 자율성을 에이전트에게 주지 않는 것</q>을 뜻한다.[^least-agency] 권한과 자율성은 별개의 축이다 — 권한을 좁혀도 자율성이 넓으면 위험하고, 그 반대도 마찬가지다.

이것을 지난 편 사다리에 직교하는 두 번째 축으로 그리면 이렇게 된다.

```
        높은 자율성 (high agency)
              ▲
              │   ⚠️ 위험 구역
              │   사다리는 높지만(단기 자격증명)
              │   재량이 넓은 에이전트
              │
  ────────────┼────────────▶  사다리 Stage
              │              (Legacy SA → Federation)
              │
              │   ✓ 안전 구역
              │   높은 Stage + 좁은 재량
              ▼
        낮은 자율성 (low agency)
```

핵심은 — **사다리를 높이 올리는 것만으로는 에이전트가 안전해지지 않는다.** Stage 4(Federation)의 깔끔한 단기 자격증명을 가진 에이전트라도, 재량(agency)이 무제한이면 여전히 위험하다. 두 축을 함께 낮춰야 한다.

---

## ② ASI 위험은 사다리 Stage에 따라 증폭되거나 완화된다

에이전트를 "사다리 어느 Stage의 NHI 위에 얹느냐"가 ASI 위험의 심각도를 좌우한다. 세 가지 대표 매핑으로 보자.

### ASI03 (정체성·권한 오남용) — Stage가 낮을수록 치명적

ASI03의 정의는 <q>에이전트가 사용자 세션을 상속하거나 시크릿을 재사용하거나 암묵적 에이전트 간 신뢰에 의존해, 권한 상승과 책임 추적 불가가 발생하는 것</q>이다.[^asi03-def] 이것을 사다리에 얹어보면:

**Stage 1(Legacy SA) 위의 에이전트 = 최악의 조합.** 에이전트가 사람이 아는 서비스 계정 자격증명을 물려받아 동작하면 — 모든 행동이 사람 활동과 로그상 구분되지 않고(NHI10), 회전 안 되는 시크릿에 영구히 묶이고(NHI7), 그 계정의 과도한 권한을 그대로 상속한다(NHI5). ASI03 하나가 NHI10·NHI7·NHI5를 동시에 끌고 들어온다.

**Stage 3~4 위의 에이전트 = 완화된 조합.** OWASP가 ASI03의 완화책으로 제시하는 것이 정확히 <q>단기·작업범위 한정(task-scoped) JIT 자격증명을 사용하고, 에이전트를 관리되는 NHI로 취급하라</q>는 것이다.[^asi03-mitigation] 그런데 이건 지난 편 사다리를 Stage 3~4까지 올린 다음 그 위에 에이전트를 얹으라는 말과 *정확히 같다.* 즉:

> **"에이전트를 1급 NHI로 다룬다" = "에이전트를 사다리 꼭대기 Stage에 올린다"**

지난 편에서 다룬 IAM 통제가 에이전트 보안의 전제 조건이라는 뜻이다. 새로운 보안 영역을 배우는 게 아니라, 이미 아는 사다리를 에이전트라는 새 주체에 적용하는 것이다.

### ASI06 (메모리·컨텍스트 오염) — 사다리에 없던 새 표면

여기서 사다리만으로는 안 되는 지점이 나온다. gMSA에는 "메모리"가 없다. 하지만 에이전트는 대화 메모리·임베딩·RAG 저장소를 갖는다. ASI06은 이 영속 저장소를 오염시켜 추론을 편향시키거나 시크릿을 유출하는 위험이다.[^asi06] 메모리 포이즈닝은 <q>메모리에 시크릿·키·토큰이 담겨 있을 때 치명적</q>이 된다 — 즉 ASI06이 NHI2(시크릿 유출)와 교차하는 순간이다.[^asi06-nhi2]

이건 사다리를 아무리 높이 올려도 자동으로 사라지지 않는다. Stage 4 Federation으로 자격증명을 완벽히 관리해도, 에이전트의 벡터 스토어에 평문 API 키가 청크로 섞여 들어가면 ASI06 → NHI2 경로는 그대로 열려 있다. **에이전트 고유의, 사다리 바깥의 위험.** 그래서 검색·생성 파이프라인 자체에 대한 별도 통제가 필요하다 — 다음 섹션의 주제다.

### ASI08 (연쇄 장애) — Stage가 낮을수록 폭발 반경 확대

ASI08은 한 에이전트의 오염·침해가 여러 에이전트·워크플로우로 번지는 위험이다. 이것이 증폭되는 근본 원인은 <q>동일 NHI가 여러 에이전트와 환경에 걸쳐 재사용되기 때문</q>이다.[^asi08-nhi9] 즉 ASI08 = NHI9(재사용) + NHI8(환경 격리 실패)의 에이전트 버전이다. dev/prod 멀티 에이전트가 같은 서비스 계정 토큰을 공유하면(낮은 Stage), 한 에이전트 침해가 전체로 번진다. 사다리에서 환경별 고유 NHI를 강제하면(Stage 3~4) 폭발 반경이 자연히 좁아진다.

### 종합 매핑표 — ASI × NHI × Stage

지금까지의 매핑을 한 장으로 정리하면 이렇다. ASI 10개 전부가 아니라, **정체성·자격증명에 직접 뿌리를 둔 6개**만 추렸다 — 이 글의 렌즈가 "NHI 사다리"이기 때문이다. "근본 NHI"는 해당 ASI 위험을 떠받치는 정체성 약점이고, "Stage 의존성"은 사다리를 올리는 것만으로 완화되는지 여부다.

| ASI 위험 | 근본 NHI | Stage 의존성 | 사다리 위에서의 거동 |
|---|---|---|---|
| ASI03 정체성·권한 오남용 | NHI5·NHI9·NHI10 | **높음** | Stage ↑ 하면 크게 완화. "1급 NHI화"가 곧 Stage ↑ |
| ASI02 도구 악용 | NHI5 | 중간 | 권한 축소로 완화되나 도구 단위 통제 별도 필요 |
| ASI06 메모리·컨텍스트 오염 | NHI2 | **없음** | 사다리 바깥. 검색·생성 파이프라인 통제 필요 |
| ASI08 연쇄 장애 | NHI9·NHI8 | 높음 | 환경별 고유 NHI(Stage ↑)로 폭발 반경 축소 |
| ASI04 공급망 | NHI3 | 낮음 | MCP·플러그인 allowlist 등 별도 통제가 주력 |
| ASI07 에이전트 간 통신 | NHI4 | 중간 | mTLS·상호 인증(Stage ↑의 부산물)로 부분 완화 |

표를 세로로 읽으면 두 부류가 보인다. **Stage 의존성이 높은 위험(ASI03·ASI08)** 은 지난 편 사다리를 올리는 것만으로 상당 부분 완화된다 — 이미 아는 IAM 통제의 연장이다. 반면 **Stage 의존성이 없거나 낮은 위험(ASI06·ASI04)** 은 사다리 바깥의 에이전트 고유 표면이라, 검색·생성 파이프라인이나 공급망 거버넌스 같은 별도 통제가 필요하다. 다음 섹션의 권한 인식 RAG는 그중 ASI06(과 ASI03·NHI5)을 동시에 겨냥한다.

**나머지 4개는 왜 뺐나.** 이 표에 없는 ASI01·ASI05·ASI09·ASI10은 누락이 아니라 의도적 제외다. 이들은 정체성·자격증명이 아니라 다른 층위에 근본 원인이 있어, NHI 사다리로는 깔끔하게 매핑되지 않는다. **ASI01(Goal Hijack)** 은 모델이 명령과 데이터를 구분하지 못하는 프롬프트 인젝션 문제이고, **ASI05(Unexpected Code Execution)** 는 샌드박스 탈출·실행 환경 격리 문제이며, **ASI09(Human-Agent Trust Exploitation)** 는 의인화·권위 편향을 악용하는 인간 심리 문제, **ASI10(Rogue Agents)** 은 특정 약점이라기보다 침해의 결과로 나타나는 일탈 현상이다. 물론 이들도 과대권한 NHI 위에서 더 위험해지지만(예: hijack된 에이전트가 넓은 권한을 가졌다면 피해가 커진다), 그건 *증폭 요인*이지 *근본 원인*이 아니다. 그래서 "NHI를 보호하면 완화된다"는 이 글의 논지가 직접 적용되는 6개에 집중했다. 나머지 4개는 프롬프트 가드레일, 실행 샌드박스, HITL(human-in-the-loop) 같은 별도 통제 영역의 주제다.

---

## ③ 권한 인식 RAG — 검색 단계에서 권한을 강제해 교집합을 푼다

ASI03·NHI5·ASI06이 한데 모이는 가장 흔한 실전 패턴이 있다. **에이전트가 RAG 인덱스 전체를 읽을 수 있는 단일 고권한 정체성으로 동작하는 것.**

이 구조에서는 영업사원이 묻든 법무팀이 묻든, 에이전트는 같은 인덱스 전체를 검색해 같은 근거로 답한다. 이것은 세 위험의 교집합이다 — 에이전트가 "전체를 읽는 하나의 정체성"으로 권한을 오남용하고(ASI03), 유효 권한이 인덱스 전체로 과대하며(NHI5), 권한 없는 문서가 컨텍스트에 섞여 들어와 오염 표면이 된다(ASI06).

`permission-aware-rag`는 이 구조를 검색 단계에서 뒤집는다. 핵심은 **검색 결과에 요청 주체(persona)의 권한을 강제하는 `can_read()` 필터를, LLM 생성 *앞단*에 끼우는 것**이다.

### 2단계 검색 + 권한 필터

```
질문 입력
   │
   ▼
[1] HNSW 벡터 검색 (oversample 30건)
   │
   ▼
[2] BGE Reranker로 관련도 재정렬 (top 15)
   │
   ▼
[3] can_read(persona, doc) 권한 필터  ◀── 여기가 핵심
   │     - 6개 권한 규칙 (ABAC/ReBAC)
   │     - persona가 볼 수 없는 문서 제거
   ▼
[4] 권한 통과 문서만 top_k로 LLM에 전달
   │
   ▼
권한 필터링된 답변 생성
```

이 구조가 세 위험을 각각 어떻게 푸는지:

**ASI03 완화** — 에이전트가 "전체를 읽는 하나의 정체성"이 아니라 "요청자의 권한을 대리하는 정체성"으로 동작한다. 권한 상속·오남용이 차단된다. 에이전트의 재량(agency)은 넓더라도, 그 재량이 발휘되는 *데이터 범위*가 요청자 권한으로 묶인다 — least agency를 데이터 축에서 구현한 셈이다.

**NHI5 완화** — 에이전트의 유효 권한이 인덱스 전체가 아니라 *요청자가 볼 수 있는 부분집합*으로 좁혀진다. 과대권한이 요청 단위로 해소된다.

**ASI06 경계 차단** — 권한 필터가 생성 *앞단*에 있으므로, 권한 없는 문서는 애초에 LLM 컨텍스트에 들어가지 못한다. 메모리/컨텍스트 오염의 한 경로(권한 없는 문서를 통한 간접 주입)가 원천 차단된다.

### 6개 권한 규칙이 각각 막는 것

`can_read()` 필터는 단일 규칙이 아니라, 우선순위 순으로 평가되는 6개 규칙의 묶음이다. 각 규칙은 문서에 따라 *허용(allow) / 명시적 차단(explicit deny) / 의견 없음(abstain, None 반환)* 중 하나를 반환하고, 어떤 규칙도 허용하지 않으면 닫힌 세계(closed-world) 모델에 따라 기본 차단된다. 규칙은 `audit_rule`을 최우선으로, `sensitivity_rule`을 최후 폴백으로 평가한다. 규칙별로 무엇을 판정하고 어떤 ASI/NHI 위험을 겨냥하는지 정리하면:

| 규칙 (우선순위) | 판정 대상 | 처리 방식 | 겨냥하는 위험 |
|---|---|---|---|
| `audit_rule` | engagement 보유 auditor | 대부분 allow, 단 hr.personnel은 abstain·privileged litigation은 **deny** | ASI03 — 감사 권한에도 privacy/특권 경계 강제 |
| `self_access_rule` | hr.personnel, finance.expense | 본인이 subject면 allow, 아니면 abstain | NHI5 — 본인 데이터로 범위 한정 |
| `project_rule` | tech.project | 멤버면 allow, 아니면 **explicit deny** | NHI5·ASI03 — 프로젝트 기밀은 role 우선 불가(임원도 외부면 차단) |
| `parties_rule` | legal.contract / legal.litigation | 당사자면 allow; 비당사자는 contract **deny**, litigation abstain | ASI06·NHI5 — NDA 당사자만, 계약은 컨텍스트 진입 차단 |
| `incident_rule` | security.incident | 4개 경로(stakeholder·security_officer·briefed exec·Critical+exec) allow, 그 외 **explicit deny** | ASI06·ASI03 — 보안 사고 ReBAC + role gate |
| `sensitivity_rule` | sensitivity 필드 보유 문서 | role별 최대 열람 등급(ROLE_DEFAULTS) 이내면 allow, 아니면 abstain | NHI5 — 민감도 등급 RBAC 폴백 |

설계상 세 가지 처리 방식이 핵심이다. **explicit deny**는 "role이 아무리 높아도 차단"을 뜻한다 — `project_rule`이 대표적인데, 임원이라도 프로젝트 멤버가 아니면 tech.project 문서를 못 본다. 이건 ASI03(권한 상속을 통한 오남용)을 정면으로 막는다. **abstain(None 반환)** 은 "이 규칙은 의견 없음, 다음 규칙에 위임"을 뜻한다 — `parties_rule`이 비당사자의 legal.litigation을 abstain시키는 이유는 disclosure_level과 role에 따라 후속 `sensitivity_rule`이 판정해야 하기 때문이다. 그리고 가장 흥미로운 건 **`audit_rule`의 예외 처리**다.

### 같은 "auditor"도 문서의 특권 등급에 따라 갈린다

`audit_rule`은 활성 engagement를 가진 감사자에게 대부분 문서의 oversight read를 allow한다. 하지만 두 개의 경계만은 감사 권한으로도 뚫지 못한다 — **개인 HR 기록(hr.personnel)** 은 abstain시켜 본인 외엔 접근을 막고, **변호사-의뢰인 특권이 걸린 소송 문서(legal.litigation + disclosure_level='privileged')** 는 코드가 명시적으로 deny를 반환한다. 감사 업무라는 정당한 사유로도 attorney-client privilege는 면제되지 않는다는 설계다.

이것이 권한 인식 RAG의 핵심을 압축한다 — **같은 "auditor"라는 정체성이라도, 문서의 특권 등급에 따라 검색 결과가 달라진다.** 일반 재무 문서는 감사자의 컨텍스트에 들어오지만, privileged 소송 문서는 같은 검색에서 제거된다. 정체성 하나에 고정된 권한이 아니라, *문서×정체성×속성*의 조합으로 매 요청 판정되는 것이다.

이 구조가 ASI06 방어에서 갖는 의미는 — **권한 없는 문서를 "조용히 누락"시키는 게 아니라, 규칙별로 명시적 deny/abstain을 추적 가능한 이유(reason)와 함께 남긴다는 것**이다. closed-world default-deny이므로 새 문서 카테고리를 추가하고 규칙 작성을 깜빡해도 안전한 쪽(차단)으로 떨어진다. 권한 없는 문서가 LLM 컨텍스트에 흘러드는 경로 자체가 설계로 봉쇄된다.

### "사람마다 답이 다른 시스템"은 버그가 아니라 보안 속성

이 아키텍처의 결과는 — **같은 질문이라도 묻는 사람의 권한에 따라 검색 결과 자체가 달라지고, 따라서 답변도 달라진다.** 프로젝트 멤버가 "이 프로젝트의 기술 결정 배경은?"이라고 물으면 tech.project 문서가 근거로 잡히지만, 같은 질문을 멤버가 아닌 임원이 하면 그 문서들은 `project_rule`의 explicit deny로 검색 단계에서 제거되어 답변 근거에 들어오지 않는다. role이 더 높아도 결과가 더 넓어지지 않는다 — 오히려 프로젝트 기밀에서는 외부자로 차단된다.

직관적으로는 "일관성 없는 시스템"처럼 보이지만, 보안 관점에서는 정반대다. 이것은 **설계된 보안 속성**이다 — 권한 경계가 답변 생성까지 일관되게 전파된다는 증거. 권한 인식 RAG는 "에이전트를 권한 경계 안에 가두는" 구체적 아키텍처이고, 두 OWASP 프레임워크(NHI Top 10 + Agentic Top 10)의 교집합을 코드로 증명하는 사례다.

---

## 마무리 — 두 축, 하나의 원칙

정리하면 이렇다. 지난 편 사다리는 **자격증명 축**이었고, 이번 편은 거기에 **자율성 축**을 더했다. 에이전트를 안전하게 운영한다는 건 두 축을 함께 낮추는 일이다 — 사다리를 Stage 3~4까지 올려 자격증명을 단기·고유화하고(ASI03·NHI5·NHI8 완화), 그 위에서 에이전트의 재량을 데이터·도구·행동 범위로 좁히는 것(least agency). 권한 인식 RAG는 그중 *데이터 범위*를 검색 단계에서 강제하는 한 가지 구현이다.

두 OWASP 프레임워크가 던지는 메시지는 결국 하나로 수렴한다 — **에이전트에 권한을 주는 NHI를 보호하지 않고는 에이전트를 보호할 수 없다.** 그리고 그 NHI 보호는, 이미 우리가 IAM 엔지니어로서 알고 있는 사다리에서 시작한다.

---

### 라이선스 및 출처

본 글의 ASI01~10 및 NHI1~10 정의·시나리오는 OWASP의 두 프로젝트 — [Top 10 for Agentic Applications (2026)](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) 및 [Non-Human Identities Top 10 (2025)](https://owasp.org/www-project-non-human-identities-top-10/2025/) — 를 참고했으며, 두 프로젝트 모두 Creative Commons Attribution-ShareAlike 4.0 라이선스를 따른다. 본 글의 OWASP 인용 부분 역시 동일 라이선스(CC BY-SA 4.0)로 재배포된다.

Role 사다리와 두 축 모델, ASI×NHI×Stage 매핑, 그리고 `permission-aware-rag` 아키텍처 해석은 필자의 IAM/RAG 실무 경험에 기반한 *해석*으로, OWASP 원문에 포함된 내용이 아니다. `permission-aware-rag`의 구체 수치(검색 단계 oversample/rerank 파라미터, 6개 권한 규칙의 이름·sub_type 매핑·처리 방식, persona 구성)는 필자가 본 프로젝트를 위해 직접 작성한 코드의 구현 세부이며, 일반 권장값이 아니라 해당 프로젝트의 시나리오에 맞춘 설계다.

### References

- OWASP Top 10 for Agentic Applications (2026), OWASP GenAI Security Project: <https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/>
- OWASP Non-Human Identities Top 10 (2025): <https://owasp.org/www-project-non-human-identities-top-10/2025/>
- OWASP Top 10 for LLM Applications (2025) — LLM06 Excessive Agency: <https://genai.owasp.org/llm-top-10/>

[^asi03-evolution]: ASI03는 OWASP Agentic Top 10에서 LLM06:2025(Excessive Agency)의 에이전트 진화형으로 위치 지어진다. OWASP Top 10 for Agentic Applications (2026).

[^least-agency]: "least agency"는 비즈니스 문제가 정당화하는 범위 이상의 자율성을 에이전트에 부여하지 않는 원칙으로, 전통적 least privilege와 구분되는 별도의 통제 축이다. OWASP Top 10 for Agentic Applications (2026).

[^asi03-def]: ASI03(Identity & Privilege Abuse) — 에이전트가 사용자 세션 상속, 시크릿 재사용, 암묵적 에이전트 간 신뢰에 의존함으로써 권한 상승 및 책임 추적 불가가 발생. OWASP Top 10 for Agentic Applications (2026).

[^asi03-mitigation]: ASI03 완화책 — 단기·작업범위 한정(JIT) 자격증명 사용, 에이전트를 관리되는 NHI로 취급. OWASP Top 10 for Agentic Applications (2026).

[^asi06]: ASI06(Memory & Context Poisoning) — 영속 메모리·임베딩·RAG 저장소의 오염을 통한 추론 편향, 시크릿 유출, 행동 변질. OWASP Top 10 for Agentic Applications (2026).

[^asi06-nhi2]: 메모리 포이즈닝은 메모리에 시크릿·키·토큰이 포함될 때 NHI2(Secret Leakage)와 교차하며 치명도가 급증한다. OWASP Top 10 for Agentic Applications (2026) / OWASP NHI Top 10 (2025).

[^asi08-nhi9]: ASI08(Cascading Failures)의 증폭 원인은 동일 NHI가 여러 에이전트·환경에 재사용되는 구조이며, 이는 NHI9(Reuse) 및 NHI8(Environment Isolation)과 직접 연결된다. OWASP Top 10 for Agentic Applications (2026) / OWASP NHI Top 10 (2025).