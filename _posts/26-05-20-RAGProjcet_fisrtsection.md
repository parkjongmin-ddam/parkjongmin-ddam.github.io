---
title: "권한 인식 RAG 만들기_Secetion 1 — 설계와 구현"
categories: [RAG, IAM]
tags: [permission-aware-rag, FastAPI, pgvector, RBAC, ABAC, JWT, BGE-M3]
description: "엔터프라이즈 RAG의 권한 차원을 메우는 사이드 프로젝트의 첫 두 단계. 가상 회사 BWCorp 설계부터 6개 권한 룰 구현까지."
---

ChatGPT의 "내 문서 기반 답변"이 처음 나왔을 때 한 가지 의문이 들었다. 이 시스템은 권한을 어떻게 처리하나.

답은 안 한다였다. 대부분의 RAG는 "이 사용자가 이 문서를 봐도 되는가"를 자체 시스템에 떠넘기거나 아예 고려하지 않는다. 데모로는 작동한다. 엔터프라이즈에는 못 들어간다.

permission-aware-rag는 그 갭을 메우려는 사이드 프로젝트다. 지난 5년간 IAM과 인증 인프라(ADFS, SAML, OIDC)를 운영하면서 본 권한 패턴을 RAG 도메인에 옮겨봤다.

이 글은 M1 (데이터 설계)와 M2 (구현) 두 단계를 묶었다. M3는 다음 글에서 다룬다.

## 권한 인식 RAG가 왜 필요한가

대부분의 RAG 데모는 이렇게 동작한다.

```
query → 벡터 검색 → top-K chunk → LLM
```

엔터프라이즈에 들어가면 query 던지는 사람이 누구냐에 따라 답이 달라져야 한다. 인사팀 직원이 자기 평가서 검색하는 건 OK다. 동료 평가서가 같이 나오면 안 된다. vector similarity가 높았다는 게 변명이 안 된다. 못 보던 거니까.

권한 인식 RAG는 이걸 retrieval 단계에서 해결한다.

```
query → 벡터 검색 → top-K candidate → 권한 필터 → 응답
                                       ↑
                                     can_read(user, doc)
```

이게 끝이라면 사이드 프로젝트할 가치도 없다. 진짜 문제는 권한이 단순 ACL이 아니라는 거다.

5년간 IAM 운영하면서 본 패턴들을 종합하면 이렇다.

- 본인 데이터는 본인만 (self-access)
- 프로젝트 멤버만 프로젝트 문서 (project membership)
- 계약 당사자만 계약 문서 (relationship-based)
- 보안 사고는 관련자 + 보안팀 + 브리핑된 임원 (multi-path)
- 감사인은 광범위하지만 일부 영역 제외 (with carve-outs)
- 그 외엔 role에 따른 매트릭스 (RBAC)

이 6개 조각이 우선순위 순서로 동작해야 한다. RBAC + ABAC + ReBAC가 따로 쓰이는 일은 없다. 항상 섞여 있다.

## BWCorp — 가상 회사 만들기

가상 회사부터 만들기로 했다.

권한 인식 RAG의 정확성을 측정하려면 "누가 무엇을 봐도 되는지"의 ground truth가 필요하다. 공개 데이터셋(MS MARCO, BEIR 등)은 권한 메타데이터가 없다. 직접 만들 수밖에.

설계 기준은 네 가지였다.

- 실제 IAM에서 발생하는 케이스를 망라
- 함정 케이스 포함 (예: 감사인이 광범위 접근권 갖지만 개인 HR과 privileged litigation은 제외)
- 한국 직장 환경 반영 (일부 문서는 한국어, 일부는 영어)
- 다양한 sensitivity (모두가 읽는 정책부터 한 명만 보는 본인 평가서까지)

가상 회사 이름은 BWCorp로 정했다. 직원 200명, 7개 부서, 외부 컨설팅 파트너 ExternalCo와 협업. 회사 디테일을 굳이 만든 이유는 문서 제목이 자연스러워야 RAG 매칭이 잘 되기 때문이다. "BWCorp 휴가 정책 v3.2"가 그냥 "휴가 정책"보다 검색에서 자연스럽다.

