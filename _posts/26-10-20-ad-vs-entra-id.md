---
layout: single
title: "[IAM 개념 정리] Active Directory와 Entra ID — 프로토콜, 구조, 정책, 조건부 액세스, 하이브리드"
excerpt: "Entra ID는 클라우드에 올린 Active Directory가 아니다. 두 시스템이 전제하는 신뢰 모델(네트워크 경계 vs ID 경계)부터 인증 프로토콜(Kerberos·NTLM vs OAuth 2.0·OIDC·SAML), 디렉터리 구조(OU 계층 vs 평면 구조와 관리 단위), 정책 적용 방식(GPO vs Intune·조건부 액세스), MFA와 보안 기본값, 하이브리드 구성(동기화 방향, PHS·PTA·페더레이션, 쓰기 저장, SOA 전환)까지 Microsoft Learn 문서를 기준으로 비교했다."
date: 2026-10-20
categories: [IAM]
tags: [ActiveDirectory, EntraID, Kerberos, ConditionalAccess, ZeroTrust, EntraConnect, HybridIdentity, MFA]
---

Entra ID를 "클라우드에 있는 Active Directory"로 이해하는 경우가 많다. 이름도 Azure Active Directory였고, 하이브리드 환경에서는 같은 계정이 양쪽에 보이니 그렇게 보일 만하다. 하지만 두 시스템은 설계 전제, 인증 프로토콜, 디렉터리 구조, 정책 적용 방식이 모두 다르다. 온프레미스 AD를 관리하던 방식 그대로 Entra ID를 관리하면 OU 구조를 재현하려다 막히거나, 네트워크 경계를 믿는 습관이 클라우드에 그대로 옮겨져 보안 공백이 생긴다.

이 글은 두 시스템의 차이를 신뢰 모델 → 인증 프로토콜 → 디렉터리 구조 → 정책 → 조건부 액세스 → MFA → 하이브리드 순서로 정리했다. 기능과 라이선스 관련 내용은 Microsoft Learn 문서를 기준으로 확인했고, 다이어그램은 직접 작성했다. 인증 프로토콜 자체(OAuth 2.0, OIDC, SAML)는 [인증 개념 7가지]({% post_url 26-10-20-auth-7-concepts %})에서 다뤘다.

---

## 1. 설계 전제: 네트워크 경계 vs ID 경계

![신뢰 모델 비교](/assets/images/2026-10-20-ad-vs-entra-id/01-trust-model.png)

### Active Directory

Active Directory는 Windows 2000(1999년 말 RTM)과 함께 나왔다. 당시 전제는 다음과 같았다.

- 사용자는 사무실에 있다.
- 업무 시스템(파일 서버, 프린터, 사내 앱)은 사내 네트워크 안에 있다.
- 기기는 회사가 지급하고 도메인에 가입돼 있다.

이 전제에서 보안 경계는 네트워크다. 사내망에 들어와 도메인에 로그인하면 그 안의 리소스에 비교적 자유롭게 접근할 수 있다. 방화벽과 VPN이 경계를 지키고, 경계 안은 신뢰한다.

### Entra ID

Entra ID는 다른 전제에서 출발했다.

- 사용자는 집, 카페, 출장지에 있다.
- 업무 시스템은 Microsoft 365, Salesforce, ServiceNow 같은 SaaS다. 회사 네트워크 안에 있지 않다.
- 기기는 회사 지급 기기일 수도, 개인 기기일 수도 있다.

사내 네트워크라는 경계가 의미를 잃었으므로 경계는 ID가 된다. 요청이 어느 네트워크에서 왔는지보다 누가, 어떤 기기로, 무엇에 접근하는지를 요청마다 평가한다. 이것이 제로 트러스트(Zero Trust) 모델이다.

