---
layout: single
title: "[IAM 개념 정리] 인증 개념 7가지 — 세션, JWT, 토큰, SSO, OAuth 2.0, OIDC"
excerpt: "로그인 후 서버가 매 요청마다 사용자를 식별하는 방법을 출발점으로 인증·인가, 세션과 쿠키, JWT, Access/Refresh Token, SSO, OAuth 2.0, OpenID Connect가 각각 어떤 문제를 해결하는지 순서대로 정리했다. SSO 장에서는 SAML 2.0·OIDC·WS-Federation의 인증 결과 전달 방식을 비교했고, 마지막 장에서 일곱 개념이 한 번의 로그인 흐름 안에서 함께 동작하는 과정을 단계별로 정리했다."
date: 2026-10-20
categories: [IAM]
tags: [authentication, authorization, session, jwt, oauth2, oidc, sso]
---

로그인할 때 비밀번호는 한 번만 보낸다. 그 뒤 서버는 매 요청마다 사용자를 어떻게 식별할까? 이 질문을 출발점으로 인증·인가, 세션, JWT, Access/Refresh Token, SSO, OAuth 2.0, OpenID Connect가 각각 어떤 문제를 해결하는지 순서대로 정리했다.

글의 구성은 Visualcoders 채널의 영상 [7 Authentication Concepts Every Senior Developer Should Know](https://www.youtube.com/watch?v=Zo4VpTSelUE)를 참고했다. 각 개념의 상세 설명과 보안 고려사항은 RFC와 OIDC 규격을 기준으로 보충했고, 다이어그램은 직접 작성했다.

---

## 1. 인증(Authentication)과 인가(Authorization)

![인증 vs 인가](/assets/images/2026-10-20-auth-7-concepts/01-authn-vs-authz.png)

### 개념

| 구분 | 인증 (AuthN) | 인가 (AuthZ) |
|---|---|---|
| 질문 | 누구인가? | 무엇을 할 수 있는가? |
| 입력 | 자격 증명 (비밀번호, 인증서, OTP, 생체 등) | 확인된 신원 + 정책 (역할, 속성, 소유 관계) |
| 결과 | 신원 확정 (예: `user_id = 1024`) | 허용 / 거부 |
| 실패 시 HTTP 응답 | `401 Unauthorized` | `403 Forbidden` |

- 인증은 요청 주체의 신원을 확정하는 단계이고, 인가는 확정된 신원이 특정 리소스에 특정 동작을 할 수 있는지 판단하는 단계다.
- 인증이 성공해도 접근이 자동으로 허용되지는 않는다. 예를 들어 로그인한 사용자가 `/photos/1024`를 `/photos/2048`로 바꿔 요청하면 인가 단계에서 거부해야 한다. 이 검사가 빠진 취약점이 IDOR(Insecure Direct Object Reference)이며, OWASP Top 10의 Broken Access Control에 해당한다.
- HTTP `401` 상태 코드 이름은 Unauthorized이지만 실제 의미는 "인증되지 않음"이다. 인증은 됐지만 권한이 없는 경우에는 `403`을 사용한다.

### 인가 모델

- RBAC(Role-Based Access Control): 역할에 권한을 부여하고 사용자에게 역할을 할당한다. 예: `admin`, `editor`, `viewer`
- ABAC(Attribute-Based Access Control): 사용자·리소스·환경 속성의 조합으로 판단한다. 예: 부서 = 리소스 소유 부서, 접속 위치 = 사내망
- 리소스 소유 기반: 리소스의 소유자 ID와 요청자 ID를 비교한다. 위의 사진 예시가 이 경우다.

### 다음 문제

HTTP는 무상태(stateless) 프로토콜이다. 각 요청은 독립적이라 서버는 직전 요청을 누가 보냈는지 기억하지 않는다. 비밀번호를 매 요청마다 보낼 수는 없으므로, 로그인 결과를 이후 요청과 연결하는 수단이 필요하다. 그 수단이 다음에 나오는 세션과 토큰이다.

---

## 2. 세션과 쿠키

![세션과 쿠키](/assets/images/2026-10-20-auth-7-concepts/02-session-cookie.png)

### 개념

- 세션: 서버가 로그인한 사용자의 상태를 저장한 기록이다. 세션 ID를 키로, 사용자 ID·권한·생성 시각 등을 값으로 저장한다.
- 쿠키: 서버가 `Set-Cookie` 헤더로 보내고 브라우저가 저장해 두었다가 같은 도메인 요청에 자동으로 첨부하는 작은 데이터다.
- 정리하면 쿠키는 세션 ID를 운반하는 수단이고, 세션은 그 ID가 가리키는 서버 측 기록이다.

### 동작 흐름

```http
POST /login HTTP/1.1
Content-Type: application/x-www-form-urlencoded

username=rahul&password=********
```

```http
HTTP/1.1 302 Found
Set-Cookie: sid=a91f...; Path=/; HttpOnly; Secure; SameSite=Lax
Location: /photos
```

```http
GET /photos HTTP/1.1
Cookie: sid=a91f...
```

1. 서버가 자격 증명을 검증하고 세션을 생성한다.
2. 추측할 수 없는 임의의 세션 ID를 쿠키로 내려보낸다.
3. 브라우저는 이후 요청마다 쿠키를 자동 첨부한다.
4. 서버는 세션 ID로 저장소를 조회해 사용자를 식별한다.

### 쿠키 보안 속성

| 속성 | 역할 |
|---|---|
| `HttpOnly` | JavaScript(`document.cookie`)에서 읽을 수 없게 해 XSS로 인한 세션 ID 탈취를 줄인다. |
| `Secure` | HTTPS 연결에서만 전송한다. |
| `SameSite` | 다른 사이트에서 시작된 요청에 쿠키를 붙일지 제어한다. `Strict` / `Lax` / `None`. CSRF 완화에 사용한다. |
| `Domain`, `Path` | 쿠키가 전송될 범위를 제한한다. |
| `Max-Age`, `Expires` | 만료 시점이다. 지정하지 않으면 브라우저 종료 시 삭제되는 세션 쿠키가 된다. |

### 세션 관리 시 주의사항

- 세션 고정(Session Fixation) 방지: 로그인 성공 시 기존 세션 ID를 폐기하고 새로 발급한다.
- 만료 정책: 유휴 타임아웃(일정 시간 요청이 없으면 만료)과 절대 타임아웃(로그인 후 최대 유지 시간)을 함께 둔다.
- 로그아웃: 브라우저의 쿠키만 지우는 것으로는 부족하고, 서버 측 세션을 삭제해야 한다.

### 장점과 한계

- 장점: 서버가 상태를 쥐고 있으므로 세션을 삭제하면 즉시 무효화된다. 강제 로그아웃, 동시 접속 제한이 쉽다.
- 한계: 서버를 여러 대로 확장하면 서버 1에서 만든 세션이 서버 2에는 없다. 해결 방법은 세 가지다.
  - 공유 세션 저장소(Redis, DB)를 둔다. 가장 일반적인 방식이다.
  - 로드밸런서의 Sticky Session으로 같은 사용자를 같은 서버로 보낸다. 서버 장애 시 세션이 유실된다.
  - 저장소 조회 없이 서버가 직접 검증할 수 있는 토큰을 사용한다. 이것이 JWT다.

---

## 3. JWT (JSON Web Token)

![JWT 구조와 검증](/assets/images/2026-10-20-auth-7-concepts/03-jwt.png)

### 개념

JWT(RFC 7519)는 클레임(claim, 주체에 대한 정보)을 JSON으로 담고 서명해서 전달하는 토큰 형식이다. 서버는 저장소를 조회하지 않고 서명과 클레임만으로 토큰을 검증한다.

### 구조

`.`으로 구분된 세 부분을 각각 Base64URL로 인코딩한다.

```text
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDI0Ii...  .SflKxwRJSMeKKF2QT4f...
└──────── Header ────────┘ └──────── Payload ───────┘ └─ Signature ─┘
```

Header

```json
{ "alg": "RS256", "typ": "JWT", "kid": "k1" }
```

Payload

```json
{
  "iss": "https://auth.example.com",
  "sub": "1024",
  "aud": "photo-api",
  "iat": 1760000000,
  "exp": 1760000900
}
```

Signature

```text
RSASHA256( base64url(header) + "." + base64url(payload), 개인키 )
```

### 주요 등록 클레임

| 클레임 | 의미 |
|---|---|
| `iss` | 발급자 |
| `sub` | 주체(사용자 식별자) |
| `aud` | 토큰을 받을 대상(수신자) |
| `exp` | 만료 시각 |
| `nbf` | 이 시각 이전에는 사용 불가 |
| `iat` | 발급 시각 |
| `jti` | 토큰 고유 ID (재사용 탐지, 폐기 목록에 활용) |

### 서명 알고리즘

- HS256(대칭키): 발급자와 검증자가 같은 비밀키를 공유한다. 검증하는 모든 서버가 토큰을 위조할 수도 있으므로 단일 서비스 내부에 적합하다.
- RS256 / ES256(비대칭키): 발급자는 개인키로 서명하고, 검증자는 공개키로 검증한다. 공개키는 JWKS 엔드포인트로 배포하고 `kid`로 키를 선택한다. 여러 서비스가 검증해야 하는 환경에 적합하다.

### 서버 검증 절차

1. `Authorization: Bearer <JWT>` 헤더에서 토큰을 추출한다.
2. Header의 `alg`가 서버가 허용한 알고리즘인지 확인한다. `alg: none`이나 예상과 다른 알고리즘은 거부한다(알고리즘 혼동 공격 방지).
3. `kid`에 해당하는 키로 서명을 검증한다. 내용이 한 글자라도 바뀌면 실패한다.
4. `exp`, `nbf`, `iss`, `aud`를 검증한다. 서버 간 시각 차이를 고려해 수십 초~수 분 정도의 허용 오차를 둔다.
5. 모두 통과하면 클레임을 신뢰하고 요청을 처리한다.

### 주의사항

- 서명된 JWT(JWS)는 암호화되지 않는다. Payload는 Base64URL 디코딩만으로 누구나 읽을 수 있으므로 비밀번호, 개인정보, 내부 시스템 정보를 넣으면 안 된다. 내용까지 숨겨야 하면 JWE를 사용한다.
- 발급한 토큰은 `exp` 전까지 유효하다. 로그아웃이나 권한 변경을 즉시 반영하려면 별도 장치가 필요하다.
  - 수명을 짧게(수 분~수십 분) 유지
  - `jti` 기반 폐기 목록(deny list) 운영 — 결국 상태 조회가 다시 생긴다.
  - 키 교체로 전체 토큰 무효화 — 영향 범위가 크다.
- 클레임이 많아지면 토큰이 커지고, 매 요청 헤더 크기가 늘어난다.

### 세션과 비교

| 항목 | 세션 | JWT |
|---|---|---|
| 상태 저장 위치 | 서버 | 토큰 자체 |
| 검증 방식 | 저장소 조회 | 서명·클레임 검증 |
| 즉시 무효화 | 쉬움 | 별도 장치 필요 |
| 수평 확장 | 공유 저장소 필요 | 공개키만 있으면 가능 |
| 서비스 간 전달 | 어려움 | 쉬움 |

JWT가 세션보다 일반적으로 우월한 것은 아니다. 단일 웹 서비스라면 세션이 단순하고 안전한 선택일 때가 많고, 여러 API 서버나 외부 서비스가 같은 토큰을 검증해야 할 때 JWT가 유리하다.

---

## 4. Access Token과 Refresh Token

![Access Token과 Refresh Token](/assets/images/2026-10-20-auth-7-concepts/04-access-refresh-token.png)

### 배경: Bearer 토큰의 위험

Bearer 토큰(RFC 6750)은 "토큰을 제시한 쪽"을 정당한 사용자로 간주한다. 서버는 토큰을 제시한 쪽이 원래 발급받은 사용자인지 구분하지 못한다. 토큰이 유출되면 만료 전까지 공격자가 그대로 사용할 수 있다.

수명을 짧게 하면 피해 기간은 줄지만 사용자는 자주 다시 로그인해야 한다. 두 요구를 함께 만족시키기 위해 토큰의 역할을 둘로 나눈다.

### 역할 분리

| 항목 | Access Token | Refresh Token |
|---|---|---|
| 용도 | 리소스 서버(API) 호출 | 새 Access Token 발급 |
| 전송 대상 | 리소스 서버, 매 요청 | 인가 서버의 토큰 엔드포인트, 필요할 때만 |
| 수명 | 짧음 (수 분~1시간) | 김 (수 시간~수십 일) |
| 권한 | 필요한 scope만 | 재발급 권한 |
| 노출 빈도 | 높음 | 낮음 |

Access Token은 자주 전송되므로 노출 가능성이 높지만 수명이 짧다. Refresh Token은 수명이 길지만 인가 서버에만 가끔 전송되므로 노출 기회가 적다.

### 갱신 흐름

```http
POST /token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&refresh_token=8xLOxBtZp8...&client_id=photo-app
```

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_token": "tGzv3JOkF0..."
}
```

1. 클라이언트가 만료된 Access Token으로 API를 호출한다.
2. 리소스 서버가 `401`과 `WWW-Authenticate: Bearer error="invalid_token"`으로 응답한다.
3. 클라이언트가 Refresh Token으로 토큰 엔드포인트에 재발급을 요청한다.
4. 인가 서버가 새 Access Token을 발급한다. 회전을 적용하면 새 Refresh Token도 함께 발급한다.
5. 클라이언트가 원래 요청을 재시도한다.

### Refresh Token 회전(Rotation)

- 재발급할 때마다 새 Refresh Token을 주고 이전 Refresh Token은 무효화한다.
- 이미 사용된 Refresh Token이 다시 들어오면 탈취로 판단해 해당 토큰 계열 전체를 폐기할 수 있다(재사용 탐지).
- OAuth 2.0 Security BCP(RFC 9700)는 public client의 Refresh Token에 대해 회전 또는 sender-constrained 토큰 적용을 요구한다. confidential client에는 선택 사항이다.

### 저장 위치

- 웹 브라우저: Refresh Token을 JavaScript가 접근할 수 있는 저장소(localStorage 등)에 두면 XSS에 노출된다. `HttpOnly` 쿠키나 BFF(Backend for Frontend) 패턴으로 서버 측에 두는 방식이 많이 쓰인다.
- 모바일 앱: OS의 보안 저장소(iOS Keychain, Android Keystore)를 사용한다.

### 한계

짧은 수명과 회전은 탈취 시 피해 기간과 범위를 줄일 뿐, 탈취 자체를 막지는 않는다. 토큰을 특정 클라이언트 키에 묶는 sender-constrained 토큰(DPoP, mTLS)을 쓰면 탈취한 토큰만으로는 사용할 수 없게 할 수 있다.

---

## 5. SSO (Single Sign-On)

![SSO 흐름](/assets/images/2026-10-20-auth-7-concepts/05-sso.png)

### 개념

SSO는 한 번 로그인으로 여러 애플리케이션을 사용하는 방식이다. 각 애플리케이션이 직접 로그인을 처리하지 않고, 공통으로 신뢰하는 IdP(Identity Provider)에 인증을 맡긴다.

| 용어 | 의미 |
|---|---|
| IdP (Identity Provider) | 사용자를 인증하고 인증 결과를 발급하는 서버. 예: Entra ID, Okta, ADFS, Keycloak |
| SP / RP | 인증 결과를 받아 사용하는 애플리케이션. SAML에서는 SP(Service Provider), OIDC·WS-Fed에서는 RP(Relying Party)라 부른다. |
| 신뢰 관계 | IdP와 SP가 사전에 메타데이터(엔드포인트, 서명 인증서, 식별자)를 교환해 둔 상태 |

### 동작 흐름

1. 사용자가 앱 A에 접속한다. 앱 A에는 세션이 없다.
2. 앱 A가 브라우저를 IdP로 리다이렉트한다.
3. IdP가 로그인 화면을 보여주고 사용자가 인증한다.
4. IdP는 자체 세션(IdP 도메인의 쿠키)을 만들고, 앱 A용 토큰 또는 Assertion을 발급한다.
5. 브라우저가 이를 앱 A에 전달한다. 앱 A는 서명을 검증하고 자체 세션을 만든다.
6. 사용자가 앱 B에 접속하면 앱 B도 IdP로 리다이렉트한다.
7. IdP에는 이미 세션이 있으므로 로그인 화면 없이 앱 B용 토큰을 새로 발급한다.

여기서 세션이 두 단계로 존재한다는 점이 중요하다. 각 앱의 세션과 IdP의 세션이 따로 있고, SSO는 IdP 세션을 재사용해서 이루어진다.

### SSO는 경험이고, 프로토콜은 별개

SSO는 "한 번 로그인"이라는 결과를 가리키며, 특정 토큰 형식이나 프로토콜이 아니다. 위 흐름의 4~5단계, 즉 IdP가 인증 결과를 앱에 어떤 형식으로 어떤 경로로 전달하는지는 프로토콜마다 다르다. 기업 환경에서 주로 쓰이는 프로토콜은 SAML 2.0, OpenID Connect, WS-Federation 세 가지다.

![SSO 프로토콜별 인증 결과 전달 방식](/assets/images/2026-10-20-auth-7-concepts/05-2-sso-protocols.png)

### SAML 2.0

XML 기반의 인증·속성 교환 표준이다. IdP가 서명한 XML Assertion이 인증 결과이며, 메시지를 실어 나르는 방식을 바인딩(binding)이라고 부른다.

**1) SP → IdP: AuthnRequest (HTTP-Redirect 바인딩)**

SP가 인증 요청 XML을 만들어 Deflate 압축 → Base64 인코딩 → URL 인코딩한 뒤 쿼리 파라미터로 붙여 IdP로 리다이렉트한다.

```xml
<samlp:AuthnRequest
    ID="_a7c3f9e1"
    Version="2.0"
    IssueInstant="2026-10-20T00:00:00Z"
    Destination="https://idp.example.com/adfs/ls/"
    AssertionConsumerServiceURL="https://app.example.com/saml/acs"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
  <saml:Issuer>https://app.example.com</saml:Issuer>
