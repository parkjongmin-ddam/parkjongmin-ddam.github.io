---
title: "권한 인식 RAG 만들기 Section 3 — 마이그레이션, 배포, 그리고 권한 인식 생성"
categories: [RAG, IAM]
tags: [permission-aware-rag, schema-migration, Hugging-Face-Spaces, Supabase, GitOps, LLM, attorney-client-privilege]
description: "M4 전체 회고. Blog 2에서 미뤄둔 schema drift를 sensitivity 마이그레이션으로 해결하고, 클라우드에 배포하고, LLM 답변 생성을 권한 필터 뒤에 붙였다. 같은 질문에 사람마다 다른 답이 나오는 시스템."
---

지난 글 마지막에서 schema drift를 발견하고 두 갈래 길 중 Path B로 갔다. 매트릭스를 거짓으로 패치하지 않고, 발견을 시스템 문제로 문서화하고, 진짜 해결은 `docs/schema-drift-migration-plan.md`에 적어 M4로 미뤘다.

이 글은 그 미뤄둔 청구서를 갚는 이야기다. 그리고 거기서 멈추지 않는다. 마이그레이션 끝내고, 보안 좀 조이고, 클라우드에 올리고, 마지막에 LLM 답변 생성까지 붙였다. M4.0부터 M4.2까지 한 번에 다룬다.

미리 말하자면, Blog 2 끝에서 "AWS ECS Fargate 배포"라고 예고했었다. 그거 안 했다. 왜 말을 바꿨는지도 이 글에 있다.

## M4.0 — sensitivity 마이그레이션

문제부터 다시 짚자. M1에서 권한 매트릭스는 `sensitivity` 기준으로 설계했는데, 데이터(문서)는 `sub_type`(topic) 기준으로 분류돼 있었다. 정책은 "privileged 문서는 누가 보냐"를 따지는데, 문서엔 privileged인지 아닌지 적혀있질 않았다. 그 사이를 코드가 ad-hoc 매핑으로 메우고 있었다. 그게 drift다.

해결 방향은 분명했다. 문서에 `sensitivity` 필드를 정식으로 추가하고, 권한 룰을 sub_type-keyed에서 sensitivity-keyed로 바꾼다. 매트릭스와 데이터가 같은 축에서 만난다.

문제는 "어떻게 바꾸느냐"였다. 권한 시스템이다. 한 번에 다 바꾸면 어디서 깨졌는지 모른다. 깨지면 누군가 못 볼 문서를 보거나, 봐야 할 문서를 못 본다. 둘 다 사고다.

그래서 **dormant-first**로 갔다. 새 필드와 새 로직을 먼저 넣되, 죽은 상태로(dormant) 넣고, 검증되면 스위치를 켜는 방식이다. 7단계로 쪼갰다.

```
1. documents에 sensitivity 컬럼 추가 (NULL 허용, 아무도 안 읽음)
2. 45개 문서에 sensitivity 값 채우기 (public/internal/restricted/privileged)
3. sensitivity_rule 추가 — 단, RULES 등록 안 함 (dormant)
4. eval로 sensitivity_rule 단독 동작 검증 (등록 전에 미리 본다)
5. RULES에서 rbac_default → sensitivity_rule 교체
6. 옛 sub_type 기반 매핑 dead code 제거
7. eval 재실행 + 회귀 확인
```

각 단계가 독립 커밋이다. 5번에서 깨지면 4번으로 돌아가면 된다. 권한 마이그레이션은 이렇게 한다. IAM 운영하면서 ACL 정책 바꿀 때 한 번에 안 바꾸는 거랑 같은 이유다.

### F1이 떨어졌다, 근데 나빠진 게 아니다

마이그레이션 끝나고 eval 돌렸더니 F1이 0.560에서 0.530으로 떨어졌다.

처음엔 회귀인 줄 알았다. 권한 룰 바꿨더니 점수가 내려갔으니까. 근데 숫자를 뜯어보니 아니었다.

마이그레이션 전엔 평가 가능 케이스가 28개였다. 후엔 34개로 늘었다. sensitivity 필드가 정식으로 생기면서, 이전엔 ground truth를 만들 수 없어 빠졌던 케이스들이 평가 대상에 들어온 것이다.

```
before: 28 eligible, F1 0.560
after:  34 eligible, F1 0.530
```

평가가 더 엄격해진 거다. 더 많은, 더 까다로운 케이스를 채점하니 평균이 내려갔다. 같은 시험을 쉬운 28문제만 풀다가 어려운 6문제를 더한 셈이다. 점수는 내려가도 시스템은 더 정확해졌다.