| 항목 | Active Directory | Entra ID |
|---|---|---|
| 등장 시기 | 1999년 (Windows 2000) | 2010년대 (Azure AD → 2023년 Entra ID로 개명) |
| 전제 환경 | 사내 네트워크, 도메인 가입 기기 | 인터넷, SaaS, 개인·회사 기기 혼재 |
| 보안 경계 | 네트워크 (방화벽, VPN) | ID (사용자·기기·앱·위험 신호) |
| 신뢰 방식 | 경계 안이면 신뢰 | 요청마다 평가 |
| 배포 형태 | 직접 운영하는 도메인 컨트롤러(DC) | Microsoft가 운영하는 SaaS (테넌트) |

### 경계 신뢰 모델의 약점

경계 안을 신뢰하는 구조에서는 공격자가 경계 안에 한 번 들어오면 할 수 있는 일이 많다. 피싱으로 사용자 PC 하나를 장악한 공격자는 그 PC의 도메인 자격 증명으로 LDAP을 조회해 그룹·권한 구조를 파악하고, 관리자 세션이 남은 서버를 찾아 다음 서버로 이동한다(측면 이동, lateral movement). 이 경로를 그래프로 확인하는 실습은 [BloodHound CE 실습]({% post_url 26-10-14-bloodhound-lab %})에 정리했다.

---

## 2. 인증 프로토콜

![인증 경로 비교](/assets/images/2026-10-20-ad-vs-entra-id/02-auth-paths.png)

### 사용하는 프로토콜

| 구분 | Active Directory | Entra ID |
|---|---|---|
| 주 인증 프로토콜 | Kerberos | OAuth 2.0, OpenID Connect |
| 보조·레거시 | NTLM | SAML 2.0, WS-Federation |
| 디렉터리 조회 | LDAP | Microsoft Graph API (HTTPS REST) |
| 전송 | 사내망의 Kerberos(88), LDAP(389/636), SMB 등 | HTTPS(443) |
| 인증 결과물 | Kerberos 티켓(TGT, 서비스 티켓) | 토큰(ID Token, Access Token, SAML Assertion) |
| 대상 앱 | 도메인 가입 기기, 파일 서버, Windows 통합 인증 앱 | 웹 앱, SaaS, 모바일 앱, API |

Entra ID에는 도메인 컨트롤러가 없다. Kerberos 티켓을 주고받는 KDC도, LDAP 서버도, SYSVOL도 없다. 조회와 관리는 Microsoft Graph API로 한다. 같은 Microsoft 제품이지만 다른 종류의 ID 플랫폼이다.

### 같은 사용자, 두 가지 인증 경로

회사 노트북을 들고 카페에서 일하는 사용자를 예로 든다.

- Teams 접속: 브라우저나 앱이 HTTPS로 Entra ID에 로그인하고 토큰을 받는다. 인터넷만 있으면 되고 VPN은 필요 없다.
- 사내 파일 서버(`\\fs01\share`) 접속: 파일 서버는 Kerberos로 인증하고, Kerberos 티켓은 DC가 발급한다. 카페에서는 DC와 파일 서버에 닿을 수 없으므로 VPN을 연결해야 접근할 수 있다.

같은 사용자, 같은 기기에서 인증 경로가 둘로 나뉜다. 이 차이를 이해해야 원격 근무 환경에서 "왜 이건 되고 저건 안 되는지"를 설명할 수 있다.

### "Kerberos는 인터넷에서 동작하지 않는다"의 예외

기본 구성에서는 맞는 말이지만 예외가 있다.

- KDC Proxy(MS-KKDCP): Kerberos 메시지를 HTTPS로 감싸 인터넷 너머의 KDC에 전달한다. Windows Server의 KDC 프록시 서비스로 구성하며, RD 게이트웨이·DirectAccess 같은 원격 접속 구성에서 쓰인다.
- Microsoft Entra Kerberos: Entra ID가 클라우드 KDC 역할을 해 Kerberos 티켓을 발급한다. Azure Files SMB 접근, Windows Hello for Business의 cloud Kerberos trust, FIDO2 보안 키로 온프레미스 리소스에 SSO하는 시나리오에 쓰인다.