</samlp:AuthnRequest>
```

```http
GET /adfs/ls/?SAMLRequest=fZJNT8MwDIb...&RelayState=%2Fphotos&SigAlg=...&Signature=... HTTP/1.1
Host: idp.example.com
```

- `ID`: 요청 식별자다. 응답의 `InResponseTo`와 비교하는 기준이 된다.
- `RelayState`: 로그인 후 돌아갈 원래 경로 등 SP가 보존하려는 상태 값이다. IdP는 그대로 돌려준다.
- `SigAlg` / `Signature`: 요청 서명이다. HTTP-Redirect 바인딩에서는 XML 안이 아니라 쿼리 문자열 전체에 서명한다. 요청 서명을 요구할지는 IdP 설정에 따른다.

**2) IdP 인증**

IdP는 자체 세션이 없으면 사용자를 인증하고, 있으면 생략한다.

**3) IdP → SP: SAMLResponse (HTTP-POST 바인딩)**

Assertion은 수 KB 크기라 URL에 담기 어렵다. 그래서 IdP는 자동 제출되는 HTML 폼을 내려보내고, 브라우저가 이를 SP의 ACS(Assertion Consumer Service) URL로 POST한다. 이때는 Deflate 없이 Base64만 적용한다.

```html
<form method="post" action="https://app.example.com/saml/acs">
  <input type="hidden" name="SAMLResponse" value="PHNhbWxwOlJlc3BvbnNlIC4uLg==" />
  <input type="hidden" name="RelayState" value="/photos" />
