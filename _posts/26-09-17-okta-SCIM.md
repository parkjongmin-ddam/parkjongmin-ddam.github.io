---
layout: single
title: "Okta 랩 6 — 자체 SCIM 서버로 실측한 Okta 프로비저닝의 실제 요청들"
excerpt: "앞선 다섯 편이 인증(OIDC·SAML·AD 위임 인증)과 코드화(Terraform)였다면, 이번엔 프로비저닝이다. Flask로 SCIM 2.0 서버를 직접 만들어 cloudflared 터널로 노출하고, Okta가 언제 어떤 요청을 보내는지 전부 로그로 받아 확인했다. 할당 해제가 DELETE가 아니라 PUT active:false라는 점, Okta의 쓰기가 전부 read-modify-write라서 서버가 writeOnly를 어기면 password가 IdP 경로로 왕복한다는 사실, 앱 쪽 계정이 사라지면 404에서 동기화가 멈추고 Retry로는 복구되지 않는다는 것, Group Push가 앱 접근 권한을 부여하지 않는다는 것, 재할당이 재생성이 아니라 재활성화라는 것까지 요청 단위로 확인한 기록이다."
date: 2026-09-17
categories: [IAM]
tags: [Okta, SCIM, Provisioning, Group-Push, Active-Directory, Flask, 실측]
---

[전편]({% post_url 26-07-30-okta-terraform %})까지 다섯 편은 Okta의 인증 프로토콜 동작과 AD 연동, 그리고 Terraform 코드화를 다뤘다. 이번에는 프로비저닝이다. Okta가 SCIM 커넥터로 다운스트림 앱에 계정을 만들고, 수정하고, 비활성화할 때 실제로 어떤 HTTP 요청을 보내는지 확인한다.

방법은 단순하다. SCIM 2.0 서버를 Flask로 직접 만들고, 모든 요청을 본문까지 로그로 남긴 뒤, Okta 콘솔에서 할당·해제·그룹 푸시 등 각 조작을 수행하며 어떤 요청이 나가는지 대조했다. 문서에는 "사용자를 생성합니다" 수준으로만 적혀 있는 동작들이 요청 단위에서는 어떻게 구현되어 있는지가 이번 기록의 내용이다.

## 1. SCIM이 무엇인지부터

SCIM(System for Cross-domain Identity Management)은 서로 다른 도메인 사이에서 계정 정보를 주고받기 위한 표준이다. 두 개의 RFC로 구성된다. **RFC 7643**이 스키마 — User·Group 리소스가 어떤 속성을 갖는지 — 를 정의하고, **RFC 7644**가 프로토콜 — 그 리소스를 REST API로 어떻게 조회·생성·수정·삭제하는지 — 을 정의한다.[^2] 표현 형식은 JSON이고, 동작은 평범한 REST다.

역할 구분이 먼저다. SCIM에는 클라이언트와 서버가 있는데, **IdP가 클라이언트이고 다운스트림 앱이 서버다.** 인증(SAML·OIDC)에서는 앱이 IdP에게 인증을 요청하는 방향이었다면, 프로비저닝에서는 반대로 IdP(Okta)가 앱의 API를 호출한다. 이번 랩에서 Flask 서버를 만든 이유가 이것이다 — 앱 쪽, 즉 SCIM 서버 역할을 직접 구현해야 Okta가 보내는 요청을 전부 볼 수 있다.

서버가 제공하는 표준 엔드포인트는 다음과 같다.

| 엔드포인트 | 역할 |
|---|---|
| `/Users` | 사용자 리소스. filter 검색, 생성(POST), 수정(PUT/PATCH), 비활성·삭제 |
| `/Groups` | 그룹 리소스와 멤버십 |
| `/ServiceProviderConfig` | 서버가 지원하는 기능 선언 (patch.supported, filter.supported 등) |
| `/Schemas`, `/ResourceTypes` | 스키마 메타데이터 |

