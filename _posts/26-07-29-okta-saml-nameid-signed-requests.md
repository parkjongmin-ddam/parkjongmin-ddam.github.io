---
layout: single
title: "Okta 랩 3 — SP-initiated SAML과 NameID format, Signed Requests 검증"
excerpt: "전편에서 IdP-initiated로만 확인했던 SAML을 SP-initiated로 다시 세운다. AuthnRequest를 직접 만들어 InResponseTo와 RelayState가 되돌아오는지 확인하고, Name ID format을 unspecified·EmailAddress·Persistent·Transient로 바꿔가며 assertion을 매번 디코드한다. 네 형식 모두 Format URI만 바뀌고 값은 동일하게 나오는 지점이 이번 검증의 핵심이다. 이어서 자체 발행 인증서로 Signed Requests를 켜고, Apps API로 콘솔에 노출되지 않는 설정까지 대조한다."
date: 2026-07-29
categories: [IAM]
tags: [Okta, SAML, NameID, SP-initiated, Signed-Requests, 실측]
---

[전편]({% post_url 26-07-29-okta-lab %})에서 SAML 2.0 앱을 붙여 attribute statement와 `AuthnContextClassRef` 문제까지 확인했지만, 검증은 전부 Okta 대시보드에서 앱 타일을 눌러 시작하는 IdP-initiated 경로였다. 실제 SP 연동에서 더 흔한 쪽은 SP가 `AuthnRequest`를 만들어 던지는 SP-initiated다. 이 글은 그 경로를 세우고, 거기에 붙는 두 가지 — Name ID format과 Signed Requests — 를 실측한 기록이다.

## 환경

- Okta Integrator Free Plan (전편과 동일 조직, `integrator-XXXXXXX.okta.com`)
- SAML 앱: `lab-saml-sp` (Audience URI `urn:lab:okta:saml-sp`, ACS `http://localhost:5000/saml/acs/okta`)
- SP 측: Windows PowerShell 5.1 + `System.Net.HttpListener` (Flask 대신 ACS 수신만 하는 최소 리스너)
- assertion 파싱: `[xml]` 캐스팅 후 XPath 없이 속성 직접 접근

## 1. SP-initiated 플로우 세우기

SP 역할은 `HttpListener`로 대신했다. `http://localhost:5000/`에 바인딩해두고 브라우저에서 SSO를 시작하면, Okta가 ACS로 보내는 POST를 그대로 받아 본문을 읽는다.

```powershell
$listener = [Net.HttpListener]::new()
$listener.Prefixes.Add('http://localhost:5000/')
$listener.Start()
'대기 중...'

$ctx = $listener.GetContext()
$raw = [IO.StreamReader]::new($ctx.Request.InputStream).ReadToEnd()
$ctx.Response.StatusCode = 200; $ctx.Response.Close(); $listener.Stop()
```

받은 본문은 `SAMLResponse=...&RelayState=...` 형태의 폼 인코딩이다. 두 값을 분리해서 각각 확인했다.

```powershell
$pairs = @{}
foreach ($p in ($raw -split '&')) {
  $kv = $p -split '=', 2
  $pairs[$kv[0]] = [Uri]::UnescapeDataString($kv[1])
}

"RelayState 반환값 : $($pairs['RelayState'])"
$xmlTxt = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($pairs['SAMLResponse']))
```

확인하려던 건 세 가지다. RelayState가 그대로 돌아오는지, `Response`와 `SubjectConfirmationData` 양쪽의 `InResponseTo`가 내가 보낸 `AuthnRequest`의 ID와 일치하는지, 그리고 NameID가 어떤 형식으로 나오는지.

![RelayState 반환과 InResponseTo 일치 확인](/assets/images/okta3/01-sp-initiated-inresponseto-relaystate.png)

RelayState는 보낸 값 `sp-init-001`이 변형 없이 돌아왔다. `InResponseTo`는 `Response` 요소와 `Assertion.Subject.SubjectConfirmation.SubjectConfirmationData` 두 곳 모두 `_b28be188e92e4530a724b55c72d3485e`로 동일했다. SP가 응답을 자기 요청에 묶어 검증할 수 있다는 뜻이고, 이 값이 없거나 다르면 unsolicited response로 취급해 거부하는 것이 SP 구현의 기본이다. IdP-initiated에서는 애초에 요청이 없으니 `InResponseTo`도 없다 — 전편과 갈리는 지점이 여기다.