Entra Kerberos가 온프레미스 리소스용으로 발급하는 것은 부분 TGT(partial TGT)다. 사용자 SID만 있고 그룹 정보가 없어서, 클라이언트가 온프레미스 DC에 보내 완전한 TGT로 교환해야 한다. 즉 Azure Files처럼 클라우드 리소스는 DC 없이 접근할 수 있지만, 온프레미스 파일 서버에 접근하려면 여전히 DC와 해당 서버에 닿을 수 있는 네트워크가 필요하다.

---

## 3. 디렉터리 구조: 계층 vs 평면

![디렉터리 구조 비교](/assets/images/2026-10-20-ad-vs-entra-id/03-structure.png)

### Active Directory: 계층 구조

AD는 포리스트 → 도메인 → OU(Organizational Unit) → 객체로 이어지는 트리다.

```text
corp.example.com (도메인)
├── OU=Seoul
│   ├── OU=Users      → GPO: 화면 잠금 10분
│   └── OU=Computers  → GPO: BitLocker 강제
└── OU=Busan
    └── OU=Users
```

OU는 두 가지 역할을 한다. 하나는 GPO를 연결하는 단위이고(OU에 연결한 GPO가 하위 객체에 상속), 다른 하나는 관리 위임 단위다(특정 OU의 사용자 비밀번호 재설정 권한을 지역 관리자에게 위임). 객체는 하나의 OU에만 속한다.

### Entra ID: 평면 구조

Entra ID 테넌트에는 OU가 없다. 사용자, 그룹, 기기가 테넌트 하나에 평면으로 존재하고, 묶음과 위임은 다른 수단으로 한다.

| AD 개념 | Entra ID에서 대응하는 것 | 차이 |
|---|---|---|
| 포리스트·도메인 | 테넌트 | 테넌트 하나가 하나의 디렉터리. 도메인은 UPN 접미사(검증된 도메인)일 뿐 |
| OU (정책 연결) | 그룹 (Intune·조건부 액세스 정책의 할당 대상) | 정책은 OU 위치가 아니라 그룹 멤버십으로 적용 |
| OU (관리 위임) | 관리 단위 (Administrative Unit) | 역할 범위만 제한. 중첩 불가, 객체가 여러 관리 단위에 속할 수 있음 |
| 보안 그룹 | 보안 그룹, Microsoft 365 그룹 | 동적 멤버십 그룹(속성 기반 자동 소속) 지원 |
| 컴퓨터 개체 | 기기 개체 (Entra 가입, 하이브리드 가입, 등록) | 조건부 액세스의 기기 신호로 사용 |
| DC, LDAP, SYSVOL | 없음 | 관리·조회는 Microsoft Graph API |

관리 단위는 관리 권한의 범위만 제한한다. 관리 단위에 넣은 사용자라도 기본 권한으로 다른 사용자를 조회하는 것은 막지 않는다. 관리 단위 생성은 무료 라이선스에서 가능하지만, 관리 단위 범위로 역할을 할당받는 관리자에게는 Entra ID P1이 필요하다.

### OU 구조를 옮기지 않는다

온프레미스 OU 트리를 Entra ID에 재현하려는 시도는 대부분 실패한다. 재현할 대상 자체가 없기 때문이다. Entra ID에서는 "이 사용자가 트리의 어디에 있는가"가 아니라 "이 사용자가 어떤 그룹에 속하고 어떤 속성을 가졌는가"로 정책과 권한이 결정된다. 부서 속성으로 동적 그룹을 만들고, 그 그룹에 라이선스와 정책을 할당하는 방식이 Entra ID의 기본 패턴이다. 이 동작은 [M365 샌드박스 1주차]({% post_url 26-10-15-m365-sandbox-week1 %})에서 실측했다.