사용자 속성은 core 스키마(`urn:ietf:params:scim:schemas:core:2.0:User` — userName, name, title, active 등)와 enterprise 확장(`extension:enterprise:2.0:User` — department, manager, employeeNumber 등)으로 나뉜다. 속성마다 mutability 같은 특성이 정의되어 있는데, 특히 `password`는 `mutability: writeOnly`, `returned: never` — 쓸 수는 있지만 응답에 절대 내보내면 안 되는 속성이다. 이 정의가 왜 실질적인 보안 장치인지는 11절에서 확인된다.

그럼 왜 SCIM이 필요한가. SSO는 인증만 해결한다. 사용자가 로그인할 수 있으려면 앱에 계정이 먼저 존재해야 하고, 퇴사하면 그 계정이 비활성화되어야 한다. 로그인 시점에 계정을 만들어주는 JIT(Just-In-Time) 프로비저닝도 있지만, JIT는 태생적으로 **떠난 사람을 처리하지 못한다** — 로그인하지 않는 사용자에게는 아무 일도 일어나지 않기 때문이다. 입사(Joiner)·이동(Mover)·퇴사(Leaver) 전체 수명주기, 특히 보안상 가장 중요한 deprovisioning을 자동화하려면 IdP가 능동적으로 앱에 요청을 보내는 SCIM 방식이 필요하다.

여기까지가 명세다. 그런데 명세가 정의하는 것과 Okta가 실제로 보내는 요청 사이에는 간극이 있다. `/ServiceProviderConfig`로 capability를 선언하게 되어 있지만 Okta는 읽지 않고, PATCH가 명세에 있지만 Okta는 PUT만 쓴다. 그 간극을 요청 단위로 확인하는 것이 이번 실측이다.

## 2. 랩 구성

| 항목 | 값 |
|---|---|
| Okta org | Integrator Free Plan |
| 앱 | SCIM-SAML-sp — AIW로 만든 커스텀 SAML 앱, General → Provisioning: SCIM |
| SCIM 서버 | 자체 Flask SCIM 2.0 서버 (scim_server.py) |
| 노출 경로 | cloudflared 터널 (`https://{tunnel-host}`) |
| 대상 계정 | seonjung.jeon, jaehong.yoo — 둘 다 AD-sourced |
| 대상 그룹 | okta-lab-users — AD-sourced |

계정과 그룹은 [랩 4]({% post_url 26-07-29-okta-ad-agent %})에서 AD Agent로 Import한 AD-sourced 리소스를 그대로 쓴다. AD → Okta → SCIM 앱으로 이어지는 전체 체인에서 Okta가 중계자 역할을 하는 구성이다. org 서브도메인·터널 호스트·토큰·앱 ID는 치환(마스킹)해 표기한다.

앱은 AIW(App Integration Wizard)로 SAML 2.0 커스텀 앱을 만들었다. ACS URL은 로컬 플레이스홀더다 — 이번 랩의 관심사는 SAML 로그인이 아니라 프로비저닝이므로 값 자체는 중요하지 않다.

![Create App Integration — SAML 2.0 선택](/assets/images/26-09-17/01-create-app-integration.png)

![앱 이름 지정 — SCIM-SAML-sp](/assets/images/26-09-17/02-saml-app-name.png)

![SAML 설정 — ACS URL은 로컬 플레이스홀더](/assets/images/26-09-17/03-saml-settings.png)

![Feedback 단계 — 별도 기입 없이 Finish](/assets/images/26-09-17/04-feedback-step.png)

SCIM 서버는 Flask로 만들어 로컬에 띄우고, cloudflared quick tunnel로 외부에 노출했다. 토큰은 환경변수로 주입한다.

![winget으로 cloudflared 설치](/assets/images/26-09-17/05-winget-cloudflared.png)

![SCIM 서버 기동 — 토큰은 환경변수로 주입](/assets/images/26-09-17/06-scim-server-start.png)

![cloudflared quick tunnel 생성](/assets/images/26-09-17/08-cloudflared-tunnel.png)

![터널 연결 사전 점검 통과](/assets/images/26-09-17/09-cloudflared-precheck.png)

Okta를 붙이기 전에, 서버가 SCIM 형태의 요청을 제대로 처리하는지 자체 테스트 스크립트로 먼저 검증했다. 인증 실패 401, filter 검색, POST 201, 중복 userName 409까지 통과한 뒤에 Okta를 연결했다.

