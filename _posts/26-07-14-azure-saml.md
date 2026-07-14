---
layout: single
title: "Entra ID 실측(3) — SAML 2.0 SP를 붙여 OIDC·OAuth와 나란히 세우기"
excerpt: "OIDC·OAuth에 이어 세 번째 프로토콜 SAML을 Entra ID에 붙인다. 앱 등록이 아니라 엔터프라이즈 애플리케이션으로 등록하고, 직접 만든 python3-saml SP로 SP-initiated SSO를 건다. NameIDPolicy 거부(AADSTS750161)와 사용자 할당 필수 같은 SAML 특유의 벽을 넘으며, 세 프로토콜을 하나의 표로 정리한 마무리 기록."
date: 2026-07-14
categories: [IAM, Entra ID]
tags: [entra-id, saml, sso, python3-saml, xmlsec, oidc, oauth2, 실측]
---

## 들어가며

앞선 두 글에서 Entra ID를 대상으로 OIDC(+PKCE)와 OAuth(Client Credentials)를 실측했다. 온프렘 ADFS에서 다루던 세 프로토콜(SAML / OIDC / OAuth) 중 두 개를 클라우드에서 재현한 셈이다. 이번 글은 나머지 하나, **SAML 2.0**이다.

SAML은 앞의 두 프로토콜과 결이 완전히 다르다. JSON/JWT가 아니라 **XML 기반**이고, 토큰이 아니라 **서명된 Assertion**을 주고받으며, Entra에서 등록하는 위치조차 다르다. 직접 만든 Service Provider(SP)를 Entra에 물려 SP-initiated SSO를 걸고, 그 과정에서 만나는 SAML 특유의 벽 두 가지를 넘는다.

**환경**
- IdP: Entra ID, 테넌트 `example-lab.onmicrosoft.com` *(예시값)*
- SP: Python 3.12 + Flask + `python3-saml`(OneLogin), `https://localhost:7000`
- 대상 사용자: 테넌트에 동기화된 계정

> 스크린샷은 `/assets/images/26-07-14-azure-saml/` 아래에 두고 `![desc](img)` 형태로 삽입한다. 민감 값(테넌트 ID·도메인·app id·object id·계정 UPN)은 본문에서 예시로 치환했다. **원본 스크린샷에는 실제 테넌트/계정 값이 노출되어 있으므로, 공개 배포 전 블러 처리가 필요하다.**

---

## SAML은 앞의 두 트랙과 어디가 다른가

먼저 지형을 잡아두면 설정이 헷갈리지 않는다.

| | OIDC / OAuth | SAML |
|---|-------------|------|
| Entra 등록 위치 | 앱 등록(App Registration) | **엔터프라이즈 앱(Enterprise Application)** |
| 프로토콜 | JSON/JWT, HTTP redirect | **XML, HTTP-POST** |
| 증명물 | id_token / access_token (JWT) | **Assertion (서명된 XML)** |
| SP 식별자 | client_id | **Entity ID (audience)** |
| 콜백 | redirect_uri | **ACS (Assertion Consumer Service) URL** |
| 서명 검증 | jwks (공개키 JSON) | **X.509 인증서 (IdP 메타데이터)** |
| 사용자 접근 | (기본 허용) | **명시적 할당 필수** |

핵심은 두 가지다. SAML은 **엔터프라이즈 앱**에서 설정하고, 서명 검증을 **X.509 인증서**로 한다. 이는 ADFS에서 Relying Party Trust로 하던 그 트랙이 클라우드로 온 것이다.

---

## 준비 — python3-saml과 xmlsec

SP 코드는 `python3-saml`(OneLogin)을 쓰는데, 이 라이브러리는 C 라이브러리 `xmlsec`에 의존한다. 예전에는 Windows에서 이 빌드가 까다로워 WSL/Mac이 권장됐지만, 지금은 미리 빌드된 wheel이 제공되어 Windows에서도 그냥 설치된다.

```powershell
pip install python3-saml
# xmlsec-1.3.x-cp312-cp312-win_amd64.whl 이 함께 설치됨 (C 빌드 불필요)
```

설치 후 실제 로드까지 되는지 확인한다. xmlsec는 런타임 DLL 문제가 종종 있어 import 확인이 안전하다.

```powershell
python -c "import xmlsec; from onelogin.saml2.auth import OneLogin_Saml2_Auth; print('OK', xmlsec.__version__)"
# -> OK 1.3.17
```

---

## Entra Enterprise Application 만들기

OIDC/OAuth와 달리 SAML은 **앱 등록이 아니라 엔터프라이즈 앱**에서 시작한다.

