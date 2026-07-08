---
layout: single
title: "[Windows Server] ADFS 고가용성 팜 구축 — CA 인증서 발급부터 2노드 팜, NLB까지"
excerpt: "앞서 만든 2-Tier CA와 SQL AG를 활용해 ADFS 2노드 고가용성 팜을 구축한 기록. CA로 SAN 인증서를 발급하고, 구성 DB를 SQL AG Listener에 연결하며, gMSA와 NLB로 팜을 완성하기까지의 실전 트러블슈팅 정리."
date: 2026-07-10
categories: [Infra, Windows Server, ADFS]
tags: [adfs, federation, gmsa, nlb, high-availability, sql-availabilitygroup, pki, certificate, hyper-v, 고가용성, 트러블슈팅]
---

## 들어가며

지금까지 만든 랩을 돌아보면 [SQL Server AlwaysOn AG](/), [2-Tier PKI(CA)](/)가 각각 완성돼 있다. 이 두 개는 사실 **ADFS를 제대로 세우기 위한 밑작업**이었다. 이번 글에서 그 둘이 하나로 합쳐진다.

- **CA** → ADFS의 SSL 인증서를 발급 (신원 증명)
- **SQL AG** → ADFS 구성 데이터베이스 저장소 (구성 DB도 HA로)

IAM 엔지니어로서 실무에서 엔터프라이즈 ADFS 팜과 WAP를 다뤄봤지만, **앞단 CA·SQL AG까지 직접 세우고 그 위에 ADFS 팜을 통째로 얹어본** 것은 이번이 처음이었다. 이 글은 **ADFS 2노드 고가용성 팜**을 구축한 기록이다. 인증서 발급 → 첫 팜 노드 → 두 번째 노드 조인 → NLB 부하분산까지, 각 단계의 트러블슈팅과 함께 정리했다. (외부 공개용 WAP는 다음 편에서 다룬다.)

**랩 환경**

| 항목 | 값 |
|---|---|
| 도메인 | lab.local (LAB) |
| 페더레이션 서비스 이름 | sts.lab.local |
| ADFS01 | 10.0.0.241 (팜 노드 1) |
| ADFS02 | 10.0.0.242 (팜 노드 2) |
| NLB VIP | 10.0.0.240 (sts가 가리키는 가상 IP) |
| 구성 DB | SQL AG (AGLISTENER) |
| 서비스 계정 | gMSA (gmsa-adfs) |
| CA | 앞서 구축한 ISCA01 (발급 CA) |

---

## 목차