![서버 자체 검증 스크립트 — 전 시나리오 통과](/assets/images/26-09-17/07-server-selftest.png)

## 3. 들어가기 전에 확인한 것들

먼저 Free Plan에서 이 실습이 가능한지부터 확인했다.

- Integrator Free Plan에서도 커스텀 앱의 General → App Settings → Provisioning에 **None / On-Premises Provisioning / SCIM** 세 개 선택지가 노출된다. SCIM 커넥터 사용 가능하다
- Supported provisioning actions는 콘솔에 5개가 표시된다 — Import New Users and Profile Updates / Push New Users / Push Profile Updates / Push Groups / Import Groups. Okta Help 문서에는 4개만 기재되어 있다.[^1] 문서가 콘솔보다 뒤처져 있다
- To App 설정의 기본값은 Create / Update / Deactivate 전부 미체크다. 매핑 테이블의 Apply on 기본값은 전 속성 "Create"

![Applications 메뉴 진입](/assets/images/26-09-17/10-applications-menu.png)

![General → App Settings — Provisioning 선택지 3개](/assets/images/26-09-17/11-general-provisioning-scim.png)

![SCIM Connection — Supported provisioning actions 5개](/assets/images/26-09-17/12-scim-connection.png)

![To App 기본값 — Create/Update/Deactivate 전부 미체크](/assets/images/26-09-17/16-to-app-defaults.png)

매핑 테이블의 Apply on 기본값이 전 속성 "Create"인 것도 화면으로 확인된다.

![Attribute Mappings — Apply on 기본값 Create (1)](/assets/images/26-09-17/17-mapping-table-1.png)

![Attribute Mappings — Apply on 기본값 Create (2)](/assets/images/26-09-17/18-mapping-table-2.png)

![Attribute Mappings — Apply on 기본값 Create (3)](/assets/images/26-09-17/19-mapping-table-3.png)

즉 SCIM URL과 토큰을 넣고 저장만 해서는 아무 일도 일어나지 않는다. To App에서 동작을 켜야 요청이 나가기 시작한다. 실측을 위해 Create Users / Update User Attributes / Deactivate Users를 켰고, Sync Password는 의도적으로 껐다 — 5절 password 관찰의 전제 조건이 된다.

![To App 활성화 — Sync Password는 미체크](/assets/images/26-09-17/20-to-app-enabled.png)

## 4. Test Connector Configuration이 실제로 보내는 요청

커넥터 설정 화면의 Test Connector Configuration 버튼이 보내는 것은 단 하나다.

![Authorization 헤더에 Bearer 토큰 입력 후 Test Connector Configuration](/assets/images/26-09-17/13-token-auth-header.png)

```
GET /Users?startIndex=1&count=2
```

![Test Connector Configuration 성공 팝업](/assets/images/26-09-17/14-test-connector-result.png)

이게 전부다. Save 시 같은 요청이 1회 더 나간다. 주목할 것은 **`/ServiceProviderConfig`를 읽지 않는다**는 점이다. SCIM 명세상 서버는 이 엔드포인트로 자신의 capability(`patch.supported` 등)를 선언하게 되어 있지만, Okta는 조회하지 않고 따라서 무시한다. 서버가 "나는 PATCH를 지원한다"고 선언해도 Okta의 동작은 달라지지 않는다.

실제로 서버의 `/ServiceProviderConfig` 응답에는 `patch.supported: true` 등 capability가 선언되어 있다. Okta는 이 선언을 읽지 않는다.

![서버의 ServiceProviderConfig 응답 — patch.supported: true](/assets/images/26-09-17/15-serviceproviderconfig.png)

To App 설정을 저장할 때는 부수 요청이 하나 더 붙는다.

```
GET /Users?startIndex=1&count=2      ← 커넥터 재검증
GET /Groups?startIndex=1&count=100   ← 앱 그룹 목록 캐시
```

Groups 조회는 앱 쪽 그룹 목록을 캐시하기 위한 것이다. 이후 Push Groups 화면의 "Create Group / Link Group" 판정과 Refresh App Groups 버튼이 이 캐시를 사용한다. 9절에서 이 캐시가 실제 판정에 쓰이는 것을 확인한다.

