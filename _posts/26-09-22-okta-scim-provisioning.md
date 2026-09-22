---
layout: single
title: "Okta SCIM 프로비저닝 검증 (1) — 자체 SCIM 서버로 본 Okta의 요청"
excerpt: "OIN 앱에 SCIM을 붙이면 Okta가 무엇을 보내는지 보이지 않는다. Flask로 SCIM 2.0 서버를 직접 만들어 cloudflared 터널로 노출하고, Okta 콘솔의 조작 하나하나가 어떤 HTTP 요청으로 번역되는지 전부 로그로 받아 확인했다. 연결 테스트는 GET /Users 하나뿐이고 ServiceProviderConfig는 읽지 않는다는 것, 할당 해제가 DELETE가 아니라 read-modify-write PUT active:false라는 것, 앱 쪽 계정이 사라지면 404에서 동기화가 멈춘다는 것, Group Push는 접근 권한을 부여하지 않는다는 것, 그리고 Import(To Okta)는 앱 호출 없이 Okta 내부 링크만 만든다는 것까지 — 요청 단위의 기록이다."
date: 2026-09-22
categories: [IAM]
tags: [Okta, SCIM, Provisioning, Lifecycle, Group-Push, 실측]
---

## 1. 배경

SAML/OIDC는 인증 시점에 IdP가 SP에 사용자 정보를 전달하는 프로토콜이다. SCIM은 인증과 무관하게 IdP가 SP의 사용자 저장소를 REST로 생성·수정·비활성화하는 프로토콜이다.[^1]

ADFS 환경에서는 계정이 이미 AD에 있어 이 층이 필요 없었다. IDaaS에서는 SaaS 앱마다 이 층이 생긴다.

OIN 앱(Slack 등)에 붙이면 Okta가 무엇을 보내는지 보이지 않는다. SCIM 서버를 직접 만들어 Okta를 클라이언트로 붙이면 요청 전부를 로그로 볼 수 있다.

학습 로드맵은 베스핀글로벌 Okta 가이드의 앱 연동·프로비저닝 항목을 참고했고, 본문은 전부 자체 org 실측이다. 이 글은 프로토콜 관찰(요청 형태)이고, 장애·퇴사·복직 체인은 [2편]({% post_url 26-09-22-okta-scim-provisioning-2 %})에서 다룬다.

## 2. 구성

| 항목 | 값 |
|---|---|
| Okta org | Integrator Free Plan |
| 앱 | AIW로 만든 커스텀 SAML 앱 (SSO는 사용하지 않고 형식만 채움) → General → Provisioning: SCIM |
| SCIM 서버 | Flask 단일 파일 — `/scim/v2` 아래 Users·Groups·ServiceProviderConfig, Bearer 인증, 필터·페이지네이션·PATCH·PUT 구현. 모든 요청·응답을 jsonl로 기록 |
| 노출 경로 | cloudflared quick tunnel (`https://{tunnel}.trycloudflare.com/scim/v2`) |
| 사용자 | AD Agent로 Import한 AD-sourced 계정, AD-sourced 그룹 1개 |

마스킹 표기: org 서브도메인 `{org}`, 터널 호스트 `{tunnel}`, 앱 리소스 ID `{app_user_id}`/`{app_group_id}`, 테스트 계정명 `<username>`, 토큰·비밀번호 값.

## 3. 게이트 확인

들어가기 전에 Free Plan에서 이 실습이 가능한지부터 확인했다.

- Integrator Free Plan에서 커스텀 앱의 Provisioning 필드에 **None / On-Premises Provisioning / SCIM** 3개가 노출된다
- Supported provisioning actions는 콘솔에 5개(Import New Users and Profile Updates / Push New Users / Push Profile Updates / Push Groups / Import Groups)가 표시된다. Okta Help 문서에는 4개만 기재되어 있다[^2]
- To App 기본값은 Create / Update / Deactivate 전부 미체크다. 매핑 테이블의 Apply on 기본값은 전 속성 "Create"

## 4. Test Connector Configuration이 보내는 요청

```
GET /scim/v2/Users?startIndex=1&count=2
```

이것 하나다. `/ServiceProviderConfig`는 읽지 않는다. 서버가 `patch.supported: true`를 선언해도 참고하지 않는다. Save 시 같은 요청이 한 번 더 나간다.

## 5. To App 저장 시 부수 요청

