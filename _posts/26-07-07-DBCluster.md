---
layout: single
title: "[SQL Server] Hyper-V 랩으로 AlwaysOn 가용성 그룹(AG) 구축 완주기 — 설치부터 Listener·시딩까지, 9개 트러블슈팅 전부 기록"
excerpt: "2노드 SQL Server 2022 AlwaysOn AG를 Hyper-V 랩에 직접 구축하며 겪은 설치 취소 후 model DB 경로 오류, 서비스 계정 잠김, 백업 경로 OS error 3, Listener CNO 권한, 보조 조인 skip, Automatic seeding Request Denied까지 — 실전 오류 9개의 진단·해결 과정을 순서대로 기록."
date: 2026-07-07
categories: [Infra, SQL Server]
tags: [sql-server, alwayson, availability-group, wsfc, hyper-v, listener, automatic-seeding, high-availability, 고가용성, 트러블슈팅]
---

## 들어가며

**SQL Server AlwaysOn 가용성 그룹(AG)** 운영을 다뤄야 할 일이 생기면서, IAM/ADFS가 전문 분야인 내 입장에선 사전 학습이 필요했음. "AG Listener 연결 불가 원인 분석" 같은 문제는 문서만 읽고 대응하는 게 무리라고 판단해서 **Hyper-V 랩에 직접 2노드 AG를 구축**해보기로 함.

기존에 구축해둔 AD 랩 환경(lab.local 도메인, DC 2대, WSFC 클러스터)이 있어서 그 위에 SQL 노드 2대를 얹는 방식으로 진행했음. 그런데 이게 전혀 순탄하지 않았음. **SQL 설치 단계부터 시작해서 AG 시딩이 완료되기까지 아홉 번 정도 벽에 부딪혔음.** 오히려 그 벽들이 전부 실무에서 만날 법한 전형적 오류라, 진단 과정까지 통째로 기록으로 남기기로 함.

이 글은 **구축 가이드 + 각 단계 트러블슈팅**을 같이 담았음. 순서대로 따라 하면 랩이 완성되고, 중간에 만난 오류들은 별도 박스로 정리해서 같은 상황을 겪을 때 참고할 수 있게 했음.

**랩 환경 정보**

| 항목 | 값 |
|---|---|
| 도메인 | lab.local (LAB) |
| 네트워크 | 10.0.0.x |
| WSFC 클러스터 | SQLCLUSTER (2노드 + File Share Witness 쿼럼) |
| SQL01 | 10.0.0.221 (Primary) |
| SQL02 | 10.0.0.222 (Secondary) |
| Listener IP | 10.0.0.224 |
| SQL Server | 2022 Enterprise Evaluation |
| OS | Windows Server 2022 Standard Evaluation |
| 서비스 계정 | LAB\svc-sqlengine, LAB\svc-sqlagent |

---

## 목차