</form>
<script>document.forms[0].submit();</script>
```

Assertion의 주요 구성 요소는 다음과 같다.

```xml
<saml:Assertion ID="_9f2e..." IssueInstant="2026-10-20T00:00:05Z" Version="2.0">
  <saml:Issuer>http://idp.example.com/adfs/services/trust</saml:Issuer>
  <ds:Signature>...</ds:Signature>
  <saml:Subject>
    <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">rahul@example.com</saml:NameID>
    <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
      <saml:SubjectConfirmationData InResponseTo="_a7c3f9e1"
          Recipient="https://app.example.com/saml/acs"
          NotOnOrAfter="2026-10-20T00:05:05Z" />
    </saml:SubjectConfirmation>
  </saml:Subject>
  <saml:Conditions NotBefore="2026-10-20T00:00:05Z" NotOnOrAfter="2026-10-20T01:00:05Z">
    <saml:AudienceRestriction>
      <saml:Audience>https://app.example.com</saml:Audience>
    </saml:AudienceRestriction>
  </saml:Conditions>
  <saml:AuthnStatement AuthnInstant="2026-10-20T00:00:03Z" SessionIndex="_9f2e...">
    <saml:AuthnContext>
      <saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport</saml:AuthnContextClassRef>
    </saml:AuthnContext>
  </saml:AuthnStatement>
  <saml:AttributeStatement>
    <saml:Attribute Name="http://schemas.xmlsoap.org/claims/Group">
      <saml:AttributeValue>photo-users</saml:AttributeValue>
    </saml:Attribute>
  </saml:AttributeStatement>
