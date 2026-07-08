---
layout: single
title: "[Windows Server] 2-Tier PKI 직접 구축하기 — 오프라인 루트 CA부터 발급 CA·CDP/AIA·인증서 발급까지"
excerpt: "Hyper-V 랩에 오프라인 루트 CA(ROOTCA)와 온라인 발급 CA(ISCA01)로 구성된 2-Tier PKI를 처음부터 구축한 기록. 하위 CA 서명 절차, CRYPT_E_REVOCATION_OFFLINE 관문, CDP/AIA HTTP 배포, 인증서 발급 검증까지 실전 트러블슈팅과 함께 정리."
date: 2026-07-09
categories: [Infra, Windows Server, PKI]
tags: [pki, certificate-authority, adcs, root-ca, subordinate-ca, cdp, aia, crl, hyper-v, adfs, 인증서, 트러블슈팅]
---

## 들어가며

ADFS 랩을 세우려면 그 앞에 **인증서 인프라(PKI)**가 필요하다. ADFS의 Token-Signing / Service Communications 인증서를 제대로 된 CA에서 발급받아야 하기 때문이다. 마침 IAM 엔지니어로서 실무에서 "루트 CA / 발급 CA 설치·운영"과 "클라이언트 인증서 CRL 오류 진단"을 다뤄봤지만, **직접 처음부터 2-Tier PKI를 세워본 적은 없었다.** 그래서 ADFS 선행 작업 겸, Hyper-V 랩에 2계층 CA를 통째로 구축해보기로 했다.

이 글은 그 구축 기록이다. 핵심은 **"왜 2단으로 나누는가"**와 **"검증 인프라(CDP/AIA)를 어떻게 세우는가"**이며, 중간에 만난 트러블슈팅(하위 CA 서명 절차, CRL 오프라인 관문, 파일/관리자 권한)도 함께 정리했다.

**랩 환경**

| 항목 | 값 |
|---|---|
| 도메인 | lab.local (LAB) |
| ROOTCA | 10.0.0.231 · **워크그룹** · 오프라인 루트 CA |
| ISCA01 | 10.0.0.232 · **도메인 가입** · 온라인 발급 CA |
| PKI 배포 지점 | pki.lab.local (= ISCA01의 IIS) |
| OS | Windows Server 2022 |

---

## 목차

