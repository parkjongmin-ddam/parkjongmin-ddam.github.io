---
title: "권한 인식 RAG 만들기 Select 2_eranker, audit log 버그, schema drift"
categories: [RAG, IAM]
tags: [permission-aware-rag, BGE-Reranker, RAGAS, audit-log, schema-drift, compliance]
description: "BGE Reranker v2-m3 도입과 평가 과정에서 발견한 두 가지: audit log 정확성 버그와 policy-data schema drift."
---

지난 글에서 M1, M2로 권한 인식 RAG의 뼈대를 잡았다. retrieval이 작동하고 권한 룰 6개가 first-match-wins으로 동작한다. 근데 retrieval이 cosine similarity 하나에만 의존하니까 false positive가 잦다.

M3에서는 BGE Reranker v2-m3를 도입한다. 진행하다가 두 가지를 발견했다.

1. 권한 평가와 디스플레이 truncation이 한 레이어에 섞여서 발생한 audit log 정확성 버그
2. 평가 하네스가 자동으로 surface한 시스템의 schema drift

이 글은 그 두 발견의 디버깅 일지다.

## BGE Reranker 도입

기존 retrieval은 BGE-M3 임베딩으로 cosine top-K를 가져오는 단순 구조였다. cross-encoder를 두 번째 단계로 넣는 이유는 명확하다.

- **Bi-encoder (BGE-M3)**: query와 document를 독립적으로 임베딩 → cosine similarity. 빠르다. 둘 사이 맥락은 못 본다.
- **Cross-encoder (BGE Reranker v2-m3)**: query와 document를 함께 트랜스포머에 넣고 attention으로 점수. 정확하다. 느리다.

전형적 패턴이다. bi-encoder로 top-30 좁히고 cross-encoder로 top-15 정밀 재랭킹.

```python
# retrieval/reranker.py
from functools import lru_cache
from sentence_transformers import CrossEncoder

MODEL_NAME = "BAAI/bge-reranker-v2-m3"

@lru_cache(maxsize=1)
def get_reranker():
    return CrossEncoder(MODEL_NAME)

def rerank(query, documents):
    model = get_reranker()
    pairs = [(query, doc["body"]) for doc in documents]
    scores = model.predict(pairs)
    return sorted(
        zip(documents, [float(s) for s in scores]),
        key=lambda x: x[1],
        reverse=True,
    )
```

retriever.py에 단계 추가하면 파이프라인은 이렇게 된다.

```
embed_query → pgvector HNSW top 30 → BGE Reranker top 15 → can_read() filter → top_k
```

첫 실행 결과에서 reranker가 일한다는 게 확인됐다. "휴가 정책이 어떻게 되나요?" query 결과:

| Doc | cosine sim | rerank score |
|---|---|---|
| DOC-002 Leave Policy v3.2 | 0.662 | +0.681 |
| DOC-001 Employee Handbook | 0.465 | +0.130 |
| DOC-025 Project Delta Sprint Planning | 0.396 | +0.002 |

cosine으로는 DOC-001과 DOC-025 차이가 0.07. 비슷해 보인다. 근데 cross-encoder 기준 0.130 vs 0.002. 65배 차이. "휴가 정책 질문에 Sprint Planning은 우연한 단어 매칭일 뿐"이라는 걸 모델이 정확히 판단한다.

여기까지는 평범한 reranker 도입 이야기. 진짜 흥미로운 건 그 다음에 일어났다.

## Retrieved: 13이 어디서 나왔는가

reranker 도입 후 응답에 자꾸 `Retrieved: 13`이 떴다.

새 파이프라인 계산상 `top_k=3`, `oversample_factor=10` → `fetch_limit=30`, rerank로 15까지 좁히고, 그 다음 권한 필터. 기대값은 15여야 한다.

근데 13이다.

처음엔 pgvector HNSW의 `ef_search` 한계인 줄 알았다. 45개 문서 규모에서 그래프 sparse하면 LIMIT 30 줘도 13만 반환할 수 있으니까. 디버그 스크립트 만들어서 직접 SQL 돌려봤다.

```python
for limit in [5, 10, 15, 20, 30, 45, 50, 100]:
    await cur.execute(
        "SELECT COUNT(*) FROM (SELECT id FROM documents "
        "ORDER BY embedding <=> %(q)s LIMIT %(l)s) sub",
        {"q": query_emb, "l": limit},
    )
```