</saml:Assertion>
```

| 요소 | 의미 |
|---|---|
| `Issuer` | Assertion을 발급한 IdP |
| `Signature` | IdP 토큰 서명 인증서로 만든 XML 서명. Response 전체, Assertion, 또는 둘 다에 서명할 수 있다. |
| `Subject/NameID` | 사용자 식별자. Format에 따라 이메일, UPN, 영구 식별자(persistent), 임시 식별자(transient) 등을 쓴다. |
| `SubjectConfirmationData` | 어떤 요청에 대한 응답인지(`InResponseTo`), 어느 ACS로 보내야 하는지(`Recipient`), 언제까지 제출해야 하는지(`NotOnOrAfter`) |
| `Conditions` | Assertion 유효 기간과 수신 대상(`Audience` = SP의 Entity ID) |
| `AuthnStatement` | 인증 시각, 인증 방식, IdP 세션 식별자(`SessionIndex`, SLO에 사용) |
| `AttributeStatement` | 그룹, 이메일, 부서 등 클레임 |

Assertion 내용까지 숨겨야 하면 SP의 암호화 인증서로 암호화한 `EncryptedAssertion`을 사용한다.

**4) SP 검증**

1. XML 서명을 IdP 메타데이터의 서명 인증서로 검증한다. 서명되지 않은 부분의 값을 신뢰하지 않도록 서명 범위(Reference)도 확인해야 한다(XML Signature Wrapping 공격 방지).
2. `Issuer`가 신뢰하는 IdP인지 확인한다.
3. `Destination`과 `Recipient`가 자신의 ACS URL과 일치하는지 확인한다.
4. `InResponseTo`가 자신이 보낸 AuthnRequest의 `ID`와 일치하는지 확인한다.
5. `Audience`가 자신의 Entity ID인지 확인한다.
6. `NotBefore`, `NotOnOrAfter`로 유효 기간을 확인한다. 서버 간 시각 차이를 고려한 허용 오차를 둔다.
7. 같은 Assertion `ID`가 다시 들어오면 거부한다(재전송 방지).

검증을 통과하면 SP는 NameID와 속성으로 자체 세션을 만들고, `RelayState`의 경로로 사용자를 보낸다.

**그 밖의 방식**

- IdP-initiated SSO: SP의 AuthnRequest 없이 IdP 포털에서 바로 SAMLResponse를 보내는 방식이다. `InResponseTo`가 없어 요청과 응답을 연결할 수 없으므로 응답 주입 공격에 취약하다. ADFS는 2016 버전부터 IdP-initiated 로그인 페이지가 기본 비활성화되어 있다.
- HTTP-Artifact 바인딩: 브라우저로는 짧은 참조값(Artifact)만 보내고, SP가 SOAP 백채널로 IdP에 실제 Assertion을 요청한다. Assertion이 브라우저를 거치지 않지만 구성이 복잡해 사용 빈도는 낮다.
- SAML은 브라우저 로그인용으로 설계되어 API 호출용 토큰을 직접 제공하지 않는다. API 접근이 필요하면 SAML Assertion을 OAuth Access Token으로 교환하는 SAML 2.0 Bearer Assertion 그랜트(RFC 7522) 등을 별도로 사용한다.

### OpenID Connect

OAuth 2.0 Authorization Code 흐름 위에서 동작한다. 브라우저로는 일회용 코드만 전달하고, 실제 토큰은 서버 간 백채널에서 받는다는 점이 SAML·WS-Fed와 가장 큰 차이다. 흐름과 ID Token 검증 절차는 [7. OpenID Connect](#7-openid-connect-oidc)에서 다루고, 여기서는 전달 방식만 정리한다.

**1) RP → IdP: 인가 요청 (프론트채널)**

```http
GET /authorize?response_type=code&client_id=photo-app
  &redirect_uri=https://app.example.com/callback
  &scope=openid%20profile&state=af0ifjsldkj&nonce=n-0S6_WzA2Mj
  &code_challenge=E9Melhoa2Owv...&code_challenge_method=S256