1. Entra 포털 → **엔터프라이즈 앱** → **+ 새 애플리케이션** → **자신만의 애플리케이션을 만드세요**
2. 이름 `saml-sp-test`, 유형은 **"갤러리에 없는 다른 애플리케이션 통합(비갤러리)"**
3. 생성 후 → **Single sign-on** → **SAML** 타일 선택

![Entra 홈 → 엔터프라이즈 앱 메뉴 진입](/assets/images/26-07-14-azure-saml/01-enterprise-app-menu.png)

![모든 애플리케이션 → + 새로운 애플리케이션](/assets/images/26-07-14-azure-saml/02-new-application.png)

![자신만의 애플리케이션 만들기 — "갤러리에 없는 다른 애플리케이션 통합(비갤러리)" 선택](/assets/images/26-07-14-azure-saml/03-create-own-app-nongallery.png)

![등록 후 saml-sp-test 개요 — Application ID / Object ID 확인](/assets/images/26-07-14-azure-saml/04-app-overview.png)

![Single sign-on 방법 선택 — SAML 타일](/assets/images/26-07-14-azure-saml/05-sso-method-select-saml.png)

SSO 방법을 고르는 화면에서 SAML/암호 기반/연결됨/IWA 등 각 방식의 설명은 "도움말 보기"에서 확인할 수 있다.

![다른 Single sign-on 방법 이해 — 각 SSO 방식 설명](/assets/images/26-07-14-azure-saml/06-sso-method-help.png)

**기본 SAML 구성**에서 두 값을 SP와 일치시켜 등록한다.

- **식별자(엔터티 ID)**: `https://localhost:7000/saml/metadata`
- **회신 URL(ACS)**: `https://localhost:7000/saml/acs`

로그인 URL·릴레이 상태·로그아웃 URL은 비워둔다(SP-initiated라 불필요). 저장하면 하단 "SAML 인증서" 섹션에 **앱 페더레이션 메타데이터 URL**이 나온다. 이것을 복사해 둔다.

SAML 타일을 고르면 "SAML로 Single Sign-On 설정" 화면이 뜨는데, ①기본 SAML 구성 ②특성 및 클레임 ③SAML 인증서 순으로 번호가 매겨져 있다. ①의 "편집"으로 들어간다.

![SAML로 Single Sign-On 설정 — 3단계 구성 개요](/assets/images/26-07-14-azure-saml/07-saml-sso-overview.png)

처음엔 식별자·회신 URL 모두 비어 있다. "식별자 추가", "답장 URL 추가"로 값을 넣는다.

![기본 SAML 구성 — 식별자/회신 URL 입력 전](/assets/images/26-07-14-azure-saml/08-basic-saml-config-empty.png)

![기본 SAML 구성 — Entity ID / ACS URL 입력 후 저장](/assets/images/26-07-14-azure-saml/09-basic-saml-config-values.png)

저장하면 "SAML 인증서" 섹션에 **앱 페더레이션 메타데이터 URL**이 채워진다.

![SAML 인증서 — 앱 페더레이션 메타데이터 URL 확인](/assets/images/26-07-14-azure-saml/10-federation-metadata-url.png)

Entra의 메타데이터 URL은 ADFS와 형태가 다르다. 끝에 `?appid=...`가 붙는 것이 특징이다.

```
https://login.microsoftonline.com/<tenant-id>/federationmetadata/2007-06/federationmetadata.xml?appid=<app-id>
```

### 사용자 할당 — SAML의 첫 함정

엔터프라이즈 앱은 App Registration과 달리 **접근할 사용자를 명시적으로 할당**해야 한다. 기본값은 아무도 접근 불가다.

**사용자 및 그룹 → + 사용자/그룹 추가**에서 테스트 계정을 할당한다. 무료 플랜에서는 그룹 할당은 막히지만(P1/P2 필요) 개별 사용자 할당은 된다. 이 단계를 빠뜨리면 로그인 시 "앱에 액세스 권한이 없다"로 막힌다.

![사용자 및 그룹 — 개별 사용자 할당](/assets/images/26-07-14-azure-saml/11-user-group-assignment.png)

---

## SP 코드 — ADFS용에서 Entra용으로

기존에 ADFS Relying Party용으로 만들어 둔 SP가 있었다. Entra로 돌리기 위해 바뀐 곳은 세 군데뿐이다.

**① 메타데이터 URL** — ADFS 경로에서 Entra의 `?appid=` URL로 교체.

