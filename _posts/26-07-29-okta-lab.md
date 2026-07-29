---
layout: single
title: "Okta 랩 2 — client_credentials와 SAML 2.0, 그리고 refresh token rotation의 replay 탐지"
excerpt: "전편에서 남긴 다음 단계를 이어간다. API Services 앱으로 client_credentials를 실측해 openid 스코프가 거부되는 지점과 sub=cid 구조를 확인하고, refresh token rotation을 켜서 전편의 미해결 항목이었던 토큰 무효화의 정체가 replay 탐지에 의한 체인 전체 폐기임을 재현한다. 이어 SAML 2.0 SP를 붙여 attribute statement와 group filter를 나누어 넣고, AuthnContextClassRef가 고정값으로 나오는 문제를 session.amr로 우회한다."
date: 2026-07-29
categories: [IAM]
tags: [Okta, OAuth2, OIDC, SAML, client-credentials, refresh-token, 실측]
---

[전편]({% post_url 26-07-28-okta-oidc %})에서 Okta의 OIDC Authorization Code + PKCE 플로우를 확인하고, 마지막에 세 가지를 다음 단계로 남겼다. API Services 앱으로 client_credentials 확인, SAML 2.0 앱으로 assertion 구조 비교, 그리고 정체가 불분명했던 refresh token 무효화 건이다. 이 글은 그 셋을 이어서 검증한 기록이다.

## 환경

- Okta Integrator Free Plan (전편과 동일 조직, `integrator-XXXXXXX.okta.com`)
- Custom Authorization Server: `default` (issuer `https://{org}.okta.com/oauth2/default`)
- 클라이언트: Windows PowerShell 5.1 + `Invoke-RestMethod`
- SAML SP: `http://localhost:5000` (전편의 Flask 테스트 앱 재사용)

## 1. API Services 앱 등록

Applications에서 `Create App Integration`으로 시작한다.

![Applications 목록에서 Create App Integration](/assets/images/okta_02/01-create-app-integration.png)

Sign-in method에서 `API Services`를 고른다. 설명에 "machine-to-machine authentication"이라고 명시돼 있는 대로, 사용자 컨텍스트 없이 클라이언트가 자기 자신으로 동작하는 앱 유형이다. 여기서 만든 앱은 Grant type이 Client Credentials로 고정되고 redirect URI를 요구하지 않는다.

![Sign-in method에서 API Services 선택](/assets/images/okta_02/02-sign-in-method-api-services.png)

앱 이름은 `oauth-service`로 했다. 생성 직후 General 탭에서 Client ID와 Client Secret이 발급된다. Client authentication은 기본값이 `Client secret`이고, `Public key / Private key`(private_key_jwt)로 바꿀 수도 있다.

![Client ID와 Client Secret 확인](/assets/images/okta_02/03-client-credentials.png)

## 2. 스코프와 인가 정책

client_credentials로 받을 access token에 실을 스코프를 Authorization Server에 먼저 만든다. Security → API → `default` → Scopes에서 `Add Scope`.

![default Authorization Server의 Scopes 탭](/assets/images/okta_02/04-authz-server-scopes.png)

`api.read`를 만들었다. User consent는 Implicit으로 뒀다. client_credentials에는 사용자가 개입하지 않으므로 동의 화면 자체가 나올 일이 없다.

![Add Scope — api.read](/assets/images/okta_02/05-add-scope-api-read.png)

여기서 끝이 아니다. 스코프를 만들어도 Access Policy가 허용하지 않으면 토큰이 나오지 않는다. Access Policies 탭에서 정책을 추가한다.

![Access Policies 탭](/assets/images/okta_02/06-access-policies.png)

`service-policy`를 만들고 적용 대상을 `All clients`가 아니라 방금 만든 `oauth-service` 하나로 한정했다. 전편에서 확인한 "접근이 세 층으로 나뉜다"는 구조가 여기서도 그대로 적용된다.

![Add Policy — service-policy](/assets/images/okta_02/07-add-policy-service.png)

정책 안에 룰을 넣는다. Grant type은 `Client Credentials`만 체크하고, Scopes requested를 `api.read`로 한정했다. Access token lifetime은 1시간이다.

![Add Rule — service-rule](/assets/images/okta_02/08-add-rule-service.png)