### 클라우드에서 DC가 꼭 필요하다면

LDAP 바인드, Kerberos·NTLM 인증, GPO가 필요한 레거시 앱을 Azure로 옮겨야 한다면 Entra ID가 아니라 Microsoft Entra Domain Services를 검토한다. Microsoft가 운영하는 관리형 도메인으로, Entra ID의 사용자를 받아 전통적인 도메인 서비스를 제공한다. 이름은 비슷하지만 Entra ID와는 별도 서비스다.

---

## 4. 정책 적용: GPO vs Intune·조건부 액세스

![정책 적용 방식](/assets/images/2026-10-20-ad-vs-entra-id/04-policy.png)

| 항목 | GPO (AD) | Intune (Entra ID 환경) | 조건부 액세스 (Entra ID) |
|---|---|---|---|
| 대상 | 도메인 가입 컴퓨터, 사용자 | 등록된 기기 (Windows, macOS, iOS, Android) | 로그인·토큰 발급 요청 |
| 적용 시점 | 부팅·로그온 시, 주기적 새로 고침 | 기기 체크인 시 | 리소스에 접근하는 순간 |
| 적용 경로 | 사내망의 DC·SYSVOL | 인터넷(HTTPS) | Entra ID 로그인 과정 |
| 할당 단위 | OU (상속), 보안 필터링 | 그룹 | 그룹, 앱, 조건 |
| 하는 일 | 기기·사용자 설정 강제 | 기기 설정 강제 + 규정 준수 판정 | 허용 / 차단 / 추가 요구(MFA 등) |

GPO 하나가 하던 일이 Entra ID 환경에서는 둘로 나뉜다.

- 기기 설정(BitLocker, 화면 잠금, 방화벽): Intune 구성 프로필과 규정 준수 정책
- 접근 통제(이 앱에 이 조건으로 들어올 수 있는가): 조건부 액세스

둘은 연결돼 있다. Intune이 기기를 "규정 준수"로 판정하면, 조건부 액세스가 그 판정을 접근 조건으로 사용한다("규정 준수 기기에서만 Exchange Online 허용").

---

## 5. 조건부 액세스와 제로 트러스트

![조건부 액세스 평가 흐름](/assets/images/2026-10-20-ad-vs-entra-id/05-conditional-access.png)

### 개념

조건부 액세스는 Entra ID의 정책 엔진이다. 로그인이 끝나고 토큰을 발급하기 전에, 요청의 신호를 정책과 대조해 허용·차단·추가 요구를 결정한다. if-then 규칙으로 생각하면 된다.

| 신호 (if) | 예 |
|---|---|
| 사용자·그룹 | 관리자 역할, 특정 부서 그룹, 외부 게스트 |
| 위치 | IP 범위, 국가·지역, 신뢰할 수 있는 위치로 지정한 사내 IP |
| 기기 | 플랫폼, 규정 준수 여부, 하이브리드 가입 여부, 기기 필터 |
| 앱 | 대상 클라우드 앱 (Exchange Online, Azure 관리 등) |
| 위험 | 로그인 위험, 사용자 위험 (Entra ID Protection) |

| 결정 (then) | 내용 |
|---|---|
| 차단 | 가장 강한 결정 |
| 조건부 허용 | MFA, 인증 강도(피싱 방지 MFA 등), 규정 준수 기기, 하이브리드 가입 기기, 승인된 클라이언트 앱, 앱 보호 정책, 비밀번호 변경, 사용 약관 동의 중 하나 이상 요구 |

### 정책 예시

```text
정책 A: 관리자 역할 → 모든 클라우드 앱 → 피싱 방지 MFA 요구
정책 B: 모든 사용자 → 신뢰할 수 있는 위치 외부 + 규정 미준수 기기 → MFA 요구
정책 C: 모든 사용자 → 허용 국가 목록 외 위치 → 차단
정책 D: 모든 사용자 → 레거시 인증 클라이언트 → 차단
```