```
GET /scim/v2/Users?startIndex=1&count=2
GET /scim/v2/Groups?startIndex=1&count=100
```

Groups 조회는 앱 그룹 목록 캐시다. 이후 Push Groups의 Create/Link 판정과 "Refresh App Groups" 버튼이 이 캐시를 쓴다.

## 6. 사용자 할당 — Push New Users

```
GET  /scim/v2/Users?filter=userName eq "<username>"&startIndex=1&count=100  → 0건
POST /scim/v2/Users  → 201
```

POST 본문(발췌):

```json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User",
              "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"],
  "userName": "<username>",
  "name": {"givenName": "<givenName>", "familyName": "<familyName>"},
  "emails": [{"primary": true, "value": "<username>", "type": "work"}],
  "title": "Manager",
  "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {"department": "Engineering"},
  "externalId": "00u{masked}",
  "groups": [],
  "password": "{masked}",
  "active": true
}
```

- `externalId` = Okta 사용자 ID. 앱 쪽 userName·이메일이 바뀌어도 같은 사람을 추적하는 키다
- department는 enterprise 확장 스키마, title은 core에 실린다. 값 없는 매핑 속성은 생략된다
- **Sync Password를 끈 상태에서도 password가 온다.** 무작위 8자다. 앱 계정에 임의 비밀번호를 박아 로컬 로그인을 막고 SSO로만 들어오게 하는 구조다

부수적인 실수 하나. AD Import 때 동명 Okta-sourced 계정을 NEW로 확정해 둔 탓에 같은 이름이 둘이었고, 처음 할당한 것은 다른 쪽 계정이었다. 할당 팝업에서 username 확인이 필요하다.

## 7. 할당 해제 — Deactivate Users

```
GET /scim/v2/Users/{app_user_id}  → 200
PUT /scim/v2/Users/{app_user_id}  → 200   (active: false)
```

- **DELETE도 PATCH도 아니다.** 리소스 전체를 읽어 active만 바꿔 되돌려 쓰는 read-modify-write다
- 앱 계정은 삭제되지 않고 비활성으로 잔존한다
- PUT 본문에 GET 응답의 id·meta가 그대로 포함된다 — Okta는 직전 GET 응답을 복사해 수정한다. 서버가 GET 응답에 password를 내보내면 PUT에도 그대로 왕복한다(12절에서 확정)[^3]

## 8. 앱 리소스 부재 시 프로필 푸시 — 404에서 멈춘다

서버 저장소를 지운 상태(앱 관리자가 계정을 직접 삭제한 상황)에서 AD title 변경 → Incremental Import → 즉시 다음 요청이 나간다.

```
GET /scim/v2/Users/{app_user_id}  → 404
```

- **404를 받으면 그 자리에서 중단한다.** filter 재검색도, POST 재생성도, 자동 재시도도 없다
- 사용자 상세에 빨간 배너가 뜨고 Tasks에 "profile updates have errors"로 기록된다. Retry는 같은 GET 404를 반복할 뿐이다
- 복구: Unassign(GET 404 → PUT 없이 종료) → 재할당(filter 0건 → POST 201, **새 앱 ID 발급**)

## 9. 프로필 변경 정상 푸시 — Push Profile Updates

AD title 변경 → Incremental Import(1 updated) → 즉시 GET 200 → PUT(title 반영).

7절과 같은 read-modify-write다. 변경 필드만 보내는 PATCH가 아니다.

AD-sourced 사용자는 Okta 콘솔에서 Profile Edit 버튼 자체가 없다. Profile Editor에서 속성 Source priority를 Okta로 바꾸면 편집은 되지만, AD → Okta → 앱 체인 관찰 목적과 어긋나 AD 쪽 변경으로 진행했다.

## 10. Group Push

```
POST /scim/v2/Groups  → 201   {"displayName": "okta-lab-users", "members": [{"value": "{app_user_id}", "display": "<username>"}]}
GET  /scim/v2/Groups/{app_group_id}
PUT  /scim/v2/Groups/{app_group_id}   (동일 내용)
```

- `GET /Groups?filter=displayName eq …` 같은 존재 확인은 없다. 5절의 캐시로 Create를 판정한다
- **members에는 앱에 할당된 사용자만 들어간다.** AD 그룹의 나머지 멤버는 제외되고, 그들에 대한 `POST /Users`도 나가지 않는다
- **Group Push는 앱 접근 권한을 부여하지 않는다.** 할당(계정 생성)과 푸시(그룹 소속)는 별개다. 가이드의 "Assign 그룹과 Push 그룹 분리" 권고의 근거가 이 구조다

