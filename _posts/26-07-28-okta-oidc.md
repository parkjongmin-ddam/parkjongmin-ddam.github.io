---
layout: single
title: "Okta Integrator Free Plan으로 OIDC PKCE 동작 검증하기 — ADFS·Entra ID와 비교"
date: 2026-07-28
categories: [IAM]
tags: [Okta, OIDC, OAuth2, PKCE, ADFS, EntraID]
---

ADFS와 Entra ID를 대상으로 진행했던 OAuth 2.0 / OIDC 검증을 Okta까지 확장했다. 세 IdP를 같은 조건에서 비교하기 위한 작업이고, 이 글은 그 첫 단계인 OIDC Authorization Code + PKCE 플로우 검증 기록이다.

## 1. 환경

Okta는 개발·테스트용 무료 조직인 Integrator Free Plan을 제공한다. 카드 등록 없이 가입할 수 있고 만료도 없다. `developer.okta.com/signup`에는 Auth0 Platform, Okta Platform 30일 트라이얼, Integrator Free Plan이 함께 나오는데, 트라이얼은 기간이 끝나면 조직이 잠기므로 계속 붙잡고 실험하려면 세 번째를 골라야 한다.

![Okta 가입 플랜 선택](/assets/images/okta/01-signup-plan-select.png)

가입 폼에 입력한 업무 이메일이 조직의 최초 슈퍼 관리자 계정이 된다.

![Okta 가입 폼](/assets/images/okta/02-signup-form.png)

활성화 메일의 안내문에 "this org is not recommended for production uses"가 명시돼 있다. 링크 유효기간은 7일이다.

![활성화 메일](/assets/images/okta/03-activation-email.png)

활성화하면 비밀번호를 설정한다. Okta는 이 단계를 "보안 방법 설정(authenticator enrollment)"으로 다룬다. 비밀번호조차 여러 authenticator 중 하나로 취급하는 구조라, 뒤에 MFA를 붙일 때도 같은 UI가 재사용된다.

![비밀번호 설정](/assets/images/okta/04-set-password.png)

관리자 계정은 비밀번호만으로 끝나지 않고 Okta Verify 등록까지 요구한다. 이 조직 레벨 authenticator 정책이 뒤에서 테스트 계정 로그인과 ID Token의 `amr` 클레임에 그대로 반영된다.

![Okta Verify 등록](/assets/images/okta/05-mfa-enroll-okta-verify.png)

| 항목 | 값 |
|---|---|
| org 도메인 | `integrator-XXXXXXX.okta.com` |
| Custom Authorization Server issuer | `https://{org}.okta.com/oauth2/default` |
| Audience | `api://default` |
| 활성 사용자 한도 | 10명 |
| Workflows | 5개 |
| 비활성화 조건 | 180일간 로그인 없음 |

포함 기능은 SSO, Universal Directory, Adaptive MFA, Lifecycle Management, API Access Management, Workflows다. Active Directory 연동도 메뉴에 노출된다.

테스트 계정은 `Directory > People > Add person`으로 만들었다. Activation을 `Activate now`로 두고 `I will set password`를 체크하면 활성화 메일 왕복 없이 바로 쓸 수 있는 계정이 생긴다.

![사용자 추가](/assets/images/okta/06-add-person.png)

3명을 만들었다. 좌하단에 Integrator Free Plan의 활성 사용자 카운터가 보인다.

![People 목록](/assets/images/okta/07-people-list.png)

사용자 상세의 Profile 탭에서 `login`, `firstName`, `lastName` 속성을 확인할 수 있다. 이 값들이 뒤에 ID Token의 `preferred_username`, `name` 클레임으로 매핑되는 원본이다.

![사용자 프로필 속성](/assets/images/okta/08-user-profile-edit.png)

그룹은 두 층으로 나눴다.

- 조직 그룹 `dept-engineering` — 소속 표현
- 앱 접근 그룹 `app-oidc-native` — 권한 부여

소속과 권한을 분리해두면 뒤에 그룹 규칙으로 멤버십을 자동화해도 앱 할당은 별도로 유지된다.

![그룹 생성](/assets/images/okta/09-add-group.png)

만든 그룹에 테스트 계정을 할당했다.