Host: idp.example.com
```

**2) IdP → RP: Authorization Code (프론트채널)**

```http
HTTP/1.1 302 Found
Location: https://app.example.com/callback?code=SplxlOBeZQQYbYS6WxSbIA&state=af0ifjsldkj
```

`response_mode=form_post`를 지정하면 코드를 쿼리 문자열 대신 자동 제출 HTML 폼으로 POST한다. URL에 값이 남지 않는다는 장점이 있다.

**3) RP → IdP: 토큰 교환 (백채널)**

```http
POST /token HTTP/1.1
Host: idp.example.com
Authorization: Basic cGhvdG8tYXBwOioqKioqKioq
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&code=SplxlOBeZQQYbYS6WxSbIA
&redirect_uri=https://app.example.com/callback&code_verifier=dBjftJeZ4CVP...
```

토큰 엔드포인트는 클라이언트를 인증한다. 방식은 다음과 같다.

| 방식 | 내용 |
|---|---|
| `client_secret_basic` | client_id와 secret을 HTTP Basic 인증 헤더로 전송 |
| `client_secret_post` | client_id와 secret을 요청 본문에 포함 |
| `private_key_jwt` | 클라이언트 개인키로 서명한 JWT를 제출. secret을 공유하지 않는다. |
| `none` + PKCE | secret을 보관할 수 없는 public client(SPA, 모바일) |

**4) 응답**

```json
{
  "access_token": "eyJ0eXAiOiJKV1Qi...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "id_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "8xLOxBtZp8..."
}
```

RP는 ID Token을 검증한 뒤 `iss` + `sub`로 사용자를 식별해 자체 세션을 만든다. Access Token은 API 호출에, Refresh Token은 갱신에 사용한다. SAML과 달리 로그인과 API 접근 토큰을 한 흐름에서 함께 받을 수 있다.

**그 밖의 방식**

- Implicit 흐름(`response_type=id_token token`): 토큰을 URL fragment로 브라우저에 직접 전달한다. 토큰이 브라우저 기록 등에 노출되므로 현재는 권장되지 않는다.
- Hybrid 흐름(`response_type=code id_token`): 프론트채널에서 ID Token을 먼저 받고 코드는 백채널에서 교환한다. 이때 ID Token의 `c_hash`로 코드가 바꿔치기되지 않았는지 확인한다.

### WS-Federation

Microsoft가 주도한 WS-* 계열 표준의 웹 브라우저용 프로필(Passive Requestor Profile)이다. 요청은 쿼리 파라미터로, 응답은 SAML 토큰을 WS-Trust의 RSTR(RequestSecurityTokenResponse) XML로 감싸 POST로 전달한다. SharePoint, WIF 기반 .NET 앱, ADFS 페더레이션을 사용하는 Microsoft 365 도메인 등에서 사용된다.

**1) RP → IdP: 로그인 요청**

```http
GET /adfs/ls/?wa=wsignin1.0&wtrealm=urn:app:photo&wctx=rm%3d0%26id%3dpassive%26ru%3d%252fphotos HTTP/1.1
Host: idp.example.com
```

| 파라미터 | 의미 |
|---|---|
| `wa` | 동작. 로그인은 `wsignin1.0`, 로그아웃은 `wsignout1.0` |
| `wtrealm` | RP 식별자. IdP는 이 값으로 신뢰 당사자를 찾고, 토큰의 Audience로 사용한다. |
| `wctx` | RP가 보존하려는 상태 값. SAML의 `RelayState`에 해당한다. |
| `wreply` | 토큰을 돌려받을 URL. 지정하지 않으면 IdP에 등록된 엔드포인트를 사용한다. |

SAML과 달리 요청 자체는 XML 메시지가 아니고 서명도 하지 않는다. 요청 ID가 없으므로 SAML의 `InResponseTo` 같은 요청-응답 연결 검증도 없다.

**2) IdP → RP: 토큰 POST**

```html
<form method="post" action="https://app.example.com/">
  <input type="hidden" name="wa" value="wsignin1.0" />
  <input type="hidden" name="wresult" value="&lt;t:RequestSecurityTokenResponse ...&gt;...&lt;/t:RequestSecurityTokenResponse&gt;" />
  <input type="hidden" name="wctx" value="rm=0&amp;id=passive&amp;ru=%2fphotos" />
</form>
```

`wresult`의 구조는 다음과 같다.

```xml
<t:RequestSecurityTokenResponse xmlns:t="http://schemas.xmlsoap.org/ws/2005/02/trust">
  <t:Lifetime>
    <wsu:Created>2026-10-20T00:00:05Z</wsu:Created>
    <wsu:Expires>2026-10-20T01:00:05Z</wsu:Expires>
  </t:Lifetime>
  <wsp:AppliesTo>
    <wsa:EndpointReference><wsa:Address>urn:app:photo</wsa:Address></wsa:EndpointReference>
  </wsp:AppliesTo>
  <t:RequestedSecurityToken>
    <saml:Assertion MajorVersion="1" MinorVersion="1" ...>
      <!-- 서명된 SAML 1.1 Assertion (Audience, Subject, Attribute 포함) -->
    </saml:Assertion>
  </t:RequestedSecurityToken>
  <t:TokenType>urn:oasis:names:tc:SAML:1.0:assertion</t:TokenType>
</t:RequestSecurityTokenResponse>
```

- 내부 토큰은 ADFS 기본값 기준 SAML 1.1이며, RP 설정에 따라 SAML 2.0 토큰을 사용할 수도 있다.
- 서명은 RSTR 바깥이 아니라 내부 SAML Assertion에 있다.

**3) RP 검증**

1. 내부 SAML 토큰의 서명을 IdP 페더레이션 메타데이터의 서명 인증서로 검증한다.
2. Issuer가 신뢰하는 IdP인지 확인한다.
3. Audience가 자신의 `wtrealm` 값인지 확인한다.
4. 토큰 유효 기간을 확인한다.
5. 재전송 탐지(토큰 재사용 캐시)를 구성한다. WIF 등 프레임워크에서는 별도 설정이 필요한 경우가 많다.

검증 후 RP는 클레임으로 세션 쿠키(WIF의 FedAuth 쿠키 등)를 만들고 `wctx`의 경로로 이동한다.

### 프로토콜 비교

| 항목 | SAML 2.0 | OpenID Connect | WS-Federation |
|---|---|---|---|
| 메시지 형식 | XML | JSON / JWT | 쿼리 파라미터 + XML(RSTR) |
| 로그인 요청 | `SAMLRequest` (AuthnRequest XML) | `/authorize` 쿼리 파라미터 | `wa=wsignin1.0&wtrealm=…` |
| 요청 서명 | 선택 (IdP 설정) | 없음 (선택적으로 Request Object) | 없음 |
| 인증 결과 전달 | 브라우저 POST로 Assertion 전달 | 브라우저로 코드 → 백채널로 토큰 수신 | 브라우저 POST로 RSTR 전달 |
| 토큰 형식 | SAML 2.0 Assertion | ID Token (JWT) | SAML 1.1 / 2.0 Assertion |
| 브라우저 경유 값 | Assertion 전체 | 일회용 코드만 | 토큰 전체 |
| 앱 식별자 | SP Entity ID | `client_id` | `wtrealm` |
| 요청-응답 연결 | `InResponseTo` | `state`, `nonce` | 없음 (`wctx`는 상태 보존용) |
| 클라이언트 인증 | 없음 (요청 서명으로 대체 가능) | 토큰 엔드포인트에서 수행 | 없음 |
| API 호출용 토큰 | 직접 제공 안 함 | Access Token 함께 발급 | 직접 제공 안 함 |
| 로그아웃 | SLO (`LogoutRequest`) | RP-Initiated / Front·Back-Channel Logout | `wa=wsignout1.0` |
| 신뢰 정보 교환 | SAML 메타데이터 XML | Discovery 문서 + JWKS | 페더레이션 메타데이터 XML |
| 주 사용처 | 기업용 SaaS, 사내 웹앱 | 최신 웹, SPA, 모바일, API | SharePoint, WIF 앱, M365 페더레이션 |

### 참고: IdP 내부 인증 방식과 연동 프로토콜은 다른 계층

위 세 프로토콜은 IdP와 앱 사이에서 인증 결과를 전달하는 방법이다. IdP가 사용자를 어떻게 인증하는지(위 흐름의 2단계)는 별개다. 예를 들어 ADFS는 사내망 도메인 가입 PC에서는 Windows 통합 인증(Kerberos/NTLM)으로 로그인 화면 없이 사용자를 인증하고, 외부에서는 폼 로그인이나 인증서, MFA를 사용할 수 있다. 어떤 방식으로 인증했든 앱이 받는 결과는 위 프로토콜 중 하나의 형식으로 전달된다.

### 운영 시 고려사항

- 로그아웃: 앱 하나에서 로그아웃해도 IdP 세션이 남아 있으면 다른 앱에서 바로 다시 로그인된다. 전체 로그아웃이 필요하면 SAML SLO나 OIDC Front-Channel / Back-Channel Logout을 별도로 구성해야 한다.
- 인증서 관리: Assertion·토큰 서명 인증서가 만료되면 연동된 모든 앱의 로그인이 실패한다. 교체 일정과 메타데이터 갱신 절차를 관리해야 한다.
- 장애 영향: IdP가 단일 장애 지점이 되므로 이중화가 필요하다.

---

## 6. OAuth 2.0

![OAuth 2.0 Authorization Code 흐름](/assets/images/2026-10-20-auth-7-concepts/06-oauth2.png)

### 해결하려는 문제

사진 인쇄 서비스가 사용자의 클라우드 사진을 읽어야 한다고 가정한다. 사용자가 클라우드 계정 비밀번호를 인쇄 서비스에 알려주면 다음 문제가 생긴다.

- 인쇄 서비스가 사진뿐 아니라 계정 전체에 접근할 수 있다.
- 접근 권한을 인쇄 서비스에만 따로 회수할 수 없다. 비밀번호를 바꾸면 모든 곳에서 끊긴다.
- 인쇄 서비스가 유출되면 비밀번호도 함께 유출된다.

OAuth 2.0(RFC 6749)은 비밀번호 대신 범위와 기간이 제한된 Access Token을 발급해 접근 권한을 위임하는 인가 프레임워크다.

### 4가지 역할

| 역할 | 예시 |
|---|---|
| Resource Owner | 사진의 주인인 사용자 |
| Client | 사진 인쇄 서비스 |
| Authorization Server | 사용자를 인증하고 토큰을 발급하는 서버 |
| Resource Server | 사진 API |

### Authorization Code 흐름

1. 인가 요청 — 클라이언트가 브라우저를 인가 서버로 보낸다.

```http
GET /authorize?response_type=code
  &client_id=photo-print
  &redirect_uri=https://print.example.com/callback
  &scope=photos.read
  &state=xyz123
  &code_challenge=E9Melhoa2Owv...&code_challenge_method=S256