```python
METADATA_URL = (
    "https://login.microsoftonline.com/<tenant-id>"
    "/federationmetadata/2007-06/federationmetadata.xml"
    "?appid=<app-id>"
)
```

**② ADFS 호환 옵션 제거** — ADFS 서명 검증용으로 켜뒀던 `lowercaseUrlencoding`을 뺀다. Entra에는 불필요하다.

**③ TLS 검증** — Entra는 공개 CA라 `verify=True`로 정상 동작. 랩 사설 CA 우회가 필요 없다.

메타데이터에서 IdP 서명 인증서를 읽어 오고(`OneLogin_Saml2_IdPMetadataParser.parse`), SP 설정에서 `wantAssertionsSigned: True`로 assertion 서명 검증을 요구한다. 나머지 흐름(`/saml/login` → AuthnRequest, `/saml/acs` → 서명검증·파싱)은 그대로다.

SP가 `/saml/metadata`로 퍼블리시하는 자체 메타데이터를 열어 보면, Entra에 등록한 Entity ID·ACS와 함께 `WantAssertionsSigned="true"`, `NameIDFormat...persistent`가 그대로 나온다. Entra에 넣은 값과 SP가 주장하는 값이 일치하는지 여기서 교차 확인할 수 있다.

![SP 자체 메타데이터 — Entity ID / ACS / NameIDFormat / WantAssertionsSigned](/assets/images/26-07-14-azure-saml/12-sp-metadata-xml.png)

---

## 실행 — 그리고 두 번째 함정 AADSTS750161

SP를 띄우면 인덱스에 `Login`과 `SP Metadata` 링크가 뜬다. `Login`을 누르면 `/saml/login`으로 들어가 AuthnRequest가 생성되고 Entra로 리다이렉트된다.

![SP 인덱스 — Login / SP Metadata 링크](/assets/images/26-07-14-azure-saml/13-sp-login-page.png)

그런데 첫 시도에서 Entra가 로그인 화면 대신 에러를 뱉었다.

```
AADSTS750161: Allowed SAML authentication request's NameIDPolicy formats are:
  emailAddress, unspecified(1.1), persistent, transient
```

SP가 요청한 NameID 형식이 Entra 허용 목록에 없다는 것이다. 코드는 다음을 요청하고 있었다.

```python
"NameIDFormat": "urn:oasis:names:tc:SAML:2.0:nameid-format:unspecified",
```

문제는 **버전**이다. Entra 허용 목록의 `unspecified`는 **1.1 버전**만이고 **2.0 unspecified는 없다**. ADFS는 2.0 unspecified를 받아줬지만 Entra는 받지 않는다 — ADFS→Entra 마이그레이션에서 자주 걸리는 지점이다.

해결은 허용 목록 중 하나로 바꾸는 것. `persistent`가 표준적이다.

```python
"NameIDFormat": "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent",
```

> **주의 — 설정 캐시**
> SP 코드가 IdP 설정을 캐시(`_SETTINGS_CACHE`)한다면, 파일만 고쳐서는 반영되지 않는다. 반드시 서버를 재시작해야 한다.

---

## 성공 — 서명된 Assertion 파싱

NameID 형식을 고치고 다시 로그인하면, 이번엔 에러 대신 Microsoft 로그인 화면이 뜬다.

![Entra 로그인 — 계정 입력](/assets/images/26-07-14-azure-saml/14-entra-login.png)

![Entra 로그인 — 암호 입력](/assets/images/26-07-14-azure-saml/15-password-input.png)

인증에 성공하면 Entra는 ACS(`/saml/acs`)로 **SAMLResponse를 HTTP-POST**로 보낸다. 개발자 도구의 Payload 탭에서 Base64로 인코딩된 SAMLResponse 원문을 확인할 수 있다.

![ACS로 POST된 SAMLResponse 원문(Base64)](/assets/images/26-07-14-azure-saml/16-samlresponse-raw.png)

SP가 이 응답의 서명을 검증하고 파싱하면 NameID와 Attributes가 나온다.

```
NameID      : 84Mpy...OfeGw      (opaque persistent id)
NameIDFormat: urn:oasis:names:tc:SAML:2.0:nameid-format:persistent

Attributes:
  .../claims/tenantid        : ['<tenant-id>']
  .../claims/objectidentifier: ['<user-object-id>']
  .../claims/displayname     : ['<사용자 표시명>']
  .../claims/identityprovider: ['https://sts.windows.net/<tenant-id>/']
  .../claims/authnmethodsreferences: ['...:PasswordProtectedTransport']
  .../ws/2005/05/identity/claims/name: ['<upn>']
```