## 11. 멤버십 변경 전파

다른 사용자를 앱에 할당하면 `POST /Users` → 그룹 GET/PUT(members 2명)이 연달아 나간다. 할당되는 순간 소속 푸시 그룹에 자동 편입된다.

- 그룹 PUT은 **항상 전체 members 목록**이다. add/remove 연산이 아니다
- 사용자 Unassign 시에는 사용자 `PUT active:false`만 발생하고 그룹 PUT은 없다 → 비활성 계정이 앱 그룹에 잔존한다. 재할당 시에는 그룹 PUT으로 복귀한다(비대칭)

## 12. 재할당과 password 왕복 판정

재할당 시퀀스: filter → 기존 계정 1건(active: false) → POST 없이 GET/PUT `active: true` → 그룹 GET/PUT. **재생성이 아니라 재활성화다.**

이 사이클에서 password의 출처를 판정했다. 서버를 고쳐 GET 응답에서 password를 제거한 뒤 나간 PUT에는 password가 없었다 → 7절 PUT의 password는 서버가 내보낸 값을 Okta가 복사한 것이다. Okta 자체 값이 아니다.

## 13. Import (To Okta) — 앱 사용자를 Okta로 가져오기

실측 재개를 위해 환경부터 되살렸다. SCIM 서버를 토큰 환경변수 주입으로 재기동하고,

![SCIM 서버 재기동 — 토큰은 환경변수로 주입](/assets/images/okta01/01-scim-server-restart.png)

cloudflared quick tunnel을 다시 띄우자 새 무작위 호스트명이 발급됐다. 16절의 교훈 그대로, 커넥터의 base URL 갱신이 첫 작업이 된다.

![cloudflared 재기동 — 새 quick tunnel URL 발급](/assets/images/okta01/02-cloudflared-restart.png)

![Provisioning → Integration — SCIM connector base URL을 새 터널 호스트로 갱신](/assets/images/okta01/03-scim-base-url-update.png)

앱 저장소에는 Okta가 만들지 않은 계정(SaaS 관리자가 콘솔에서 직접 만든 상황)을 넣어 두었다. store JSON에 core 스키마 형태의 사용자를 직접 추가하고,

![python 한 줄로 앱 전용 계정을 store에 직접 추가](/assets/images/okta01/04-add-app-only-user.png)

서버 재기동 후 API로 조회해 신규 계정이 `active: True`로 들어간 것을 확인했다. 이 시점 store에는 4건 — 기존 링크 2건(True), 비활성 1건(False), 앱 전용 신규 1건(True) — 이 있다.

![GET /Users 조회 — 신규 앱 전용 계정 active True 확인](/assets/images/okta01/05-store-users-check.png)

이 상태에서 Import 탭의 Import Now를 실행했다.

![Import 탭 — Import Now 실행](/assets/images/okta01/06-import-now.png)

```
GET /scim/v2/Users?startIndex=1&count=100
GET /scim/v2/Groups?startIndex=1&count=100
```

각 1회, 페이지 크기 100이다. 요약 결과는 4 users scanned / 1 new / 2 updated(기존 링크) / 1 removed / 0 groups scanned.

![Import 스캔 결과 — 4 users scanned, 0 groups scanned](/assets/images/okta01/07-import-scan-result.png)

- "removed" = 앱에서 `active: false`인 계정. Okta 상태에는 변화 없다
- "0 groups scanned" — `GET /Groups`는 나갔으나 Okta가 Push로 만든 그룹은 Import 대상에서 제외된다
- 확인 화면에서 앱 전용 계정이 기존 Okta 사용자와 EXACT match(username·email 일치)로 잡힌다. 드롭다운은 EXACT / NEW / EXISTING I specify / IGNORE — AD Import와 같은 UI다
- Imported User 열의 Name이 공란이었다 — 서버 레코드에 `name.givenName/familyName`은 있고 `displayName`은 없었다. Import 방향 매핑이 core name 구조체를 그대로 읽지 않는 것으로 보인다(원인 미확인)

![EXACT match 확인 화면 — Imported User의 Name은 공란, 드롭다운은 EXACT/NEW/EXISTING/IGNORE](/assets/images/okta01/08-import-exact-match.png)

![EXACT match 선택 후 Confirm Assignments 1](/assets/images/okta01/09-import-confirm-assignments.png)