Host: auth.example.com
```

2. 사용자 인증과 동의 — 사용자는 인가 서버의 화면에서 로그인하고 요청된 권한(`photos.read`)에 동의한다. 클라이언트는 비밀번호를 보지 못한다.

3. Authorization Code 전달 — 인가 서버가 `redirect_uri`로 리다이렉트하면서 일회용 코드를 전달한다.

```http
HTTP/1.1 302 Found
Location: https://print.example.com/callback?code=SplxlOBeZQQYbYS6WxSbIA&state=xyz123
```

4. 토큰 교환 — 클라이언트가 백채널(서버 간 통신)로 코드를 토큰으로 교환한다.

```http
POST /token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&code=SplxlOBeZQQYbYS6WxSbIA
&redirect_uri=https://print.example.com/callback
&client_id=photo-print&code_verifier=dBjftJeZ4CVP...
```

5. API 호출 — Access Token으로 리소스 서버를 호출한다. 리소스 서버는 토큰의 유효성과 scope를 확인하고 허용된 데이터만 반환한다.

### 왜 코드를 한 번 더 교환하는가

브라우저 리다이렉트(프론트채널)로 전달되는 값은 브라우저 기록, 로그, Referer 헤더 등에 남을 수 있다. 그래서 프론트채널로는 수명이 짧은 일회용 코드만 보내고, 실제 토큰은 클라이언트 인증을 거친 백채널에서 받는다.

### 보안 파라미터

| 파라미터 | 목적 |
|---|---|
| `state` | 인가 요청과 응답을 연결해 CSRF를 방지한다. |
| `redirect_uri` 정확 일치 | 공격자 도메인으로 코드가 전달되는 것을 막는다. 인가 서버는 사전 등록된 값과 정확히 비교해야 한다. |
| PKCE (`code_challenge` / `code_verifier`) | 코드를 가로채도 원래 클라이언트만 토큰으로 교환할 수 있게 한다(RFC 7636). 현재는 모든 클라이언트에 권장되며, client secret을 안전하게 보관할 수 없는 SPA·모바일 앱에는 필수다. |

### 그랜트 유형

| 그랜트 | 용도 | 현재 권장 여부 |
|---|---|---|
| Authorization Code (+ PKCE) | 사용자가 있는 대부분의 앱 | 권장 |
| Client Credentials | 사용자 없이 서비스 간 호출 | 권장 |
| Device Authorization | 입력이 어려운 기기 (TV, CLI) | 권장 |
| Refresh Token | 토큰 갱신 | 권장 |
| Implicit | 과거 SPA용, 토큰을 URL로 직접 전달 | 사용 중단 권고 |
| Resource Owner Password | 클라이언트가 비밀번호를 직접 받음 | 사용 중단 권고 |

### 리소스 서버의 토큰 검증

- JWT 형식 Access Token: 인가 서버의 공개키(JWKS)로 로컬에서 서명과 클레임을 검증한다. 빠르지만 폐기가 즉시 반영되지 않는다.
- 불투명(opaque) 토큰: 인가 서버의 인트로스펙션 엔드포인트(RFC 7662)에 유효성을 묻는다. 폐기가 즉시 반영되지만 매 요청마다 인가 서버를 호출한다.

### OAuth는 인증 프로토콜이 아니다

OAuth 2.0의 Access Token은 "이 토큰으로 어떤 리소스에 접근할 수 있다"를 나타낼 뿐, "이 토큰을 가진 사람이 누구다"를 보장하지 않는다. Access Token은 원래 리소스 서버에 보내도록 설계되었으므로, 클라이언트가 이를 로그인 증거로 쓰면 다른 앱에서 발급된 토큰을 받아들이는 문제가 생길 수 있다. 로그인에 필요한 신원 정보는 다음의 OpenID Connect가 담당한다.

---

## 7. OpenID Connect (OIDC)

![OpenID Connect](/assets/images/2026-10-20-auth-7-concepts/07-oidc.png)

### 개념

OpenID Connect는 OAuth 2.0 위에 신원 계층을 추가한 인증 프로토콜이다. 흐름은 OAuth 2.0 Authorization Code와 같고, 다음이 추가된다.

- 인가 요청의 scope에 `openid`를 포함한다.
- 토큰 응답에 ID Token이 함께 온다.
- 사용자 정보를 조회하는 UserInfo 엔드포인트가 정의된다.
- IdP 설정을 자동으로 가져오는 Discovery 문서(`/.well-known/openid-configuration`)가 정의된다.

```http
GET /authorize?response_type=code
  &client_id=photo-app
  &redirect_uri=https://photo.example.com/callback
  &scope=openid%20profile%20email
  &state=abc&nonce=n-0S6_WzA2Mj
  &code_challenge=...&code_challenge_method=S256
