---
layout: single
title: "Entra ID에 OIDC/OAuth 앱을 등록하고 confidential+PKCE를 실측하다 — 온프렘 ADFS와 같은 결론인가"
excerpt: "온프렘 ADFS에서 확인한 'discovery에 광고 없어도 PKCE를 강제한다'는 결론이 클라우드 Entra ID에서도 성립하는지 검증한 기록. Entra ID 포털에서 Web(confidential) 앱을 등록하고 client secret·Graph 권한을 잡은 뒤, client credentials(S2S)와 OIDC Authorization Code+PKCE를 직접 던지고, 틀린 code_verifier를 먼저 보내는 negative-first로 Entra가 PKCE를 실제 검증(AADSTS501481)하는지 실측했다."
date: 2026-07-14
categories: [Infra, Identity]
tags: [entra-id, azure-ad, oidc, oauth2, pkce, rfc9700, confidential-client, microsoft-graph, client-credentials, 실측]
---

## 들어가며

앞선 글에서 온프렘 **ADFS**를 두고 하나의 질문을 실측으로 닫았다 — discovery(`.well-known/openid-configuration`)에 `code_challenge_methods_supported`가 없어도 ADFS는 PKCE를 실제로 검증하고 강제한다는 것. (→ [ADFS는 discovery에 광고하지 않아도 PKCE를 강제한다]({% post_url 26-07-14-pkce %}))

그렇다면 같은 질문을 **클라우드 Entra ID(구 Azure AD)** 로 옮기면 어떻게 될까. 특히 이번엔 public client가 아니라 **Web(confidential) 앱**, 즉 client_secret을 가진 앱에 PKCE를 **병행**했을 때다. RFC 9700은 confidential client에 대해 PKCE를 **MUST가 아니라 RECOMMENDED**로 둔다. 그럼 Entra는 confidential 앱이 보낸 code_challenge를 무시할까, 아니면 secret이 있어도 code_verifier를 실제로 대조할까?

이 글은 그 답을 문서가 아니라 **실측**으로 남긴 기록이다. 동시에 Entra ID 포털에서 앱을 **등록하는 전 과정**(앱 등록 → redirect URI → client secret → Graph 권한 → 관리자 동의)과, 그 위에서 **두 가지 흐름**(S2S client credentials, OIDC Authorization Code + PKCE)을 실제로 던진 과정을 스크린샷과 함께 정리한다.

**환경 정보**
- IdP: Microsoft Entra ID (클라우드), 테넌트 `contoso.onmicrosoft.com` *(예시값)*
- 앱 유형: Web application, **confidential client**(client_secret 보유)
- 테스트 클라이언트: Python 3.12 + Flask / requests, 자가서명 인증서 로컬 실행
- 프로토콜: ① OAuth2 Client Credentials(S2S) → Microsoft Graph, ② OIDC Authorization Code + PKCE(S256)

> 스크린샷은 `/assets/images/26-07-14-azure-adfs-oidc-oauth/` 아래에 두고 `![desc](img)` 형태로 삽입한다. 민감 값(테넌트 도메인·app id·secret·계정)은 본문에서 예시로 치환했다. **원본 스크린샷에는 실제 테넌트/계정 값이 노출되어 있으므로, 공개 배포 전 블러 처리가 필요하다.**

---

## 1. Entra ID 포털에서 앱 등록