## 5. 사용자 할당 — Push New Users

seonjung.jeon을 앱에 할당하면 다음 순서로 요청이 나간다.

![Assignments에서 azlab 계정 할당](/assets/images/26-09-17/24-assign-azlab.png)

```
GET /Users?filter=userName eq "<username>"&startIndex=1&count=100   → 0건
POST /Users                                                          → 201
```

먼저 filter로 기존 계정 존재 여부를 확인하고, 없으면 생성한다. POST 본문에서 확인한 사실들:

- schemas는 `urn:ietf:params:scim:schemas:core:2.0:User` + `extension:enterprise:2.0:User` 두 개. **department는 enterprise 확장 아래, title은 core 스키마**에 실린다
- `externalId`에는 Okta 사용자 ID(`00u…`)가 들어간다. Okta 쪽에서 이 계정을 추적하는 키다
- 값이 없는 매핑 속성(middleName, honorific 등)은 본문에서 생략된다
- `groups`는 빈 배열이다. 그룹 소속은 사용자 생성 시점에 실리지 않는다 (10절 참조)

예상 밖이었던 것은 password다. **Sync Password를 체크하지 않았는데도 POST 본문에 `password`가 포함됐다.** 무작위 8자다. 이는 버그가 아니라 의도된 동작으로 보인다 — 앱 계정에 아무도 모르는 임의 비밀번호를 박아 넣어, SSO를 우회한 로컬 로그인을 사실상 막는 구조다.

![POST /Users 본문 — Sync Password 미체크 상태에서도 password 포함](/assets/images/26-09-17/23-post-user-body.png)

부수적인 실수도 기록해 둔다. 처음에 Okta-sourced 동명 계정(gmail 주소)을 잘못 할당했다. [랩 4]({% post_url 26-07-29-okta-ad-agent %})의 Import에서 PARTIAL match를 NEW로 확정한 결과 동명이인 계정이 2건 존재했기 때문이다. 할당 팝업은 표시 이름 위주라 구분이 어렵다. 할당 전에 userName을 확인하는 습관이 필요하다.

![잘못 할당된 Okta-sourced 동명 계정 — 표시 이름은 동일하다](/assets/images/26-09-17/21-assign-wrong-account.png)

![할당 팝업 — userName을 확인해야 하는 지점](/assets/images/26-09-17/22-assign-popup-detail.png)

## 6. 할당 해제 — DELETE가 아니라 PUT active:false

Unassign 시 나가는 요청은 다음과 같다.

```
GET /Users/{id}
PUT /Users/{id}    ← 전체 본문, active: false
```

**DELETE도 PATCH도 아니다.** 직전 GET 응답을 통째로 복사해 `active`만 `false`로 바꾼 전체 본문을 PUT으로 되돌려 보내는 read-modify-write다. 이 방식의 함의는 11절에서 다시 다룬다 — 서버가 GET 응답에 내보낸 값은 무엇이든 PUT에 그대로 왕복한다.

![Unassign 시 요청 로그 — GET 후 PUT](/assets/images/26-09-17/25-unassign-requests.png)

![PUT 본문 — 전체 리소스 사본에 active:false](/assets/images/26-09-17/26-put-deactivate-body.png)

결과적으로 앱 계정은 삭제되지 않고 비활성 상태로 잔존한다. 그리고 **그룹 멤버십은 갱신되지 않는다.** 비활성화된 계정이 앱 그룹의 members에 그대로 남는다. 이 비대칭은 10절에서 다시 확인한다.

## 7. 앱 쪽 계정이 사라지면 — 404에서 멈춘다

가장 실무적인 관찰은 우연히 나왔다. 서버의 store를 삭제한 상태에서 AD의 title을 변경하자 Incremental Import → Okta 프로필 반영 → 프로필 푸시가 트리거됐고, Okta는 저장해 둔 앱 ID로 조회를 시도했다.

```
GET /Users/{id}   → 404
```