![ACS 성공 — NameID(persistent) + Attributes 파싱 결과](/assets/images/26-07-14-azure-saml/17-acs-success-attributes.png)

두 가지를 읽을 수 있다.

**NameID가 불투명(opaque)하다.** persistent 형식은 이메일이나 UPN이 아니라 **SP별로 고정된 익명 식별자**를 준다. 같은 사용자는 이 SP에 항상 같은 값이 오지만 다른 SP에는 다른 값이 간다. OIDC의 `sub`(pairwise)와 같은 프라이버시 보호 개념이다.

**Attributes가 XML에서 파싱됐다.** Entra가 서명한 assertion을, SP가 메타데이터에서 읽은 X.509 인증서로 검증하는 데 성공했다는 뜻이기도 하다. 검증에 실패했다면 "SAML 검증 실패"가 떴을 것이다. 클레임 자체는 OIDC의 id_token 클레임과 대응하지만, 담기는 그릇이 JSON이 아니라 서명된 XML이라는 점이 다르다.

---

## 세 프로토콜 완주 — 하나의 표로

이로써 온프렘에서 다루던 세 프로토콜을 Entra에서 모두 재현했다.

| 항목 | OIDC | OAuth (S2S) | SAML |
|------|------|-------------|------|
| Entra 등록 | 앱 등록 | 앱 등록 | 엔터프라이즈 앱 |
| 증명물 | id_token (JWT) | access_token (JWT) | Assertion (서명 XML) |
| 사용자 식별자 | sub / preferred_username | (없음, 앱 토큰) | NameID (persistent) |
| 클레임 형식 | JSON | JSON | XML attributes |
| 서명 검증 | jwks (공개키) | jwks | X.509 (메타데이터) |
| 콜백 | redirect_uri | (없음) | ACS URL |
| 사용자 할당 | 불필요 | 불필요 | 필수 |

SAML만 유독 열이 다르다 — XML, 엔터프라이즈 앱, ACS POST, 사용자 명시 할당. 레거시 프로토콜로 불리지만 여전히 엔터프라이즈에서 광범위하게 쓰이는 이유(성숙도, 서명 기반 신뢰 모델)를 설정과 실행으로 확인한 셈이다.

---

## 곁다리 트러블슈팅

> **AADSTS750161 — NameIDPolicy 거부**
> Entra는 `emailAddress / unspecified(1.1) / persistent / transient`만 허용한다. **2.0 unspecified는 받지 않는다.** ADFS는 받아주므로, ADFS→Entra 전환 시 SP의 NameIDFormat을 `persistent`(또는 emailAddress)로 바꿔야 한다.

> **"앱에 액세스 권한이 없음" — 사용자 미할당**
> 엔터프라이즈 앱은 할당된 사용자만 로그인 가능하다. `사용자 및 그룹`에서 개별 사용자를 할당하지 않으면 로그인이 막힌다. 무료 플랜에서는 그룹 할당이 불가하니(P1/P2 필요) 개별 사용자로 할당한다.

> **localhost vs 127.0.0.1**
> SP의 Entity ID/ACS를 `localhost`로 등록했다면 접속도 `localhost`로 해야 한다. `127.0.0.1`은 SAML에서 다른 호스트로 취급되어 audience 불일치가 날 수 있다.

> **설정 캐시로 수정이 반영되지 않을 때**
> IdP 설정을 캐시하는 구조라면 파일 수정 후 서버를 재시작해야 새 값이 적용된다.

---

## 정리

- SAML은 **엔터프라이즈 앱**에서 등록하고, 서명된 **XML Assertion**을 **X.509 인증서**로 검증한다. OIDC/OAuth와 등록 위치·프로토콜·검증 방식이 모두 다르다.
- Entra는 **2.0 unspecified NameIDPolicy를 거부**한다(AADSTS750161). ADFS와의 차이라 마이그레이션 시 주의해야 한다.
- 엔터프라이즈 앱은 **사용자 명시 할당이 필수**다. 이것이 OIDC 앱 등록과의 눈에 띄는 운영 차이다.
- persistent NameID는 SP별 **불투명 식별자**를 주어, OIDC의 pairwise `sub`와 같은 프라이버시 모델을 따른다.

세 프로토콜을 같은 IdP(Entra)에서 나란히 세워 보니, 표면의 형식 차이 아래에 공통 구조(신원 주장 + 서명 검증 + 대상 바인딩)가 반복된다는 것이 보인다. 그리고 그 공통 구조를 실제로 이해하는 가장 빠른 길은, 역시 문서를 읽는 것보다 SP를 하나 띄워 직접 던져보는 것이었다.