NameID는 `urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified`로, 값은 Okta username(이메일 형식)이었다. 앱 설정의 기본값이 Unspecified인 상태 그대로다.

## 2. Name ID format 바꿔가며 비교

앱의 SAML Settings에서 Name ID format만 바꾸고 나머지는 고정한 채, 매번 다시 로그인해 assertion을 디코드했다. 파싱 코드는 형식과 값만 뽑도록 줄였다.

```powershell
$enc = ($raw -split '&' | Where-Object { $_ -like 'SAMLResponse=*' }) -replace '^SAMLResponse=',''
$xml = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String([Uri]::UnescapeDataString($enc)))

[xml]$x = $xml
$fmt = $x.Response.Assertion.Subject.NameID.Format
$val = $x.Response.Assertion.Subject.NameID.InnerText
"Format : $fmt"
"Value  : $val"
```

### EmailAddress

먼저 `EmailAddress`로 바꿨다.

![Name ID format을 EmailAddress로 변경](/assets/images/okta3/02-nameid-format-emailaddress.png)

브라우저 개발자도구 Network 탭에서 ACS로 가는 POST의 Payload에 `SAMLResponse` 하나만 실려 나가는 것을 확인할 수 있다. base64 인코딩일 뿐 암호화가 아니어서, 앞서 앱 설정에서 Assertion Encryption을 `Unencrypted`로 둔 상태라면 이 값만 떠서 디코드해도 전문이 그대로 보인다.

![ACS로 전송되는 SAMLResponse 페이로드 (EmailAddress)](/assets/images/okta3/03-samlresponse-payload-email.png)

디코드 결과는 `urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress`. 값은 앞서 unspecified일 때와 같은 이메일이다.

![EmailAddress 형식 디코드 결과](/assets/images/okta3/04-nameid-email-result.png)

### Persistent

다음은 `Persistent`.

![Name ID format을 Persistent로 변경](/assets/images/okta3/05-nameid-format-persistent.png)

![ACS로 전송되는 SAMLResponse 페이로드 (Persistent)](/assets/images/okta3/06-samlresponse-payload-persistent.png)

Format은 `urn:oasis:names:tc:SAML:2.0:nameid-format:persistent`로 바뀌었다. 그런데 값은 또 같은 이메일이다.

![Persistent 형식 디코드 결과](/assets/images/okta3/07-nameid-persistent-result.png)

### Transient

마지막으로 `Transient`.

![Name ID format을 Transient로 변경](/assets/images/okta3/08-nameid-format-transient.png)

Format은 `urn:oasis:names:tc:SAML:2.0:nameid-format:transient`. 값은 여전히 동일하다.

![Transient 형식 디코드 결과](/assets/images/okta3/09-nameid-transient-result.png)

### 관찰

네 형식을 돌린 결과, **바뀐 것은 `Format` 속성의 URI 문자열뿐이고 `NameID`의 실제 값은 네 번 모두 같았다.**

SAML 2.0 명세의 의도대로라면 `persistent`는 SP별로 다른 불투명(opaque) 가명이어야 하고, `transient`는 세션마다 달라지는 일회성 식별자여야 한다. 어느 쪽도 사용자의 이메일이 그대로 나올 값이 아니다. Okta는 형식 선택을 값 생성 규칙이 아니라 **선언용 라벨**로만 다루고, 실제 값은 별도 항목인 Application username에서 가져온다. 캡처에서 Application username이 계속 `Okta username`으로 고정돼 있는데, 네 번의 결과값이 전부 이메일이었던 이유가 이것이다.

실무에서 걸리는 지점은 두 가지다. SP가 `Format`을 보고 "이건 가명이니 로그에 남겨도 된다"거나 "transient니까 저장하지 않는다"고 판단하도록 구현돼 있으면, 실제로는 PII가 그 자리에 들어온다. 반대로 진짜 가명이 필요하면 Application username을 커스텀 표현식(예: 사용자 ID 기반 값)으로 바꿔야 하고, format만 건드려서는 아무것도 달라지지 않는다.

## 3. Signed Requests