관리자 계정으로 [entra.microsoft.com](https://entra.microsoft.com)에 로그인하고, 테넌트 도메인을 먼저 확인한다.

![entra.microsoft.com에 관리자 계정으로 로그인](/assets/images/26-07-14-azure-adfs-oidc-oauth/01-entra-admin-login.png)

![Entra ID 테넌트 도메인 조회](/assets/images/26-07-14-azure-adfs-oidc-oauth/02-entra-domain-lookup.png)

App registrations 메뉴에서 새 애플리케이션을 등록한다. 온프렘 ADFS가 **Application Group + Native/Server application**으로 앱을 잡던 것과 달리, Entra는 **App registration** 하나에 platform·secret·권한을 붙여가는 방식이다.

![Entra ID 앱 등록 절차 진입](/assets/images/26-07-14-azure-adfs-oidc-oauth/03-app-registration-steps.png)

![애플리케이션 등록 화면 — 이름·리다이렉션 URI 입력](/assets/images/26-07-14-azure-adfs-oidc-oauth/04-app-registration-screen.png)

등록에서 한 번 멈칫하게 되는 지점이 **지원되는 계정 유형(Supported account types)** 이다. 단일 테넌트(이 조직 디렉터리만) / 멀티테넌트 / 개인 MS 계정 포함 중 무엇을 고르느냐에 따라 issuer와 로그인 대상 범위가 달라진다. 이번 실측은 단일 테넌트 기준이다.

![지원되는 계정 유형에 대한 상세 안내](/assets/images/26-07-14-azure-adfs-oidc-oauth/05-supported-account-types.png)

![앱 등록 완료 — Application(client) ID / Directory(tenant) ID 확인](/assets/images/26-07-14-azure-adfs-oidc-oauth/06-app-registration-done.png)

등록이 끝나면 **Application(client) ID**와 **Directory(tenant) ID**가 발급된다. 이 두 값이 이후 토큰 요청의 핵심 파라미터다.

---

## 2. Redirect URI와 Authentication 구성

OIDC Authorization Code 흐름을 쓰려면 redirect URI를 정확히 등록해야 한다. 로컬 Flask 테스트라 루프백(`https://localhost:5001/callback`) 기준으로 잡고, 값이 정확한지 두 번 확인했다. redirect URI 불일치는 이후 `AADSTS50011` 류 에러의 단골 원인이라 여기서 확정해 두는 게 낫다.

![Redirect URI 구성 확인](/assets/images/26-07-14-azure-adfs-oidc-oauth/07-redirect-uri-config.png)

![Authentication — Redirect URI 정보 재확인](/assets/images/26-07-14-azure-adfs-oidc-oauth/08-authentication-redirect-recheck.png)

![Authentication — 설정 정보 재확인](/assets/images/26-07-14-azure-adfs-oidc-oauth/09-authentication-settings-recheck.png)

---

## 3. client secret 발급 (confidential client)

이 앱을 **confidential client**로 만드는 핵심 단계다. Certificates & secrets에서 client secret을 발급한다. secret 값은 발급 직후 한 번만 노출되므로 이때 안전하게 보관해야 한다.

![client secret 발급 진행](/assets/images/26-07-14-azure-adfs-oidc-oauth/10-secret-issue-1.png)

![client secret 발급 진행 (계속)](/assets/images/26-07-14-azure-adfs-oidc-oauth/11-secret-issue-2.png)

![client secret 발급 확인 — Value는 이 화면에서만 전체 노출](/assets/images/26-07-14-azure-adfs-oidc-oauth/12-secret-issue-confirm.png)

이 secret이 있으므로 이 앱은 secret만으로도 자신을 인증할 수 있다. 이번 실측의 관전 포인트는 **"secret이 있는데도 PKCE(code_verifier)를 Entra가 대조하는가"** 이다.

---

## 4. OAuth 키 발급과 검증 등록

이어서 OAuth 토큰 발급에 필요한 키/검증 설정을 잡는다.

![OAuth 키 발급](/assets/images/26-07-14-azure-adfs-oidc-oauth/13-oauth-key-issue.png)

![OAuth 키 발급 확인](/assets/images/26-07-14-azure-adfs-oidc-oauth/14-oauth-key-confirm.png)

![OAuth 검증 등록 step01](/assets/images/26-07-14-azure-adfs-oidc-oauth/15-oauth-verify-register.png)

---

## 5. API 권한 — Microsoft Graph와 관리자 동의

S2S(client credentials)로 Graph를 호출하려면 **애플리케이션 사용 권한(application permission)** 을 부여하고 **관리자 동의(admin consent)** 를 눌러야 한다. 여기서는 `Microsoft Graph → User.Read.All`(application)을 붙였다.

application permission은 위임(delegated)과 달리 로그인한 사용자 없이 앱 자체 권한으로 동작하므로, 반드시 테넌트 관리자 동의가 선행되어야 실제로 발급된 토큰에 role이 실린다.

![API 사용 권한 부여 화면](/assets/images/26-07-14-azure-adfs-oidc-oauth/16-api-permission-grant.png)

![OAuth 권한 추가](/assets/images/26-07-14-azure-adfs-oidc-oauth/17-oauth-permission-add.png)

![애플리케이션 사용 권한 추가](/assets/images/26-07-14-azure-adfs-oidc-oauth/18-oauth-app-permission.png)

![애플리케이션 사용 권한 추가 — step02](/assets/images/26-07-14-azure-adfs-oidc-oauth/19-oauth-app-permission-step02.png)

![애플리케이션 사용 권한 — 최종 확인](/assets/images/26-07-14-azure-adfs-oidc-oauth/20-oauth-app-permission-final.png)

![애플리케이션 사용 권한 — 관리자 동의까지 완료](/assets/images/26-07-14-azure-adfs-oidc-oauth/21-oauth-app-permission-final2.png)

권한 상태가 "Granted for {tenant}"로 바뀌면 준비 완료다.

---

## 6. 테스트 환경 준비

로컬에서 던지기 전에, 클라우드(Entra) 엔드포인트로 통신이 되는지와 Flask 실행에 필요한 인증서·가상환경이 준비됐는지 확인한다.

![Cloud(Entra) 통신 유무 확인](/assets/images/26-07-14-azure-adfs-oidc-oauth/22-cloud-connectivity-check.png)

![Flask 테스트용 인증서 및 가상환경 확인](/assets/images/26-07-14-azure-adfs-oidc-oauth/23-flask-cert-venv-check.png)

---

## 7. 흐름 ① — Client Credentials(S2S)로 Graph 호출

첫 번째로 **로그인 사용자 없이** client_id + client_secret만으로 토큰을 받는 S2S(client credentials) 흐름이다. `oauth_entra_s2s.py`를 실행하면 token 엔드포인트에서 access_token을 받고, 그 토큰으로 Microsoft Graph `/users`를 호출한다.

![client_secret 토큰만으로 로그인 후 Graph /users 호출 결과](/assets/images/26-07-14-azure-adfs-oidc-oauth/24-s2s-client-secret-login.png)

실측 결과(민감 값 치환):

```text
[1] token request : 200
    token_type : Bearer
    expires_in : 3599

[2] access_token payload:
    aud   : https://graph.microsoft.com
    appid : <application-client-id>
    roles : ['User.Read.All']
    upn   : (none)          # 사용자 컨텍스트 없음 = 앱 권한 토큰

[3] Graph /users : 200
    12 users
    - adm-...@contoso.onmicrosoft.com
    - user01@contoso.onmicrosoft.com
    - ...
```

읽을 포인트는 두 가지다.

- `aud`가 `https://graph.microsoft.com`, `roles`에 `User.Read.All`이 실렸다 — 앞서 부여한 **application permission + 관리자 동의**가 토큰에 반영됐다는 뜻.
- `upn`이 비어 있다 — 이건 사용자 위임 토큰이 아니라 **앱 자체 권한 토큰**이라는 신호다. 그래서 로그인 화면 없이 곧장 Graph를 호출할 수 있었다.

### 대화형(OIDC) 로그인 — 동의·MFA·계정 확인

같은 앱을 사용자 로그인(OIDC) 쪽으로 태우면 브라우저 흐름이 붙는다. 최초 로그인 시 앱 권한에 대한 동의, 2차 인증 수단 등록, 그리고 로그인 후 사용자 계정 정보 확인까지 이어진다.

![로그인 이후 동의(수락) 버튼 클릭](/assets/images/26-07-14-azure-adfs-oidc-oauth/25-consent-accept.png)

![로그인 후 2차 인증 수단 등록](/assets/images/26-07-14-azure-adfs-oidc-oauth/26-mfa-register.png)

![로그인 후 사용자 계정 정보 확인](/assets/images/26-07-14-azure-adfs-oidc-oauth/27-user-account-info.png)

### Entra ID 접근 테스트

발급받은 토큰/세션으로 Entra ID 리소스 접근을 몇 차례 확인했다.

![Entra ID 접근 테스트 01](/assets/images/26-07-14-azure-adfs-oidc-oauth/28-entra-access-test-01.png)

![Entra ID 접근 테스트 02](/assets/images/26-07-14-azure-adfs-oidc-oauth/29-entra-access-test-02.png)

![Entra ID 접근 테스트 03](/assets/images/26-07-14-azure-adfs-oidc-oauth/30-entra-access-test-03.png)

---

## 8. 흐름 ② — confidential + PKCE를 negative-first로 실측

이 글의 핵심이다. **Web(confidential) 앱**에 OIDC Authorization Code + PKCE(S256)를 얹고, ADFS 때와 똑같은 **negative-first** 기법으로 Entra가 code_verifier를 실제 검증하는지 가른다.

negative-first가 필요한 이유는 ADFS 글에서 정리한 것과 같다 — **authorization code는 1회용**이라, 올바른 verifier로 먼저 성공시키면 code가 소진되어 그 다음 실패가 "PKCE 실패"인지 "code 재사용"인지 구분되지 않는다. 그래서 **code를 소진하기 전에 틀린 verifier를 먼저** 던진다.

![PKCE 검증 step01 — 테스트 클라이언트 시작](/assets/images/26-07-14-azure-adfs-oidc-oauth/31-pkce-verify-step01.png)

![PKCE 검증 step02 — Entra 로그인 화면](/assets/images/26-07-14-azure-adfs-oidc-oauth/32-pkce-verify-step02-login.png)

로그인으로 code를 1개 확보한 뒤, ① 틀린 verifier로 먼저 교환하고 ② 그 다음 올바른 verifier로 재시도했다. 결과는 이렇다(민감 값 치환).

```json
{
  "mode": "Entra Web(confidential)+PKCE [negative-first]",
  "step1_wrong_verifier": {
    "http": 400,
    "error": "invalid_grant",
    "error_description": "AADSTS501481: The Code_Verifier does not match the code_challenge supplied in the authorization request."
  },
  "step2_correct_verifier_after": {
    "http": 200,
    "error": null
  },
  "VERDICT": "Entra가 PKCE를 실제로 검증함. 틀린 code_verifier -> 거부. discovery에 광고 없어도 강제됨 (ADFS와 동일 패턴)."
}
```

![PKCE 검증 step03 — 틀린 verifier가 AADSTS501481로 거부됨](/assets/images/26-07-14-azure-adfs-oidc-oauth/33-pkce-verify-step03-error.png)

두 가지가 확정된다.

- **step1**: confidential 앱(secret 보유)인데도 틀린 code_verifier를 던지니 `400 invalid_grant / AADSTS501481: The Code_Verifier does not match the code_challenge`로 **거부**됐다. Entra는 secret이 있어도 PKCE를 **무시하지 않고 대조한다.** RFC 9700이 confidential에 대해 RECOMMENDED로 둔 그 조합을, Entra는 실제로 검증한다.
- **AADSTS501481**은 code_verifier ↔ code_challenge 불일치를 명시한, **PKCE에 특정된 에러**다. redirect 불일치(50011)나 code 소진 같은 다른 원인과 섞이지 않는다.

### ADFS와 갈리는 지점 — step2

여기서 온프렘 ADFS와 클라우드 Entra의 **동작 차이**가 드러난다.

| 항목 | 온프렘 ADFS | 클라우드 Entra ID |
|------|-------------|-------------------|
| 틀린 verifier(step1) | 거부 `MSIS9720` | 거부 `AADSTS501481` |
| 그 뒤 올바른 verifier(step2) | **거부** `invalid_grant` (code 이미 소진) | **성공** `200` |
| 실패 교환 시 code 소진 | 소진함 | **소진하지 않음** |

ADFS는 실패한 토큰 교환에서도 authorization code를 **소진**시켜 step2가 `invalid_grant`이었다. 반면 **Entra는 step2에서 `200`으로 정상 발급**됐다 — 즉 Entra는 PKCE 검증에 실패한 교환에서는 code를 **소진하지 않고**, 이어진 올바른 verifier 교환을 받아줬다.

두 제품 모두 **PKCE를 강제**한다는 결론은 같지만, 실패한 code의 수명 처리(one-time 소진 시점)는 구현이 다르다. negative-first가 아니었다면 ADFS에서는 이 차이를 code 소진(MSIS9612)에 묻혀 볼 수 없었을 것이고, Entra에서는 애초에 성공에 묻혀 검증 여부 자체를 가릴 수 없었을 것이다.

> **핵심**: discovery(`code_challenge_methods_supported`)의 침묵은 ADFS든 Entra든 PKCE 미지원의 근거가 아니다. 둘 다 **광고 없이 검증·강제**한다. 다만 실패한 code의 소진 시점은 제품마다 다르므로, "검증한다"를 깨끗이 증명하려면 negative-first로 원인을 분리해야 한다.

---

## 정리

이번 실측으로 확정된 사실.

1. **Entra ID 앱 등록의 전 과정** — App registration → redirect URI → client secret(confidential화) → Graph application permission + 관리자 동의 — 을 밟으면, 온프렘 ADFS의 Application Group과 같은 목적지에 도달한다. 경로(포털 UX)는 다르지만 개념(confidential client + scope/permission)은 대응된다.
2. **Client Credentials(S2S)** 는 사용자 없이 앱 권한 토큰을 발급한다 — `roles: User.Read.All`, `upn: none`, Graph `/users` 200. 관리자 동의가 토큰에 role로 반영됨을 확인.
3. **Entra는 confidential 앱의 PKCE도 실제로 검증·강제한다** — secret이 있어도 틀린 code_verifier는 `AADSTS501481`로 거부. discovery에 광고 없어도 마찬가지. 이는 온프렘 ADFS의 결론([26-07-14 글]({% post_url 26-07-14-pkce %}))과 **동일한 패턴**이다.
4. **다만 실패한 code의 소진 시점은 다르다** — ADFS는 실패 교환에서도 code를 소진(step2 거부)하지만, Entra는 소진하지 않아 올바른 verifier로 재시도가 성공(step2 200)한다. "같은 결론, 다른 구현"을 negative-first가 분리해서 보여줬다.

교훈을 한 줄로 — **RFC 9700이 confidential에 PKCE를 권장(RECOMMENDED)하는 그 조합을, ADFS도 Entra도 discovery 광고 없이 실제로 강제한다. secret이 있으니 PKCE는 장식일 거라는 가정은 실측 앞에서 깨진다.**