이걸 "F1 0.560 달성"이라고 옛날 숫자로 자랑하고 싶은 유혹이 있었다. 안 했다. eval은 시스템을 정직하게 보려고 만든 거다. 숫자 좋아 보이려고 평가를 느슨하게 두는 건 본말전도다. Blog 2에서 schema drift를 패치 안 하고 문서화한 거랑 같은 원칙이다.

(reranker recall은 +0.007 개선됐다. 이건 진짜 개선이다.)

## M4.0.5 — 보안 하드닝

마이그레이션 끝나고 배포 들어가기 전에, 작은 정거장을 하나 만들었다. 0.5로 번호 매긴 이유는 기능 추가가 아니라 안전장치라서다.

두 가지를 넣었다.

**첫째, JWT 시크릿 키 검증.** mock JWT issuer가 개발 편의상 약한 기본 키(`change-me-in-production`)를 쓰고 있었다. 로컬에선 괜찮다. 근데 이걸 그대로 클라우드에 올리면 누구나 토큰을 위조한다. config validator를 추가했다.

```python
@model_validator(mode="after")
def _validate_jwt_secret(self) -> "Settings":
    is_dev = self.environment.lower() in {"development", "dev", "local", "test"}
    if is_dev:
        return self
    # production인데 기본 키거나 32바이트 미만이면 기동 거부
    if self.jwt_secret_key == _INSECURE_JWT_DEFAULT:
        raise ValueError("JWT_SECRET_KEY is still the insecure default...")
    if len(self.jwt_secret_key.encode("utf-8")) < 32:
        raise ValueError("JWT_SECRET_KEY must be at least 32 bytes...")
    return self
```

`ENVIRONMENT=production`이면 약한 키로는 앱이 아예 안 뜬다. fail-fast다. 운영 환경에서 인증이 약한 채로 조용히 돌아가는 것보다, 시작부터 죽는 게 낫다.

**둘째, Pydantic `extra="forbid"`.** 요청 모델에 정의 안 된 필드가 들어오면 무시하는 게 기본 동작이다. 근데 권한 시스템에선 이게 위험하다. 오타난 파라미터나 누군가 끼워넣은 필드가 조용히 무시되면, 의도와 다르게 동작해도 모른다. 5개 모델에 `ConfigDict(extra="forbid")`를 박았다. 모르는 필드 오면 422로 거부한다.

이 두 개가 M4.1 배포에서 바로 진가를 발휘한다. 다음 절에서 나온다.

## M4.1 — 클라우드 배포

Blog 2에서 "AWS ECS Fargate"라고 했다. 막상 견적 내보니 안 맞았다.

이 시스템은 BGE-M3 임베딩 모델과 BGE Reranker를 메모리에 올린다. 둘이 합쳐서 4GB가 넘는다. ECS Fargate에서 이 메모리를 상시 띄우면 월 190달러쯤 나온다. 사이드 프로젝트 데모에 매달 190달러는 과하다. 면접에서 보여줄 용도인데, 면접관이 한 번 들어와 보고 끝일 시스템에 그 돈을 태울 이유가 없다.

방향을 틀었다. **Hugging Face Spaces (Docker) + Supabase.** 둘 다 무료 티어로 충분하다.

- HF Spaces: Docker SDK로 FastAPI 앱을 통째로 띄운다. CPU 16GB 무료. 모델 메모리가 여기 들어간다.
- Supabase: managed Postgres + pgvector. 문서와 임베딩, audit log가 여기 산다.

컴퓨트(모델·정책 엔진)는 HF, 상태(문서·벡터)는 Supabase. 깔끔하게 갈렸다.

말 바꾼 게 부끄러운가 하면 아니다. 처음 계획이 틀렸으면 고치는 거다. AWS는 나중에 이력서용으로 따로 올릴 수 있다(크레딧도 있다). 지금 필요한 건 "작동하는 데모를 무료로 24시간 띄우는 것"이고, 그건 HF+Supabase가 더 맞다.

### Supabase RLS를 안 쓴 건 의도다

Supabase 쓴다고 하면 으레 묻는다. "RLS(Row Level Security) 쓰지 그랬어?"

안 썼다. 의도적으로. RLS는 row 단위 boolean 필터다. "이 row를 이 사용자가 보는가"를 SQL 정책으로 건다. 근데 우리 권한 모델은 6개 룰이 우선순위를 갖고 first-match로 평가된다. audit_rule이 sensitivity_rule보다 먼저 봐야 하고, 감사인은 감사 범위 문서를 보되 privileged 소송 문서는 못 본다(attorney-client privilege). 이런 우선순위 있는 조건부 정책을 RLS로 표현하는 건 가능은 해도 끔찍하다.