**404를 받으면 Okta는 그 자리에서 중단한다.** filter로 재검색하지도, POST로 재생성하지도, 자동 재시도하지도 않는다. 사용자 상세에 빨간 배너가 뜨고 Dashboard → Tasks에 "profile updates have errors"로 기록된다. Tasks에서 Retry Selected를 눌러도 동일한 `GET /Users/{id}` 404가 반복될 뿐이다.

복구 경로는 링크를 새로 만드는 것뿐이었다.

1. Unassign — `GET /Users/{id}` 404 → PUT 없이 종료. Okta 쪽 할당만 해제된다
2. 재할당 — filter 0건 → `POST /Users` 201로 **새 앱 ID 발급** → 복구

![404 반복 후 Unassign → 재할당으로 새 앱 ID 발급](/assets/images/26-09-17/27-404-recovery.png)

![Unassign 후 Tasks의 오류 항목이 사라진 화면](/assets/images/26-09-17/28-tasks-cleared.png)

실무 시나리오로 옮기면 이렇다. SaaS 쪽 관리자가 콘솔에서 계정을 직접 지워버린 사용자는 Okta의 Retry로 복구되지 않는다. Unassign 후 재할당으로 Okta-앱 간 링크를 다시 만들어야 한다.

## 8. 프로필 변경 푸시 — Push Profile Updates

정상 경로도 확인했다. AD에서 title을 변경하고 Incremental Import(1 updated)를 돌리면 Okta 프로필에 반영되고, 즉시 다음 요청이 나간다.

![AD에서 title 변경](/assets/images/26-09-17/29-ad-title-change.png)

![Directory Integrations — AD 연동 진입](/assets/images/26-09-17/31-directory-integrations.png)

![Import Now 실행](/assets/images/26-09-17/32-import-now.png)

![Incremental Import 결과 — 1 existing user updated](/assets/images/26-09-17/30-incremental-import.png)

```
GET /Users/{id}    → 200
PUT /Users/{id}    ← title 반영된 전체 본문, active: true
```

![프로필 푸시 로그 — GET 200 후 PUT으로 title 반영](/assets/images/26-09-17/33-profile-push-put.png)

6절과 동일한 read-modify-write다. 변경된 필드만 보내는 PATCH가 아니라 매번 전체 본문 PUT이다.

이 실측은 [랩 4]({% post_url 26-07-29-okta-ad-agent %})에서 남겨뒀던 incremental import 확인을 겸했다. 부수 확인 사항으로, AD-sourced 사용자는 Okta 콘솔에서 Profile Edit 버튼 자체가 없다. 프로필의 원천이 AD이므로 수정 경로가 AD → Import 한 방향으로만 열려 있다.

## 9. Group Push — 접근 권한과는 별개다

Push Groups에서 okta-lab-users를 푸시하면 다음이 나간다.

```
POST /Groups        ← displayName + members    → 201
GET /Groups/{id}
PUT /Groups/{id}    ← 동일 내용 재동기화
```

`GET /Groups?filter=displayName eq …` 같은 존재 확인 요청은 없다. Create Group인지 Link Group인지는 4절에서 캐시해 둔 그룹 목록으로 판정한다.

![Group Push 요청 로그와 본문 — members에는 할당된 사용자만](/assets/images/26-09-17/35-group-push-requests.png)

본문에서 확인한 중요한 사실 두 가지:

**첫째, members에는 앱에 할당된 사용자만 들어간다.** AD 그룹 okta-lab-users에는 멤버가 셋(seonjung.jeon, jaehong.yoo, guyong.lee)이지만, 푸시된 members에는 앱에 할당된 seonjung.jeon 한 명뿐이었다. 나머지 멤버에 대한 `POST /Users`도 나가지 않는다.

**둘째, Group Push는 앱 접근 권한을 부여하지 않는다.** 할당(계정 생성)과 푸시(그룹 소속 동기화)는 완전히 별개의 축이다. Okta가 "Assign에 쓰는 그룹과 Push하는 그룹을 분리하라"고 권고하는 근거가 바로 이 구조다.

형식적인 부분은 이렇다. `members[].value`는 앱 사용자 ID, `display`는 userName이다. 콘솔의 Push Status는 Active로 표시되고, AD-sourced 그룹에는 Windows 로고 아이콘이 붙는다.

## 10. 멤버십 변경 전파 — 그리고 비대칭

