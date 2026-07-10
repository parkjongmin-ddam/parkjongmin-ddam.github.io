---
layout: single
title: "[ADFS] ADFS와 PKCE — 실무 관행과 RFC 9700 권고 사이의 간극"
excerpt: "ADFS에 OIDC/OAuth 앱을 등록할 때 'OIDC=Server, OAuth=Native'가 프로토콜 규칙인지 관행인지 표준까지 추적한 기록. 앱 유형과 프로토콜이 직교한다는 점, openid가 id_token 스위치라는 점, 그리고 RFC 9700의 PKCE 권고와 ADFS 실제 구현 사이의 간극을 실측으로 닫는 방법까지 정리."
date: 2026-07-10
categories: [Infra, Identity]
tags: [adfs, oauth2, oidc, pkce, rfc9700, confidential-client, application-group, 인증, 표준]
---

## 들어가며

ADFS에서 OIDC랑 OAuth를 등록할 때 앱 유형을 뭘로 골라야 하나? 실무에선 OIDC=Server application, OAuth=Native application으로 해왔는데, 이게 프로토콜이 정한 규칙인지 아니면 그냥 관행인지 애매했음. Python 샘플코드로 인증 3종을 테스트하려고 앱을 등록하다가 이 지점에서 멈칫했고, 이참에 표준까지 근거를 추적해봤음.

> 환경값은 예시로 치환함. federation 이름 `sts.lab.local`, CA는 `lab-ISCA01-CA` 등.

---

## 1. 실무에서 써온 방식: "OIDC=Server, OAuth=Native"

실무에서 애플리케이션을 ADFS Application Group에 등록할 때, OIDC 웹앱은 "Server application accessing a web API"(secret 발급 가능)로, OAuth는 "Native application accessing a web API"로 만들곤 했음. 그리고 Permitted scopes에서 `openid` 체크 유무로 OIDC냐 OAuth냐가 갈린다고 이해했음.

이 이해는 **부분적으로 맞고, 한 군데 오해가 있었음.**

---

## 2. 앱 유형과 프로토콜은 직교한다

MS 공식 문서(AD FS OpenID Connect/OAuth concepts)를 근거로 확인한 핵심:

**앱 유형(Server/Native)을 가르는 진짜 기준은 프로토콜이 아니라 "secret을 안전하게 보관할 수 있느냐"임.**

- **Server application = confidential client**: secret(또는 인증서)으로 자신을 인증. 서버 백엔드가 secret을 숨길 수 있을 때.
- **Native application = public client**: secret을 숨길 수 없음(SPA·모바일·데스크톱). 그래서 PKCE로 코드 교환을 보호.

**프로토콜(OIDC/OAuth)을 가르는 기준은 별개임.** MS 문서가 명확히 말함 — 관리자가 리소스에 scope를 openid로 구성하고 클라이언트가 요청에 `scope=openid`를 보내야 ADFS가 id_token을 발급함. openid가 있으면 OIDC(id_token), 없으면 순수 OAuth(access_token만)임.

즉 openid 체크는 OIDC냐 OAuth냐를 가르는 게 아니라, **id_token을 발급할지 켜는 스위치**임. 여기서 실무상 흔한 함정이 나옴 — 순수 OAuth(access_token만)로 쓰려는 앱에 openid를 체크하면, 의도와 달리 id_token까지 발급되어 사실상 OIDC로 동작함. **순수 OAuth가 목적이면 openid scope는 빼야 하고, 켜면 Native든 Server든 OIDC가 됨.** 앱 유형과 프로토콜은 **직교하는 두 축**이라, Native+OIDC도 Server+순수OAuth도 다 성립함.

이 기준으로 보면 실무에서 OIDC를 Server로, OAuth를 Native로 등록한 것도 설명됨. OIDC 웹앱은 서버 백엔드가 있어 secret 보관이 되고, OAuth 대상은 SPA/네이티브라 secret을 못 숨김. 프로토콜이 앱 유형을 강제한 게 아니라, 각 앱의 secret 보관 능력이 앱 유형을 결정한 것.

---

## 3. 진짜 개정 지점: PKCE

여기서 실무 시절과 현재 표준이 갈리는 지점을 발견했음.

**과거 관행**: confidential(Server) client는 secret만으로 인증하고 PKCE는 안 씀. PKCE는 secret 못 숨기는 public client용이라고 알았음.

**현재 표준 (RFC 9700, 2025년 1월 IETF 발행)**: authorization code flow에서

- **public client → PKCE 필수(MUST)**
- **confidential client → PKCE 권장(RECOMMENDED)**

즉 Server app이라도 secret + PKCE를 병행하는 게 현재 권고임. "secret 쓰면 PKCE 불필요"라는 내 기억은 그 시절엔 맞았고, 지금은 "둘 다"가 defense-in-depth 관점의 권고임.