```

```json
{
  "access_token": "SlAV32hkKG...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjFlOWdkazcifQ..."
}
```

### ID Token

ID Token은 OIDC Core 규격상 JWT 형식이며 서명이 필수다. 필요하면 추가로 암호화할 수 있다.

```json
{
  "iss": "https://auth.example.com",
  "sub": "248289761001",
  "aud": "photo-app",
  "exp": 1760003600,
  "iat": 1760000000,
  "nonce": "n-0S6_WzA2Mj",
  "auth_time": 1759999990,
  "email": "rahul@example.com"
}
```

클라이언트는 ID Token을 받으면 다음을 검증한다.

1. 서명 — IdP의 JWKS 공개키로 검증한다.
2. `iss` — 신뢰하는 IdP인지 확인한다.
3. `aud` — 자신의 `client_id`가 포함되어 있는지 확인한다. 다른 앱용으로 발급된 토큰을 거부하기 위해서다.
4. `exp` — 만료되지 않았는지 확인한다.
5. `nonce` — 인가 요청 때 보낸 값과 같은지 확인한다. 토큰 재전송(replay) 공격을 막는다.

사용자는 `sub` 단독이 아니라 `iss` + `sub` 조합으로 식별한다. `sub`는 IdP 안에서만 고유하기 때문이다.

### ID Token과 Access Token 비교

| 항목 | ID Token | Access Token |
|---|---|---|
| 목적 | 인증 결과 전달 (누구인가) | 리소스 접근 권한 (무엇을 할 수 있는가) |
| 수신자 | 클라이언트 앱 | 리소스 서버 (API) |
| 형식 | 서명된 JWT (규격상 고정) | 불투명 문자열 또는 JWT (구현에 따라 다름) |
| `aud` | 클라이언트 `client_id` | API 식별자 |
| API 호출 | 사용하지 않음 | 사용 |

ID Token을 API 호출에 보내거나 Access Token을 로그인 증거로 쓰는 것은 대표적인 오용이다.

### OAuth만 쓸지 OIDC까지 쓸지

- 사진 인쇄 서비스처럼 사용자의 데이터에 접근만 하면 되고 사용자가 누구인지 알 필요가 없다면 OAuth 2.0 Access Token만 요청한다.
- "Google로 로그인"처럼 앱이 사용자의 신원을 확인해야 하면 `openid` scope를 추가해 ID Token까지 받는다.
- 두 경우 모두 흐름은 같고, 요청하는 scope와 받는 토큰만 달라진다.

---

## 8. 전체 관계

![7가지 개념의 관계](/assets/images/2026-10-20-auth-7-concepts/08-overview.png)

| 개념 | 해결하는 문제 | 핵심 |
|---|---|---|
| Authentication | 요청 주체가 누구인가 | 자격 증명 검증 → 신원 확정 |
| Authorization | 무엇을 허용할 것인가 | 역할·속성·소유 관계로 판단 |
| Session / Cookie | 무상태 HTTP에서 로그인 상태 유지 | 서버 저장 + 세션 ID 쿠키 |
| JWT | 저장소 조회 없는 검증 | 서명된 클레임 |
| Access / Refresh Token | 토큰 탈취 피해 최소화 | 짧은 접근 토큰 + 보호된 갱신 토큰 |
| SSO | 여러 앱에서 반복 로그인 | IdP 세션 재사용 |
| OAuth 2.0 | 비밀번호 공유 없는 접근 위임 | scope가 제한된 Access Token |
| OpenID Connect | OAuth 기반 로그인 | OAuth + ID Token |

개념 간 연결은 다음과 같다.

- OIDC의 ID Token은 JWT 형식이다.
- OIDC와 SAML은 SSO를 구현하는 프로토콜이다.
- OAuth 2.0의 Access Token은 Bearer 토큰으로 동작하며, JWT일 수도 불투명 토큰일 수도 있다.
- 웹 애플리케이션은 IdP에서 OIDC로 사용자를 인증한 뒤, 자체적으로는 세션과 쿠키로 로그인 상태를 유지하는 경우가 많다.

일곱 개념은 서로 대체하는 선택지가 아니라 하나의 인증 체계 안에서 각자 다른 계층의 문제를 맡는다. 기술을 고를 때는 "무엇이 유행인가"보다 "어떤 문제를 해결해야 하는가"를 먼저 정해야 한다.

---

## 9. 최종 동작: 일곱 개념이 한 번의 로그인에서 함께 동작하는 방식

![인증 체계 한눈에 보기](/assets/images/2026-10-20-auth-7-concepts/09-auth-system-map.png)

앞에서 개념을 하나씩 나눠 봤다면, 여기서는 실제 서비스 하나에서 이 개념들이 어느 단계에 쓰이는지 끝까지 따라가 본다.

### 시나리오와 구성

사용자가 사진 서비스 웹앱에 처음 접속해 자기 사진을 조회하고, 시간이 지나 Access Token이 만료되는 상황까지를 가정한다.

| 구성 요소 | 역할 |
|---|---|
| 브라우저 | 사용자 에이전트. 세션 쿠키만 보관한다. |
| 웹앱 (RP) | OIDC 클라이언트이자 BFF(Backend for Frontend). 토큰을 서버 측에 보관한다. |
| IdP / 인가 서버 | 사용자를 인증하고 ID Token, Access Token, Refresh Token을 발급한다. |
| API (리소스 서버) | 사진 데이터를 제공한다. JWT Access Token을 검증하고 인가를 판단한다. |

![전체 동작 흐름](/assets/images/2026-10-20-auth-7-concepts/10-end-to-end-flow.png)

### 단계별 동작

**로그인 (①~⑩)**

| 단계 | 동작 | 관련 개념 |
|---|---|---|
| ① | 브라우저가 `/photos`를 요청한다. 세션 쿠키가 없으므로 웹앱은 로그인하지 않은 사용자로 판단한다. | 세션 · 쿠키 |
| ② | 웹앱이 `state`, `nonce`, PKCE `code_challenge`를 생성해 저장하고, 브라우저를 IdP의 `/authorize`로 리다이렉트한다. scope는 `openid profile photos.read`다. | OAuth 2.0 · OIDC |
| ③ | 브라우저가 IdP에 인가 요청을 전달한다. | OAuth 2.0 · OIDC |
| ④ | IdP가 사용자를 인증한다. IdP 세션이 이미 있으면 로그인 화면 없이 넘어간다. 같은 IdP를 쓰는 다른 앱에 이미 로그인했다면 여기서 SSO가 이루어진다. | 인증 · SSO |
| ⑤ | IdP가 일회용 Authorization Code를 붙여 웹앱의 callback으로 리다이렉트한다. 브라우저를 거치는 값은 이 코드뿐이다. | OAuth 2.0 |
| ⑥ | 브라우저가 코드를 웹앱에 전달한다. 웹앱은 `state`가 ②에서 저장한 값과 같은지 확인한다. | OAuth 2.0 |
| ⑦ | 웹앱이 서버 간 백채널로 코드를 토큰으로 교환한다. 이때 클라이언트 인증과 `code_verifier`를 함께 보낸다. | OAuth 2.0 · PKCE |
| ⑧ | IdP가 ID Token, Access Token(JWT), Refresh Token을 발급한다. | OIDC · JWT · Access/Refresh Token |
| ⑨ | 웹앱이 ID Token의 서명, `iss`, `aud`, `exp`, `nonce`를 검증해 사용자를 확인하고 자체 세션을 만든다. 세 토큰은 세션에 연결해 서버 측에 보관한다. | 인증 · JWT · 세션 |
| ⑩ | 웹앱이 세션 ID를 `HttpOnly`, `Secure`, `SameSite` 쿠키로 내려보낸다. 브라우저는 토큰을 직접 갖지 않는다. | 세션 · 쿠키 |

**API 호출 (⑪~⑮)**

| 단계 | 동작 | 관련 개념 |
|---|---|---|
| ⑪ | 브라우저가 세션 쿠키와 함께 `/photos/1024`를 요청한다. 웹앱은 세션으로 사용자를 식별한다. | 세션 · 쿠키 |
| ⑫ | 웹앱이 세션에 보관된 Access Token을 `Authorization: Bearer` 헤더에 넣어 API를 호출한다. | Access Token · Bearer |
| ⑬ | API는 IdP의 공개키(JWKS)로 JWT 서명을 검증하고 `iss`, `aud`, `exp`를 확인한다. 이어서 scope에 `photos.read`가 있는지, 요청한 사진의 소유자가 토큰의 `sub`와 같은지 판단한다. 다른 사용자의 사진이면 `403`을 반환한다. | JWT · 인가 |
| ⑭ | 검증과 인가를 통과하면 허용된 데이터만 반환한다. | 인가 |
| ⑮ | 웹앱이 결과를 화면으로 응답한다. | — |

**토큰 갱신 (⑯~⑰)**

| 단계 | 동작 | 관련 개념 |
|---|---|---|
| ⑯ | Access Token이 만료되면 API가 `401 invalid_token`을 반환한다. 웹앱은 보관 중인 Refresh Token으로 IdP에 재발급을 요청한다. 사용자는 이 과정을 인지하지 못한다. | Refresh Token |
| ⑰ | IdP가 새 Access Token과 새 Refresh Token을 발급하고 이전 Refresh Token은 무효화한다. 웹앱은 세션에 연결된 토큰을 교체하고 원래 요청을 재시도한다. | Refresh Token 회전 |

### 각 개념이 맡은 위치

| 개념 | 이 흐름에서 쓰인 단계 |
|---|---|
| 인증 | ④ IdP의 사용자 인증, ⑨ 웹앱의 ID Token 검증 |
| 인가 | ⑬ API의 scope·소유자 검사 |
| 세션 · 쿠키 | ①, ⑨~⑪ 웹앱과 브라우저 사이의 로그인 상태 유지 |
| JWT | ⑧ ID Token과 Access Token의 형식, ⑨·⑬ 서명 검증 |
| Access · Refresh Token | ⑫ API 호출, ⑯~⑰ 갱신 |
| SSO | ④ IdP 세션 재사용 |
| OAuth 2.0 · OIDC | ②~⑧ 로그인과 토큰 발급 전체 흐름 |

### 이 구성을 택한 이유

- 브라우저에 토큰을 두지 않으므로 XSS가 발생해도 Access Token과 Refresh Token을 직접 탈취하기 어렵다. 브라우저 쪽 공격 표면은 `HttpOnly` 세션 쿠키 하나로 줄어든다.
- 웹앱과 브라우저 사이는 세션으로 즉시 무효화할 수 있고, 웹앱과 API 사이는 JWT로 저장소 조회 없이 검증한다. 세션과 JWT를 경쟁 관계가 아니라 구간별로 나눠 쓰는 방식이다.
- 인증(누구인가)은 IdP에 맡기고, 인가(무엇을 허용하는가)는 데이터를 가진 API가 최종 판단한다. Access Token의 scope는 위임 범위의 상한일 뿐이므로, 리소스 단위 소유자 검사는 API에서 별도로 수행해야 한다.
- 같은 IdP를 쓰는 다른 앱에 접속하면 ④에서 로그인 화면이 생략된다. 각 앱은 각자 ⑤~⑩을 거쳐 자체 세션을 만든다.

### 다른 구성일 때 달라지는 점

- SPA가 토큰을 직접 다루는 경우: ⑦의 토큰 교환을 브라우저가 수행하고 Access Token을 메모리에 둔다. client secret을 둘 수 없으므로 PKCE가 필수이고, Refresh Token 회전이나 sender-constrained 토큰(DPoP)이 필요하다.
- IdP가 SAML만 지원하는 경우: ②~⑧이 AuthnRequest와 SAMLResponse 교환으로 바뀐다. 웹앱은 Assertion을 검증해 세션을 만들 수 있지만 API용 Access Token은 받지 못하므로, 별도의 토큰 교환이나 API 자체 인증이 필요하다.
- 서비스 간 호출만 있는 경우: 사용자가 없으므로 ①~⑩ 대신 Client Credentials 그랜트로 Access Token을 받아 ⑫부터 진행한다.

---

## 참고

- Visualcoders, [7 Authentication Concepts Every Senior Developer Should Know](https://www.youtube.com/watch?v=Zo4VpTSelUE)
- [RFC 6749 — The OAuth 2.0 Authorization Framework](https://datatracker.ietf.org/doc/html/rfc6749)
- [RFC 6750 — Bearer Token Usage](https://datatracker.ietf.org/doc/html/rfc6750)
- [RFC 7519 — JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)
- [RFC 7636 — Proof Key for Code Exchange (PKCE)](https://datatracker.ietf.org/doc/html/rfc7636)
- [RFC 7662 — OAuth 2.0 Token Introspection](https://datatracker.ietf.org/doc/html/rfc7662)
- [RFC 9700 — Best Current Practice for OAuth 2.0 Security](https://datatracker.ietf.org/doc/html/rfc9700)
- [RFC 7522 — SAML 2.0 Profile for OAuth 2.0 Client Authentication and Authorization Grants](https://datatracker.ietf.org/doc/html/rfc7522)
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
- [OAuth 2.0 Form Post Response Mode](https://openid.net/specs/oauth-v2-form-post-response-mode-1_0.html)
- [OASIS SAML 2.0 Core / Bindings](https://docs.oasis-open.org/security/saml/v2.0/)
- [OASIS WS-Federation 1.2](https://docs.oasis-open.org/wsfed/federation/v1.2/ws-federation.html)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