Intune 규정 준수 기기로 사내에서 접속한 사용자는 추가 프롬프트 없이 들어오고, 해외에서 개인 기기로 접속한 사용자는 MFA를 요구받거나 차단된다. 비밀번호를 아는지만 보던 판단이 접속 맥락 전체를 보는 판단으로 바뀐다. AD와 GPO만으로는 로그인 시점에 이런 판단을 할 수 없다.

### 라이선스와 운영 시 주의사항

- 조건부 액세스에는 Entra ID P1(또는 이를 포함한 Microsoft 365 Business Premium, E3/E5 등)이 필요하다. 로그인 위험·사용자 위험 조건은 Entra ID Protection 기능이라 P2가 필요하다.
- 새 정책은 보고 전용(report-only) 모드로 먼저 켜고, 로그인 로그에서 어떤 요청이 영향을 받는지 확인한 뒤 적용한다.
- 비상 접근 계정(break glass)은 정책에서 제외한다. 정책을 잘못 만들어 관리자 전원이 잠기는 상황을 대비하기 위해서다. 구성 과정은 [비상 접근 계정 구성]({% post_url 26-10-08-sandbox-break %})에 정리했다.
- 라이선스가 만료돼도 기존 정책은 삭제·비활성화되지 않는다. 조회와 삭제만 가능하고 수정은 할 수 없다.

---

## 6. MFA와 보안 기본값

### AD 환경의 MFA

Kerberos와 NTLM 자체에는 "추가 인증 요소를 요구한다"는 개념이 없다. AD 환경에서 다단계 인증을 구현하는 방법은 별도 구성이다.

- 스마트 카드·인증서 로그온(PKINIT), Windows Hello for Business: AD가 기본 지원하지만 PKI 또는 키 신뢰 구성이 필요하다.
- ADFS MFA 어댑터: ADFS로 페더레이션하는 앱에 추가 인증을 건다. 타사 MFA 제품도 어댑터로 연결한다.
- NPS 확장: VPN·RADIUS 인증에 Entra MFA를 연결한다.
- 타사 MFA 솔루션의 에이전트

### Entra ID의 MFA

Entra ID에서는 MFA가 기본 기능이다. 적용 방법은 두 가지이고, 동시에 쓸 수 없다.

| 항목 | 보안 기본값 (Security Defaults) | 조건부 액세스 |
|---|---|---|
| 라이선스 | 무료 | Entra ID P1 이상 |
| 설정 | 켜기 / 끄기만 가능 | 조건·대상·예외를 세밀하게 지정 |
| MFA 등록 | 모든 사용자에게 Authenticator 앱 등록 강제 | 정책으로 지정 |
| MFA 요구 시점 | 관리자 역할: 로그인할 때마다 / 일반 사용자: Microsoft가 필요하다고 판단할 때 | 정책 조건에 맞을 때 |
| 레거시 인증 | 차단 | 정책으로 차단 |
| Azure 관리 작업 | 포털·CLI·PowerShell 접근 시 MFA | 정책으로 지정 |

보안 기본값은 "모든 로그인에 MFA를 건다"가 아니다. 일반 사용자는 위치·기기·역할 등을 보고 필요할 때만 MFA를 요구받는다. 무료 테넌트나 소규모 조직의 출발점으로는 충분하지만, 예외 처리나 기기 조건이 필요해지면 보안 기본값을 끄고 조건부 액세스로 옮긴다.

---

## 7. 하이브리드: 둘 다 운영하는 환경

![하이브리드 인증 방식](/assets/images/2026-10-20-ad-vs-entra-id/06-hybrid-auth.png)

대부분의 조직은 하나를 고르지 않고 둘 다 운영한다. 온프레미스 AD 계정을 Entra ID로 동기화해, 같은 아이디와 비밀번호로 사내 리소스와 M365에 모두 로그인한다.