![그룹에 사용자 할당](/assets/images/okta/10-assign-people-to-group.png)

![그룹 멤버 확인](/assets/images/okta/11-group-members.png)

## 2. 앱 등록

`Applications > Create App Integration`에서 시작한다.

![App Integration 생성](/assets/images/okta/12-create-app-integration.png)

Sign-in method는 OIDC를 선택했다. 같은 화면의 API Services는 client credentials 전용(M2M)이라 사용자 로그인이 필요한 이번 시나리오와는 맞지 않는다.

![Sign-in method 선택](/assets/images/okta/13-signin-method-oidc.png)

Application type은 Native Application을 골랐다. 앞선 ADFS·Entra 검증과 조건을 맞추기 위한 선택이다.

![Application type — Native](/assets/images/okta/14-app-type-native.png)

Grant type은 Authorization Code와 Refresh Token만 켰다.

![Grant type 설정](/assets/images/okta/15-grant-types.png)

Redirect URI는 다음과 같이 잡았다.

```
Sign-in  : http://localhost:5000/callback/okta-oidc
Sign-out : http://localhost:5000/
```

![Redirect URI와 Assignments](/assets/images/okta/16-redirect-uri-assignments.png)

Native 앱은 client secret이 없고 PKCE가 강제된다. Client authentication이 `None`으로 고정되고 `Require PKCE as additional verification`이 체크된 상태로 생성된다.

ADFS는 discovery에 `code_challenge_methods_supported`를 광고하지 않으면서 내부적으로만 PKCE를 검증했다. Okta는 같은 RFC 9700 권고를 따르면서도 UI에서 필수 여부를 명시적으로 드러낸다.

![Client Credentials — PKCE 필수](/assets/images/okta/17-client-credentials-pkce.png)

## 3. 접근이 세 층으로 나뉜다

앱을 만들고 authorize 요청을 던졌더니 두 번에 걸쳐 다른 이유로 막혔다.

첫 번째는 로그인 화면에서 인라인 배너가 떴다.

```
이 앱에 액세스할 수 없습니다. 액세스를 요청하려면 관리자에게 문의하십시오.
```

![미할당 사용자 차단](/assets/images/okta/30-unassigned-user-blocked.png)

앱에 그룹이 할당되지 않은 상태였다. 주목할 부분은 차단 시점이다. username 입력 후 비밀번호 화면에서 표시됐다. 인증이 완료되기 전에 접근 권한 유무가 노출된다는 뜻이다.

`Assign to Groups`로 `dept-engineering`을 앱에 연결했다.

![앱에 그룹 할당](/assets/images/okta/18-assign-app-to-groups.png)

그룹을 할당하고 재시도했더니 이번에는 인증까지 성공한 뒤 실패했다. System Log는 이렇게 남았다.

```
OAuth2 authorization request   FAILURE: no_matching_policy
  target: default (AuthorizationServer)
Authentication of user via MFA SUCCESS
User login to Okta             SUCCESS
Evaluation of sign-on policy   CHALLENGE
```

Authorization Server의 Access Policy가 비어 있었다. 정리하면 Okta는 세 개의 독립된 게이트를 거친다.

| 게이트 | 관리 위치 | 실패 시 증상 |
|---|---|---|
| 앱 할당 | Applications > Assignments | 로그인 화면 인라인 배너 |
| 인증 정책 | 앱 > Sign On | MFA 챌린지, 정책 위반 메시지 |
| 인가 정책 | Security > API > Authorization Servers > Access Policies | `no_matching_policy` |

ADFS는 RP Trust 하나에 발급 규칙과 접근 정책이 함께 들어 있다. Okta는 이 층이 완전히 분리돼 있어, 하나만 설정하고 동작을 기대하면 어긋난다.

Access Policy는 `Security > API > default`에서 만들었다.

![API Access Policy 생성](/assets/images/okta/19-api-policy-create.png)

정책은 껍데기고 실제 판정은 Rule이 한다. Grant type, 사용자 조건, 스코프 조건에 더해 토큰 수명까지 여기서 정한다.

```
Policy   : Assign to = All clients
Rule     : Grant type = Authorization Code, Refresh Token
           User       = Any user assigned the app
           Scopes     = Any scopes
```