## 9 페르소나

페르소나 9명을 정했다.

| 페르소나 | role | dept | 특이사항 |
|---|---|---|---|
| user_emp_001 | employee | engineering | Project Delta 멤버 |
| user_emp_002 | employee | marketing | 다른 부서 (대조군) |
| user_emp_003 | employee | engineering | Project Delta 멤버 |
| user_tl_001 | team_lead | engineering | 팀 리드 |
| user_exec_001 | executive | executive | 임원 |
| user_sec_001 | security_officer | security | 보안 담당 |
| user_ext_001 | contractor | external | Project Alpha + ExternalCo 계약 당사자 |
| user_aud_001 | auditor | external | SOC2 감사인 |
| user_hrs_001 | hr_specialist | hr | HR 전담 |

각 페르소나가 어떤 룰을 통해 어떤 문서를 보는지를 미리 매핑하고 시작했다. 9 × 45 = 405개 페어의 접근 가능 여부를 의도적으로 분포시켰다.

`audit_engagement_id`는 auditor만 갖는다. 감사 진행 중일 때만 광범위 접근을 발동시키는 contextual claim이다. 평소엔 auditor도 일반 직원처럼 취급된다. ADFS claim rule 짜다 보면 흔히 보는 패턴이다.

## 분류 체계 — 첫 결정의 함정

문서를 어떻게 분류할지가 다음 결정이었다. 두 옵션이 있었다.

- sensitivity 기반: `public / internal / restricted / privileged`
- topic 기반: `hr.policy, tech.runbook, finance.expense, ...`

sensitivity 기반이면 권한 룰이 단순해진다. "manager는 internal까지 읽는다" 같은 표현이 가능하다. 근데 RAG 검색 정확도 측면에서는 topic 기반이 더 직관적이다. "휴가 정책" query가 `hr.policy`를 정확히 잡는다.

topic 기반으로 갔다. 권한 룰은 topic-keyed 매트릭스로도 표현 가능하다고 봤다.

(이게 M3에서 큰 부메랑으로 돌아온다. 다음 글에서 자세히.)

24개 sub_type을 정해 45 문서에 분포시켰다.

```
hr.policy (3), hr.compensation (2), hr.personnel (2), hr.recruitment (1)
security.policy (2), security.incident (3), security.threat_intel (1), security.compliance (1)
tech.architecture (2), tech.api (2), tech.runbook (2), tech.project (4)
finance.budget (2), finance.statement (2), finance.expense (3), finance.tax (1)
marketing.campaign (2), marketing.brand (2), marketing.research (2)
legal.contract (2), legal.regulatory (1), legal.opinion (1), legal.litigation (2)
```

## 6개 권한 룰

룰을 매트릭스 하나로 끝낼 수도 있었다. 근데 그러면 "본인 비용은 본인만" 같은 ABAC가 안 들어간다.

6개 룰을 우선순위 순서로 정했다.

```
1. audit_rule       — 감사인 광범위 접근 (HR + privileged litigation 제외)
2. self_access_rule — 본인이 subject인 문서 접근
3. project_rule     — tech.project는 project_members만 (strict closure)
4. parties_rule     — legal.contract는 당사자만 (litigation은 fall-through)
5. incident_rule    — security.incident는 stakeholder/security_officer/exec 4경로
6. rbac_default     — role 매트릭스 catch-all
```

순서가 의도적이다. audit이 최상단인 건 감사 시즌에 빨리 광범위 접근을 grant하기 위함이다. self_access는 자기 평가서 보는 게 manager 권한 체크 거치면 이상하니까 일찍. project/parties/incident는 ABAC. 다 끝나면 rbac_default가 catch-all이다.

각 룰의 abstain(None 반환) vs explicit DENY 선택도 신중했다. `project_rule`은 "멤버 아니면 명시적 DENY"(strict closure)다. `self_access_rule`은 "본인 아니면 None"(다음 룰에 맡김)다. XACML 표준의 deny-overrides 패턴과 비슷하다.

여기까지가 M1이다. 코드는 한 줄도 안 썼지만 데이터와 정책이 명확하면 구현은 기계적이다.