그래서 정책 엔진은 애플리케이션 레이어(`permission/policy.py`)에 두고, DB는 순수 저장소로 썼다. 이건 약점이 아니라 설계 결정이다. 권한 로직이 한 곳(코드)에 모여있어 테스트하고 감사하기 쉽다. 면접에서 이걸 물으면 오히려 할 말이 많다.

### GitOps — push 한 번으로 배포

배포 방식은 GitOps로 갔다. GitHub `main`에 push하면 GitHub Actions가 HF Space로 force-push하고, HF가 Docker 빌드해서 띄운다.

```
git push origin main
  → GitHub Actions (.github/workflows/deploy.yml)
  → HF Space force push
  → Docker build → 모델 로드 → Running
```

GitHub이 단일 진실의 원천이다. HF Space를 직접 건드릴 일이 없다. 비밀값(DB URL, JWT 키, Anthropic 키)은 HF Space Secrets로 주입한다. 이미지에도 git에도 안 들어간다.

배포하면서 잔버그를 몇 개 잡았다. `session.py`의 `close_pool()`이 로직이 뒤집혀서 풀을 영영 안 닫고 있었고(early return 버그), Dockerfile에서 torch를 CPU 전용으로 받게 해서 이미지를 5GB에서 1.5GB로 줄였다. HF Space의 YAML front matter가 60자 넘는 short_description를 거부해서 두 번 리젝당하기도 했다. 이런 건 배포 안 해보면 모른다.

### 그래서 — 같은 질문, 다른 결과

배포 끝나고 라이브로 검증했다. 같은 질의 `"ExternalCo dispute litigation"`을 두 사람으로 던졌다.

임원(`user_exec_001`):
```
문서: [DOC-044, DOC-040, DOC-012]   ← DOC-044 1순위
allowed: 9 / denied: 6
```

감사인(`user_aud_001`):
```
문서: [DOC-040, DOC-022, DOC-012, DOC-032, DOC-023]   ← DOC-044 없음
allowed: 13 / denied: 2
```

DOC-044는 ExternalCo 소송 문서다. privileged로 분류돼 있다. 임원은 본인이 그 소송 당사자라 `parties_rule`로 본다. 감사인은 감사 범위(`audit_engagement_id`) 내 문서를 더 많이 보지만(allowed 13), DOC-044만은 `audit_rule`이 막는다. 감사라도 attorney-client privilege는 못 뚫는다.

같은 질문, 같은 파라미터, 다른 신원, 다른 결과. 이게 클라우드에서 돈다. 여기까지가 검색이다. 진짜 재미는 그 다음이다.

## M4.2 — 권한 인식 생성

여태 만든 건 "권한 필터링된 검색"이다. 사용자가 볼 수 있는 문서 목록을 돌려준다. 근데 RAG의 G는 Generation이다. 답변을 생성해야 한다.

여기서 대부분의 RAG가 사고를 친다. 검색은 권한 필터링해놓고, 정작 LLM 프롬프트에 권한 없는 문서를 슬쩍 끼워넣어서 답변으로 누출시킨다. 검색 단계의 보안이 생성 단계에서 무너진다.

이걸 막는 방법은 단순하다. **권한 필터를 LLM 앞에 둔다.**

```
검색 → 재순위 → 권한 필터(can_read) → 통과한 문서만 → LLM
                      ↑                              ↑
                  여기서 막힘                  여기엔 통과한 것만
```

`/answer` 엔드포인트를 새로 만들었다. `/query`(검색만)는 그대로 두고. `/answer`는 `retrieve()`를 그대로 재사용한 뒤, 그 결과 중 **허용된 문서만** Claude에게 넘긴다.

```python
# api/routes/answer.py (핵심)
result = await retrieve(principal, request.query, ...)
# 허용된 것만 LLM 컨텍스트로
context_docs = result.allowed[:request.top_k]
answer = await generate_answer(request.query, context_docs)
```

`generate_answer`는 허용 문서가 0개면 LLM을 부르지도 않고 거부한다. 부를 이유가 없다. 볼 수 있는 게 없으니까.

생성 모델은 Claude Sonnet 4.6으로 했다. 이 작업—권한 필터링 끝난 소수 문서를 읽고 인용 달아 답하기—은 추론 난이도가 낮다. Opus 쓸 이유가 없다. 이 프로젝트의 가치는 답변 문장력이 아니라 생성 *앞단*의 권한 필터링이다. Sonnet이 비용·속도 면에서 맞다.

