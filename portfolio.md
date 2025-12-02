# 포트폴리오

## 소개
이 포트폴리오는 Terraform, SSO 인증, Okta, Microsoft 365, ADFS, Keycloak, MBAM, Active Directory 등 다양한 주제를 다루는 기술 기사와 가이드 모음입니다.

---

## Terraform VPC, Subnet, Gateway 및 Route Table 설정
**카테고리:** terraform  
**태그:** AWS, terraform, vpc, subnet, gateway, route-table

이 가이드는 Terraform을 사용하여 AWS에서 VPC, 서브넷, 인터넷 게이트웨이, NAT 게이트웨이, 라우팅 테이블을 설정하는 방법을 설명합니다. 이 구성은 ap-northeast-2 리전에서 하나의 퍼블릭 서브넷과 하나의 프라이빗 서브넷을 포함하는 VPC를 생성합니다.

### 주요 포인트:
- ap-northeast-2에서 AWS 제공자 구성
- CIDR 블록 10.0.0.0/16으로 VPC 생성
- ap-northeast-2a에 CIDR 10.0.0.0/24로 퍼블릭 서브넷
- ap-northeast-2b에 CIDR 10.0.10.0/24로 프라이빗 서브넷
- 인터넷 게이트웨이 및 NAT 게이트웨이 설정
- 퍼블릭 및 프라이빗 라우팅 테이블

---

## Terraform 기본 가이드 (AWS 환경 설정)
**카테고리:** terraform  
**태그:** AWS, terraform

이 가이드는 AWS EC2 인스턴스 생성, IAM 계정 생성, 액세스 키 발급, zsh 및 oh-my-zsh 설치, AWS CLI 구성, AWS Linux 환경에서 Terraform 설치를 다룹니다.

### 주요 포인트:
- AWS EC2 인스턴스 생성
- IAM 계정 설정 및 액세스 키 발급
- zsh 및 oh-my-zsh 설치
- AWS CLI 구성
- Terraform 설치 및 기본 사용법

---

## SSO 인증 프로토콜에 대한 이해
**카테고리:** SSO  
**태그:** SAML, OIDC, OAuth, SSO

이 기사는 SAML, OAuth, OpenID Connect의 개념을 설명하며, 정의, 작동 원리, 주요 특징, 사용 사례, SSO 환경에서의 역할을 포함합니다.

### 주요 포인트:
- SAML: 인증 및 권한 부여를 위한 XML 기반 프로토콜
- OAuth: 리소스 접근을 위한 권한 부여 프로토콜
- OpenID Connect: OAuth 2.0 기반 인증 프로토콜

---

## Okta에서 Google Workspace 설정하기
**카테고리:** okta  
**태그:** okta, google-workspace, sso, saml

이 가이드는 Okta에서 Google Workspace 앱을 추가하고 Google Apps 회사 도메인을 설정하는 단계별 지침을 제공하며, 테스트 환경에서도 적용 가능합니다.

### 주요 포인트:
- 사전 준비: Okta 계정, Google Workspace 계정, 도메인 정보
- Okta Admin Console에서 단계별 설정
- Google Workspace 앱 통합
- 도메인 검증 및 테스트

---

## Office 365 E3 평가판과 Microsoft 365 Business 평가판 비교
**카테고리:** Office365  
**태그:** windows, ADFS, o365, m365

이 기사는 ADFS 경험이 있는 엔지니어를 위한 Office 365 E3와 Microsoft 365 Business 플랜을 비교하여 상세한 통찰력을 제공합니다.

### 주요 포인트:
- Office 365 E3 개요 및 기능
- Microsoft 365 Business 플랜 비교
- 상세 기능 비교 및 추천

---

## Keycloak ↔ ADFS 연동
**카테고리:** ActivcDirectoryFederationService  
**태그:** windows, ADFS

이 가이드는 OIDC를 사용하여 ADFS(2016, FBL Level 3)와 Keycloak을 통합하는 방법을 설명하며, `response_type=code id_token` 형태의 하이브리드 플로우에 중점을 둡니다.

### 주요 포인트:
- ADFS 인증 요청 구조
- Keycloak OIDC IdentityProvider SPI 확장
- 플로우 비교 및 배포 방법

---

## MBAM Windows 10 BitLocker Management 이해하기
**카테고리:** MBAM Windows 10 BitLocker Management  
**태그:** windows, MBAM, BitLocker

이 기사는 BitLocker 드라이브 암호화 관리를 위한 솔루션인 MBAM(Microsoft BitLocker Administration and Monitoring)에 대한 개요를 제공합니다.

### 주요 포인트:
- 중앙 집중식 BitLocker 암호화 관리
- 키 복구 관리
- 암호화 상태 모니터링
- 정책 준수 관리

---

## Active Directory 시작하기
**카테고리:** active-directory  
**태그:** windows, active-directory

이 기사는 네트워크 리소스 관리를 위한 Microsoft의 디렉터리 서비스인 Active Directory의 기본 개념과 설정 방법을 다룹니다.

### 주요 포인트:
- 사용자 및 그룹 관리
- 도메인 컨트롤러 기능
- 정책 기반 관리
- 디렉터리 서비스 및 통합

---

## 블로그 스타트
**카테고리:** coding  
**태그:** python, jekyll, blog

이 포스트는 Django 프로젝트 시작에 대한 기본 가이드를 제공하며, 프로젝트 생성, 앱 설정, 뷰 작성, URL 구성, 서버 실행을 포함합니다.

### 주요 포인트:
- Django 프로젝트 및 앱 생성
- 기본 뷰 및 URL 설정
- 서버 실행

---

## 결론
이 포트폴리오는 클라우드 컴퓨팅, 인증, 시스템 관리의 다양한 측면에 대한 가치 있는 통찰력을 제공하는 기술 기사와 가이드를 보여줍니다. 각 기사는 복잡한 주제를 이해하기 위한 단계별 지침과 주요 포인트를 제공하도록 설계되었습니다. 