jaehong.yoo를 앱에 할당하자 사용자 생성과 그룹 갱신이 연달아 나갔다.

![두 사용자 할당 상태](/assets/images/26-09-17/36-assignments-two-users.png)

```
GET /Users?filter=…        → 0건
POST /Users                → 201
GET /Groups/{id}
PUT /Groups/{id}           ← members 2명 (전체 목록)
GET /Groups/{id}
PUT /Groups/{id}           ← 동일 내용, 순서만 다름
```

앱에 할당되는 순간, 그 사용자가 속한 푸시 그룹의 members에 자동으로 편입된다. 그리고 **그룹 PUT은 항상 전체 members 목록이다.** PATCH의 add/remove 연산이 아니라 매번 전체 교체다. 멤버가 수천 명인 그룹이라면 멤버 한 명의 변경마다 전체 목록이 왕복한다는 뜻이다.

반면 seonjung.jeon을 Unassign했을 때는 사용자 `PUT active:false`만 발생하고 **그룹 PUT은 나가지 않았다.** 비활성 계정이 앱 그룹 members에 그대로 남는다. 할당은 그룹 갱신을 동반하지만 해제는 동반하지 않는 비대칭이다. 앱 쪽에서 그룹 멤버십으로 권한을 판정한다면, 비활성 계정이 권한 그룹에 남아 있는 상태를 앱이 스스로 걸러야 한다.

![멤버십 전파 로그 — 할당 시 그룹 PUT 동반, 해제 시 사용자 PUT만](/assets/images/26-09-17/37-membership-propagation.png)

## 11. 재할당은 재활성화다 — 그리고 password의 출처

seonjung.jeon을 다시 할당하자 이번에는 filter가 기존 계정 1건(active: false)을 찾았다.

```
GET /Users?filter=…                → 1건 (active: false)
GET /Users/{id} → PUT active:true  ×2
GET /Groups/{id} → PUT             ×2   ← members 복귀
```

POST는 나가지 않는다. **재할당은 재생성이 아니라 재활성화다.** 새 앱 ID 발급 없이 기존 계정을 되살리고, 이번에는 그룹 PUT도 함께 나가 members에 복귀한다.

이 사이클에서 앞서 미뤄둔 password 출처 문제를 판정했다. 6절의 PUT 본문에 password가 실려 있었는데, 이것이 Okta가 자체적으로 넣은 것인지 서버 응답의 반사인지 구분해야 했다.

수정 전 로그에서는 PUT 본문의 속성 목록에 password가 들어 있다.

![수정 전 — PUT 본문 키 목록에 password 존재](/assets/images/26-09-17/38-put-body-with-password.png)

![수정 전 — 마지막 PUT의 속성 목록에도 password](/assets/images/26-09-17/39-put-keys-list.png)

서버를 수정해 GET 응답에서 password를 제거(writeOnly 준수)한 뒤 같은 조작을 반복하자, 나가는 PUT에 password가 사라졌다.

![서버 패치 — 응답에서 writeOnly 속성 제거(public/_mask)](/assets/images/26-09-17/40-server-writeonly-patch.png)

![패치 후 GET 응답 키 목록 — password 없음](/assets/images/26-09-17/41-get-keys-no-password.png)

![패치 후 왕복 확인 — 모든 PUT에서 pw= 빈 값](/assets/images/26-09-17/42-put-no-password.png)

결론은 이렇다. **Okta는 PUT 시 자기 쪽에서 비밀번호를 싣지 않는다.** 이전 PUT에 password가 있었던 것은 서버가 GET 응답에 password를 내보냈고, Okta의 read-modify-write가 그것을 그대로 복사한 결과다. 뒤집어 말하면 — **SCIM 서버가 password 속성의 writeOnly를 어기는 순간, 비밀번호가 IdP 경로로 왕복하기 시작한다.** SCIM 서버 구현에서 `returned: never` 속성 처리는 명세 준수 문제가 아니라 실질적인 유출 방지 장치다.[^2]

## 12. 실습 중 실수와 교훈