### 동기화 도구

| 도구 | 구조 | 특징 |
|---|---|---|
| Microsoft Entra Connect Sync (구 Azure AD Connect) | 온프레미스 동기화 서버에 설치 | 기능이 가장 많음, 서버 운영 필요 |
| Microsoft Entra Cloud Sync | 경량 프로비저닝 에이전트 + 클라우드 설정 | 에이전트는 아웃바운드 연결만 필요, 설정은 Entra 관리 센터에서 |

Microsoft는 Connect Sync에서 Cloud Sync로의 단계적 이전을 계획하고 있고, 2026년 7월부터 대상 테넌트에 순차 안내한다고 공지했다(첫 단계는 Cloud Sync로 요구사항을 충족하는 테넌트 대상). 신규 구축이라면 Cloud Sync로 충분한지 먼저 검토한다.

### 하이브리드 인증 방식

동기화와 별개로, 클라우드 로그인 시 비밀번호를 어디서 검증할지 정해야 한다.

| 항목 | 비밀번호 해시 동기화 (PHS) | 통과 인증 (PTA) | 페더레이션 (ADFS) |
|---|---|---|---|
| 검증 위치 | Entra ID (동기화된 해시와 비교) | 온프레미스 에이전트가 DC에 확인 | 온프레미스 ADFS |
| 추가 인프라 | 없음 | 경량 에이전트 (권장 3대) | ADFS 2대 이상 + WAP 2대 이상, 부하 분산, TLS 인증서 |
| 온프레미스 장애 시 | 클라우드 로그인 유지 | 로그인 불가 (PHS로 수동 전환) | 로그인 불가 |
| 계정 상태 반영 | 사용 중지만 반영, 최대 30분 지연 (비밀번호 해시는 약 2분 주기로 동기화) | 사용 중지·잠금·만료·비밀번호 만료·로그인 시간을 로그인 시점에 반영 | PTA와 같음 |
| 적합한 경우 | 대부분의 조직 | 온프레미스 정책을 로그인 시점에 그대로 적용해야 할 때 | 타사 MFA 연동, sAMAccountName 로그인 등 Entra ID가 직접 지원하지 않는 요구가 있을 때 |

Microsoft는 어떤 방식을 쓰든 PHS를 함께 켜 둘 것을 권장한다. 온프레미스 장애나 랜섬웨어로 DC·ADFS가 멈췄을 때 PHS로 전환해 클라우드 로그인을 복구할 수 있고, Entra ID Protection의 유출 자격 증명 탐지가 PHS를 전제로 하기 때문이다. PHS 구축 과정은 [Entra Connect 하이브리드 동기화 구축]({% post_url 26-07-06-entra-connect-hybrid %})에 정리했다.

### 동기화 방향과 원본 권한

![동기화 방향](/assets/images/2026-10-20-ad-vs-entra-id/07-sync-direction.png)

동기화된 객체의 원본(Source of Authority)은 기본적으로 온프레미스 AD다.

- 동기화된 사용자의 이름, 부서, 그룹 멤버십 같은 속성은 AD에서 바꿔야 한다. Entra ID 쪽에서는 수정이 막히거나, 수정해도 다음 동기화 때 AD 값으로 덮어써진다.
- Entra ID에서 직접 만든 사용자(클라우드 전용 계정)는 기본적으로 AD에 생기지 않는다.
- 동기화 범위(OU 필터링)에서 빠진 사용자는 Entra ID에서 삭제된다. OU 정리를 하다가 범위 밖으로 옮기면 클라우드 계정이 사라진다.

변경 전에 "이 객체의 원본이 어디인가"를 먼저 확인하는 것이 하이브리드 운영의 기본이다.

다만 방향이 AD → Entra ID 한쪽만 있는 것은 아니다.