1. [ADFS 팜 아키텍처](#1-adfs-팜-아키텍처)
2. [사전 준비 — KDS 키와 gMSA](#2-사전-준비--kds-키와-gmsa)
3. [ADFS SSL 인증서 발급 (CA 활용)](#3-adfs-ssl-인증서-발급-ca-활용)
4. [ADFS01 — 첫 팜 노드 구성](#4-adfs01--첫-팜-노드-구성)
5. [ADFS02 — 팜 조인](#5-adfs02--팜-조인)
6. [NLB 부하분산 구성](#6-nlb-부하분산-구성)
7. [sts DNS + 최종 검증](#7-sts-dns--최종-검증)
8. [트러블슈팅 총정리](#8-트러블슈팅-총정리)

---

## 1. ADFS 팜 아키텍처

먼저 전체 그림. **팜의 실제 멤버는 ADFS01/02 두 대뿐**이고, SQL AG와 CA는 팜이 사용하는 외부 자원이다.

```
        [ sts.lab.local → 10.0.0.240 VIP (NLB) ]
                    │  (NLB 부하분산)
          ┌─────────┴─────────┐
          ▼                   ▼
     [ADFS01 .241]       [ADFS02 .242]   ← 팜 (이 둘만 멤버)
          │                   │
          └─── 구성 DB 연결 ───┘
                    │
                    ▼
          [ SQL AG (AGLISTENER) ]  ← 구성 저장소 (팜 멤버 아님)
                    │
              [ DC (AD) ]  ← 사용자 인증
```

각 요소의 역할을 명확히 구분하면 이렇다.

- **ADFS 팜** = ADFS01 + ADFS02. 실제 토큰 발급을 담당하는 멤버.
- **SQL AG** = 팜이 구성 데이터를 저장하는 DB. 멤버가 아니라 "창고" 역할. Listener를 쓰므로 SQL 노드 장애조치가 나도 ADFS는 투명하게 동작.
- **CA 인증서** = 팜의 SSL 신원. 멤버가 아니라 "사업자등록증" 역할. 모든 노드가 동일한 sts 인증서를 사용.
- **NLB** = 앞단 부하분산. sts(VIP)로 오는 요청을 두 노드에 분산. SQL AG의 Listener와 비슷한 역할을 ADFS 앞에서 수행.
- **gMSA** = 두 노드가 공유하는 서비스 계정. 암호를 사람이 관리하지 않고 AD가 자동 교체하며, 허가된 컴퓨터만 암호를 조회한다. (자세한 이유는 2장에서)

**구성 DB를 왜 SQL AG로?** WID(Windows Internal Database)를 써도 되지만, SQL을 쓰면 구성 DB를 Listener 경유로 접속해 SQL 노드 장애에도 견딜 수 있다. 앞서 만든 AG를 실전으로 활용하는 셈이다.

---

## 2. 사전 준비 — KDS 키와 gMSA

ADFS 팜은 공용 **서비스 계정**이 필요하다. 두 노드(ADFS01/ADFS02)가 **같은 신원으로 토큰 서명·서비스 통신**을 해야 하기 때문이다. 이 계정으로 무엇을 쓸 수 있는데, 왜 하필 **gMSA(그룹 관리 서비스 계정)** 인지 짚고 간다.

**왜 gMSA인가 — 일반 계정과의 비교**

| 방식 | 암호 관리 | 팜 확장 | SPN | 문제점 |
|---|---|---|---|---|
| 일반 도메인 계정 | **사람이 수동 관리** | 노드마다 같은 암호 입력 | 수동 등록 | 암호 유출·만료·변경 시 팜 전체 장애 |
| gMSA | **AD가 자동 생성·주기적 교체** | 컴퓨터 계정만 추가하면 끝 | 자동 관리 | (거의 없음) |

핵심 이유를 정리하면 이렇다.

- **암호를 사람이 몰라도 된다**: gMSA의 암호는 AD가 자동 생성하고 **주기적으로 자동 교체**한다(기본 30일). 관리자도 그 암호를 모른다. 일반 계정은 암호를 사람이 정하고 관리해야 하는데, ADFS처럼 오래 운영되는 서비스에서 **암호 만료·유출·변경이 곧 팜 장애**로 이어진다. gMSA는 이 위험을 원천 제거한다.
- **여러 노드가 안전하게 공유**: 팜의 모든 노드가 같은 서비스 계정을 써야 하는데, gMSA는 **허가된 컴퓨터(ADFS01$/ADFS02$)만 암호를 조회**하도록 AD가 통제한다. 일반 계정처럼 각 서버에 평문 암호를 넣어둘 필요가 없다.
- **팜 확장이 쉽다**: 나중에 ADFS03을 추가해도, 그 컴퓨터 계정을 `PrincipalsAllowedToRetrieveManagedPassword`에 넣기만 하면 된다. 암호 재배포가 불필요하다.
- **SPN 자동 관리**: 서비스 주체 이름(SPN, `http/sts.lab.local`)을 gMSA에 지정하면 Kerberos 인증이 매끄럽게 동작한다.

한마디로, gMSA는 **"사람이 암호를 관리하지 않아도 되는, 여러 서버가 공유하는 서비스 계정"** 이다. ADFS 팜처럼 다중 노드가 장기 운영되는 서비스에 Microsoft가 공식 권장하는 방식이다. (단일 노드 랩이라면 일반 계정도 가능하지만, 팜이라면 gMSA가 정석이다.)

그래서 두 노드가 같은 계정으로 동작해야 하는 이번 구성에 gMSA가 적합하다.

### KDS 루트 키 (DC에서)

gMSA를 쓰려면 KDS 루트 키가 선행돼야 한다.

```powershell
# DC에서 - 랩은 -10시간으로 즉시 사용
Add-KdsRootKey -EffectiveTime ((Get-Date).AddHours(-10))
```

### gMSA 생성 — 순서 함정

```powershell
# DC에서
New-ADServiceAccount -Name "gmsa-adfs" `
    -DNSHostName "sts.lab.local" `
    -ServicePrincipalNames "http/sts.lab.local" `
    -PrincipalsAllowedToRetrieveManagedPassword "ADFS01$","ADFS02$"
```

> **[트러블슈팅 #1] gMSA 생성 순서 — 컴퓨터 계정이 먼저**
>
> 위 명령을 ADFS VM 생성 전에 실행하면 실패한다.
> ```
> Cannot find an object with identity: 'ADFS01$'
> ```
> `PrincipalsAllowedToRetrieveManagedPassword`는 "이 gMSA 암호를 가져갈 수 있는 컴퓨터"를 지정하는데, ADFS01/ADFS02 VM을 아직 안 만들어 컴퓨터 계정(ADFS01$/ADFS02$)이 AD에 없기 때문이다. **닭-달걀 문제**다.
>
> **해결**: KDS 루트 키만 먼저 만들어 두고, gMSA는 **ADFS VM들을 도메인 조인시킨 후**에 생성한다. 순서를 이렇게 잡으면 된다:
> ```
> KDS 루트 키 → ADFS VM 생성/도메인 조인 → (ADFS01$/ADFS02$ 생김) → gMSA 생성
> ```

![ADFS VM 도메인 조인 — Add-Computer](/assets/images/26-07-08-adfs/01-pc-domain-join.png)
*그림 2-1. 각 ADFS 노드를 도메인에 조인(Add-Computer) — 이 시점에 ADFS01$/ADFS02$ 컴퓨터 계정이 생겨야 gMSA를 만들 수 있다*

---

## 3. ADFS SSL 인증서 발급 (CA 활용)

여기서 앞서 만든 CA가 실전 투입된다. ADFS 팜은 `sts.lab.local` SSL 인증서가 필요하고, **SAN(Subject Alternative Name)** 을 포함해야 한다.

### 필요한 SAN

| 이름 | 용도 |
|---|---|
| sts.lab.local | 페더레이션 서비스 이름 (CN + SAN) |
| enterpriseregistration.lab.local | 디바이스 등록/Workplace Join |
| certauth.sts.lab.local | 인증서 기반 인증 |

### 요청 파일 + 발급 (ISCA01에서, 관리자 권한)

```powershell
@"
[Version]
Signature="`$Windows NT`$"
[NewRequest]
Subject = "CN=sts.lab.local"
KeyLength = 2048
KeySpec = 1
MachineKeySet = TRUE
ProviderName = "Microsoft RSA SChannel Cryptographic Provider"
RequestType = PKCS10
Exportable = TRUE
[Extensions]
2.5.29.17 = "{text}"
_continue_ = "dns=sts.lab.local&"
_continue_ = "dns=enterpriseregistration.lab.local&"
_continue_ = "dns=certauth.sts.lab.local&"
[RequestAttributes]
CertificateTemplate = WebServer
"@ | Out-File "C:\certtest\adfs-req.inf" -Encoding ASCII
```

![인증서 요청 .inf 파일 작성](/assets/images/26-07-08-adfs/02-cert-req-inf.png)
*그림 3-1. SAN 3개(sts / enterpriseregistration / certauth)를 포함한 요청 .inf 작성*

```cmd
certreq -new "C:\certtest\adfs-req.inf" "C:\certtest\adfs-req.csr"
certreq -submit -config "ISCA01.lab.local\lab-ISCA01-CA" "C:\certtest\adfs-req.csr" "C:\certtest\adfs-cert.cer"
certreq -accept "C:\certtest\adfs-cert.cer"
```

![CSR 생성 → ISCA01 제출·발급 → 저장소 설치](/assets/images/26-07-08-adfs/03-certreq-submit-accept.png)
*그림 3-2. certreq -new/-submit/-accept — CSR 생성, ISCA01 발급 CA에 제출·발급, 개인키 결합해 저장소에 설치*

> **`Exportable = TRUE`가 핵심**: 팜의 모든 노드(ADFS02)가 **동일한 인증서**를 써야 하므로, PFX로 내보내 배포할 수 있어야 한다. `certreq -accept`는 CSR 생성 시 만든 개인키와 발급된 인증서를 결합해 저장소에 설치하는 단계로, 이걸 해야 개인키 포함 완전한 인증서가 된다.

### 검증 + PFX 내보내기

```powershell
Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Subject -like "*sts.lab*" } |
    Format-List Subject, DnsNameList, HasPrivateKey

# 배포용 PFX
$cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Subject -like "*sts.lab*" } | Select-Object -First 1
$pw = ConvertTo-SecureString "<PFX_PASSWORD>" -AsPlainText -Force
Export-PfxCertificate -Cert $cert -FilePath "C:\certtest\adfs-cert.pfx" -Password $pw
```

![발급 확인 + SAN 검증 — DnsNameList 3개 + HasPrivateKey True](/assets/images/26-07-08-adfs/04-san-verify.png)
*그림 3-3. DnsNameList에 SAN 3개, HasPrivateKey: True — 개인키 포함 인증서 정상 발급 확인*

![PFX 형식으로 내보내기 — Export-PfxCertificate](/assets/images/26-07-08-adfs/05-pfx-export.png)
*그림 3-4. 배포용 PFX(adfs-cert.pfx) 내보내기 — 팜의 모든 노드가 동일 인증서를 쓰기 위함*

`DnsNameList`에 SAN 3개가 다 나오고 `HasPrivateKey: True`면 인증서 준비 완료. 이 PFX를 ADFS01/ADFS02에 설치한다.

![설치 전 인증서·PFX 최종 재확인](/assets/images/26-07-08-adfs/06-cert-recheck.png)
*그림 3-5. Thumbprint 확인 + Test-Path로 PFX 존재 확인 — ADFS 설치 직전 최종 점검*

---

## 4. ADFS01 — 첫 팜 노드 구성

### 인증서 설치 (ADFS01)

발급한 PFX를 ADFS01의 인증서 저장소에 설치한다.

![CA 서버(ISCA01)에서 ADFS01로 PFX 복사](/assets/images/26-07-08-adfs/07-cert-copy-to-adfs01.png)
*그림 4-1. New-PSDrive + Copy-Item으로 ISCA01의 PFX를 ADFS01로 이동*

```powershell
$pw = ConvertTo-SecureString "<PFX_PASSWORD>" -AsPlainText -Force
Import-PfxCertificate -FilePath "C:\adfs-cert.pfx" -CertStoreLocation Cert:\LocalMachine\My -Password $pw
```

![ADFS01 인증서 저장소에 PFX 설치 완료](/assets/images/26-07-08-adfs/08-pfx-import-adfs01.png)
*그림 4-2. Import-PfxCertificate — ADFS01 LocalMachine\My에 sts 인증서 설치 완료*

### 역할 설치 + 팜 구성

```powershell
Install-WindowsFeature ADFS-Federation -IncludeManagementTools

$cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Subject -like "*sts.lab*" }

Install-AdfsFarm `
    -FederationServiceName "sts.lab.local" `
    -FederationServiceDisplayName "LAB ADFS" `
    -CertificateThumbprint $cert.Thumbprint `
    -GroupServiceAccountIdentifier "LAB\gmsa-adfs`$" `
    -SQLConnectionString "Server=AGLISTENER;Database=AdfsConfiguration;Integrated Security=True"
```

![ADFS 역할 설치 — Install-WindowsFeature ADFS-Federation](/assets/images/26-07-08-adfs/09-install-adfs-feature.png)
*그림 4-3. ADFS-Federation 역할 설치 (Success)*

![인증서 Thumbprint + AGLISTENER 연결 확인](/assets/images/26-07-08-adfs/10-thumbprint-aglistener.png)
*그림 4-4. 팜 구성 전 점검 — 인증서 Thumbprint 확인 + AGLISTENER 1433 포트 TcpTestSucceeded True*

![Install-AdfsFarm 구성 완료](/assets/images/26-07-08-adfs/11-install-adfsfarm-complete.png)
*그림 4-5. Install-AdfsFarm — "The configuration completed successfully" (KDS 복제/재부팅/UPN 관련 WARNING은 정상)*

**핵심은 `-SQLConnectionString "Server=AGLISTENER"`** 이다. 구성 DB를 SQL AG Listener에 만든다. SQL 노드가 장애조치돼도 ADFS는 Listener만 보므로 투명하게 동작한다. gMSA 식별자 뒤의 `$`는 PowerShell에서 백틱으로 이스케이프한다.

성공하면 `The configuration completed successfully.`가 나온다. 단 몇 개의 WARNING이 함께 뜨는데 모두 정상이다(KDS 키 복제 대기 안내, 재부팅 필요 안내, UPN suffix 안내).

![SQL AG(SQL02 프라이머리)에 ADFS 구성 DB 생성 확인](/assets/images/26-07-08-adfs/12-adfs-db-on-sqlag.png)
*그림 4-6. AGLISTENER 경유로 생성된 구성 DB — AdfsConfigurationV4 / AdfsArtifactStore가 SQL AG에 ONLINE으로 존재*

### 재부팅 후 서비스 확인

```powershell
Get-Service adfssrv
```

> **[트러블슈팅 #2] 재부팅 후 adfssrv가 자동 시작 안 됨**
>
> 재부팅하면 adfssrv가 `Stopped`로 남아 있을 수 있다. 부팅 초기에 ADFS가 gMSA 암호를 AD에서 가져와야 하는데, 그 시점엔 네트워크/AD 통신이 아직 준비 안 돼 타이밍이 어긋나기 때문이다.
>
> **해결**: 수동 시작.
> ```powershell
> Start-Service adfssrv
> ```
> `Test-ADServiceAccount gmsa-adfs`가 True면 이후 재부팅부터는 대개 자동으로 올라온다.

![재부팅 후 adfssrv 수동 시작 → Running](/assets/images/26-07-08-adfs/13-adfssrv-running.png)
*그림 4-7. 재부팅 직후 adfssrv가 Stopped → `Start-Service adfssrv`로 Running 전환 (StartType Automatic)*

### 동작 검증

```powershell
Get-AdfsProperties | Select-Object HostName, HttpsPort
```
`HostName: sts.lab.local`이 나오면 팜 구성 완료. 브라우저로 로그인 페이지를 확인하려면:

```
https://sts.lab.local/adfs/ls/idpinitiatedsignon.aspx
```

AD FS 관리 콘솔에서도 팜이 정상 구성됐는지 둘러본다.

![AD FS 콘솔 — Overview](/assets/images/26-07-08-adfs/14-adfs-console-overview.png)
*그림 4-8. AD FS 관리 콘솔 Overview — 페더레이션 서비스 정상 로드*

![AD FS 콘솔 — Certificates](/assets/images/26-07-08-adfs/15-adfs-console-certificates.png)
*그림 4-9. Certificates — Service communications(sts, ISCA01 발급) + Token-decrypting/signing 자동 생성*

![AD FS 콘솔 — Relying Party Trusts (초기 비어 있음)](/assets/images/26-07-08-adfs/16-adfs-console-rpt.png)
*그림 4-10. Relying Party Trusts — 아직 신뢰 당사자 없음(초기 상태)*

![AD FS 콘솔 — Application Groups (초기 비어 있음)](/assets/images/26-07-08-adfs/17-adfs-console-appgroups.png)
*그림 4-11. Application Groups — 초기 상태(비어 있음)*

> **[트러블슈팅 #3] MSIS7012 — 에러처럼 보이지만 정상 신호**
>
> 위 주소에 접속하면 "AZLAB ADFS" 브랜딩과 함께 `MSIS7012: An error occurred` 페이지가 뜰 수 있다. **이건 ADFS가 정상 동작한다는 증거다** — 에러 페이지지만 ADFS 웹 서비스가 응답하고 있다는 뜻이다. MSIS7012는 **IdP-initiated 로그인 페이지가 기본 비활성**(ADFS 2019+ 보안 기본값)이라서 나는 것뿐이다.
>
> **해결**: 페이지 활성화 (팜이라 한 노드에서 하면 전체 적용).
> ```powershell
> Set-AdfsProperties -EnableIdPInitiatedSignonPage $true
> ```
> 이후 새로고침하면 로그인 페이지가 정상적으로 뜬다.

![IdP-initiated 로그인 페이지 활성화](/assets/images/26-07-08-adfs/18-enable-idp-signon.png)
*그림 4-12. `Set-AdfsProperties -EnableIdPInitiatedSignonPage $true` — 팜이라 한 노드에서 실행하면 전체 적용*

> **참고 — PowerShell 5.1의 metadata 접속 실패**: `Invoke-WebRequest`로 federationmetadata.xml을 받으면 "The underlying connection was closed"로 실패할 수 있다. 이는 PowerShell 5.1의 TLS/SNI 처리 문제이며 ADFS 자체는 정상이다. **브라우저로는 잘 열리므로** 검증은 브라우저로 하면 된다.

---

## 5. ADFS02 — 팜 조인

두 번째 노드를 같은 팜에 조인한다. ADFS01은 명령어로 했지만, ADFS02는 GUI 마법사로 진행했다(둘 다 경험).

### 사전 — DC 복제 확인

팜 구성 때 "KDS 키 10시간 대기" 경고가 있었으므로, ADFS02가 gMSA를 쓰려면 키가 복제돼 있어야 한다.

```powershell
# DC에서
repadmin /syncall /AdeP
```

> **[트러블슈팅 #4] DC가 한 대만 살아있을 때**
>
> 랩에서 DC 2대 중 한 대(DC02)가 꺼져 있으면 `repadmin`이 RPC unavailable(1722)로 실패한다. 하지만 **KDS 키와 gMSA가 살아있는 DC(DC01)에 있으면, DC01 단독으로도 ADFS02 조인이 가능**하다. ADFS02의 DNS를 DC01로 지정하면 된다. 복제는 "두 DC 모두에 확실히" 하려던 것일 뿐, DC01만 쓰면 복제 없이도 인증은 된다.

![ADFS 노드 고정 IP·DNS(DC 지정) 설정](/assets/images/26-07-08-adfs/20-node-ip-dns.png)
*그림 5-1. New-NetIPAddress로 고정 IP, Set-DnsClientServerAddress로 DNS를 DC로 지정 (TS#4의 "DNS를 DC로")*

![DC LDAP(389) 통신 + 도메인 해석 확인](/assets/images/26-07-08-adfs/19-ldap-dc-check.png)
*그림 5-2. Test-NetConnection DC:389 TcpTestSucceeded True + Resolve-DnsName — 살아있는 DC로 LDAP 인증 경로 정상*

### 인증서 설치 (ADFS02)

ADFS01과 **동일한** PFX를 설치한다(팜의 모든 노드가 같은 sts 인증서를 써야 함).

```powershell
Install-WindowsFeature ADFS-Federation -IncludeManagementTools
$pw = ConvertTo-SecureString "<PFX_PASSWORD>" -AsPlainText -Force
Import-PfxCertificate -FilePath "C:\adfs-cert.pfx" -CertStoreLocation Cert:\LocalMachine\My -Password $pw
```

### GUI 마법사로 조인

서버 관리자 → ADFS 구성 마법사:

1. Welcome: **"Add a federation server to a federation server farm"** (Create가 아님)
2. Specify Farm: 아래 함정 주의
3. Specify Service Account: `LAB\gmsa-adfs`
4. Specify Certificate: sts 인증서
5. Configure

![구성 마법사 Step 1 — Welcome: 팜에 서버 추가](/assets/images/26-07-08-adfs/21-wizard-welcome.png)
*그림 5-3. Welcome — Create가 아니라 **Add a federation server to a farm** 선택*

![구성 마법사 Step 2 — Connect to AD DS](/assets/images/26-07-08-adfs/22-wizard-connect-adds.png)
*그림 5-4. Connect to AD DS — 도메인 관리자 계정으로 연결*

> **[트러블슈팅 #5] Specify Farm — WID 옵션 vs SQL Server 옵션**
>
> 마법사의 Specify Farm 화면에는 두 라디오 버튼이 있다.
> - "Specify the primary federation server ... using **Windows Internal Database**"
> - "Specify the database location for an existing farm using **SQL Server**"
>
> ADFS01이 SQL AG로 구성 DB를 만들었으므로, **아래쪽(SQL Server)** 을 선택하고 Database Host Name에 **AGLISTENER**를 입력해야 한다. 위쪽(WID)을 고르고 AGLISTENER를 넣으면 "AGLISTENER라는 ADFS 서버에 연결"하려 해서 조인이 안 된다. WID 팜과 SQL 팜은 조인 방식이 다르다.

![구성 마법사 Step 3 — Specify Farm: SQL Server + AGLISTENER](/assets/images/26-07-08-adfs/23-wizard-specify-farm-sql.png)
*그림 5-5. Specify Farm — 아래쪽 **SQL Server** 선택 + Database Host Name에 **AGLISTENER** (TS#5의 핵심)*

![구성 마법사 Step 4 — Specify SSL Certificate](/assets/images/26-07-08-adfs/24-wizard-specify-cert.png)
*그림 5-6. Specify Certificate — ADFS01과 동일한 sts 인증서 선택*

![구성 마법사 Step 5 — Specify Service Account (gMSA)](/assets/images/26-07-08-adfs/25-wizard-service-account.png)
*그림 5-7. Specify Service Account — gmsa-adfs (gMSA) 지정*

![구성 마법사 Step 6 — Review Options](/assets/images/26-07-08-adfs/26-wizard-review.png)
*그림 5-8. Review — Data Source=AGLISTENER, gMSA로 실행 확인*

![구성 마법사 Step 7 — Pre-requisite Checks 통과](/assets/images/26-07-08-adfs/27-wizard-prereq.png)
*그림 5-9. Pre-requisite Checks — All prerequisite checks passed*

![구성 마법사 Step 8 — Results: 구성 성공](/assets/images/26-07-08-adfs/28-wizard-results.png)
*그림 5-10. Results — This server was successfully configured (재부팅/UPN WARNING은 정상)*

조인 후 서비스 확인. 팜에 두 노드가 다 있는지:

```powershell
Get-AdfsFarmInformation
```

![조인 후 재부팅 — 노드 신원 확인](/assets/images/26-07-08-adfs/29-post-join-hostname.png)
*그림 5-11. 재부팅 후 hostname/도메인 확인 — ADFS02가 정상 조인·부팅*

![Get-AdfsFarmInformation — 팜 노드 상세](/assets/images/26-07-08-adfs/30-farm-nodes-detail.png)
*그림 5-12. FarmNodes 상세 — ADFS01/ADFS02 두 노드가 BehaviorLevel 4로 존재*

![Get-AdfsFarmInformation — 2노드 팜 확인](/assets/images/26-07-08-adfs/31-farm-info.png)
*그림 5-13. FarmNodes {ADFS01, ADFS02} — 2노드 팜 완성*

`FarmNodes: {ADFS01.lab.local, ADFS02.lab.local}`가 나오면 2노드 팜 완성이다.

> **gMSA 검증 팁**: ADFS02에는 RSAT-AD-PowerShell이 없어 `Test-ADServiceAccount`가 안 될 수 있다. 대신 **adfssrv가 Running이면 gMSA는 정상**이다(서비스가 gMSA로 실행되니까). `Get-WmiObject Win32_Service -Filter "Name='adfssrv'"`의 StartName이 `LAB\gmsa-adfs$`인지로도 확인 가능.

---

## 6. NLB 부하분산 구성

두 ADFS 노드를 하나의 sts 이름(VIP)으로 묶는 부하분산 계층을 얹는다.

### 사전 — MAC 스푸핑 허용 (Hyper-V 호스트)

```powershell
# Hyper-V 호스트에서
Set-VMNetworkAdapter -VMName "ADFS01" -MacAddressSpoofing On
Set-VMNetworkAdapter -VMName "ADFS02" -MacAddressSpoofing On
```

![Hyper-V — 양 노드 MAC 스푸핑 On](/assets/images/26-07-08-adfs/32-mac-spoofing.png)
*그림 6-1. Set-VMNetworkAdapter -MacAddressSpoofing On — ADFS01/ADFS02 모두 On (NLB 필수 선행)*

> **이거 안 하면 NLB가 동작 안 한다.** NLB는 여러 노드가 같은 VIP의 트래픽을 공유하며 MAC 주소를 조작하는데, Hyper-V 기본값은 보안상 이를 차단한다. 명시적으로 허용해야 한다.

### NLB 클러스터 생성

```powershell
# 양 노드에 NLB 기능 설치
Install-WindowsFeature NLB -IncludeManagementTools

# ADFS01에서 - 클러스터 생성
New-NlbCluster -InterfaceName "Ethernet" `
    -ClusterName "sts-nlb" `
    -ClusterPrimaryIP 10.0.0.240 `
    -SubnetMask 255.255.255.0 `
    -OperationMode Multicast

# ADFS02 추가
Add-NlbClusterNode -NewNodeName "ADFS02.lab.local" -NewNodeInterface "Ethernet"
```

![NLB 기능 설치 (양 노드 공통)](/assets/images/26-07-08-adfs/33-install-nlb.png)
*그림 6-2. Install-WindowsFeature NLB — 양 노드에 NLB 기능 설치*

![새 NLB 클러스터 생성 (ADFS01)](/assets/images/26-07-08-adfs/34-new-nlb-cluster.png)
*그림 6-3. New-NlbCluster — sts-nlb, VIP 10.0.0.240(랩 실제 화면은 .219.240), Multicast 모드*

![ADFS02 노드 추가 → Converged](/assets/images/26-07-08-adfs/35-add-nlb-node.png)
*그림 6-4. Add-NlbClusterNode — ADFS02가 Converged 상태로 합류*

> Hyper-V 랩에서는 **Multicast** 모드가 안정적이다. Unicast는 단일 NIC 환경에서 노드 간 통신 문제가 생길 수 있다.

> **[트러블슈팅 #6] Add-NlbClusterNode — NlbBound: False**
>
> 노드 추가가 아래 에러로 실패할 수 있다.
> ```
> Failed to get the specified interface or NLB is not bound to the specified interface.
> ```
> `Get-NlbClusterNodeNetworkInterface -HostName "ADFS02.lab.local"`로 확인하면 `NlbBound: False`로 나온다. NLB 기능은 설치됐지만 원격 노드의 인터페이스에 NLB 드라이버 바인딩이 아직 안 된 상태다.
>
> **해결**: 대개 **재시도하면** 바인딩까지 되면서 붙는다. 계속 안 되면 `nlbmgr` GUI로 "Add Host To Cluster"를 하면 바인딩을 자동 처리해준다.

### 상태 확인

```powershell
Get-NlbClusterNode | Format-Table Name, State -AutoSize
```
양 노드가 **Converged**(ADFS01은 `Converged(default)` = 기본 호스트)면 NLB 완성이다.

---

## 7. sts DNS + 최종 검증

NLB가 됐으니 sts를 VIP로 연결한다.

```powershell
# DC에서 - sts → VIP
Add-DnsServerResourceRecordA -ZoneName "lab.local" -Name "sts" -IPv4Address "10.0.0.240"
Resolve-DnsName sts.lab.local
```

![sts → VIP DNS A 레코드 등록 + 해석 확인](/assets/images/26-07-08-adfs/36-sts-dns.png)
*그림 7-1. Add-DnsServerResourceRecordA — sts를 NLB VIP로 등록, Resolve-DnsName으로 해석 확인*

> 앞서 단일 노드 테스트를 위해 hosts 파일에 sts를 임시로 넣었다면, 이 시점에 제거한다. DNS(VIP)가 정식 경로다.

### 최종 검증

브라우저로 sts(VIP)를 통해 ADFS에 접속한다.

```
https://sts.lab.local/adfs/ls/idpinitiatedsignon.aspx
https://sts.lab.local/federationmetadata/2007-06/federationmetadata.xml
```

![sts(VIP) 로그인 페이지 정상 표시](/assets/images/26-07-08-adfs/37-signin-page.png)
*그림 7-2. sts(VIP) → NLB → ADFS 팜 경로로 "AZLAB ADFS" 로그인 페이지 정상 표시*

![federationmetadata.xml 정상 응답](/assets/images/26-07-08-adfs/38-federation-metadata-xml.png)
*그림 7-3. federationmetadata.xml(SAML 2.0 metadata) 정상 출력 — 페더레이션 엔드포인트 동작 확인*

로그인 페이지와 federation metadata(XML)가 둘 다 뜨면:

- sts DNS(VIP) → NLB → ADFS 팜 경로가 완전히 동작
- 사용자가 이 주소로 로그인 가능
- 한 노드가 죽어도 NLB가 다른 노드로 분산 → 서비스 유지

**내부망 ADFS 고가용성 팜 완성.**

> 인증서 경고가 뜬다면 정상이다. ISCA01 CA가 발급한 인증서라, 접속하는 클라이언트가 그 루트 CA를 아직 신뢰하지 않으면 경고가 난다. 루트 CA 인증서를 클라이언트 신뢰 저장소에 배포하면 경고가 사라진다.

---

## 8. 트러블슈팅 총정리

| # | 단계 | 증상 | 원인 | 해결 |
|---|---|---|---|---|
| 1 | gMSA 생성 | `Cannot find ADFS01$` | ADFS VM 미생성으로 컴퓨터 계정 없음 | ADFS 도메인 조인 후 gMSA 생성 |
| 2 | 팜 구성 후 | adfssrv 자동 시작 실패 | 부팅 시 gMSA 암호 조회 타이밍 | `Start-Service adfssrv` 수동 시작 |
| 3 | 접속 검증 | MSIS7012 에러 페이지 | IdP-initiated 페이지 기본 비활성 | `Set-AdfsProperties -EnableIdPInitiatedSignonPage $true` |
| 4 | ADFS02 조인 전 | repadmin RPC 실패 (1722) | DC 한 대 다운 | 살아있는 DC 단독으로 진행 가능 |
| 5 | ADFS02 조인 | 조인 안 됨 | WID 옵션 선택 | SQL Server 옵션 + AGLISTENER |
| 6 | NLB 노드 추가 | NlbBound: False | 원격 인터페이스 바인딩 미완 | 재시도 또는 nlbmgr GUI |

### 진단 시그니처

- gMSA `Cannot find 컴퓨터$` → **컴퓨터 계정 먼저** (도메인 조인 후 gMSA)
- MSIS7012 → **정상 동작 신호**, IdP-initiated 활성화만
- 팜 조인 → **SQL 팜은 SQL Server 옵션 + AGLISTENER** (WID 아님)
- NLB `NlbBound: False` → **재시도 / GUI**
- ADFS 서비스가 gMSA로 Running → **gMSA 정상** (Test-ADServiceAccount 대체 확인)

---

## 마치며

앞서 만든 **CA와 SQL AG가 ADFS 팜에서 하나로 합쳐지는** 과정이 이번 구축의 핵심이었다. CA로 발급한 SAN 인증서가 팜의 SSL 신원이 되고, SQL AG Listener가 구성 DB를 받치고, gMSA가 두 노드의 공용 계정이 되고, NLB가 앞단에서 부하를 나눈다. 각각 따로 배웠던 조각들이 실제로 맞물려 돌아가는 걸 확인하니, 왜 그 밑작업들을 먼저 했는지가 분명해졌다.

특히 "구성 DB를 SQL AG에 연결"한 부분은 실무에서도 의미가 크다. ADFS 구성 정보가 단일 SQL 노드에 묶이지 않고, AG 장애조치로 보호되기 때문이다. (다만 ADFS가 만든 구성 DB가 자동으로 AG에 포함되지는 않아, 별도로 AG에 추가하는 작업이 필요하다 — 이건 팜을 마저 완성한 뒤 다룰 예정이다.)

지금까지가 **내부망 ADFS 고가용성 팜**이다. 다음 편에서는 이 팜을 외부에 안전하게 공개하는 **WAP(Web Application Proxy)** 를 DMZ에 세운다.