![Access Policy Rule 추가](/assets/images/okta/20-api-policy-rule.png)

## 4. PKCE 강제 여부 — negative-first

정상 플로우를 확인하기 전에 실패부터 만들었다. `code_challenge` 없이 authorize를 호출했다.

```
GET /oauth2/default/v1/authorize
    ?client_id={CLIENT_ID}
    &response_type=code
    &scope=openid profile email
    &redirect_uri=http://localhost:5000/callback/okta-oidc
    &state=test123
```

결과는 HTTP 400이었고 Okta가 자체 오류 페이지를 렌더링했다.

```
오류 코드: invalid_request
애플리케이션에 PKCE 코드 챌린지가 필요합니다.
```

두 가지가 눈에 띈다.

첫째, 로그인 화면이 뜨지 않았다. 인증을 시작하기 전에 요청 자체를 거부한다. 사용자 상호작용이 낭비되지 않고 authorization code도 생성되지 않는다.

둘째, 오류를 `redirect_uri`로 되돌려보내지 않았다. OAuth 2.0 규격상 `invalid_request`는 리다이렉트로 전달할 수 있지만 Okta는 자체 페이지를 택했다. 클라이언트 앱의 오류 핸들링 코드는 호출되지 않는다.

## 5. 정상 플로우

RFC 7636 Appendix B의 검증 쌍을 사용했다.

```
code_verifier  : dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
code_challenge : E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
```

`offline_access`를 스코프에 넣어야 refresh token이 발급된다. Grant type만 켜서는 나오지 않는다.

`code_challenge`를 포함해 authorize를 호출하면 이번에는 정상적으로 로그인 화면이 뜬다. 상단에 앱 이름이 노출된다.

![Authorize 로그인 화면](/assets/images/okta/21-authorize-login.png)

테스트 계정으로 로그인하니 조직 authenticator 정책 때문에 Okta Verify 등록이 먼저 걸렸다. 관리자에게 적용됐던 정책이 일반 사용자에게도 그대로 적용된다. 이 등록을 마쳐야 authorization code가 발급된다.

![테스트 계정 MFA 등록](/assets/images/okta/22-mfa-enroll-test-user.png)

토큰 교환은 client secret 없이 `code_verifier`만으로 성공했다.

```powershell
$body = @{
  grant_type    = 'authorization_code'
  client_id     = '{CLIENT_ID}'
  code          = '{CODE}'
  redirect_uri  = 'http://localhost:5000/callback/okta-oidc'
  code_verifier = 'dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk'
}
Invoke-RestMethod -Method Post -Uri "$issuer/v1/token" `
  -Body $body -ContentType 'application/x-www-form-urlencoded'