한 가지 더 있다. 앱의 General Settings에 `Proof of possession` 항목이 있는데, 체크하면 토큰 요청에 DPoP 헤더를 요구한다. 이번 검증은 순수 client_credentials 동작을 보는 것이라 해제 상태로 뒀다.

![Proof of possession(DPoP) 해제 상태](/assets/images/okta_02/09-dpop-disabled.png)

## 3. client_credentials 실측

client_secret_basic(Authorization 헤더)으로 먼저 요청했다.

```powershell
$s1 = Invoke-RestMethod -Method Post -Uri $uri `
  -Headers @{ Authorization = "Basic $basic" } `
  -Body @{ grant_type='client_credentials'; scope='api.read' } `
  -ContentType 'application/x-www-form-urlencoded'
```

`token_type: Bearer`, `expires_in: 3600`, `scope: api.read`로 정상 발급됐다. `expires_in`은 앞서 룰에 넣은 1시간과 일치한다. 응답에 `id_token`도 `refresh_token`도 없다. 사용자가 없으니 ID Token을 만들 근거가 없고, client_credentials에는 refresh token을 발급하지 않는 것이 RFC 6749의 권고다.

![client_secret_basic 토큰 발급 결과](/assets/images/okta_02/10-token-client-secret-basic.png)

client_secret_post(본문에 `client_id`/`client_secret`)로도 동일하게 성공했다. 그다음 `scope=openid`로 던져봤다.

```json
400
{"error":"invalid_scope","error_description":"Cannot request 'openid' scopes using client credentials."}
```

메시지가 명확하다. ADFS나 Entra ID에서 같은 시도를 하면 원인을 좁히는 데 시간이 걸리는데, Okta는 `error_description`에 이유를 그대로 적어준다. 전편에서 정리한 "실패 원인 구분" 항목의 연장선이다.

![client_secret_post 성공과 openid 스코프 거부](/assets/images/okta_02/11-token-post-openid-rejected.png)

발급된 access token의 payload를 디코드했다.

![access token payload](/assets/images/okta_02/12-access-token-payload.png)

| 클레임 | 값 |
|---|---|
| `iss` | `https://{org}.okta.com/oauth2/default` |
| `aud` | `api://default` |
| `cid` | 클라이언트 ID |
| `sub` | **클라이언트 ID (cid와 동일)** |
| `scp` | `[api.read]` |

`sub`가 `cid`와 같은 값이다. 사용자 컨텍스트가 없으므로 주체(subject)가 클라이언트 자신이 된다. 리소스 서버에서 토큰을 검증할 때 `sub`를 사용자 식별자로 가정하고 짜면, M2M 토큰이 들어오는 순간 클라이언트 ID를 사용자 ID로 오인하게 된다. `cid`와 `sub`가 같으면 M2M, 다르면 사용자 위임 흐름으로 구분하는 편이 안전하다.

## 4. refresh token rotation — 전편 미해결 항목의 재현

전편 9절에 남긴 항목이다. rotation이 꺼져 있고 발급한 지 10분밖에 안 된 refresh token이 `invalid_grant`로 죽었고, System Log에는 `invalid_refresh_token`만 남았다. 남은 가설은 그 직전의 code 재사용 시도가 replay 탐지를 건드렸을 가능성이었다.

이번에는 rotation을 명시적으로 켜고 replay를 의도적으로 일으켜, 그 탐지가 어디까지 파급되는지 확인했다. 앱 설정의 `Refresh token behavior`를 `Rotate token after every use`로 바꾸고 Grace period는 0초로 뒀다.

![Refresh token behavior를 rotation으로 변경](/assets/images/okta_02/13-refresh-token-rotation-on.png)

전편과 같은 Authorization Code + PKCE 흐름으로 토큰을 받아 RT1을 확보했다.

![rotation 테스트 — 토큰 교환](/assets/images/okta_02/14-rotation-test-setup.png)

RT1으로 갱신해 RT2를 받았다. 값이 바뀌었으므로 rotation은 정상 동작한다.

```
1단계 RT1 확보: QJDMzL0T1xv4...
2단계 RT2 확보: BxD9ht7a9M5k...
   회전 발생 여부(RT1 != RT2): True
```

여기서 이미 사용한 RT1을 다시 던졌다.

```json
400
{"error":"invalid_grant","error_description":"The refresh token is invalid or expired."}
```