### 누출이 구조적으로 불가능하다

이론은 됐고, 실제로 막히는지 봤다. 아까 그 질의를 `/answer`로 다시 던졌다.

임원에게 온 답변(요약):
> ExternalCo가 미지급 컨설팅비 **KRW 1.2억**을 청구한 상업 분쟁. BWCorp 인정 한도 0.7억. 위험 평가 테이블(합의 가능 영역 0.9~1.0억, 최악 1.35억). 2026-11-15 사전 조정 예정. 합의 시 임원+Legal Director 공동 결재 필요. **본 사안은 attorney-client privilege 대상.** — 인용 [DOC-044, DOC-040, DOC-012]

감사인에게 온 답변(요약):
> 계약상 준거법(대한민국법)과 관할(서울중앙지법). 5년 비밀유지 의무. 보안 인시던트 INC-2026-09-003에 ExternalCo 인력 연루(1.2GB 데이터 유출 시도, 차단됨). 법무팀이 litigation 가능성 검토 중. — 인용 [DOC-040, DOC-012]

감사인 답변을 보라. 소송 금액(1.2억)이 없다. 위험 평가가 없다. 합의 전략이 없다. attorney-client privilege 언급도 없다. DOC-044에 있던 내용이 한 글자도 안 섞였다.

LLM이 거짓말을 잘해서가 아니다. **DOC-044를 애초에 못 봤기 때문이다.** 권한 필터가 LLM 앞에서 잘랐으니, Claude의 컨텍스트엔 그 문서가 들어간 적이 없다. 못 본 걸 누출할 방법은 없다.

이게 "프롬프트에 조심해서 권한 없는 내용 안 넣기"와 다른 점이다. 그건 사람이 실수하면 뚫린다. 이건 파이프라인 순서가 보장한다. 권한 필터를 거치지 않은 문서는 generate_answer 함수에 도달할 경로 자체가 없다.

여기서 M4.0.5의 `extra="forbid"`가 빛난다. 누가 `/answer`에 이상한 파라미터로 컨텍스트를 주입하려 해도 422로 막힌다. 그때 넣은 안전장치가 생성 단계에서 일한다.

## M4 끝내고 보니

```
✓ M4.0:   sensitivity 마이그레이션 (dormant-first 7단계)
✓ M4.0.5: JWT validator + extra=forbid 보안 하드닝
✓ M4.1:   HF Spaces + Supabase 배포 (GitOps) + 권한 차이 라이브 검증
✓ M4.2:   /answer — 권한 필터 뒤의 LLM 생성, 누출 구조적 차단
```

Blog 2에서 미뤄둔 schema drift를 갚았다. 갚는 김에 배포하고 생성까지 붙였다. 시작은 "검색되는 문서 목록"이었는데, 끝은 "누가 묻느냐에 따라 권한 범위 안에서 답하는 시스템"이 됐다.

돌아보면 M4의 진짜 교훈은 두 개다.

하나, F1이 떨어진 걸 회귀로 오해할 뻔했다. 숫자만 보면 나빠졌는데, 들여다보니 평가가 정직해진 거였다. 측정값이 나빠 보일 때 측정 자체를 의심하는 건 위험하지만, 측정 *조건*이 바뀌었는지는 봐야 한다.

둘, 권한은 단계마다 다시 보장해야 한다. 검색에서 필터링했다고 생성에서 안전한 게 아니다. 각 단계가 권한을 통과시킨 것만 다음 단계로 넘긴다는 불변식을, 코드 구조로 강제해야 한다. 주석으로 "여기 조심"이라 적는 걸로는 안 된다.

다음은 M5. README는 이미 갈아엎었고(이 시리즈 쓰면서 실제 구현이랑 안 맞는 부분이 자꾸 걸려서 결국 전면 재작성했다), 남은 건 데모 영상과 트레이싱이다. Langfuse를 붙여서 "권한 필터가 LLM 앞에서 무엇을 걸렀는지"를 trace로 시각화할 생각이다. 말로 설명하는 것보다 trace 하나 보여주는 게 빠르니까.

그 얘긴 다음 글에서. 시리즈를 여기서 닫을 수도 있지만, 트레이싱까지 붙이면 진짜 완성이라, 한 편 더 갈 것 같다.

---

Repo: [github.com/parkjongmin-ddam/permission-aware-rag](https://github.com/parkjongmin-ddam/permission-aware-rag)