결과: LIMIT 30이면 정확히 30개 반환. HNSW는 정상이었다. 가설 폐기.

retriever.py에 5줄짜리 debug print 박고 다시 돌렸다.

```
[debug] top_k=3, oversample=10, fetch_limit=30, use_reranker=True, rerank_keep=15
[debug] SQL fetched 30 rows
[debug] triples before rerank: 30
[debug] reranked & truncated to keep: 15
[debug] triples after rerank stage: 15
[debug] allowed=5, denied=10
```

allowed=5, denied=10. 합치면 15. 파이프라인은 정상.

근데 응답 `total_retrieved`는 13이다. 어디서 2개가 사라졌나.

```python
# retriever.py 마지막 줄
return RetrievalResult(allowed=allowed[:top_k], denied=denied)
#                              ^^^^^^^^^^^^^^^
#                              여기서 top_k=3으로 자름
```

찾았다. 5개 allowed 중 3개만 살리고 2개 버린 것. `total_retrieved = len(result.allowed) + len(result.denied) = 3 + 10 = 13`.

미스터리는 해결됐다. 근데 여기서 ML 엔지니어와 IAM 엔지니어의 시각이 갈린다.

ML 관점: top-K UX truncation이니까 정상. 사용자에게 보여줄 건 3개고 나머진 버려도 됨.

IAM 관점: 이건 audit log 정확성을 깨는 심각한 버그다.

audit_log 코드 다시 보자.

```python
await write_audit_log(
    user_id=principal.user_id,
    query=request.query,
    granted_doc_ids=[d.id for d in result.allowed],   # 3개만!
    denied_doc_ids=[d.id for d in result.denied],
    ...
)
```

사용자는 시스템이 보기에 5개 문서에 접근 권한이 있었다. 권한 정책이 그렇게 결정했다. 근데 audit_log엔 3개를 grant했다고 기록된다.

이게 왜 문제인가. SOX, GDPR, ISO 27001 컴플라이언스 감사에서는 "이 시점에 이 사용자가 어떤 데이터에 접근 가능했나"가 핵심 질문이다. UI에서 3개 보여줬다는 사실은 반드시 audit log에 정확히 5개 grant로 기록되어야 후속 추적이 가능하다.

IAM 운영하면서 가장 자주 본 사고 패턴이 "권한은 줬는데 로그가 안 남아서 조사 불가능"이다. RAG 시스템이라고 다를 게 없다.

해결은 layer 책임 분리다.

```python
# retriever.py — truncation 제거
return RetrievalResult(allowed=allowed, denied=denied)  # 전체 grant 기록

# api/routes/query.py — display-time truncation 분리
displayed = result.allowed[:request.top_k]

await write_audit_log(
    ...
    granted_doc_ids=[d.id for d in result.allowed],  # 전체 5개 기록
    ...
)

return QueryResponse(
    results=[DocumentResult(...) for d in displayed],  # 3개만 표시
    total_displayed=len(displayed),
    total_allowed=len(result.allowed),
)
```

`total_displayed ≠ total_allowed`인 게 정상이고 이걸 명시적으로 응답에 노출하는 게 IAM 시스템의 투명성이다. 권한 평가는 retrieval 레이어, 디스플레이 결정은 presentation 레이어. 단일 책임 원칙의 IAM 버전.

## 평가 — 얼마나 좋아졌나

reranker가 감으로는 좋아 보였다. 얼마나 좋아진 건지 숫자가 필요했다.

RAGAS 패턴 따라 precision@K, recall@K를 측정하기로 했다. 핵심 설계 결정 하나: ground truth를 어떻게 정의할 것인가.

쉬운 방법은 문서 메타데이터의 `expected_readers` 필드를 쓰는 거다. M1에서 만들어둔 거니까. 근데 이건 "권한 정책이 누구를 허용해야 하는지에 대한 사람의 추정"이지 실제 정책과는 다르다. 정책에는 RBAC default + ABAC rules 6개가 복합 작용하니까.

답은 명확하다. 시스템의 실제 권한 함수 `can_read()`를 직접 호출해 ground truth를 계산한다.

```python
def compute_truth(persona_id, relevant_doc_ids, docs):
    """Truth = 주제 관련 + 실제 정책이 허용하는 문서"""
    principal = get_principal(persona_id)
    truth = set()
    for doc_id in relevant_doc_ids:
        doc = docs.get(doc_id)
        if doc and can_read(principal, doc).is_allowed:
            truth.add(doc_id)
    return truth
```