여기까지는 SP가 서명 없이 `AuthnRequest`를 보낸 상태다. Okta가 서명을 요구하는지 먼저 메타데이터에서 확인했다.

```powershell
$mdUrl = 'https://{org}.okta.com/app/{appId}/sso/saml/metadata'
[xml]$md = (Invoke-WebRequest -Uri $mdUrl -UseBasicParsing).Content
"WantAuthnRequestsSigned : $($md.EntityDescriptor.IDPSSODescriptor.WantAuthnRequestsSigned)"
```

`false`였다. 기본값에서는 서명하지 않은 요청도 받는다는 뜻이다. 이걸 `true`로 만들려면 SP 인증서를 올려야 하므로, 검증용 자체 서명 인증서를 발행했다.

```powershell
$cert = New-SelfSignedCertificate `
  -Subject 'CN=lab-saml-sp' `
  -KeyAlgorithm RSA -KeyLength 2048 `
  -HashAlgorithm SHA256 `
  -KeyExportPolicy Exportable `
  -KeyUsage DigitalSignature `
  -CertStoreLocation Cert:\CurrentUser\My `
  -NotAfter (Get-Date).AddYears(2)

# 공개키를 PEM으로 내보내기 (Okta 업로드용)
$b64 = [Convert]::ToBase64String($cert.RawData, 'InsertLineBreaks')
$pem = "-----BEGIN CERTIFICATE-----`r`n$b64`r`n-----END CERTIFICATE-----"
$pem | Out-File -Encoding ascii "$env:USERPROFILE\lab-saml-sp.pem"
```

`KeyUsage`를 `DigitalSignature`로 한정한 건 이 인증서의 용도가 요청 서명 검증뿐이기 때문이다. Okta에 올리는 것은 개인키가 아니라 공개키 PEM이다.

![메타데이터 확인과 자체 서명 인증서 발행](/assets/images/okta3/10-selfsigned-cert-for-signed-requests.png)

앱의 SAML Settings에서 `Show Advanced Settings`를 열면 Signature Certificate 항목이 나온다. 여기서 방금 만든 PEM을 올린다.

![Advanced Settings의 Signature Certificate 업로드](/assets/images/okta3/11-signature-certificate-browse.png)

업로드되면 Subject(`CN=lab-saml-sp`)와 유효기간이 표시된다. `New-SelfSignedCertificate`에 준 `AddYears(2)`가 730일로 그대로 반영됐다.

![업로드된 인증서 정보](/assets/images/okta3/12-certificate-uploaded.png)

인증서가 올라간 뒤에야 Signed Requests 체크박스가 활성화된다. 켜면 `Validate SAML requests with signature certificates`가 적용된다.

![Signed Requests 활성화](/assets/images/okta3/13-signed-requests-enabled.png)

체크박스 아래 설명에 그냥 지나치기 쉬운 문장이 하나 붙어 있다. "SSO URLs will be read dynamically from the request." 서명 검증을 켜면 Okta는 앱 설정에 저장된 ACS URL 대신 **요청에 담긴 `AssertionConsumerServiceURL`을 따른다**. 서명으로 요청의 출처가 보장되니 URL도 신뢰한다는 설계인데, 뒤집어 말하면 SP 개인키가 유출됐을 때 공격자가 assertion 수신 위치를 임의로 지정할 수 있다는 뜻이기도 하다. 고정 ACS만 쓰는 환경이라면 이 동작 변경을 인지하고 켜는 편이 낫다.

## 4. Apps API로 설정 대조

콘솔 UI에 전부 노출되지 않는 값들이 있어서, Apps API로 앱 객체를 직접 조회해 `settings.signOn`을 확인했다.

```powershell
$app = Invoke-RestMethod -Uri "$org/api/v1/apps/$appId" -Headers $h
$app.settings.signOn | ConvertTo-Json -Depth 6
```

![Apps API로 조회한 signOn 설정](/assets/images/okta3/14-apps-api-signon-settings.png)

```json
{
  "ssoAcsUrl": "http://localhost:5000/saml/acs/okta",
  "audience": "urn:lab:okta:saml-sp",
  "recipient": "http://localhost:5000/saml/acs/okta",
  "destination": "http://localhost:5000/saml/acs/okta",
  "subjectNameIdTemplate": "${user.userName}",
  "subjectNameIdFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
  "responseSigned": true,
  "assertionSigned": true,
  "signatureAlgorithm": "RSA_SHA256",
  "digestAlgorithm": "SHA256",
  "honorForceAuthn": true,
  "authnContextClassRef": "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport",
  "spIssuer": null,
  "requestCompressed": false,
  "attributeStatements": [ ... ]
}
```

앞 절의 관찰이 여기서 확인된다. `subjectNameIdTemplate`이 `${user.userName}`이고 `subjectNameIdFormat`은 그와 독립된 별개 필드다. 콘솔의 Name ID format 드롭다운은 뒤쪽만 바꾸고, 값을 만드는 건 앞쪽 템플릿이다. 형식을 Persistent로 바꿔도 이메일이 나온 이유가 JSON 두 줄로 드러난다.

나머지도 대조해두면 쓸모가 있다.

- `responseSigned`/`assertionSigned` 모두 `true` — Okta는 Response와 Assertion에 이중 서명한다. SP가 둘 중 하나만 검증하도록 짜여 있어도 통과하므로, 어느 쪽을 검증하는지 SP 구현에서 명확히 해둘 필요가 있다.
- `honorForceAuthn: true` — SP가 `ForceAuthn="true"`를 보내면 기존 세션이 있어도 재인증을 요구한다.
- `authnContextClassRef`가 `PasswordProtectedTransport`로 **설정값 자체에 박혀 있다.** 전편에서 MFA를 거쳐도 이 값이 안 바뀌던 문제의 근거가 이것이다. 런타임 인증 결과가 아니라 앱에 저장된 정적 값을 그대로 싣는다.
- `spIssuer: null` — SP Entity ID 검증을 하지 않는 상태다.
- `attributeStatements`에 전편에서 넣은 `groups` 필터가 `filterType: REGEX`, `filterValue: ".*"`로 남아 있다.

## 5. 미해결 항목

Signed Requests를 켠 뒤 서명된 `AuthnRequest`를 실제로 만들어 통과시키는 데까지는 가지 못했다. PowerShell에서 `SignedXml`로 SAML 요청에 XML-DSig를 붙이려면 canonicalization과 `Reference` URI 처리를 직접 맞춰야 해서, 미서명 요청이 거부되는 것까지만 확인하고 남겨뒀다. 확인이 필요한 것은 두 가지다. 서명 누락 시 Okta가 반환하는 오류 식별자, 그리고 "SSO URLs read dynamically" 동작에서 요청의 ACS URL을 앱 설정과 다른 값으로 넣었을 때 실제로 그쪽으로 전송되는지 여부다.

## 6. 정리

| 항목 | 확인 내용 |
|---|---|
| `InResponseTo` | `Response`와 `SubjectConfirmationData` 양쪽에 동일 값 — SP가 요청·응답 대응 검증 가능 |
| RelayState | 보낸 값 그대로 반환, 변형 없음 |
| Name ID format 4종 | `Format` URI만 변경, `NameID` 값은 4회 모두 동일 |
| 값 결정 주체 | `subjectNameIdFormat`이 아니라 `subjectNameIdTemplate`(`${user.userName}`) |
| persistent / transient | 명세상 가명·일회성이나 실제로는 이메일 그대로 — SP 구현이 오판할 여지 |
| `WantAuthnRequestsSigned` | 기본 `false`, SP 인증서 업로드 후에만 활성화 가능 |
| Signed Requests 부작용 | ACS URL을 앱 설정이 아닌 요청에서 동적으로 읽음 |
| 서명 범위 | `responseSigned` + `assertionSigned` 이중 서명 |
| `authnContextClassRef` | 앱 설정에 박힌 정적 값 — 전편 고정 문제의 근거 확인 |
| `spIssuer` | `null` — SP Entity ID 미검증 |

전편에서 "MFA를 거쳐도 `AuthnContextClassRef`가 안 바뀐다"고 관찰만 해뒀던 건을 이번에 API로 근거까지 확인했다. 다음은 예고해둔 대로 Okta AD Agent로 온프레미스 AD를 연동해 ADFS의 페더레이션 모델과 대조하는 작업이고, 서명된 `AuthnRequest` 생성은 그 전에 별도로 마무리할 생각이다.
