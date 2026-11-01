---
layout: single
title: "Keycloak ↔ ADFS 연동"
categories: ["IAM", "ADFS"]
permalink: "/activcdirectoryfederationservice/ADFS-keycloak/"
tags: [windows, ADFS]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# Keycloak ↔ ADFS 연동 및 OIDC IdentityProvider SPI 확장 가이드

## 🔧 1. 목표

- ADFS(2016, FBL Level 3)를 Keycloak과 OIDC 방식으로 연동
- `response_type=code id_token` 형태의 Hybrid Flow 사용
- Keycloak SPI 확장으로 기본 OIDC 연동 동작 커스터마이징

---

## 🛠️ 2. ADFS 인증 요청 구조

### ✅ 기본 Authorization Code Flow
```http
GET /authorize?
  response_type=code
  &client_id=client123
  &redirect_uri=https://keycloak/callback
  &scope=openid profile email
```

### ✅ Hybrid Flow (커스터마이징 필요)
```http
GET /authorize?
  response_type=code id_token
  &client_id=client123
  &redirect_uri=https://keycloak/callback
  &scope=openid profile email
  &nonce=xyz
```

### 🧩 3. Keycloak OIDC IdentityProvider SPI 확장
📁 프로젝트 구조
```CSS
keycloak-custom-oidc-idp/
├── pom.xml
└── src/
    └── main/java/com/example/keycloak/
        ├── CustomOIDCIdentityProvider.java
        └── CustomOIDCIdentityProviderFactory.java
```

### 📄 CustomOIDCIdentityProvider.java
```java
public class CustomOIDCIdentityProvider extends OIDCIdentityProvider {
    public CustomOIDCIdentityProvider(KeycloakSession session, OIDCIdentityProviderConfig config) {
        super(session, config);
    }

    @Override
    protected UriBuilder createAuthorizationUrl(AuthenticationRequest request) {
        // 상위 구현이 client_id, redirect_uri, scope, state, nonce를 채움
        // response_type만 code -> code id_token으로 교체 (Hybrid Flow)
        return super.createAuthorizationUrl(request)
            .replaceQueryParam(OAuth2Constants.RESPONSE_TYPE, "code id_token");
    }
}
```

- 참고: Keycloak의 실제 시그니처는 `protected UriBuilder createAuthorizationUrl(AuthenticationRequest request)` (`AbstractOAuth2IdentityProvider`, `OIDCIdentityProvider`). 26.x 기준. 버전에 따라 다를 수 있으므로 사용하는 버전의 소스를 확인할 것.
- 참고: 기본 브로커 콜백 엔드포인트는 GET 쿼리 파라미터(`code`, `state`)만 읽음. Hybrid Flow의 기본 response_mode는 fragment이므로, 콜백 처리까지 별도 확장이 필요할 수 있음.

### 📄 CustomOIDCIdentityProviderFactory.java
```java
public class CustomOIDCIdentityProviderFactory extends OIDCIdentityProviderFactory {
    public static final String PROVIDER_ID = "custom-oidc";

    @Override
    public String getId() {
        return PROVIDER_ID;   // SPI 등록 ID (기본 "oidc"와 겹치지 않게)
    }

    @Override
    public String getName() {
        return "CustomOIDC";
    }

    @Override
    public OIDCIdentityProvider create(KeycloakSession session, IdentityProviderModel model) {
        return new CustomOIDCIdentityProvider(session, new OIDCIdentityProviderConfig(model));
    }
}
```

- 참고: Factory 등록을 위해 `src/main/resources/META-INF/services/org.keycloak.broker.provider.IdentityProviderFactory` 파일에 `com.example.keycloak.CustomOIDCIdentityProviderFactory`를 한 줄로 기재해야 함.

### 🧪 배포 방법
```
1.mvn package로 JAR 빌드

2.${KEYCLOAK_HOME}/providers 디렉토리에 복사

3.Keycloak 서버 재시작

4.Admin Console > Identity Providers > CustomOIDC 선택
```

### 🔐 4. Flow 동작 방식 비교

| **항목**            | **Implicit Flow**                     | **Hybrid Flow**                              |
|---------------------|---------------------------------------|---------------------------------------------|
| **토큰 전달 방식**   | 브라우저에 직접 전달<br>(URL 해시 통해) | 일부 토큰 브라우저로 전달,<br>access_token 등은 서버 교환 |
| **백엔드 서버 필요 여부** | ❌ 없음                                | ✅ 있음 (code 교환 필요)                     |
| **보안 수준**       | 낮음 (token 노출)                     | 중간~높음 (access_token 서버 보관)           |
| **리프레시 토큰**    | ❌ 지원 안 됨                          | ✅ 가능                                     |
| **Keycloak 브로커 지원**   | ❌ 브로커 설정에서 code 외 response_type 미지원 | ⚠️ 커스텀 SPI 필요                          |

- 참고: 위 "Keycloak 브로커 지원"은 Keycloak이 외부 OP(ADFS)에 요청을 보내는 Identity Provider 설정 기준임. Keycloak이 OP(서버)로 동작할 때는 클라이언트 설정의 Implicit Flow Enabled 옵션으로 Implicit Flow를 지원함(비권장).