산출물:
- `docs/data-spec.md` + `docs/data-spec.ko.md`
- `data/documents.yaml` (45 문서)
- 권한 룰 6개 결정

## M2 — 설계를 코드로

목표는 명확했다. M1에서 결정한 게 다 동작하는 HTTP API를 만들자.

스택:
- FastAPI (async, OpenAPI 자동 생성, Pydantic 검증)
- PostgreSQL + pgvector (별도 vector DB 없이 관계형 DB에 임베딩 컬럼)
- BGE-M3 임베딩 (한국어 성능 OK, 로컬 실행, API 비용 0, 1024차원)
- HNSW 인덱스

`docker-compose.yml`로 pgvector 띄우고 스키마는 이렇게.

```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT, sub_type TEXT, sensitivity TEXT, language TEXT,
    subject TEXT, project_id TEXT, project_members TEXT[],
    parties TEXT[], case_id TEXT,
    stakeholders TEXT[], severity TEXT, executive_briefed BOOLEAN,
    disclosure_level TEXT, tags TEXT[],
    expected_readers TEXT[],
    embedding vector(1024)
);

CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON documents USING gin (project_members);
CREATE INDEX ON documents USING gin (parties);
CREATE INDEX ON documents USING gin (stakeholders);
```

GIN 인덱스는 ABAC에서 "user_id가 project_members 배열에 있는가" 쿼리를 빠르게 하기 위한 거다.

### Windows에서 한 시간 헤맨 거

psycopg 3 비동기 풀로 연결. Windows에서 첫 시도 때 한 시간 헤맸다. SelectorEventLoop 정책을 명시 안 하면 psycopg async가 안 돌아간다.

```python
import sys, asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

한 줄 빠뜨려서 1시간.

### 임베딩 + 인제스트

BGE-M3는 `sentence-transformers`로 로컬 실행. `lru_cache` 싱글톤으로 모델 한 번만 로드.

```python
from functools import lru_cache
from sentence_transformers import SentenceTransformer

@lru_cache(maxsize=1)
def get_embedder():
    return SentenceTransformer("BAAI/bge-m3")
```

`scripts/ingest.py` 한 파일로 yaml 읽어서 임베딩 계산하고 UPSERT.

### Mock JWT auth

JWT 쓰는 이유는 실제 OAuth/OIDC 클레임 흐름을 시뮬레이션하기 위함이다. production에서는 IdP가 JWT 발급, RAG는 검증만 한다. mock-login 엔드포인트는 개발 편의로 만들었다.

`PERSONAS` dict에 9명 메타데이터 박아둠.

```python
PERSONAS = {
    "user_emp_001": {"user_id": "user_emp_001", "role": "employee", "dept": "engineering"},
    # ...
    "user_aud_001": {
        "user_id": "user_aud_001",
        "role": "auditor",
        "dept": "external",
        "audit_engagement_id": "AUDIT-2026-SOC2-001",  # auditor만 이 필드
    },
}
```

`Principal`은 frozen dataclass.

```python
@dataclass(frozen=True)
class Principal:
    user_id: str
    role: str
    dept: str | None = None
    audit_engagement_id: str | None = None
    raw_claims: dict[str, Any] = field(default_factory=dict)