이렇게 하면:
- `relevant_docs`는 주제 관련성만 사람이 라벨링
- `truth = relevant ∩ allowed`는 시스템이 자동 계산
- 평가는 retrieve가 truth를 잡아냈나만 측정

테스트 케이스는 6개로 시작했다가 18개로 확장했다. 6개로는 통계 신뢰도가 약했고 권한 룰 6개 중 `parties_rule`이 한 번도 테스트되지 않았다.

확장 시 의도:
- 모든 6개 권한 룰 cover (`parties_rule` 추가)
- 미사용 페르소나 (emp_003, exec_001) 활성화
- 19개 sub_type 중 13개 cover (카테고리 다양성)
- 양의/음의 케이스 균형 (받아야 할 사람이 받는가 + 차단되어야 할 사람이 차단되나)

최종 18 케이스 × 평균 2.9 페르소나 = 52 persona-case 페어.

### 결과

평가 돌렸다. Eligible 케이스(truth가 비어있지 않은 것) 52 중 28개.

```
metric         w/o rerank    w/ rerank     delta
precision@5    0.302         0.390         +0.088   (+29% 상대)
recall@5       1.000         0.991         -0.009   (단일 케이스 손실)
F1             0.464         0.560         +0.096   (+21% 상대)
```

해석하면.

recall 손실은 사실상 한 케이스다. TC-005 (보안 사고 query) × `user_sec_001` 케이스에서 reranker가 DOC-013 (Insider Threat)을 top-5 밖으로 밀어냈다. 나머지 27개 케이스는 recall 1.0 유지. reranker가 coverage를 거의 그대로 유지하면서 precision만 끌어올리는 이상적 trade-off 곡선이다.

precision 개선의 일부는 N<K artifact다. 짚어야 한다.

```
TC-004 × user_emp_001 ("내 비용 보고서 확인" query):
  Truth: DOC-030 (1개)
  W/o rerank: [DOC-030, DOC-025, DOC-006, DOC-001, DOC-021]    → P=0.20 (1/5)
  W/  rerank: [DOC-030]                                          → P=1.00 (1/1)
```

reranker ON에서 시스템이 1개만 반환했고 그게 정답이라 precision=1.0이 됐다. 5개 중 1개 맞춘 것과 1개 중 1개 맞춘 것은 같은 정답률이지만 precision 분모가 다르다.

이 부분은 caveat로 짚고 가야 한다. precision 분모가 작은 케이스에서 trivially 올라간 효과가 섞여 있다. 우리 시스템은 의도적으로 약한 후보로 padding하지 않기 때문에 (top-15 rerank 후 권한 필터 통과한 것만 표시) precision@K가 부분적으로는 padding 정책 차이를 측정하고 있다는 뜻이다.

이걸 분리하려면 NDCG@5나 MAP 같은 padding-invariant metric이 필요하다. future work으로 적어뒀다.

## 평가가 발견한 schema drift

여기까지가 reranker 도입 + 정량 측정 이야기다. 일반 RAG 프로젝트의 종착점이다. 근데 18 케이스 평가 결과를 자세히 보다 이상한 패턴이 눈에 띄었다.

```
[TC-013] password policy and security guidelines × user_emp_003
   Truth (0): (empty — persona has no relevant access)
[TC-014] microservices architecture × user_emp_001 (engineer)
   Truth (0): (empty — persona has no relevant access)
[TC-016] 직원 채용 프로세스 × user_hrs_001 (HR specialist)
   Truth (0): (empty — persona has no relevant access)
[TC-017] marketing campaign × user_emp_002 (marketing dept)
   Truth (0): (empty — persona has no relevant access)
```

이게 다 의도된 거부일까.

- 일반 직원이 회사 password policy 못 본다? 실제 조직에선 의무 숙지 대상이다.
- 엔지니어가 microservices architecture 못 본다? 일하려면 필요하다.
- HR specialist가 채용 프로세스 못 본다? 본인 업무 영역이다.
- 마케팅 부서 직원이 마케팅 캠페인 못 본다? 직장 그만둬야 한다.

뭔가 잘못됐다. rules.py를 열어봤다.