- Confirm(EXACT) → **앱으로 나가는 요청 없이 Okta 내부 링크만 생성된다.** Assignments에 Individual로 표시되어 Push로 만든 할당과 구분되지 않는다

![Confirm 다이얼로그 — 기존 Okta 사용자 1명에게 할당, 신규 생성 0](/assets/images/okta01/10-import-confirm-dialog.png)

![Assignments — Import 링크 사용자도 Individual로 표시된다](/assets/images/okta01/11-assignments-individual.png)

## 14. Import 링크와 Group Push

- Import 링크 직후 그룹 PUT은 없다. 11절(할당 → 즉시 그룹 PUT)과 비대칭이다
- Push Groups → Push now → `GET /Groups/{app_group_id}`×2 → PUT×2, members 3명(Import 링크 사용자 포함)

![Push Groups — Push now로 그룹 멤버십 강제 동기화](/assets/images/okta01/12-push-now.png)

![서버 로그 — 그룹 GET×2 후 PUT×2, members에 Import 링크 사용자 포함 3명](/assets/images/okta01/13-push-put-members.png)

- Push now는 Okta 쪽 멤버 목록 전체를 다시 PUT하는 강제 동기화다
- 앱에 따로 만든 계정을 Import로 붙인 뒤에는 Push now 또는 다음 멤버십 변경 이벤트가 있어야 앱 그룹이 맞춰진다

## 15. 정리

| 조작 | 앱으로 나가는 요청 | 비고 |
|---|---|---|
| 연결 테스트 | GET /Users count=2 | ServiceProviderConfig 안 읽음 |
| 할당 | filter GET → POST | externalId = Okta ID, password 포함 |
| 프로필 변경 | GET → 전체 PUT | 404면 중단, 재시도 없음 |
| 할당 해제 | GET → PUT active:false | 그룹 PUT 없음 |
| 재할당 | filter → GET → PUT active:true → 그룹 PUT | 재생성 아님 |
| 그룹 푸시 | POST /Groups → GET/PUT | 할당된 사용자만 members |
| 멤버 변경 | 그룹 GET → 전체 PUT | add/remove 아님 |
| Import | GET /Users + GET /Groups (100건 페이지) | 링크만, 앱 호출 없음 |
| Push now | 그룹 GET/PUT×2 | 전체 재동기화 |

- Okta는 서버 capability를 읽지 않고, 수정은 전부 read-modify-write PUT이다
- 할당·해제·Import·Push는 서로 다른 경로이고 그룹 동기화가 따라오는 조건이 제각각이다. "앱 쪽 상태가 왜 이런가"는 어느 경로로 만들어졌는지를 먼저 봐야 한다
- SCIM 서버 구현 쪽 교훈: writeOnly 속성을 응답에 내보내면 IdP의 read-modify-write 경로로 그 값이 왕복한다

## 16. 실습 중 실수

- 서버 코드를 고친 뒤 재기동 확인 없이 결론을 두 번 뒤집었다. 판정 전에 실행 중 프로세스의 동작을 직접 확인해야 한다
- PowerShell 5의 `Set-Content -Encoding UTF8`은 BOM을 붙이고, `-Encoding` 없는 `Get-Content`는 CP949로 읽는다. 서버 파일 1회 손상, JSON 저장소 1회 기동 실패
- 저장소 삭제로 8절의 404 시나리오가 우연히 생겼다 — 결과적으로 가장 실무적인 관찰이 됐다
- cloudflared quick tunnel은 재시작마다 주소가 바뀐다. 재개 시 Base URL 갱신이 첫 작업이다

## 다음 편

[2편]({% post_url 26-09-22-okta-scim-provisioning-2 %})에서 장애·퇴사·복직 체인을 다룬다.

- 연결 장애 중 할당과 Retry, AD Disable → Okta → 앱 비활성화 푸시 실패, AD Enable → 재링크 절차
- AD 그룹 멤버 변경의 앱 그룹 전파, 비활성 멤버의 Push now 처리

---

[^1]: RFC 7643 (SCIM Core Schema), RFC 7644 (SCIM Protocol)
[^2]: Okta Help, "Add SCIM provisioning to app integrations" — <https://help.okta.com/oie/en-us/content/topics/apps/apps_app_integration_wizard_scim.htm>
[^3]: RFC 7643 §7 — password 속성은 mutability `writeOnly`, returned `never`