```

FastAPI dependency injection으로 라우터에 주입.

### 권한 룰 6개

`permission/types.py`에 결정 객체부터.

```python
class Effect(Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"

@dataclass(frozen=True)
class PolicyDecision:
    effect: Effect
    rule_name: str
    reason: str

    @property
    def is_allowed(self) -> bool:
        return self.effect == Effect.ALLOW
```

각 룰은 `(Principal, document) → Optional[PolicyDecision]` 형태의 순수 함수다. None 반환은 "이 룰 안 맞음, 다음 룰" (abstain).

#### project_rule — strict closure

```python
def project_rule(principal, document):
    if document.get("sub_type") != "tech.project":
        return None  # abstain

    members = document.get("project_members") or []
    if principal.user_id in members:
        return PolicyDecision.allow(...)

    return PolicyDecision.deny(...)  # 멤버 아니면 명시적 거부
```

"멤버 아니면 명시적 DENY"가 핵심이다. tech.project가 fall through로 rbac_default 거치면 role이 manager인 사람이 멤버 아닌데도 본다는 이상한 상황이 생긴다. 프로젝트 비밀유지가 직급보다 우선이다.

#### audit_rule — exclusion 패턴

```python
def audit_rule(principal, document):
    if principal.role != "auditor":
        return None
    if principal.audit_engagement_id is None:
        return None  # 감사 안 하는 auditor는 일반 직원 취급

    sub_type = document.get("sub_type")

    # Exclusion 1: 개인 HR 기록 (privacy)
    if sub_type == "hr.personnel":
        return None  # 다른 룰에 맡김, 끝까지 가면 default deny

    # Exclusion 2: privileged litigation (attorney-client)
    if sub_type == "legal.litigation":
        if document.get("disclosure_level") == "privileged":
            return PolicyDecision.deny(...)

    return PolicyDecision.allow(...)
```

흥미로운 디테일은 두 exclusion이 다르다는 거다. hr.personnel에서는 None 반환(다른 룰이 처리하게), privileged litigation에서는 DENY 반환(다음 룰도 grant 못 하게). 전자는 `self_access_rule`이 본인 평가서를 grant할 여지를 남기는 거고, 후자는 어떤 경로로도 못 접근하게 봉쇄하는 거다.

이 미묘한 차이가 IAM에서 자주 헷갈리는 부분이다. ADFS claim rule에서도 비슷한 함정 자주 봤다.

#### incident_rule — ReBAC + role + attribute

```python
def incident_rule(principal, document):
    if document.get("sub_type") != "security.incident":
        return None

    # Path 1: stakeholder (ReBAC)
    if principal.user_id in document.get("stakeholders", []):
        return PolicyDecision.allow(...)

    # Path 2: security officer (role)
    if principal.role == "security_officer":
        return PolicyDecision.allow(...)

    # Path 3: briefed executive (role + attribute)
    if principal.role == "executive" and document.get("executive_briefed"):
        return PolicyDecision.allow(...)

    # Path 4: critical incidents auto-escalate to exec
    if principal.role == "executive" and document.get("severity") == "Critical":
        return PolicyDecision.allow(...)

    # 그 외 다 DENY (security incident는 closed-by-default)
    return PolicyDecision.deny(...)
```

한 룰 안에 누구와 관련 있나(stakeholder), 어떤 역할인가(security_officer/executive), 어떤 컨텍스트인가(briefed, severity) 세 차원이 다 들어간다. ADFS claim rule 짜다 보면 이런 OR + AND 조합 매일 본다.

### can_read() 오케스트레이션

```python
RULES = [
    audit_rule,
    self_access_rule,
    project_rule,
    parties_rule,
    incident_rule,
    rbac_default,
]

def can_read(principal, document):
    for rule in RULES:
        decision = rule(principal, document)
        if decision is not None:
            return decision
    # 모든 룰이 None → default DENY
    return PolicyDecision.deny(rule_name="default", reason="...")
```

핵심 패턴 두 가지다.
- **first-match-wins**: 한 룰이 ALLOW나 DENY 반환하면 즉시 종료
- **closed-world default**: 모든 룰이 None이면 DENY. principle of least privilege

XACML의 deny-overrides 알고리즘과 거의 같다. 룰 우선순위가 명시적이라 더 강한 보장이 있다.

### /query 엔드포인트

```python
@router.post("", response_model=QueryResponse)
async def query_documents(request, principal: Principal = Depends(...)):
    result = await retrieve(principal, request.query, top_k=request.top_k)

    await write_audit_log(
        user_id=principal.user_id,
        query=request.query,
        retrieved_doc_ids=[d.id for d in result.allowed + result.denied],
        granted_doc_ids=[d.id for d in result.allowed],
        denied_doc_ids=[d.id for d in result.denied],
        audit_engagement_id=principal.audit_engagement_id,
    )

    return QueryResponse(
        results=[DocumentResult.from_scored(d) for d in result.allowed],
        ...
    )
```

audit_log는 모든 query를 기록한다. 성공이든 실패든. 컴플라이언스 감사에서 "이 사용자가 이 시점에 무엇을 물었고 무엇을 받았고 무엇이 거부됐는가"가 핵심이니까.

(M3에서 이 audit_log 코드가 미묘하게 잘못돼 있다는 걸 발견한다. 다음 글에서.)

### 9 × 6 verification

M2 마무리는 verification matrix였다. 9 페르소나 × 6 룰의 핵심 시나리오 약 50개를 직접 돌렸다.

| 시나리오 | 페르소나 | 문서 | 기대 결과 |
|---|---|---|---|
| 본인 비용 접근 | emp_001 | DOC-030 (own expense) | ALLOW (self_access) |
| 타인 비용 차단 | emp_001 | DOC-031 (other expense) | DENY (default) |
| 프로젝트 멤버 접근 | ext_001 | DOC-022 (Project Alpha) | ALLOW (project) |
| 프로젝트 비멤버 차단 | emp_001 | DOC-024 (Project Gamma) | DENY (project closure) |
| 감사인 광범위 접근 | aud_001 | DOC-026 (Budget) | ALLOW (audit) |
| 감사인 HR personnel 차단 | aud_001 | DOC-006 (Perf Review) | DENY (audit exclusion) |
| 보안 담당 사고 접근 | sec_001 | DOC-011 (Incident) | ALLOW (incident) |
| 일반 직원 사고 차단 | emp_001 | DOC-011 (Incident) | DENY (incident closure) |

전부 의도대로 작동 확인. 이게 됐을 때 M2 완료다.

## 디버깅 함정들

M2 진행 중 마주친 자잘한 것들. 짧지만 기록 가치는 있다.

### PowerShell + JSON 인코딩

한국어 query를 HTTP body에 넣을 때 PowerShell 5.1이 UTF-8 처리를 제대로 못 한다. PowerShell 7로 가도 좀 낫지만 완벽하진 않다. 결국 Python httpx로 우회했다.

```python
import httpx
r = httpx.post(url, json={"query": "휴가 정책이 어떻게 되나요?"})
```

이게 답이라는 결론에 도달하는 데 30분 걸렸다.

### JWT_SECRET_KEY가 23바이트

```
JWT_SECRET_KEY=change-me-in-production
```

이거 23바이트다. HS256 권장 길이 32바이트 미달. PyJWT가 `InsecureKeyLengthWarning` 뱉는다. 동작은 한다. M4에서 Secrets Manager로 옮길 때 32바이트 random으로 같이 교체할 예정.

### Pydantic v2의 silent extras

`api/routes/query.py`에서 이런 케이스를 만났다.

```python
class DocumentResult(BaseModel):
    rerank_score: float | None = None  # 실제 필드

# 다른 곳에서:
DocumentResult(reranker_score=5.234)   # 오타 (er 더 들어감)
```

Pydantic v2 기본 동작은 모르는 kwarg를 조용히 무시한다. `reranker_score=5.234`가 silently dropped, 실제 필드 `rerank_score`는 default None 유지. 응답 JSON에 `"rerank_score": null`이 박힌다. 에러도 경고도 안 뜬다.

이런 종류 디버깅 1시간 들었다. `model_config = ConfigDict(extra="forbid")`을 모든 모델에 박아두면 잡힌다. M4에서 일괄 적용할 예정.

## 다음

M2가 끝났을 때 시스템은 작동했지만 retrieval이 cosine similarity 하나에만 의존한다는 게 약점이었다.

cosine은 빠르지만 "단어가 비슷하게 나오는가"만 본다. "진짜 이 query에 답하는가"는 못 본다. "휴가 정책" query에 "Project Delta Sprint Planning" 문서가 sim=0.396으로 top-3에 올라오는 false positive가 잦았다.

M3에서는 BGE Reranker v2-m3 (cross-encoder)를 도입한다. 그 과정에서 audit log 정확성 버그를 잡는다. 평가를 정량화하다가 시스템 자체의 policy-data schema drift까지 자동으로 surface 된다.

다음 글에서.

---

Repo: [github.com/parkjongmin-ddam/permission-aware-rag](https://github.com/parkjongmin-ddam/permission-aware-rag)