1. [왜 2-Tier인가](#1-왜-2-tier인가)
2. [Tier 1 — 오프라인 루트 CA (ROOTCA)](#2-tier-1--오프라인-루트-ca-rootca)
3. [Tier 2 — 온라인 발급 CA (ISCA01)](#3-tier-2--온라인-발급-ca-isca01)
4. [하위 CA 인증서 서명 (ROOTCA ↔ ISCA01)](#4-하위-ca-인증서-서명-rootca--isca01)
5. [CDP/AIA HTTP 배포 인프라](#5-cdpaia-http-배포-인프라)
6. [인증서 발급 검증](#6-인증서-발급-검증)
7. [트러블슈팅 총정리](#7-트러블슈팅-총정리)

---

## 1. 왜 2-Tier인가

CA를 한 대로 쓰지 않고 **루트 / 발급** 두 계층으로 나누는 이유는 신뢰 체인의 최상단을 지키기 위해서다.

```
   ┌─────────────────────────────────────┐
   │  Tier 1: ROOTCA (오프라인 루트 CA)     │
   │  - 워크그룹 (도메인 미가입)             │
   │  - 자기 서명 (신뢰 체인 최상단)         │
   │  - ISCA 서명 후 전원 OFF / 격리         │
   └──────────────┬──────────────────────┘
                  │ (ISCA 인증서 서명 1회)
                  ▼
   ┌─────────────────────────────────────┐
   │  Tier 2: ISCA01 (온라인 발급 CA)       │
   │  - 도메인 가입 (lab.local)             │
   │  - Enterprise Subordinate CA          │
   │  - 실제 인증서 발급 (ADFS, 웹서버 등)  │
   └─────────────────────────────────────┘
```

핵심 논리는 이렇다. 루트가 뚫리면 그 아래 **모든 인증서가 무효**가 되어 PKI 전체를 다시 세워야 한다. 반면 발급 CA(ISCA)가 뚫리면 그것만 폐기하고 재발급하면 된다. 그래서 루트는 **평소에 전원 OFF + 네트워크 분리**로 격리해 공격 표면을 없애고, 실제 발급 업무는 온라인 하위 CA가 담당한다. 루트의 유일한 임무는 하위 CA 인증서 서명이고, 그건 1년에 몇 번 있을까 말까 하므로 평소엔 꺼둬도 된다.

이 구조 때문에 두 서버는 정책이 정반대다.

| | ROOTCA | ISCA01 |
|---|---|---|
| 도메인 가입 | ❌ 워크그룹 | ✅ lab.local |
| CA 종류 | Standalone **Root** | Enterprise **Subordinate** |
| 온라인 여부 | 오프라인 (구성 후 격리) | 상시 온라인 |
| 자기 서명 | O | ❌ (루트가 서명) |

---

## 2. Tier 1 — 오프라인 루트 CA (ROOTCA)

### 기본 설정 (워크그룹 유지)

ROOTCA는 **도메인에 가입하지 않는다.** 오프라인 격리가 목적이라 도메인 통신 자체가 방해가 된다.

```powershell
# 컴퓨터명 / IP만 설정, 도메인 가입 안 함
Rename-Computer -NewName "ROOTCA" -Restart
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 10.0.0.231 -PrefixLength 24 -DefaultGateway 10.0.0.2

# 확인 — Domain이 WORKGROUP이어야 정상
(Get-CimInstance Win32_ComputerSystem).Domain
```

### CAPolicy.inf 먼저 생성

CA 구성 **전에** CAPolicy.inf를 만들어야 한다. CA 구성 시점에 이 파일이 자동으로 읽혀 갱신 키 길이·유효기간·CRL 주기를 정한다.

```powershell
@'
[Version]
Signature="$Windows NT$"
[PolicyStatementExtension]
Policies=InternalPolicy
[InternalPolicy]
OID=1.2.3.4.1455.67.89.5
[Certsrv_Server]
RenewalKeyLength=2048
RenewalValidityPeriod=Years
RenewalValidityPeriodUnits=10
CRLPeriod=Weeks
CRLPeriodUnits=52
LoadDefaultTemplates=0
AlternateSignatureAlgorithm=1
'@ | Set-Content -Path C:\Windows\CAPolicy.inf -Encoding ASCII
```

> `LoadDefaultTemplates=0` — 루트 CA는 직접 인증서를 발급하지 않으므로 템플릿을 로드하지 않는다.

### 역할 설치 + 독립형 루트 CA 구성

```powershell
# 역할 설치 (GUI 마법사 대신 한 줄)
Install-WindowsFeature ADCS-Cert-Authority -IncludeManagementTools

# 독립형 루트 CA 구성
Install-AdcsCertificationAuthority `
    -CAType StandaloneRootCA `
    -CACommonName "lab-ROOTCA-CA" `
    -KeyLength 2048 `
    -HashAlgorithmName SHA256 `
    -ValidityPeriod Years -ValidityPeriodUnits 10 `
    -CryptoProviderName "RSA#Microsoft Software Key Storage Provider"
```

> **StandaloneRootCA가 핵심**: 워크그룹이라 Enterprise CA(AD 필요)를 쓸 수 없다. GUI로 구성할 때도 "독립형(Standalone)"을 골라야 한다.

구성 후 확인하면 `CA type: Stand-alone Root CA`, 루트 인증서가 자기 서명으로 생성되고 유효기간이 정확히 10년(예: 2036년)으로 잡힌다.

### CA 레지스트리 구성

```cmd
certutil -setreg CA\DSConfigDN "CN=Configuration,DC=lab,DC=local"
certutil -setreg CA\CRLPeriodUnits 52
certutil -setreg CA\CRLPeriod "Weeks"
certutil -setreg CA\CRLDeltaPeriodUnits 0
certutil -setreg CA\ValidityPeriodUnits 10
certutil -setreg CA\ValidityPeriod "Years"
certutil -setreg CA\AuditFilter 127
```

`AuditFilter 127`은 모든 CA 이벤트를 감사한다. 실제 로그가 남으려면 Windows 감사 정책도 켜야 한다.

```powershell
auditpol /set /subcategory:"Certification Services" /success:enable /failure:enable
Restart-Service CertSvc
certutil -CRL   # CRL 발행
```

이제 `C:\Windows\System32\CertSrv\CertEnroll\`에 **루트 인증서(.crt)와 CRL(.crl)** 이 생성된다. 이 두 파일이 다음 단계(ISCA 서명·체인 완성)에서 쓰인다.

---

## 3. Tier 2 — 온라인 발급 CA (ISCA01)

ISCA01은 ROOTCA와 정반대로 **도메인에 가입**한다. AD 통합 발급을 해야 하기 때문이다.

```powershell
# 컴퓨터명 + IP + DNS(반드시 DC를 가리켜야 도메인 가입 가능)
Rename-Computer -NewName "ISCA01" -Restart
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 10.0.0.232 -PrefixLength 24 -DefaultGateway 10.0.0.2
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses 10.0.0.10   # DC IP

# 도메인 가입 (ROOTCA와 다른 핵심 차이)
Add-Computer -DomainName "lab.local" -Credential (Get-Credential) -Restart
```

> ROOTCA는 DNS·도메인을 신경 쓰지 않았지만, ISCA01은 **DNS가 DC를 가리켜야** 도메인 가입과 AD 통합이 된다. 이게 두 서버의 결정적 차이다.

### AD CS 역할 설치 + 하위 CA 구성

```powershell
Install-WindowsFeature ADCS-Cert-Authority -IncludeManagementTools

# 하위 CA용 CAPolicy.inf (루트와 달리 RenewalUnits=5, URL 줄 추가 등)
# ... (하위 CA용 설정) ...

Install-AdcsCertificationAuthority `
    -CAType EnterpriseSubordinateCA `
    -CACommonName "lab-ISCA01-CA" `
    -KeyLength 2048 `
    -HashAlgorithmName SHA256 `
    -CryptoProviderName "RSA#Microsoft Software Key Storage Provider"
```

여기서 구성을 실행하면 아래 WARNING이 뜬다.

```
WARNING: The Active Directory Certificate Services installation is incomplete.
use the request file "...azlab-ISCA01-CA.req" to obtain a certificate from the parent CA.
The operation completed successfully. 0x0 (WIN32: 0)
ErrorId 398
```

> **[트러블슈팅 #1] "installation is incomplete" WARNING은 정상**
>
> 처음 보면 실패로 착각하지만, 이건 **하위 CA의 필수 절차**다. 하위 CA는 스스로 완성될 수 없고, 부모(ROOTCA)가 "너를 하위 CA로 인정한다"고 서명해줘야 활성화된다. 그래서 요청 파일(`.req`)을 만들고 서명을 기다리는 상태가 된 것. `The operation completed successfully. 0x0`가 함께 나오는 게 그 증거. 이 시점의 ISCA CA 서비스는 **중지 상태가 정상**이다.

---

## 4. 하위 CA 인증서 서명 (ROOTCA ↔ ISCA01)

이제 ISCA01이 만든 `.req`를 ROOTCA로 가져가 서명받는다. 이게 2-Tier의 핵심 절차다.

```
ISCA01: .req 생성  ──(파일 전달)──▶  ROOTCA: 서명 → .cer 발급
                                            │
ISCA01: .cer 설치 → CA 시작  ◀──(파일 전달)──┘
```

### 파일 전달 (ISCA01 → ROOTCA)

랩에서는 ROOTCA가 아직 온라인이므로 관리 공유로 복사한다. ROOTCA는 워크그룹이라 **로컬 계정**으로 인증해야 한다.

```powershell
# ISCA01에서 — ROOTCA는 워크그룹이라 ROOTCA\Administrator 자격증명 필요
$cred = Get-Credential   # ROOTCA\Administrator
New-PSDrive -Name R -PSProvider FileSystem -Root "\\10.0.0.231\C$" -Credential $cred
Copy-Item "C:\ISCA01.lab.local_lab-ISCA01-CA.req" -Destination "R:\"
```

> **[트러블슈팅 #2] 워크그룹 서버 공유 접근은 컴퓨터명\계정 형식**
>
> ROOTCA가 도메인 미가입(워크그룹)이라 도메인 자격증명(LAB\...)이 통하지 않는다. `ROOTCA\Administrator` 형식으로 **로컬 계정** 인증을 해야 한다. 이 원리는 실무에서 격리된 서버·DMZ 서버에 접근할 때 그대로 적용된다.

### ROOTCA에서 서명

독립형 루트 CA는 요청을 **수동 승인**하도록 되어 있다(보안 기본값). submit → 승인 → 검색 3단계.

```cmd
:: ROOTCA에서
certreq -submit -config "ROOTCA\lab-ROOTCA-CA" "C:\ISCA01...req"   :: RequestId 확인
certutil -resubmit 3                                               :: 승인 (RequestId)
certreq -retrieve 3 "C:\ISCA01-signed.cer"                         :: 발급 인증서 저장
```

`certutil -dump`로 확인하면 발급된 인증서의 Issuer가 `lab-ROOTCA-CA`로 나온다 — 루트가 서명했다는 증거다.

### ISCA01에서 인증서 설치 + CA 시작

signed.cer와 루트 인증서를 ISCA01로 가져와 설치한다.

```powershell
# ISCA01에서
Import-Certificate -FilePath "C:\ROOTCA_lab-ROOTCA-CA.crt" -CertStoreLocation Cert:\LocalMachine\Root
certutil -installcert "C:\ISCA01-signed.cer"
Start-Service CertSvc
```

그런데 여기서 서비스 시작이 실패한다.

> **[트러블슈팅 #3] CRYPT_E_REVOCATION_OFFLINE — 2-Tier의 대표 관문**
>
> **증상**:
> ```
> Active Directory Certificate Services did not start:
> Could not load or verify the current CA certificate. lab-ISCA01-CA
> The revocation function was unable to check revocation because
> the revocation server was offline. 0x80092013 (CRYPT_E_REVOCATION_OFFLINE)
> ```
>
> **원인**: ISCA01이 시작하려면 자기 인증서가 폐기되지 않았는지 **ROOTCA의 CRL을 확인**해야 하는데, ROOTCA가 오프라인이고 CDP 경로가 아직 없어 CRL을 가져올 데가 없다. 그래서 검증 실패 → 시작 거부.
>
> **해결**: CRL 서버가 오프라인일 때 검증을 건너뛰도록 설정. 오프라인 루트 구조에서 흔히 쓰는 방식이다.
> ```cmd
> certutil -setreg ca\CRLFlags +CRLF_REVCHECK_IGNORE_OFFLINE
> ```
> ```powershell
> Start-Service CertSvc
> ```
> 이후 확인하면 `CA type: Enterprise Subordinate CA`, `CA cert verify status: 0`(체인 검증 통과)으로 정상 기동한다.

이 시점에 2-Tier 계층 자체는 완성된다. ROOTCA(루트) → ISCA01(발급)의 신뢰 체인이 이어졌다.

---

## 5. CDP/AIA HTTP 배포 인프라

CA가 발급하는 인증서에는 **"나를 검증하려면 여기로 와"** 라는 주소가 박힌다.

- **CDP (CRL Distribution Point)**: "이 인증서가 폐기되지 않았나?" → CRL 파일 주소
- **AIA (Authority Information Access)**: "발급자(상위 CA) 인증서는 어디 있나?" → CA 인증서 주소 (체인 완성용)

기본값은 LDAP + 로컬 경로라, 오프라인 루트 환경에서는 검증이 안 된다(위 #3의 근본 원인). 그래서 **온라인 ISCA01의 IIS를 HTTP 배포 지점**으로 세운다. ROOTCA는 꺼져 있어도, 그 CRL·인증서 파일을 ISCA 웹서버에 올려두면 검증자는 언제든 HTTP로 접근할 수 있다.

### DNS + IIS 준비

```powershell
# DC에서 — pki 별칭이 ISCA01을 가리키게
Add-DnsServerResourceRecordCName -ZoneName "lab.local" -Name "pki" -HostNameAlias "ISCA01.lab.local"

# ISCA01에서 — IIS + CertEnroll 가상 디렉터리
Install-WindowsFeature Web-Server -IncludeManagementTools
New-WebVirtualDirectory -Site "Default Web Site" -Name "CertEnroll" `
    -PhysicalPath "C:\Windows\System32\CertSrv\CertEnroll"
Set-WebConfigurationProperty -Filter /system.webServer/security/requestFiltering `
    -Name allowDoubleEscaping -Value $true `
    -PSPath "IIS:\Sites\Default Web Site\CertEnroll"
```

> **[트러블슈팅 #4] 델타 CRL과 allowDoubleEscaping**
>
> 델타 CRL 파일명에는 `+` 문자가 들어간다(`lab-ISCA01-CA+.crl`). IIS는 기본적으로 이 문자를 차단해서 `404.11` 에러가 난다. `allowDoubleEscaping=true`를 설정해야 델타 CRL을 HTTP로 서비스할 수 있다. 실무 CDP 트러블슈팅의 단골이다.
>
> **또 하나의 함정 — 로컬 게시 경로와 웹 경로 불일치**: CDP/AIA를 설정할 때 로컬 게시 경로(CA가 CRL을 떨구는 곳)와 IIS 가상 디렉터리가 가리키는 물리 경로가 **같아야** 한다. 이 랩에서는 둘 다 `CertEnroll`로 통일해, CA가 CRL을 게시하면 별도 복사 없이 곧바로 HTTP로 서비스되게 했다. 경로가 어긋나면 CRL 발행은 되는데 HTTP 404가 나는 상황이 생긴다.

### CDP/AIA 경로 설정

```cmd
:: ISCA01에서 — 로컬 게시 + LDAP + HTTP 3중 경로
certutil -setreg CA\CACertPublicationURLs "1:C:\Windows\system32\CertSrv\CertEnroll\%1_%3%4.crt\n2:ldap:///CN=%7,CN=AIA,...\n2:http://pki.lab.local/CertEnroll/%1_%3%4.crt"
certutil -setreg CA\CRLPublicationURLs "1:C:\Windows\system32\CertSrv\CertEnroll\%3%8%9.crl\n10:ldap:///CN=%7%8,...\n2:http://pki.lab.local/CertEnroll/%3%8%9.crl"

net stop certsvc && net start certsvc
:: 서비스 안정화 위해 10초 대기 후 게시 (초기화 전 게시하면 실패)
certutil -CRL
```

숫자 플래그(1:, 2:, 10:)와 `%` 변수는 Windows CA 표준 토큰이라 도메인과 무관하게 그대로 쓴다. 설정 후 HTTP 접근을 확인하면 CRL이 200으로 응답한다.

```powershell
(Invoke-WebRequest -Uri "http://pki.lab.local/CertEnroll/lab-ISCA01-CA.crl" -UseBasicParsing).StatusCode
# 200
```

> **참고 — 루트 인증서의 file:// 경고**: `certutil -verify`를 돌리면 ROOTCA 레벨의 CDP/AIA가 `file://ROOTCA/...`로 잡혀 Failed가 뜰 수 있다. 이는 ROOTCA 구성 시 CDP/AIA를 HTTP로 설정하지 않았을 때 발생하는데, 루트는 신뢰 앵커로 이미 신뢰 저장소에 설치돼 있으므로 발급 목적에는 지장이 없다. 완벽을 기하려면 ROOTCA CDP/AIA도 HTTP로 재설정하고 루트 인증서를 재발급하면 된다.

---

## 6. 인증서 발급 검증

CA가 실제로 동작하는지 — HTTP CDP/AIA가 박힌 인증서를 발급하는지 — 를 테스트한다.

### 템플릿 게시 + 발급

WebServer 템플릿은 기본 게시돼 있고, Domain Admins / Enterprise Admins에게 발급 권한이 있다.

```powershell
# 요청 파일 (WebServer 템플릿, 컴퓨터 키 저장소)
@"
[NewRequest]
Subject = "CN=test.lab.local"
KeyLength = 2048
MachineKeySet = TRUE
RequestType = PKCS10
[RequestAttributes]
CertificateTemplate = WebServer
"@ | Out-File "C:\certtest\test-req.inf" -Encoding ASCII
```
```cmd
certreq -new "C:\certtest\test-req.inf" "C:\certtest\test-req.csr"
certreq -submit -config "ISCA01.lab.local\lab-ISCA01-CA" "C:\certtest\test-req.csr" "C:\certtest\test-cert.cer"
:: → Certificate retrieved(Issued) Issued
```

> **[트러블슈팅 #5] MachineKeySet + 관리자 권한 + 작업 경로**
>
> 두 가지 벽을 연달아 만났다.
> - `MachineKeySet=TRUE`(컴퓨터 키 저장소)는 **관리자 권한 프롬프트**가 필수다. 일반 창에서 실행하면 "Administrator permissions are needed to use the selected options" 경고가 뜬다. → 관리자 권한 cmd/PowerShell에서 실행.
> - `C:\` 루트에 CSR을 쓰려다 `ERROR_ACCESS_DENIED`가 났다. Windows가 C:\ 루트 쓰기를 제한하기 때문. → 전용 작업 폴더(`C:\certtest`)를 만들어 거기서 작업.
>
> 정리하면 CA/인증서 작업은 **관리자 권한 + 전용 폴더**가 안전하다.

### 발급 인증서 검증 (핵심)

발급된 인증서에 우리가 설정한 HTTP CDP/AIA가 박혔는지 확인한다.

```powershell
certutil -dump "C:\certtest\test-cert.cer" | Select-String "http://","CRL Distribution","Authority Info"
```

결과:
```
CRL Distribution Points
    URL=http://pki.lab.local/CertEnroll/lab-ISCA01-CA.crl
Authority Information Access
    URL=http://pki.lab.local/CertEnroll/ISCA01.lab.local_lab-ISCA01-CA.crt
```

발급 인증서에 **HTTP CDP/AIA가 정확히 박혔다.** 앞으로 ISCA01이 발급하는 모든 인증서(ADFS, 웹서버 등)에 이 경로가 들어가고, 검증자는 `http://pki.lab.local/CertEnroll/`로 CRL과 CA 인증서를 받아 체인을 검증할 수 있다. 이것으로 발급 인프라가 완성됐다.

---

## 7. 트러블슈팅 총정리

| # | 증상 | 원인 | 해결 |
|---|---|---|---|
| 1 | 하위 CA 구성 후 "installation incomplete" WARNING | 하위 CA는 부모 서명 필요 (정상 절차) | .req를 ROOTCA에서 서명받아 설치 |
| 2 | 워크그룹 서버 공유 접근 실패 | 도메인 자격증명이 안 통함 | `컴퓨터명\Administrator` 로컬 계정으로 인증 |
| 3 | ISCA CA 시작 실패 (CRYPT_E_REVOCATION_OFFLINE) | 오프라인 루트라 CRL 확인 불가 | `CRLF_REVCHECK_IGNORE_OFFLINE` 설정 |
| 4 | 델타 CRL HTTP 404.11 / CRL 경로 불일치 | `+` 문자 차단 / 게시·웹 경로 불일치 | allowDoubleEscaping=true / 경로를 CertEnroll로 통일 |
| 5 | 인증서 발급 실패 (권한/경로) | MachineKeySet은 관리자 필요, C:\ 루트 쓰기 제한 | 관리자 권한 + 전용 폴더에서 작업 |

### 진단 시그니처

- `ErrorId 398` + "installation incomplete" → 하위 CA **정상**, 부모 서명 대기
- `CRYPT_E_REVOCATION_OFFLINE 0x80092013` → **CRL 검증 경로** 문제 (오프라인 루트)
- `404.11` (CRL 접근) → **allowDoubleEscaping** 확인
- 워크그룹 서버 접근 → **컴퓨터명\로컬계정**
- CA/인증서 작업 → **관리자 권한 + 전용 폴더**

---

## 마치며

IAM 엔지니어로서 실무에서 CA를 "운영"해봤지만, 직접 **오프라인 루트부터 CDP/AIA까지 통째로 세워본** 것은 이번이 처음이었다. 그동안 막연했던 개념들 — 왜 루트를 오프라인으로 두는지, CDP/AIA가 인증서 안에 어떻게 박히는지, CRL 검증이 왜 실패하는지 — 이 직접 구축하면서 선명해졌다.

특히 `CRYPT_E_REVOCATION_OFFLINE`으로 CA가 시작조차 안 되던 순간과, 발급 인증서를 dump해서 HTTP CDP/AIA가 정확히 박힌 걸 확인한 순간이 인상적이었다. 실무에서 다뤘던 "클라이언트 인증서 CRL 오류"가 결국 이 CDP 경로·CRL 게시 문제였다는 걸, 인프라를 직접 세워보고 나서야 완전히 이해했다.

이제 발급 CA가 준비됐으니, 다음은 이 CA로 **ADFS 인증서를 발급하고 ADFS 팜을 구성**하는 단계로 넘어간다.