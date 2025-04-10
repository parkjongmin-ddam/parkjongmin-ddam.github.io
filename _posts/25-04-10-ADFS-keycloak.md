---
layout: single
title: "Keycloak ↔ ADFS 연동"
categories: ActivcDirectoryFederationService
tag: [windows, ADFS]
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
    protected URI createAuthorizationUrl(OIDCIdentityProviderConfig config, String state, String nonce) {
        return UriBuilder.fromUri(config.getAuthorizationUrl())
            .queryParam(OAuth2Constants.RESPONSE_TYPE, "code id_token")  // Hybrid Flow 적용
            .queryParam(OAuth2Constants.CLIENT_ID, config.getClientId())
            .queryParam(OAuth2Constants.REDIRECT_URI, config.getRedirectUrl())
            .queryParam(OAuth2Constants.SCOPE, config.getDefaultScope())
            .queryParam(OAuth2Constants.STATE, state)
            .queryParam(OIDCLoginProtocol.NONCE_PARAM, nonce)
            .build();
    }
}
```

### 📄 CustomOIDCIdentityProviderFactory.java
```java
public class CustomOIDCIdentityProviderFactory extends OIDCIdentityProviderFactory {
    @Override
    public String getName() {
        return "CustomOIDC";
    }

    @Override
    public OIDCIdentityProvider create(KeycloakSession session, OIDCIdentityProviderConfig config) {
        return new CustomOIDCIdentityProvider(session, config);
    }
}
```

### 🧪 배포 방법
```
1.mvn package로 JAR 빌드

2.${KEYCLOAK_HOME}/providers 디렉토리에 복사

3.Keycloak 서버 재시작

4.Admin Console > Identity Providers > CustomOIDC 선택
```

### 🔐 4. Flow 동작 방식 비교
```
아래는 요청하신 내용을 표로 작성한 결과입니다:

| **항목**            | **Implicit Flow**                     | **Hybrid Flow**                              |
|---------------------|---------------------------------------|---------------------------------------------|
| **토큰 전달 방식**   | 브라우저에 직접 전달<br>(URL 해시 통해) | 일부 토큰 브라우저로 전달,<br>access_token 등은 서버 교환 |
| **백엔드 서버 필요 여부** | ❌ 없음                                | ✅ 있음 (code 교환 필요)                     |
| **보안 수준**       | 낮음 (token 노출)                     | 중간~높음 (access_token 서버 보관)           |
| **리프레시 토큰**    | ❌ 지원 안 됨                          | ✅ 가능                                     |
| **Keycloak 지원**   | ❌ 기본 미지원                         | ⚠️ 커스텀 SPI 필요                          |

```