예상대로 거부된다. 전편에서 봤던 것과 **문구가 완전히 동일한** 응답이다.

![RT1 재사용 거부](/assets/images/okta_02/15-rotation-replay-rejected.png)

핵심은 다음 단계다. replay가 탐지된 뒤, 정상적으로 발급받았고 아직 쓰지 않은 RT2가 여전히 유효한지 확인했다.

```json
4단계 RT2 사용
   FAILURE - replay 탐지가 후속 토큰까지 무효화
400
{"error":"invalid_grant","error_description":"The refresh token is invalid or expired."}
```

RT2도 죽었다. Okta는 replay를 탐지하면 해당 토큰만 거부하는 것이 아니라 그 인증에서 파생된 refresh token 체인 전체를 폐기한다. OAuth 2.1 초안과 RFC 9700이 rotation 구현에 권고하는 동작 그대로다. 탈취된 토큰이 먼저 사용되면 정상 클라이언트의 토큰도 함께 죽으면서 침해가 표면화된다.

![replay 탐지가 RT2까지 무효화](/assets/images/okta_02/16-rotation-chain-revoked.png)

전편의 미해결 항목에 대해 말할 수 있는 것은 여기까지다. 재사용 탐지가 체인 전체를 폐기한다는 것, 그리고 그 결과가 `invalid_grant` + `The refresh token is invalid or expired.`라는 전편과 동일한 응답으로 나타난다는 것은 확인했다. 다만 전편 사례는 rotation이 꺼진 상태였고 직접 유발한 것은 authorization code 재사용이었다. code 재사용이 refresh token 폐기까지 트리거하는지는 이번 실험으로 증명되지 않는다. 증상이 같다는 정황이 하나 늘었을 뿐이라, 이 부분은 여전히 열어둔다.

## 5. SAML 2.0 앱 등록

같은 조직에 SAML SP를 붙인다. `Create App Integration`에서 이번에는 `SAML 2.0`을 고른다.

![Sign-in method에서 SAML 2.0 선택](/assets/images/okta_02/17-saml-sign-in-method.png)

앱 이름은 `saml-sp`.

![SAML 앱 General Settings](/assets/images/okta_02/18-saml-general-settings.png)

SAML Settings에서 ACS URL과 Audience URI(SP Entity ID)를 넣는다. Name ID format은 `Unspecified`, Application username은 `Okta username`으로 뒀다.

![SAML Settings — ACS URL과 Audience URI](/assets/images/okta_02/19-saml-settings.png)

Entra ID가 OIDC 앱(앱 등록)과 SAML 앱(엔터프라이즈 애플리케이션)을 서로 다른 화면으로 갈라놓은 것과 달리, Okta는 `Create App Integration` 한 곳에서 sign-in method만 바꿔 고른다. 앱 목록도 프로토콜과 무관하게 하나로 유지된다.

## 6. Attribute statement 구성

만들어진 앱의 Sign On 탭에서 assertion에 실을 속성을 정한다.

![saml-sp의 Sign On 탭](/assets/images/okta_02/20-saml-sign-on-tab.png)

초기 상태는 비어 있다. `Add expression`으로 하나씩 넣는다.

![Attribute statements 초기 상태](/assets/images/okta_02/21-attribute-statements-empty.png)

이름과 Okta Expression Language 표현식을 짝지어 넣는 방식이다. `email`은 `user.profile.email`.

![Add expression — email](/assets/images/okta_02/22-add-expression-email.png)

그룹도 표현식으로 넣을 수 있다. `user.getGroups({'group.profile.name': '.*'})`.

![Add expression — groups](/assets/images/okta_02/23-add-expression-groups.png)

`email`, `firstName`, `lastName`, `groups` 네 개를 구성했다.

![Attribute statements 구성 완료](/assets/images/okta_02/24-attribute-statements-done.png)

그런데 Okta에는 그룹 전용 블록인 `Group attribute statements`가 따로 있다. 표현식을 쓰지 않고 이름·Name format·필터만으로 선언하는 방식이다. 그룹은 이쪽으로 옮겨 `groups` 이름에 `Matches regex` `.*` 필터로 재설정했다.

![Group attribute statements 재설정](/assets/images/okta_02/25-group-attribute-statements.png)