```python
ROLE_DEFAULTS = {
    "employee": frozenset({
        "hr.policy", "hr.handbook",
        "tech.runbook", "tech.documentation",
        "marketing.public",
        "legal.public",
    }),
    "team_lead": frozenset({
        "hr.policy", "hr.handbook",
        ...
    }),
    ...
}
```

매트릭스의 sub_type들 (`hr.handbook`, `tech.documentation`, `marketing.public`, `marketing.internal`, `legal.public`, `security.audit`, `security.training`, `finance.forecast`). 이건 sensitivity 기반 분류 체계다. "이 문서는 어디까지 노출되는가"를 기술한다.

실제 데이터(documents.yaml) 열어보면:

```yaml
- id: DOC-001
  sub_type: hr.policy
- id: DOC-008
  sub_type: hr.recruitment
- id: DOC-016
  sub_type: tech.architecture
- id: DOC-034
  sub_type: marketing.campaign
- id: DOC-042
  sub_type: legal.regulatory
```

데이터의 sub_type들은 topic 기반이다. "이 문서는 무엇에 관한 것인가"를 기술한다.

두 layer가 서로 다른 분류 축으로 설계됐다.

매트릭스에 적힌 `hr.handbook`, `marketing.public` 같은 sub_type은 데이터에 존재하지 않는다. dead entries. 어떤 문서와도 매칭 안 됨. 반대로 데이터의 `hr.recruitment`, `tech.architecture`, `marketing.campaign` 같은 sub_type은 매트릭스 어디에도 안 적혀있다. 어떤 role도 default access 못 받음.

세어 보니 매트릭스 9개 entry가 dead, 데이터 13개 sub_type이 default 권한 없이 떠있는 상태였다.

**policy-data schema drift.** IAM 시스템에서 가장 흔한 안티패턴 중 하나다. 정책 작성자와 데이터 분류 담당자가 서로 다른 시점에 다른 추상화 수준에서 작업하면 발생한다.

(M1에서 topic-based로 가기로 결정했을 때 미래에 부메랑처럼 돌아오는 거였다. 이전 글에서 떡밥 던졌던 그거다.)

여기서 두 갈래 길이 있었다.

**Path A**: 매트릭스를 적당히 패치한다. `marketing.public` → `marketing.research`로 단순 치환하거나 미싱 sub_type에 ad-hoc grant 추가. eval 결과는 깔끔해진다. 본질적 일관성 문제는 묻힌다.

**Path B**: 매트릭스를 그대로 두고 발견 자체를 시스템 문제로 문서화한다. 진짜 해결은 sensitivity 필드를 문서에 추가하는 schema migration으로 미루고 그 migration plan을 작성한다.

Path B로 갔다. 테스트 결과를 정상화하기 위한 retrofit은 시스템을 거짓되게 만든다. 발견된 drift는 진짜고 평가가 자동으로 surface한 게 진짜 가치다.

대신 `docs/schema-drift-migration-plan.md`에 production migration 계획을 정식 문서로 작성했다. Context / Decision / Target Schema / Migration Steps / Risks / Rollback / Out of Scope. 실제 회사에서 production system 마이그레이션할 때 쓰는 양식. M4 단계로 deferred.

rules.py 매트릭스 위에는 inline 코멘트로 "이 매트릭스의 한계를 인지하고 있고 해결 계획은 별도 문서에 있다"를 명시했다.

```python
# Role-based default access matrix.
#
# Status: legacy implementation — schema drift acknowledged.
# See docs/schema-drift-migration-plan.md for the production migration
# plan (sensitivity-field based redesign, deferred to M4+).
```

## M3 끝내고 보니

```
✓ M3.1: BGE Reranker v2-m3 + audit log fix
✓ M3.2: A/B compare 5 케이스 정성 분석
✓ M3.3: RAGAS-style eval 18 케이스 × 52 페어 + F1 +0.096
✓ M3.3 보너스: schema drift 자동 발견 + production migration plan
```

reranker 도입은 평범한 RAG 작업이다. 근데 그 과정에서 audit log 버그를 발견하고 평가 시스템이 schema drift를 surface해줬다.

다음은 M4. schema drift migration 먼저 하고 (계획 그대로 따라가면 됨) 그 다음 AWS ECS Fargate 배포. M5에서 README + 데모 + 시리즈 마감.

---

Repo: [github.com/parkjongmin-ddam/permission-aware-rag](https://github.com/parkjongmin-ddam/permission-aware-rag)