```

`token_type: Bearer`, `expires_in: 3600`과 함께 access_token · id_token · refresh_token이 모두 반환됐다.

![토큰 응답](/assets/images/okta/23-token-response.png)

### 발급된 토큰

두 토큰을 디코딩한 결과다.

![토큰 디코딩 결과](/assets/images/okta/24-token-decoded.png)

Access Token
```json
{
  "iss": "https://{org}.okta.com/oauth2/default",
  "aud": "api://default",
  "cid": "{CLIENT_ID}",
  "uid": "{OKTA_USER_ID}",
  "scp": ["profile", "offline_access", "email", "openid"],
  "sub": "{USERNAME}@{org}.okta.com"
}
```

ID Token
```json
{
  "sub": "{OKTA_USER_ID}",
  "aud": "{CLIENT_ID}",
  "name": "{DISPLAY_NAME}",
  "amr": ["mfa", "otp", "pwd", "okta_verify"],
  "idp": "{IDP_ID}",
  "preferred_username": "{USERNAME}@{org}.okta.com",
  "at_hash": "..."
}
```

`sub` 값이 두 토큰에서 다르다. Access Token은 UPN 문자열, ID Token은 불투명한 Okta user ID다. 앱이 `sub`를 사용자 키로 쓸 때 어느 토큰을 참조하느냐에 따라 값이 갈린다. 안정적인 식별자는 ID Token의 `sub` 또는 Access Token의 `uid`이며 두 값은 동일하다.

`amr`에는 실제 사용된 인증 수단이 그대로 실린다. ADFS는 `authnmethodsreferences` 클레임에 URI 형태로 담고, Entra는 `amr`을 쓰되 값 어휘가 다르다.

## 6. PKCE 실패가 code를 소진시키는가

ADFS 검증에서 확인했던 특성이다. PKCE 교환에 실패하면 그 authorization code가 소진되어 올바른 verifier로 재시도해도 실패한다. Entra ID는 소진시키지 않았다.

기준선부터 확인했다. 정상적으로 교환을 마친 code를 그대로 한 번 더 던지면 거부된다. authorization code는 일회용이라는 RFC 6749 §4.1.2 요구사항 그대로다.

![정상 교환 후 code 재사용](/assets/images/okta/31-code-replay-error.png)

문제는 교환이 **실패한** 경우다. Okta는 어느 쪽인지 확인하기 위해 다음 순서로 테스트했다.

1. 새 authorization code 발급
2. 틀린 `code_verifier`로 교환 시도
3. 맞는 `code_verifier`로 동일 code 재시도

2단계 결과.

```json
{"error":"invalid_grant","error_description":"PKCE verification failed."}
```

3단계 결과.

```json
{"error":"invalid_grant","error_description":"The authorization code is invalid or has expired."}
```

![PKCE 실패가 code를 소진](/assets/images/okta/32-pkce-failure-consumes-code.png)

Okta는 ADFS와 같다. 검증 실패만으로 code가 소진된다.

| IdP | PKCE 실패 후 재시도 | 오류 식별자 |
|---|---|---|
| ADFS | 불가 (소진) | MSIS9720 |
| Entra ID | 가능 (미소진) | AADSTS501481 |
| Okta | 불가 (소진) | `invalid_grant` / PKCE verification failed. |

표본이 셋이 되니 Entra가 예외적으로 관대한 쪽이라고 말할 근거가 생겼다.

RFC 6749는 code 재사용 시 거부를 요구하지만, 검증 실패 시 code를 폐기할지는 명시하지 않는다. OAuth 2.0 Security BCP가 권고하는 보수적 처리를 ADFS와 Okta가 따르고 Entra는 따르지 않는 구조로 정리된다.

오류 문구가 두 단계를 구분해준다는 점도 기록해둘 만하다. PKCE 불일치와 소진된 code 재사용이 서로 다른 `error_description`으로 나온다. ADFS가 양쪽을 MSIS9720으로 뭉뚱그리는 것과 대비된다. 진단은 쉬워지지만 공격자에게 "verifier만 틀렸다"는 정보를 주는 셈이라 트레이드오프가 있다.

구현 관점에서는 하나로 정리된다. PKCE 실패는 토큰 교환 재시도로 복구할 수 없고 authorize 요청부터 다시 시작해야 한다.

System Log에도 동일 초에 두 이벤트가 연달아 남는다.

```
OAuth2 token request  FAILURE: pkce_verification_failed
OAuth2 token request  FAILURE: invalid_authorization_code
```

## 7. groups 클레임과 정규식 함정

기본 상태에서는 ID Token에 그룹 정보가 없다. Authorization Server에 클레임을 직접 추가해야 한다.

`Security > API > Authorization Servers > default > Claims > Add Claim`

| 필드 | 값 |
|---|---|
| Name | `groups` |
| Include in token type | ID Token / Always |
| Value type | Groups |
| Filter | Matches regex |
| Include in | Any scope |

여기서 한 번 막혔다. Filter에 `*`를 넣었더니 클레임이 아예 나오지 않았다. `*`는 단독으로 성립하지 않는 정규식이라 매칭되는 그룹이 없었던 것이다.

![groups 클레임 regex 오류](/assets/images/okta/25-groups-claim-regex-error.png)

`.*`로 고치니 정상 출력됐다.

![groups 클레임 설정](/assets/images/okta/26-groups-claim-config.png)

```
groups : {Everyone, app-oidc-native, dept-engineering}
```

![groups 클레임 검증](/assets/images/okta/29-groups-claim-verified.png)

잘못된 정규식을 넣어도 저장은 되고 오류도 나지 않는다. 조용히 빈 결과만 반환된다.

`Include in token type`을 ID Token으로 고르면 옆에 드롭다운이 하나 더 붙는데, `Userinfo / id_token request`를 선택하면 authorization code 플로우에서는 클레임이 나오지 않는다. `Always`여야 한다.

운영에서는 `.*` 대신 `^(dept|app)-` 같은 접두사 필터로 좁히는 편이 낫다. `Everyone`까지 전부 나오면 토큰 크기가 커지고 불필요한 정보가 노출된다. 홈랩에서 oauth2-proxy 세션 쿠키가 4KB를 넘어 nginx ingress가 502를 뱉었던 것도 같은 계열의 문제였다.

## 8. Refresh token 동작

앱 설정의 `Refresh token behavior`는 기본값이 `Use persistent token`이다. 이 상태에서 갱신하면 refresh token 값이 그대로 유지된다.

```
refresh SUCCESS
refresh token 동일 여부: True
```

![refresh token 동작 확인](/assets/images/okta/28-refresh-token-test.png)

갱신 시 클레임이 재평가된다는 점도 확인됐다. 클레임을 추가하기 **전에** 발급된 refresh token으로 갱신했는데, 새로 받은 ID Token에는 `groups`가 들어 있었다. 갱신 시점의 Authorization Server 설정과 사용자 상태를 다시 읽는다. 반대로 말하면 정책을 축소하는 방향으로 바꿔도 기존 토큰이 살아 있는 한 즉시 반영되지 않으므로, 권한 회수에는 토큰 폐기가 함께 필요하다.

`auth_time`은 원래 인증 시각이 유지되고 `iat`만 갱신된다. 앱에서 재인증 요구 정책을 만들 때 기준으로 삼을 수 있는 값이다.

![갱신 전 기준 ID Token](/assets/images/okta/27-id-token-after-claim.png)

## 9. 미해결 항목

검증 중간에 refresh token이 한 번 무효화됐다.

```json
{"error":"invalid_grant","error_description":"The refresh token is invalid or expired."}
```

System Log에는 `invalid_refresh_token`으로만 남았다. rotation은 꺼져 있었고 발급 후 10분밖에 지나지 않아 만료도 아니다.

처음에는 그 직전에 수행한 Authorization Server 클레임 생성이 원인이라고 추정했다. 통제 실험으로 확인해보니 아니었다. 클레임을 다시 수정한 직후 동일한 refresh token으로 갱신에 성공했다.

남은 가설은 그 이전에 수행한 code 재사용 시도가 replay 탐지를 유발했을 가능성이다. Okta 문서는 refresh token 재사용이 탐지되면 최근 발급된 refresh token과 인증 이후의 access token을 무효화한다고 설명한다. authorization code 재사용에도 유사한 처리가 있다면 설명이 되지만, 문서에서 명시적 근거를 찾지 못했다. 별도 실험이 필요한 항목으로 남겨둔다.

## 10. 정리

| 항목 | ADFS | Entra ID | Okta |
|---|---|---|---|
| PKCE 미포함 요청 차단 시점 | 토큰 교환 | 토큰 교환 | authorize (로그인 이전) |
| PKCE 실패 시 code 소진 | 소진 | 미소진 | 소진 |
| 오류 식별 체계 | MSIS97xx | AADSTSxxxxx | `error` + `error_description` |
| 실패 원인 구분 | 단일 코드로 뭉뚱그림 | 구분됨 | 구분됨 |
| groups 클레임 발급 | 클레임 룰 + scope | 앱 등록 optional claims | Authorization Server 클레임 |
| 접근 통제 계층 | RP Trust 통합 | 앱 등록 + Conditional Access | 앱 할당 / 인증 정책 / 인가 정책 3층 |
| refresh token 획득 조건 | 별도 스코프 불필요 | `offline_access` | `offline_access` |

다음 단계는 API Services 앱으로 client_credentials 플로우를 확인하고, SAML 2.0 앱으로 assertion 구조와 NameID format을 비교하는 것이다. 그 뒤에 Okta AD Agent로 온프레미스 AD를 연동해 ADFS의 페더레이션 모델과 구조를 대조할 예정이다.