두 블록에 같은 이름을 넣으면 assertion에 동일 이름 Attribute가 중복으로 실릴 수 있다. 그룹은 한쪽에만 두는 편이 안전하다. 전편에서 OIDC `groups` 클레임을 만들 때 정규식 필터에 걸렸던 것과 같은 함정이 SAML 쪽에도 그대로 있는 셈이다.

## 7. AuthnContextClassRef 고정 문제와 amr 우회

SP에 SSO를 걸고 브라우저 개발자 도구 Network 탭에서 ACS로 들어오는 `SAMLResponse`를 캡처했다. Base64로 인코딩된 form parameter 하나로 전달된다.

![SAMLResponse form parameter 캡처](/assets/images/okta_02/27-samlresponse-payload.png)

디코드해서 확인하는 과정에서 걸린 지점이 `AuthnContextClassRef`다. MFA를 통과해도 값이 `PasswordProtectedTransport`로 고정돼 나온다. SP 입장에서는 assertion만 보고 "이 세션이 MFA를 거쳤는지"를 판별할 수 없다.

OIDC였다면 ID Token의 `amr` 클레임을 보면 된다. SAML에는 대응하는 표준 요소가 없지만, Okta Expression Language의 `session.amr`을 attribute statement로 내보내면 같은 정보를 SP에 전달할 수 있다.

![Add expression — amr = session.amr](/assets/images/okta_02/26-add-expression-amr.png)

다시 SSO를 걸어 assertion의 AttributeStatement를 파싱했다.

```
groups = Everyone, app-saml, dept-engineering
firstName = ...
lastName = ...
amr = mfa, otp, pwd, okta_verify
email = ...
```

`groups`는 다중값 Attribute 하나로 실렸고, `amr`도 의도한 대로 들어왔다.

![디코드한 AttributeStatement](/assets/images/okta_02/28-decoded-attributes.png)

`amr`은 값 하나가 아니라 `AttributeValue` 4개를 가진 다중값 Attribute로 나온다. `pwd`(비밀번호), `otp`, `okta_verify`, 그리고 이들을 묶는 `mfa`가 함께 실린다. 어떤 인증 수단을 거쳤는지까지 SP가 알 수 있다.

```xml
<Attribute Name="amr" NameFormat="...attrname-format:unspecified">
  <AttributeValue xsi:type="xs:string">mfa</AttributeValue>
  <AttributeValue xsi:type="xs:string">otp</AttributeValue>
  <AttributeValue xsi:type="xs:string">pwd</AttributeValue>
  <AttributeValue xsi:type="xs:string">okta_verify</AttributeValue>
</Attribute>
```

![amr Attribute의 XML 구조](/assets/images/okta_02/29-amr-attribute-xml.png)

다만 이건 표준 요소가 아니라 벤더 확장이다. SP를 여러 IdP에 붙일 계획이라면 `AuthnContextClassRef`를 기준으로 삼되 Okta에서는 이 값을 신뢰할 수 없다는 점을 감안해야 하고, Okta 전용이라면 `amr` attribute를 쓰는 편이 정보량이 많다.

## 8. 정리

| 항목 | 확인 내용 |
|---|---|
| client_credentials + `openid` | `invalid_scope`로 거부, `error_description`에 사유 명시 |
| M2M access token의 `sub` | 클라이언트 ID (`cid`와 동일) — 사용자 식별자로 쓰면 안 됨 |
| client_credentials의 refresh token | 미발급 |
| refresh token rotation | 재사용 탐지 시 체인 전체 폐기 (후속 RT2까지 무효화) |
| rotation 실패 응답 | `invalid_grant` + `The refresh token is invalid or expired.` |
| SAML 앱 등록 경로 | OIDC와 동일한 `Create App Integration` (Entra ID와 대비) |
| 그룹 전달 | attribute expression과 group filter 두 경로 — 중복 주의 |
| `AuthnContextClassRef` | MFA 통과해도 `PasswordProtectedTransport` 고정 |
| MFA 여부 판별 | `session.amr`을 attribute로 내보내 우회 (다중값) |

프로토콜 세 개를 같은 조직에서 확인했다. 남은 것은 Okta AD Agent로 온프레미스 AD를 연동해 ADFS의 페더레이션 모델과 구조를 대조하는 작업이다. 전편의 refresh token 무효화 건은 code 재사용과의 인과가 아직 미확인 상태로 남아 있어, AD 연동 이후 별도로 통제 실험을 설계할 생각이다.