주의할 강도 — confidential에 대해서는 **MUST가 아니라 RECOMMENDED**임. 그러니 secret만 쓰는 과거 방식이 지금도 "위반"은 아님. 다만 PKCE를 곁들이면 코드 주입 공격에 한 겹 더 방어된다는 것.

> PKCE 연혁: 2015 RFC 7636(모바일용 선택적 도입) → 2025 RFC 9700(public 필수/confidential 권장) → OAuth 2.1 draft(code flow 전체 필수화 방향).

---

## 4. ADFS라는 온프렘 제품의 간극

여기가 이 글의 핵심임. RFC는 IETF 표준이지 MS 제품 문서가 아님. **RFC 권고와 ADFS 실제 구현은 별개**라 따로 확인해야 했음.

**확인된 것 (MS Learn):** ADFS는 **Windows Server 2019부터** OAuth authorization code grant에 대해 PKCE를 지원함. 다만 MS 문서는 PKCE를 **public client의 코드 가로채기 완화** 맥락으로만 설명함 — "confidential client도 PKCE를 쓰라/받는다"는 명시가 없음. 즉 RFC(confidential에 권장)와 ADFS 문서 사이에 공백이 있음.

**현실 함정 (Microsoft Q&A):** ADFS(그리고 Entra조차)는 PKCE를 실제로 지원하면서도 discovery 문서(`.well-known/openid-configuration`)에 `code_challenge_methods_supported`를 광고하지 않는 것으로 알려져 있음. RFC 8414상 이 필드가 없으면 미지원으로 봐야 하지만, ADFS는 예외임. 이 필드에 의존하는 클라이언트 라이브러리는 PKCE를 건너뛸 수 있음.

**결론: "confidential + PKCE"가 ADFS에서 실제로 동작하는지는 MS 공식 문서로 확정할 수 없고, 랩에서 직접 던져보는 것 외엔 방법이 없음.** 문서 추적의 마지막 한 조각은 문서가 아니라 실측으로만 닫힘.

---

## 5. 그래서 어떻게 검증하나

이 조사를 코드로 옮겨, 한 Application Group에 두 클라이언트를 등록하고 조합을 실측하는 구성으로 만들었음.

- **Server application (confidential)** — OIDC 로그인 + Client Credentials(S2S) 공용. `SERVER_USE_PKCE` 플래그로 PKCE 병행 여부를 토글.
- **Native application (public)** — PKCE 로그인. secret 없음.

Server+PKCE 실험의 가능한 결과 세 가지:

1. **성공** → WS2019+ ADFS가 confidential+PKCE를 받아줌 (RFC 9700 권고를 온프렘에서 충족)
2. **id_token은 나오지만 PKCE 무시** → ADFS가 code_challenge를 무시 (동작하나 방어는 secret만)
3. **거부(invalid_client 등)** → 이 빌드는 조합을 안 받음 → secret-only로 전환

어느 결과든 데이터로 남음. discovery의 PKCE 광고 여부(`code_challenge_methods_supported`)를 먼저 찍고, 없어도 미지원 단정하지 않고 실제 flow로 최종 판단하는 게 핵심 — 위 Q&A 함정을 피하는 순서임.

---

## 정리 — 핵심 교훈

1. **앱 유형과 프로토콜은 직교한다.** Server/Native는 secret 보관 능력으로, OIDC/OAuth는 openid scope 유무로 각각 결정됨. 실무 관행이 맞았어도 이유는 다를 수 있음 — 근거를 추적하면 "왜"가 정확해짐.

2. **openid는 프로토콜 선택이 아니라 id_token 스위치임.** openid를 체크하면 그 앱은 id_token을 받아 OIDC로 동작함. 순수 OAuth(access_token만)가 목적이라면 openid scope를 빼야 함 — 켜두면 Native든 Server든 의도와 무관하게 OIDC가 됨.

3. **표준은 개정된다.** confidential client에 PKCE를 곁들이는 건 과거엔 안 하던 것이고 지금은 RFC 9700이 권장함. "그때 맞았다"가 "지금도 맞다"를 보장하지 않음.

4. **RFC 권고 ≠ 제품 구현.** ADFS는 온프렘이라 최신 OAuth 권고를 그대로 따르지 않을 수 있음. PKCE 지원은 WS2019+지만 confidential+PKCE의 실제 거동은 문서로 확정 불가 → 실측이 답.

5. **discovery의 PKCE 광고 부재에 속지 말 것.** ADFS/Entra는 지원하면서도 `code_challenge_methods_supported`를 안 실음. 메타데이터로 판단하지 말고 flow를 던져볼 것.

확인해보니 실무 관행 자체는 대체로 옳았음. 다만 "왜 그렇게 하는지"의 이유가 프로토콜이 아니라 secret 보관 능력이었다는 것, 그리고 PKCE 권고가 그새 바뀌었다는 것 — 이 둘을 정확히 알게 된 게 이번 소득임. ADFS는 실측으로 확인하는 일이 남았고, 결과는 별도로 정리 예정.