1. [AG가 뭔지부터 — 고가용성 개념 정리](#1-ag가-뭔지부터--고가용성-개념-정리)
2. [사전 준비 — 왜 이 조건들이 필요한가](#2-사전-준비--왜-이-조건들이-필요한가)
3. [SQL Server 2022 설치 (양 노드)](#3-sql-server-2022-설치-양-노드)
4. [방화벽 포트 개방](#4-방화벽-포트-개방)
5. [AlwaysOn 기능 활성화 (양 노드)](#5-alwayson-기능-활성화-양-노드)
6. [SSMS 설치](#6-ssms-설치)
7. [AG에 넣을 DB 준비 (생성 + Full 백업)](#7-ag에-넣을-db-준비-생성--full-백업)
8. [AG 생성 마법사 + Listener 구성](#8-ag-생성-마법사--listener-구성)
9. [Listener·조인·시딩 트러블슈팅 3연쇄](#9-listener조인시딩-트러블슈팅-3연쇄)
10. [AG 동작 검증](#10-ag-동작-검증)
11. [오늘 만난 트러블슈팅 총정리](#11-오늘-만난-트러블슈팅-총정리)

---

## 1. AG가 뭔지부터 — 고가용성 개념 정리

용어부터 헷갈려서 정리하고 넘어감.

- **HA (High Availability, 고가용성)** = 큰 개념. "서버 하나 죽어도 서비스 안 끊김"을 만드는 모든 기술
- **AlwaysOn** = Microsoft SQL Server가 HA를 구현하는 기능 브랜드
- **AG (Availability Group, 가용성 그룹)** = AlwaysOn의 핵심 단위. **DB 묶음을 여러 서버에 복제**해두는 것

우리가 만드는 구조를 그림으로 표현하면 이럼.

```
        [ Listener: 10.0.0.224 ]  ← 앱은 여기로만 접속 (가상 이름)
                 │
        ┌────────┴────────┐
        │                 │
   ┌─────────┐       ┌─────────┐
   │  SQL01  │  →→→  │  SQL02  │
   │ Primary │ 동기화 │Secondary│
   │(주 복제본)│       │(보조 복제본)│
   └─────────┘       └─────────┘
     읽기/쓰기          읽기전용(대기)
        │                 │
        └────── WSFC ──────┘
          (SQLCLUSTER + FSW 쿼럼)
```

**동작 시나리오**

1. 평소엔 앱이 Listener(.224)로 접속 → 실제론 SQL01(주)에 연결됨
2. SQL01이 데이터를 쓰면 → **실시간으로 SQL02(보조)에 복제**(동기 커밋)
3. SQL01이 죽으면 → WSFC가 감지 → **SQL02가 자동으로 주 복제본으로 승격**(자동 장애조치)
4. 앱은 여전히 Listener(.224)로 접속 → 이제 SQL02로 연결됨 → **앱은 아무것도 안 바꿔도 서비스 유지**

여기서 핵심은 **"앱이 물리 서버가 아니라 Listener만 바라본다"**는 점임. 그래서 서버가 죽어도 앱 입장에선 끊김이 최소화됨. 실무에서 자주 만나는 "Listener 연결 불가" 문제가 바로 이 구조에서 3~4번 과정이 틀어졌을 때 생기는 것임.

---

## 2. 사전 준비 — 왜 이 조건들이 필요한가

AG를 만들기 전에 아래가 갖춰져 있어야 함.

| 조건 | 이유 |
|---|---|
| **WSFC 클러스터** | AG의 기반. 노드 상태 감지와 자동 장애조치를 WSFC가 담당 |
| **양 노드 도메인 조인** | 서비스 계정 인증, 클러스터 통신 전제 |
| **동일한 서비스 계정** | 양 노드가 같은 계정을 쓰면 미러링 엔드포인트 권한 부여가 간단 |
| **동일한 데이터/로그 경로** | Automatic seeding의 필수 조건 |

이 랩에서는 WSFC(SQLCLUSTER, FSW 쿼럼)가 이미 구성돼 있는 상태에서 시작함.

---

## 3. SQL Server 2022 설치 (양 노드)

SQL01, SQL02 각각에 동일하게 설치함. 설치 관리자에서 아래 값으로 진행.

![설치 전 사전 확인 — PowerShell로 메모리·잔여 폴더·ISO 마운트 점검](/assets/images/26-07-07-dbcluster/pre-check.png)
*설치 시작 전 PowerShell로 메모리, 잔여 폴더(재설치 시 클린 상태), ISO 마운트를 점검*

| 화면 | 설정값 |
|---|---|
| Installation Type | New SQL Server standalone installation |
| Edition | **Evaluation** (Enterprise 기능 = 풀 AG 지원) |
| Feature | **Database Engine Services** 만 |
| Instance | **Default instance** (MSSQLSERVER) |
| Engine 서비스 계정 | LAB\svc-sqlengine |
| Agent 서비스 계정 | LAB\svc-sqlagent, **Startup Type = Automatic** |
| IFI | Grant Perform Volume Maintenance Tasks 체크 |
| 인증 모드 | **Mixed Mode** + sa 암호 + Add Current User |
| Azure Extension | **체크 해제** |

![Instance Configuration - Default instance(MSSQLSERVER)](/assets/images/26-07-07-dbcluster/install-instance.png)
*Instance Configuration — Default instance(MSSQLSERVER) 선택 (AG 랩 표준)*

![Database Engine Configuration - Mixed Mode 인증](/assets/images/26-07-07-dbcluster/install-dbengine.png)
*Database Engine Configuration — Mixed Mode + sa 암호 + Add Current User*

![SQL Server 2022 Server Configuration - 서비스 계정 설정](/assets/images/26-07-07-dbcluster/01-server-configuration.png)
*그림 3-1. 서비스 계정을 도메인 계정으로 지정하고 Agent Startup Type을 Automatic으로 변경*

> **Agent Startup Type을 Automatic으로** 바꾸는 게 포인트임. 기본값이 Manual이라 놓치기 쉬운데, AG 환경에서 Agent가 자동 시작 안 되면 백업 잡·모니터링이 안 돌아서 나중에 트러블슈팅 포인트가 됨. (실무의 "SQL Agent 자동시작 실패" 이슈와 정확히 같은 주제)

**AG용인데 왜 Default instance인가?** 기본 인스턴스는 `SQL01` 서버명만으로 접속되지만, 명명된 인스턴스는 `SQL01\인스턴스명` 형태라 Listener 구성·포트 설정이 복잡해짐. AG 랩에서는 양 노드를 똑같이 Default instance로 맞추는 게 표준임.

**Clustered = No가 맞는 이유.** FCI(장애조치 클러스터 인스턴스)는 인스턴스 자체를 클러스터화하지만, AG는 독립 인스턴스 위에 DB 단위로 복제하는 구조라 각 노드는 **독립(비클러스터) 인스턴스**로 설치해야 함.

![SQL Server 2022 설치 완료 - Complete](/assets/images/26-07-07-dbcluster/install-complete.png)
*정상 설치 완료 — Database Engine Services / SQL Browser / SQL Writer 모두 Succeeded*

### 설치 후 검증

설치가 끝나면 반드시 아래 3가지를 확인함.

```powershell
# ① 서비스 자동 시작 + Running 확인
Get-Service MSSQLSERVER, SQLSERVERAGENT | Format-Table Name, Status, StartType -AutoSize

# ② 엔진 접속 + 서버명/버전
sqlcmd -S localhost -E -Q "SELECT @@SERVERNAME AS ServerName, @@VERSION AS Version;"

# ③ 시스템 DB 파일 경로 확인 (이게 제일 중요)
sqlcmd -S localhost -E -Q "SELECT name, physical_name FROM sys.master_files ORDER BY database_id;"
```

③번에서 master/model/msdb/tempdb 파일이 전부 정상 경로(`C:\Program Files\...\MSSQL16.MSSQLSERVER\MSSQL\DATA\`)에 있어야 함. 왜 이게 중요한지는 아래 트러블슈팅에서 설명함.

![서비스 자동 시작 + Running 상태 확인](/assets/images/26-07-07-dbcluster/verify-services.png)
*① MSSQLSERVER / SQLSERVERAGENT 모두 Running + Automatic*

![sys.master_files 경로 확인 - model.mdf 정상 경로](/assets/images/26-07-07-dbcluster/verify-masterfiles.png)
*③ 시스템 DB 파일이 전부 정상 `...\MSSQL\DATA\` 경로 — model.mdf가 여기 있어야 #1 오류가 안 남*

> **[트러블슈팅 #1] 설치 취소로 인한 model DB 경로 오류**
>
> **증상**: SQL 서비스(MSSQLSERVER)가 시작 안 됨. 이벤트 로그에 아래 에러.
> ```
> FCB::Open failed: Could not open file
> D:\dbs\sh\5uj5\1008_054209\cmd\11\obj\x64retail\sql\mkmastr\databases\model.mdf
> OS error: 3(The system cannot find the path specified.)
> ```
> Service Control Manager 이벤트에는 `service terminated with service-specific error %%945`.
>
> **원인**: `D:\dbs\sh\...`는 **Microsoft가 SQL Server를 컴파일한 빌드 서버의 내부 경로**임. 이런 폴더가 내 서버에 있을 리 없음. 설치가 **model DB 생성 단계(`SqlEngineConfigAction`)에서 취소**되면, master는 만들어졌지만(그래서 서비스는 등록되고 ERRORLOG도 생김) model이 안 만들어져서 그 경로가 템플릿(빌드 경로) 그대로 남음. 엔진은 부팅 시 model을 참조하는데 그걸 못 찾아 기동 실패함.
>
> **진단 루트**: `FCB::Open failed` + `OS error 3` → 곧바로 "master/model 파일 경로 문제"로 직행. Event `%%945`도 세트로 기억.
>
> **해결**: 부분 설치된 인스턴스를 제거하고 **취소 없이** 클린 재설치. 설치 진행률 화면(`SqlEngineConfigAction_install_confignonrc_Cpu64`)에서 멈춘 것처럼 보여도 **절대 취소 금지** — 이 단계가 바로 model/msdb/tempdb를 생성하는 과정임. 시스템 DB 생성이라 시간이 걸리는 게 정상.
>
> **참고**: 인스턴스 제거는 SQL Installation Center의 Maintenance가 아니라 **제어판(appwiz.cpl) → Microsoft SQL Server 2022 (64-bit) → 제거**에서 함. Maintenance의 "Remove node from failover cluster"는 FCI 전용이라 AG 랩에선 건드리면 안 됨.

![Installation Progress - SqlEngineConfigAction 단계](/assets/images/26-07-07-dbcluster/02-install-progress.png)
*그림 3-2. 이 SqlEngineConfigAction 단계에서 취소하면 model DB가 생성되지 않아 #1 오류가 발생함. 절대 취소 금지.*

![Complete with failures - 설치 취소로 인한 실패 결과](/assets/images/26-07-07-dbcluster/install-complete-failures.png)
*실제로 설치가 취소·실패하면 이렇게 Database Engine Services가 Failed로 끝남 (#1 상황)*

---

## 4. 방화벽 포트 개방

양 노드 모두에서 아래 포트를 열어야 함.

```powershell
# SQL 엔진 포트 (원격 접속 + Listener)
New-NetFirewallRule -DisplayName "SQL Engine 1433" -Direction Inbound -Protocol TCP -LocalPort 1433 -Action Allow

# AG 미러링 엔드포인트 포트 (노드 간 데이터 동기화)
New-NetFirewallRule -DisplayName "SQL AG Endpoint 5022" -Direction Inbound -Protocol TCP -LocalPort 5022 -Action Allow

# SQL Browser (선택)
New-NetFirewallRule -DisplayName "SQL Browser 1434 UDP" -Direction Inbound -Protocol UDP -LocalPort 1434 -Action Allow
```

| 포트 | 용도 |
|---|---|
| 1433/TCP | SQL 엔진 (앱·Listener 접속, 원격 관리) |
| 5022/TCP | AG 미러링 엔드포인트 (노드 간 데이터 동기화) |
| 1434/UDP | SQL Browser (명명된 인스턴스용, 기본 인스턴스는 선택) |

![방화벽 규칙 개방 - New-NetFirewallRule 1433/5022/1434](/assets/images/26-07-07-dbcluster/firewall.png)
*양 노드에서 1433(엔진)·5022(AG 엔드포인트)·1434(Browser) 포트를 PowerShell로 개방*

> **[트러블슈팅 #2] 원격 접속만 안 되고 로컬은 되는 상황**
>
> **증상**: SQL01의 SSMS에서 SQL02로 접속 시도 시 아래 에러.
> ```
> error: 40 - Could not open a connection to SQL Server (Error: 5)
> Additional information: Access is denied
> ```
> "Access is denied" 때문에 권한 문제로 보이지만, 진짜 원인은 위에 있음.
>
> **원인**: `error: 40` = 네트워크 연결 자체가 안 됨. SQL02의 방화벽이 1433을 막고 있어서 원격(SQL01→SQL02) 접속이 차단된 것. 로컬(SQL02 자기 자신)은 되지만 원격이 안 되는 게 시그니처.
>
> **해결**: 위 방화벽 규칙을 **양 노드 모두** 실행. `error: 40` + 로컬은 되고 원격만 안 됨 → **방화벽 또는 SQL 원격 접속 설정**을 제일 먼저 의심하는 게 표준 진단 루트. (드물게 SQL Configuration Manager에서 TCP/IP 프로토콜이 비활성인 경우도 있는데, SQL2022는 기본 활성)

> **[트러블슈팅 참고] 서비스 계정 잠김으로 설치 중단**
>
> SQL02 설치 중 Server Configuration 단계에서 "The SQL Server service account login or password is not valid" 에러가 남. 원인은 앞선 설치 시도·취소를 반복하면서 svc-sqlengine/svc-sqlagent 암호 검증이 여러 번 실패 → **도메인 계정 잠금 정책 임계치를 넘어 계정이 잠긴** 것. DC에서 `Get-ADUser <계정> -Properties LockedOut`으로 확인하고 `Unlock-ADAccount`로 해제하면 됨. 실무에서도 "서비스 계정 로그인 실패 반복 → 계정 잠김 → 서비스 시작 불가"는 아주 흔한 장애 패턴. 랩에서는 `Set-ADUser <계정> -PasswordNeverExpires $true`로 완화 가능(운영은 gMSA 권장).

![Server Configuration - 서비스 계정 로그인/암호 검증 오류](/assets/images/26-07-07-dbcluster/service-account-invalid.png)
*"The SQL Server service account login or password is not valid" — 계정 잠김 시 이 검증 오류로 설치가 막힘*

---

## 5. AlwaysOn 기능 활성화 (양 노드)

AG를 만들려면 먼저 각 노드에서 AlwaysOn 기능을 켜야 함. **SQL Server Configuration Manager**에서 진행 (로컬 전용이라 각 서버에서 직접 실행해야 함).

1. `Win + R` → `SQLServerManager16.msc`
2. SQL Server Services → **SQL Server (MSSQLSERVER)** 우클릭 → Properties
3. **AlwaysOn High Availability** 탭 → "Enable AlwaysOn Availability Groups" 체크
   - Windows failover cluster name에 **SQLCLUSTER**가 자동으로 뜨면 정상(WSFC 인식)
4. Apply → **서비스 재시작**

SQL02에서도 동일하게 반복함.

![SQL Server Configuration Manager - AlwaysOn 활성화 탭](/assets/images/26-07-07-dbcluster/alwayson-enable.png)
*MSSQLSERVER Properties → AlwaysOn High Availability 탭 → Enable 체크 (WSFC = SQLCLUSTER 자동 인식)*

![서비스 재시작](/assets/images/26-07-07-dbcluster/alwayson-restart.png)
*Apply 후 SQL Server 서비스 재시작으로 활성화 반영*

### 활성화 확인

```powershell
Invoke-Sqlcmd -ServerInstance "SQL01" -Query "SELECT SERVERPROPERTY('IsHadrEnabled') AS HADR"
Invoke-Sqlcmd -ServerInstance "SQL02" -Query "SELECT SERVERPROPERTY('IsHadrEnabled') AS HADR"
```

양 노드 모두 `1`이 나오면 활성화 완료.

![IsHadrEnabled = 1 확인 (PowerShell)](/assets/images/26-07-07-dbcluster/alwayson-verify.png)
*Invoke-Sqlcmd로 SQL01·SQL02 모두 IsHadrEnabled = 1 확인*

> **[트러블슈팅 #3] Invoke-Sqlcmd 파라미터 오류 (SQLPS vs SqlServer 모듈 충돌)**
>
> **증상**:
> ```
> Invoke-Sqlcmd : A parameter cannot be found that matches parameter name 'TrustServerCertificate'.
> ```
>
> **원인**: `-TrustServerCertificate`는 최신 **SqlServer 모듈(22.x)**에만 있는 파라미터인데, PowerShell이 옛날 **SQLPS 모듈**을 먼저 로드해서 그 파라미터를 못 찾는 것. SSMS 21+ 부터는 SqlServer 모듈이 자동 포함되지 않아서 별도 설치가 필요함.
>
> **해결**: 파라미터를 빼면 됨. 옛 SQLPS 모듈의 `Invoke-Sqlcmd`는 암호화를 강제하지 않아서 `-TrustServerCertificate` 없이도 접속됨.
> ```powershell
> Invoke-Sqlcmd -ServerInstance "SQL01" -Query "SELECT SERVERPROPERTY('IsHadrEnabled') AS HADR"
> ```
> 최신 모듈이 필요하면: `Install-Module -Name SqlServer -Scope CurrentUser -Force -AllowClobber`
>
> **연결 고리**: 이 SQLPS 모듈 문제는 실무에서 만나는 **"InitializeDefaultDrives 타임아웃"** 이슈와 같은 뿌리임. 옛 SQLPS가 PowerShell 드라이브(SQLSERVER:\)를 초기화하려다 타임아웃 나는 것.

---

## 6. SSMS 설치

AG 구성은 SSMS 마법사로 하는 게 편함. **SQL01 한 곳에만** 설치하면 됨 — SSMS는 클라이언트 도구라 하나로 양 노드를 원격 관리할 수 있음(리모컨 하나로 TV 두 대 조작하는 개념).

2026년 7월 기준 최신은 **SSMS 22**. 반드시 Microsoft 공식 페이지에서 받아야 함.

- 다운로드: `https://learn.microsoft.com/en-us/ssms/install/install`
- "Download SQL Server Management Studio 22 installer" → `vs_SSMS.exe` (부트스트래퍼, 수 MB)
- 관리자 권한으로 실행 → Visual Studio Installer가 열림

![SSMS 22 다운로드 페이지](/assets/images/26-07-07-dbcluster/ssms-download.png)
*Microsoft 공식 페이지에서 SSMS 22 부트스트래퍼(vs_SSMS.exe) 다운로드*

![Visual Studio Installer - SSMS Core Components 설치](/assets/images/26-07-07-dbcluster/ssms-install.png)
*Visual Studio Installer 기반 — SSMS Core Components만 설치*

> **참고**: SSMS 21부터 설치 방식이 Visual Studio Installer 기반으로 바뀜. 화면에 "Visual Studio Installer"가 떠서 헷갈리는데, **이건 설치 도구일 뿐이고 Visual Studio 본체는 안 깔림**. 워크로드(AI Assistance, Business Intelligence 등)는 전부 체크 해제하고 **SSMS Core Components만** 설치하면 됨. AG 랩에는 Core만으로 충분.

### SSMS 첫 연결

설치 후 SSMS 실행 → 로그인 화면은 **"Skip and add accounts later"**(온프레미스 SQL 접속엔 MS 계정 불필요) → 연결 창에서:

- Server name: `localhost` (또는 `SQL01`)
- Authentication: Windows Authentication
- **Trust Server Certificate 체크** ⚠️

> **[트러블슈팅 #4] SSMS 연결 시 인증서 오류**
>
> SSMS 20 버전부터 **Encrypt 기본값이 Mandatory(필수 암호화)**로 바뀜. 그런데 랩 서버는 자체 서명 인증서만 있어서, **Trust Server Certificate를 체크 안 하면 로컬 접속인데도 인증서 신뢰 오류**가 남. 랩에서는 이 체크가 표준. (실무 프로덕션에선 CA 발급 인증서를 붙여서 이 체크 없이 암호화 접속 — 2-Tier PKI 랩과 연결되는 지점)

SQL01의 SSMS 하나에 SQL01, SQL02를 모두 연결해두면 한 화면에서 양 노드를 관리할 수 있음. (SQL02 연결도 동일하게 Trust Server Certificate 체크)

![SSMS 연결 창 - Trust Server Certificate 체크](/assets/images/26-07-07-dbcluster/ssms-connect.png)
*Encrypt=Mandatory 기본값 + Trust Server Certificate 체크로 자체 서명 인증서 신뢰 (#4)*

---

## 7. AG에 넣을 DB 준비 (생성 + Full 백업)

AG에 참여하는 DB는 두 가지 조건을 만족해야 함.

1. **Full recovery model** — AG는 트랜잭션 로그를 실시간으로 보조 노드에 보내 동기화함. Simple 모델은 로그를 바로 잘라버려서 보낼 게 없으니 AG 불가.
2. **Full 백업 1회 이상** — AG가 보조 노드에 DB를 처음 만들 때 이 백업을 기준점으로 씀.

SQL01(주 복제본이 될 노드)의 SSMS에서 실행.

```sql
USE master;
GO

-- 재실행 안전성 확보 (잔재 정리)
IF DB_ID('TestAG') IS NOT NULL
    DROP DATABASE TestAG;
GO

-- 1. DB 생성
CREATE DATABASE TestAG;
GO

-- 2. Full recovery model (AG 필수)
ALTER DATABASE TestAG SET RECOVERY FULL;
GO

-- 3. 샘플 테이블 + 데이터 (장애조치 후 데이터 유지 확인용)
USE TestAG;
CREATE TABLE dbo.FailoverTest (
    id INT IDENTITY PRIMARY KEY,
    note NVARCHAR(100),
    created_at DATETIME2 DEFAULT SYSDATETIME()
);
INSERT INTO dbo.FailoverTest (note) VALUES (N'AG 구성 전 초기 데이터 - SQL01에서 작성');
GO

-- 4. Full 백업 (AG 필수)
-- ▼ 경로 주의: SQL 서비스 계정이 접근 가능한, SQL01 로컬에 실재하는 폴더여야 함
--   기본 백업 폴더는 설치 시 자동 생성 + 권한 보장이라 가장 안전
BACKUP DATABASE TestAG
TO DISK = N'C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\Backup\TestAG.bak'
WITH INIT, COMPRESSION;
GO

-- 5. 검증
USE master;
SELECT name, recovery_model_desc, state_desc
FROM sys.databases WHERE name = 'TestAG';
GO
```

![SSMS - TestAG 생성/백업 스크립트 실행](/assets/images/26-07-07-dbcluster/testag-create.png)
*SQL01 SSMS에서 CREATE DATABASE → RECOVERY FULL → 샘플 데이터 → Full 백업 스크립트 실행*

검증 쿼리에서 `TestAG / FULL / ONLINE`이 나오면 준비 완료.

![TestAG 생성 및 recovery model 검증 결과](/assets/images/26-07-07-dbcluster/03-testag-full-online.png)
*그림 7-1. TestAG가 FULL recovery model + ONLINE 상태 — AG 참여 조건 충족*

> **[트러블슈팅 #5] 백업 실패 — OS error 3 (경로 없음)**
>
> **증상**:
> ```
> Msg 3201: Cannot open backup device 'C:\Backup\TestAG.bak'.
> Operating system error 3(The system cannot find the path specified.).
> ```
>
> **원인**: 백업 경로 폴더가 없거나, **"사람이 RDP로 보는 경로"와 "SQL 서비스 계정이 보는 경로"가 어긋난** 경우. `C:\Backup`을 만들었는데도 실패한다면, 그 폴더를 **SQL01이 아닌 다른 서버**(호스트나 DC)에서 만들었을 가능성이 큼. SQL 백업은 항상 **SQL 엔진이 도는 서버, 서비스 계정 기준**으로 경로를 봄.
>
> **해결**: 폴더 추적으로 시간 쓰지 말고, **SQL 설치 시 자동 생성되는 기본 백업 폴더**(`...\MSSQL16.MSSQLSERVER\MSSQL\Backup\`)를 쓰면 됨. 이 폴더는 무조건 존재하고 svc-sqlengine 권한도 이미 있음.
>
> **에러 코드 시그니처**: `OS error 3` = 경로 없음, `OS error 5` = 권한 없음. 두 개는 세트로 기억. (설치 때 본 model 파일 `OS error 3`과 같은 "경로 문제" 시그니처)

---

## 8. AG 생성 마법사 + Listener 구성

SQL01 SSMS → Object Explorer → **Always On High Availability** 우클릭 → **New Availability Group Wizard**

> **팁**: 마법사 메뉴가 비활성으로 보이면 SQL01 노드를 **F5로 새로고침**. AlwaysOn 활성화 후 SSMS가 갱신 전 상태를 보고 있는 것. (설정 변경 후 F5 갱신은 자주 쓰는 습관)

**마법사 화면별 설정**

| 단계 | 설정 |
|---|---|
| Specify AG Name | AG 이름: `AG-TEST`, Cluster type: Windows Server Failover Cluster |
| Select Databases | TestAG 체크 → "Meets prerequisites" 초록 확인 |
| Specify Replicas | 아래 표 참조 |
| Select Data Synchronization | **Automatic seeding** |
| Validation | 통과 확인 |
| Summary → Finish | 생성 |

![New Availability Group 마법사 - Specify Options (AG-TEST)](/assets/images/26-07-07-dbcluster/ag-wizard-options.png)
*Specify Options — AG 이름 AG-TEST, Cluster type = WSFC*

![Select Databases - TestAG (Meets prerequisites)](/assets/images/26-07-07-dbcluster/ag-wizard-databases.png)
*Select Databases — TestAG 체크, "Meets prerequisites" 확인*

**Specify Replicas — Replicas 탭 (핵심)**

| 항목 | SQL01 | SQL02 |
|---|---|---|
| Initial Role | Primary | Secondary |
| Automatic Failover | ☑️ | ☑️ |
| Availability Mode | **Synchronous commit** | **Synchronous commit** |
| Readable Secondary | Yes | Yes |

![Specify Replicas - 복제본 설정](/assets/images/26-07-07-dbcluster/04-specify-replicas.png)
*그림 8-1. 양 노드 Synchronous commit + Automatic Failover 체크*

> **순서 주의**: **Synchronous commit을 먼저** 선택해야 Automatic Failover 체크가 활성화됨. 비동기 모드에서는 자동 장애조치가 원천적으로 불가능하기 때문. 동기 커밋이어야 두 노드 데이터가 항상 일치(데이터 손실 0)하고, 그래야 자동 장애조치가 안전하게 됨. `Required synchronized secondaries to commit`은 2노드 랩에서는 **0**으로 둠(1로 하면 보조가 죽을 때 주 노드 쓰기가 막힘).
>
> **주의**: SSMS 그리드 체크박스는 클릭 후 **다른 셀로 포커스를 옮겨야 값이 확정**됨. 확정 전에 Next를 누르면 Summary에 이전 값(Manual)이 그대로 반영될 수 있음. 만약 이렇게 됐으면 AG 생성 후 T-SQL로 변경 가능: `ALTER AVAILABILITY GROUP [AG-TEST] MODIFY REPLICA ON N'SQL01' WITH (FAILOVER_MODE = AUTOMATIC);` (양 노드 각각)

**Specify Replicas — Listener 탭**

- **Create an availability group listener** 선택
- Listener DNS Name: `AGLISTENER`
- Port: `1433`
- Network Mode: **Static IP**
- Add → Subnet 선택 → IP: `10.0.0.224`

![Select Data Synchronization - Automatic seeding](/assets/images/26-07-07-dbcluster/ag-wizard-seeding.png)
*Select Data Synchronization — Automatic seeding 선택*

![Listener 탭 - AGLISTENER / 1433 / Static IP](/assets/images/26-07-07-dbcluster/ag-wizard-listener.png)
*Listener 탭 — AGLISTENER, Port 1433, Static IP 구성*

![Validation - 전 항목 Success](/assets/images/26-07-07-dbcluster/ag-wizard-validation.png)
*Validation — 전 항목 Success 확인 후 Finish*

> **[트러블슈팅 #6] Automatic seeding 잔재로 Validation Error**
>
> **증상**: Validation에서 아래 두 Error.
> ```
> ❌ The databases TestAG already exist on secondary SQL02
> ❌ The following files already exist:
>    C:\...\MSSQL\DATA\TestAG.mdf, C:\...\MSSQL\DATA\TestAG_log.ldf
> ```
> Automatic seeding은 "보조에 DB가 **없어야**" 새로 만드는데, 이미 있으니 막힘.
>
> **원인**: 이전 AG 마법사 시도(취소한 것)가 **Automatic seeding을 일부 시작**해서 SQL02에 TestAG를 만들어버림. 마법사를 취소/재시작하면서 SQL02의 잔재가 남음.
>
> **해결 — 2단계**:
> 먼저 SQL02의 DB를 삭제(SQL02에 연결된 쿼리 창에서!):
> ```sql
> USE master;
> IF DB_ID('TestAG') IS NOT NULL
> BEGIN
>     ALTER DATABASE TestAG SET OFFLINE WITH ROLLBACK IMMEDIATE;
>     DROP DATABASE TestAG;
> END
> ```
> 그런데 **DROP DATABASE가 물리 파일까지는 안 지우는 경우**가 있음(특히 OFFLINE 후 DROP). Validation이 여전히 "파일이 존재한다"고 막으면, 파일을 직접 삭제해야 함. SQL01 PowerShell에서 WinRM으로 원격 삭제:
> ```powershell
> Invoke-Command -ComputerName SQL02 -ScriptBlock {
>     $data = "C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\DATA"
>     Remove-Item "$data\TestAG.mdf" -Force -ErrorAction SilentlyContinue
>     Remove-Item "$data\TestAG_log.ldf" -Force -ErrorAction SilentlyContinue
>     Get-ChildItem $data -Filter "TestAG*"   # 결과 비어있으면 성공
> }
> ```
> 삭제 후 마법사에서 **Re-run Validation** → Error가 Success로 바뀜 → Next → Finish.
>
> **핵심 교훈**: **논리적 DB 삭제(DROP) ≠ 물리 파일 삭제**. "DB를 지웠는데 왜 재생성이 안 되지?" 같은 상황에서는 물리 파일 잔재를 의심할 것.

---

## 9. Listener·조인·시딩 트러블슈팅 3연쇄

여기가 이 글의 핵심임. 마법사 Finish를 눌렀는데 **"The wizard finished with errors"**가 뜨면서, Listener 생성 실패가 연쇄적으로 두 개의 문제를 더 일으켰음. 하나씩 풀어감.

![마법사 Finish 결과 - Listener 생성 Error](/assets/images/26-07-07-dbcluster/05-wizard-finished-errors.png)
*그림 9-1. AG 본체는 성공했지만 Listener 생성이 Error, 이로 인해 "Joining secondaries"가 Skipped 처리됨*

Finish 결과를 자세히 보면 이런 상태였음.

```
✅ Creating availability group 'AG-TEST'          — 성공 (AG 본체는 생성됨)
✅ Waiting for AG to come online                  — 성공
❌ Creating Availability Group Listener 'AGLISTENER' — Error   ← 첫 번째 문제
⏭️ Joining secondaries to availability group      — Skipped   ← 여기서 파생
```

**중요**: AG-TEST 자체는 온라인으로 정상 생성됐고, 딱 **Listener 생성만** 실패한 것. 그런데 Listener 실패 때문에 마법사가 **SQL02를 AG에 조인하는 단계를 건너뜀**. 이게 나중에 시딩 실패로 이어짐.

### [트러블슈팅 #7] Listener 생성 실패 — CNO 권한 부족

**원인**: Listener를 만들려면 WSFC가 AD에 **VCO(Virtual Computer Object)** 라는 컴퓨터 개체(AGLISTENER)를 생성해야 하는데, 그 작업 주체인 **CNO(클러스터 이름 개체 SQLCLUSTER$)**가 AD에서 컴퓨터 개체를 만들 권한이 없어서 실패함. 이게 실무에서 만나는 **"Listener 연결 불가"** 문제의 대표 원인.

**해결**: DC에서 **VCO를 미리 생성**하고, 그 개체에 CNO가 Full Control을 갖도록 권한을 부여함.

```powershell
# DC(2022_DC01)에서 관리자 권한으로 실행

# 1. AGLISTENER 컴퓨터 개체를 미리 생성 (비활성 상태로)
New-ADComputer -Name "AGLISTENER" -Enabled $false `
    -Path "CN=Computers,DC=lab,DC=local"

# 2. 방금 만든 VCO에 CNO(SQLCLUSTER$)가 Full Control 갖도록 권한 부여
$vco = Get-ADComputer "AGLISTENER"
$cno = Get-ADComputer "SQLCLUSTER"
$acl = Get-Acl "AD:$($vco.DistinguishedName)"
$sid = New-Object System.Security.Principal.SecurityIdentifier $cno.SID
$ace = New-Object System.DirectoryServices.ActiveDirectoryAccessRule($sid, "GenericAll", "Allow")
$acl.AddAccessRule($ace)
Set-Acl "AD:$($vco.DistinguishedName)" $acl
```

> **주의**: `dsacls`로 위임하는 방법도 있는데(`dsacls ... /G 'LAB\SQLCLUSTER$:CC;computer'`), PowerShell에서는 `$` 문자를 변수로 해석해서 "The parameter is incorrect" 에러가 남. `$`를 포함한 계정명은 **작은따옴표**로 감싸야 함. 위의 New-ADComputer 방식이 더 확실함.

![DC에서 VCO 사전 생성 + CNO 권한 부여 (New-ADComputer / Set-Acl)](/assets/images/26-07-07-dbcluster/dc-vco-fix.png)
*DC에서 AGLISTENER 컴퓨터 개체를 미리 생성하고 CNO(SQLCLUSTER$)에 GenericAll 권한 부여*

VCO 생성 후, AG는 이미 있으니 **Listener만 T-SQL로 추가**함 (SQL01에서).

```sql
ALTER AVAILABILITY GROUP [AG-TEST]
ADD LISTENER N'AGLISTENER' (
    WITH IP ((N'10.0.0.224', N'255.255.255.0')),
    PORT = 1433
);
GO
```

미리 만든 VCO 방식에서는 WSFC가 새로 만드는 게 아니라 **이미 있는 AGLISTENER 개체를 사용**하므로, "개체 생성 권한 없음"을 우회함. 이번엔 `Commands completed successfully`.

![VCO 권한 부여 결과 검증 (Get-ADComputer / Get-Acl)](/assets/images/26-07-07-dbcluster/dc-vco-verify.png)
*AGLISTENER 개체 Enabled 상태 + CNO 권한이 부여됐는지 검증*

![Listener ONLINE 확인](/assets/images/26-07-07-dbcluster/06-listener-online.png)
*그림 9-2. AGLISTENER / 1433 / 10.0.0.224 / ONLINE — Listener 생성 성공*

### [트러블슈팅 #8] 보조 복제본이 AG에 조인 안 됨

Listener는 살렸지만, 아까 마법사에서 **"Joining secondaries" 단계가 Skipped**됐기 때문에 SQL02가 여전히 AG에 조인되지 않은 상태였음. 그래서 SQL02에서 AG 관련 명령을 실행하면 이런 에러가 남.

```
Msg 15151: Cannot alter the availability group 'AG-TEST',
because it does not exist or you do not have permission.
```

**원인**: SQL02 입장에서 AG-TEST가 안 보임 = 조인이 안 됨. 확인 방법:

```sql
-- SQL02 연결 창에서
SELECT name FROM sys.availability_groups;   -- 비어있으면 조인 안 된 것
```

**해결**: SQL02를 AG에 수동으로 조인시킴. **반드시 SQL02에 연결된 창에서** 실행.

```sql
-- ① SQL02(보조)에서 — AG 조인
ALTER AVAILABILITY GROUP [AG-TEST] JOIN;
GO

-- ② SQL02(보조)에서 — 시딩 권한 부여 (조인 후에 실행돼야 먹힘)
ALTER AVAILABILITY GROUP [AG-TEST] GRANT CREATE ANY DATABASE;
GO
```

> **핵심 순서**: 반드시 **JOIN 먼저 → 그다음 GRANT**. 순서가 바뀌면 "AG does not exist"가 남. JOIN이 안 된 상태에서는 GRANT도 실행이 안 됨.

### [트러블슈팅 #9] Automatic seeding "Request Denied"

조인 후 시딩 상태를 봤더니 계속 실패하고 있었음.

```sql
SELECT ar.replica_server_name, has.current_state, has.failure_state_desc
FROM sys.dm_hadr_automatic_seeding has
JOIN sys.availability_replicas ar ON has.ag_remote_replica_id = ar.replica_id
ORDER BY has.start_time DESC;
```

결과:
```
replica_server_name   current_state   failure_state_desc
SQL02                 FAILED          Request Denied
SQL02                 FAILED          Request Denied
...
```

**원인**: `Request Denied` = 주 복제본이 SQL02에 DB를 만들려는 시딩 요청이 **거부됨**. 원인은 **SQL02에 `GRANT CREATE ANY DATABASE`가 안 걸려서**임. 앞서 조인이 안 된 상태에서 GRANT를 시도해 실패했던 게 여기서 드러난 것.

**해결**: #8에서 JOIN을 완료한 뒤 **SQL02에서 GRANT CREATE ANY DATABASE를 다시 실행**하고, SQL01에서 시딩 모드를 재설정해 시딩을 다시 트리거함.

```sql
-- SQL02(보조)에서 — 시딩 권한 (조인 완료 후이므로 이번엔 성공)
ALTER AVAILABILITY GROUP [AG-TEST] GRANT CREATE ANY DATABASE;
GO
```
```sql
-- SQL01(주)에서 — 시딩 모드 재설정으로 재시도 트리거
ALTER AVAILABILITY GROUP [AG-TEST]
MODIFY REPLICA ON N'SQL02' WITH (SEEDING_MODE = AUTOMATIC);
GO
```

그 후 시딩 상태를 다시 확인하니 성공.

```
replica_server_name   current_state   failure_state_desc
SQL02                 COMPLETED       NULL           ← 성공!
SQL02                 FAILED          Request Denied  (이전 시도들)
```

![시딩 COMPLETED 확인](/assets/images/26-07-07-dbcluster/07-seeding-completed.png)
*그림 9-3. 가장 최근 시딩이 COMPLETED / failure_state_desc = NULL — TestAG가 SQL02로 완전히 복제됨*

> **오늘 가장 크게 데인 부분 — 쿼리를 어느 서버에서 날리는가**
>
> 이 3연쇄 트러블슈팅에서 가장 많이 헤맨 원인이 사실 이거였음. `MODIFY REPLICA`는 **주(SQL01)에서만**, `JOIN`과 `GRANT CREATE ANY DATABASE`는 **보조(SQL02)에서만** 실행돼야 하는데, SSMS 탭이 여러 개 열려 있으니 **엉뚱한 서버에 연결된 창에서 명령을 날려** "AG does not exist" 에러가 반복됐음.
>
> **습관화할 것**: AG 관련 명령 실행 전에 항상 `SELECT @@SERVERNAME;`으로 현재 창의 서버를 확인. Object Explorer에서 원하는 서버 노드를 클릭하고 New Query를 열면 그 서버에 연결된 창이 생김.
>
> | 명령 | 실행 서버 |
> |---|---|
> | `CREATE/ALTER AVAILABILITY GROUP ... (생성/구조 변경)` | 주 (SQL01) |
> | `MODIFY REPLICA` | 주 (SQL01) |
> | `ADD LISTENER` | 주 (SQL01) |
> | `JOIN` | 보조 (SQL02) |
> | `GRANT CREATE ANY DATABASE` | 보조 (SQL02) |

---

## 10. AG 동작 검증

모든 조치 후 최종 상태 확인.

**Listener 상태** (SQL01에서)

```sql
SELECT agl.dns_name, agl.port, agla.ip_address, agla.state_desc
FROM sys.availability_group_listeners agl
CROSS APPLY sys.availability_group_listener_ip_addresses agla;
```
결과: `AGLISTENER / 1433 / 10.0.0.224 / ONLINE`

**AG 전체 상태 + 장애조치 모드** (SQL01에서)

```sql
SELECT
    ag.name AS AG명,
    ar.replica_server_name AS 복제본,
    ars.role_desc AS 역할,
    ars.synchronization_health_desc AS 건강도,
    ar.failover_mode_desc AS 장애조치모드,
    ar.availability_mode_desc AS 가용성모드
FROM sys.availability_groups ag
JOIN sys.availability_replicas ar ON ag.group_id = ar.group_id
JOIN sys.dm_hadr_availability_replica_states ars ON ar.replica_id = ars.replica_id;
```
결과: SQL01=PRIMARY / HEALTHY, SQL02=SECONDARY / HEALTHY, 둘 다 AUTOMATIC + SYNCHRONOUS_COMMIT.

**Listener 실제 접속 테스트**

```powershell
Invoke-Sqlcmd -ServerInstance "AGLISTENER" -Query "SELECT @@SERVERNAME AS ConnectedNode"
```
→ 현재는 **SQL01**(주 복제본) 반환. "앱이 Listener로 접속 → 주 노드 연결"이 검증됨.

### 다음 단계: 장애조치 3종 검증

이 랩의 최종 목표는 아래 3종 검증임 (다음 포스트에서 진행 예정).

1. **수동 장애조치** — SSMS에서 SQL02로 failover → 역할이 뒤바뀌는지
2. **자동 장애조치** — SQL01 강제 종료 → SQL02가 자동 승격되는지
3. **Listener 접속 유지** — 장애조치 전후로 Listener(.224) 접속이 유지되고 FailoverTest 데이터가 그대로인지

---

## 11. 오늘 만난 트러블슈팅 총정리

구축 과정에서 만난 9개 오류를 한 표로 정리함. 전부 실무에서 만날 법한 전형적 패턴이라, 실제 운영 대응에도 그대로 쓰일 것.

| # | 단계 | 증상 | 원인 | 핵심 해결 |
|---|---|---|---|---|
| 1 | 설치 | SQL 서비스 시작 안 됨 (`FCB::Open failed`, `OS error 3`, `%%945`) | 설치 취소로 model DB가 빌드 경로(`D:\dbs\...`)에 남음 | 취소 없이 클린 재설치. SqlEngineConfigAction 단계 절대 취소 금지 |
| 2 | 방화벽 | 원격 접속만 실패 (`error: 40`, Access denied) | 방화벽이 1433 차단 | 양 노드에 1433/5022 방화벽 개방 |
| 3 | 활성화 | `Invoke-Sqlcmd` 파라미터 오류 | 옛 SQLPS 모듈 로드 (SqlServer 모듈 미설치) | `-TrustServerCertificate` 제거 또는 SqlServer 모듈 설치 |
| 4 | SSMS | 연결 시 인증서 오류 | SSMS 20+ Encrypt 기본 Mandatory | Trust Server Certificate 체크 |
| 5 | DB 준비 | 백업 실패 (`OS error 3`) | 백업 경로가 SQL 서비스 계정 기준으로 없음 | 기본 백업 폴더(`...\MSSQL\Backup\`) 사용 |
| 6 | AG 마법사 | Validation Error (DB/파일 이미 존재) | 취소된 seeding 잔재가 SQL02에 남음 | DB DROP + 물리 파일 직접 삭제 후 Re-run |
| 7 | Listener | Listener 생성 실패 (wizard finished with errors) | CNO가 AD에서 VCO 생성 권한 없음 | DC에서 VCO 미리 생성 + CNO에 GenericAll 부여 후 ADD LISTENER |
| 8 | 조인 | SQL02에서 `AG does not exist` | Listener 실패로 보조 조인이 Skipped됨 | SQL02에서 `ALTER AVAILABILITY GROUP JOIN` |
| 9 | 시딩 | Automatic seeding `Request Denied` | 보조에 `GRANT CREATE ANY DATABASE` 누락 | JOIN 후 SQL02에서 GRANT → SQL01에서 SEEDING_MODE 재설정 |

### 오늘 얻은 진단 시그니처

- `OS error 3` = **경로 없음**, `OS error 5` = **권한 없음**
- `error: 40` + 로컬만 됨 → **방화벽/원격 접속 설정**
- `FCB::Open failed` + model 경로 이상 → **설치 중단 잔재**
- **논리 삭제(DROP) ≠ 물리 파일 삭제**
- Listener 생성 실패 → **CNO의 VCO 생성 권한** 의심
- `Request Denied` (시딩) → 보조의 **GRANT CREATE ANY DATABASE** 확인
- AG 명령 실행 전 **`SELECT @@SERVERNAME;`으로 서버 확인** (주/보조 구분)
- 설정 변경 후 SSMS는 **F5 새로고침**

---

## 마치며

IAM 엔지니어 입장에서 SQL Server AG는 낯선 영역이었지만, 막상 직접 구축해보니 **결국 AD/DNS/WSFC/서비스 계정/방화벽 같은 인프라 기반 위에 얹힌 것**이라 완전히 새로운 건 아니었음. 오히려 Listener 문제의 핵심(트러블슈팅 #7)이 **AD의 CNO 권한 문제**였다는 점에서, IAM/AD 배경이 진단에 직접적으로 유리했음.

무엇보다 **설치 로그와 이벤트 로그의 에러 코드로 원인을 역추적하고, 논리와 물리를 구분하고, 명령을 올바른 서버에서 실행하는** 진단 습관이 이번 랩에서 몸에 붙었음. 특히 마지막에 시딩이 안 되던 이유가 "쿼리를 엉뚱한 서버에서 날려서"였다는 걸 스스로 깨달았을 때, AG 운영에서 주/보조 컨텍스트가 얼마나 중요한지 체감했음.

이 아홉 개의 벽은 문서만 읽었으면 절대 몸에 안 붙었을 것들임. 다음은 **장애조치 3종 검증**을 진행하고, 그 결과를 별도 포스트로 남길 예정임.