| 기능 | 방향 | 내용 |
|---|---|---|
| 비밀번호 쓰기 저장 (Password Writeback) | Entra ID → AD | 셀프 서비스 비밀번호 재설정(SSPR) 결과를 AD에 반영. Entra ID P1 필요 |
| 그룹 프로비저닝 | Entra ID → AD | Cloud Sync로 클라우드 그룹을 AD에 생성해 온프레미스 앱 권한에 사용 |
| 기기 쓰기 저장 | Entra ID → AD | 기기 개체를 AD에 기록 (ADFS 조건부 접근 등에 사용) |
| SOA 전환 | 원본 자체를 이동 | 동기화된 그룹·사용자의 관리 원본을 클라우드로 전환. 그룹 SOA는 2025년, 사용자 SOA는 2026년 1월 GA |

SOA 전환은 "AD가 항상 원본"이라는 전제를 객체 단위로 바꾸는 기능이다. 전환한 객체는 이후 Entra ID에서 관리하므로, 온프레미스 의존을 줄이는 단계적 클라우드 이전에 쓰인다.

---

## 8. 정리

![전체 비교](/assets/images/2026-10-20-ad-vs-entra-id/08-overview.png)

| 항목 | Active Directory | Entra ID |
|---|---|---|
| 설계 전제 | 사내 네트워크 | 인터넷, SaaS |
| 보안 경계 | 네트워크 | ID |
| 인증 | Kerberos, NTLM | OAuth 2.0, OIDC, SAML, WS-Fed |
| 조회·관리 | LDAP, ADUC, PowerShell AD 모듈 | Microsoft Graph, Entra 관리 센터 |
| 구조 | 포리스트 / 도메인 / OU 계층 | 테넌트 평면 구조, 그룹, 관리 단위 |
| 기기 정책 | GPO | Intune |
| 접근 통제 | 네트워크 위치, ACL | 조건부 액세스 |
| MFA | 별도 구성 (스마트 카드, ADFS 어댑터 등) | 기본 기능 (보안 기본값, 조건부 액세스) |
| 인프라 | DC 직접 운영 | Microsoft 운영 SaaS |

AD는 건물 안을 위해, Entra ID는 건물 밖을 위해 만들어졌다. 둘은 대체 관계가 아니라 서로 다른 시대의 ID 플랫폼이고, 지금 대부분의 환경은 두 시스템을 동기화로 연결해 함께 운영한다. Entra ID를 다룰 때 필요한 것은 AD 지식을 버리는 것이 아니라, 어떤 개념이 그대로 통하고(사용자, 그룹) 어떤 개념은 대응하는 것이 없거나 전혀 다른지(OU, GPO, DC)를 구분하는 것이다.

---

## 참고

- [Microsoft Entra 보안 기본값](https://learn.microsoft.com/entra/fundamentals/security-defaults)
- [조건부 액세스 개요](https://learn.microsoft.com/entra/identity/conditional-access/overview)
- [하이브리드 ID 인증 방법 선택 (PHS, PTA, 페더레이션)](https://learn.microsoft.com/entra/identity/hybrid/connect/choose-ad-authn)
- [Microsoft Entra Cloud Sync란?](https://learn.microsoft.com/entra/identity/hybrid/cloud-sync/what-is-cloud-sync)
- [Microsoft Entra Kerberos 소개](https://learn.microsoft.com/entra/identity/authentication/kerberos)
- [관리 단위 (Administrative units)](https://learn.microsoft.com/entra/identity/role-based-access-control/administrative-units)
- [사용자 Source of Authority 가이드](https://learn.microsoft.com/entra/identity/hybrid/user-source-of-authority-guidance)
- [Microsoft Entra Domain Services 개요](https://learn.microsoft.com/entra/identity/domain-services/overview)
- [Microsoft Entra 새로운 기능 (What's new)](https://learn.microsoft.com/entra/fundamentals/whats-new)