- 서버 코드를 고친 뒤 재기동 확인 없이 로그를 읽어 결론을 두 번 뒤집었다. 판정을 내리기 전에 **실행 중인 프로세스의 실제 동작**(GET 응답의 키 목록)을 직접 확인해야 한다
- store 삭제로 7절의 404 시나리오가 우연히 만들어졌다 — 결과적으로 가장 실무적인 관찰이 됐다
- 동명이인 계정을 잘못 할당했다(5절). 할당 팝업에서 userName을 확인하는 습관이 필요하다

## 13. 랩 정리와 보안 뒷정리

이 랩은 비밀번호가 오가는 실측이라 정리 항목에 보안 사항이 포함된다.

- **Okta**: Push Groups에서 okta-lab-users를 Unlink(Delete the group in target app) → Assignments 전원 Unassign → Provisioning → Integration에서 Enable API integration 해제 또는 General → Provisioning: None
- **AD**: 실험으로 바꿨던 seonjung.jeon의 title을 원복
- **로컬**: cloudflared 종료, SCIM 토큰 폐기. 그리고 요청 로그(`scim_requests.jsonl`)에 **평문 password가 남아 있는 구간을 삭제 또는 마스킹**해야 한다. 11절에서 확인했듯 서버가 writeOnly를 지키기 전까지의 로그에는 password가 그대로 담겨 있다
- **서버 코드**: 초기 버전은 POST 본문을 통째로 저장·반환해 password를 응답에 노출했다. 응답 직전에 민감 속성을 제거하는 수정본으로 교체했다

![AD title 원복](/assets/images/26-09-17/34-ad-title-revert.png)

실습용이라도 SCIM 서버는 자격증명이 흐르는 경로다. 로그 정책과 응답 필터링을 처음부터 설계에 넣어야 한다는 것을 몸으로 확인한 셈이다.

## 14. 미실측 항목

- **PATCH 방식** — Okta가 AIW 앱에 PATCH를 쓰는 조건이 있는지. 이번 실측에서는 전부 PUT이었다
- **Import(To Okta)** — 앱 사용자를 Okta로 가져오는 반대 방향(GET 페이지네이션)
- **Push now 강제 동기화** — 비활성 멤버가 그룹 members에서 빠지는지(10절의 비대칭이 해소되는지)
- **서버 5xx·타임아웃 시 Okta의 재시도 간격**

## 정리

문서만으로는 예측되지 않았던 지점은 다음과 같다.

1. Test Connector Configuration은 `GET /Users` 하나만 보낸다. `/ServiceProviderConfig`는 읽지 않으며 서버가 선언한 capability는 무시된다
2. Sync Password를 끄고도 POST에 무작위 password가 실린다. 로컬 로그인을 막는 장치다
3. 할당 해제는 DELETE가 아니라 전체 본문 PUT의 `active: false`다. 계정은 비활성으로 잔존한다
4. 앱 쪽 계정이 사라지면 404에서 동기화가 멈추고, Retry로 복구되지 않는다. Unassign → 재할당으로 링크를 새로 만들어야 한다
5. Group Push는 앱 접근 권한을 부여하지 않는다. 할당과 푸시는 별개의 축이다
6. 그룹 갱신은 항상 전체 members PUT이며, 할당은 그룹 갱신을 동반하지만 해제는 동반하지 않는다
7. 재할당은 재생성이 아니라 재활성화다
8. Okta의 쓰기는 read-modify-write이므로, SCIM 서버가 password의 writeOnly를 어기면 비밀번호가 IdP 경로로 왕복한다

3·4·6번은 다운스트림 앱 쪽 설계에, 8번은 SCIM 서버 구현에 직접 영향을 주는 지점이다. "SCIM으로 프로비저닝한다"는 한 문장 뒤에 이만큼의 동작 차이가 숨어 있다.

---

[^1]: Okta Help — Provisioning and Deprovisioning 개요의 provisioning actions 목록 — <https://help.okta.com/en-us/content/topics/provisioning/lcm/lcm-provision-deprovision.htm>
[^2]: SCIM 2.0 스키마 명세(RFC 7643) — password 속성은 `mutability: writeOnly`, `returned: never`로 정의된다 — <https://datatracker.ietf.org/doc/html/rfc7643#section-4.1.1>
