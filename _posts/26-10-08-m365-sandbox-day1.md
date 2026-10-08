---
layout: single
title: "M365 E5 개발자 샌드박스 환경 점검 — 서비스 플랜·Azure 구독 조회와 PowerShell 로그인 트러블슈팅"
excerpt: "E5 인스턴트 샌드박스를 만든 뒤 실습 전에 환경을 점검했다. 관리자 MFA, 서비스 플랜, Azure 구독, PowerShell 모듈, 예산 경보 다섯 항목. 조회 과정에서 Windows PowerShell 5.1의 로그인 문제 — WAM 창 핸들 오류, 디바이스 코드 접근 거부, AADSTS50197, 어셈블리 버전 충돌 — 를 연달아 만났고, 서비스 플랜은 Graph Explorer로 대체 조회한 뒤 PowerShell 7로 옮겨서 해결했다. 지출 한도 없는 Azure Plan 구독이라 예산 경보까지 걸어 둔 기록이다."
date: 2026-10-08
categories: [IAM]
tags: [M365, E5, Sandbox, Graph, Azure, PowerShell, WAM, 실측]
---

M365 E5 개발자 샌드박스(Instant sandbox)를 만든 뒤, 실습 전에 환경을 점검한 기록이다. 점검 항목은 관리자 MFA, 서비스 플랜, 같은 테넌트의 Azure 구독, PowerShell 모듈, 예산 경보 다섯 가지다. 조회 과정에서 Windows PowerShell 5.1의 로그인 문제를 여러 번 만났고, PowerShell 7로 옮겨서 해결했다.

샌드박스 생성 과정에서 겪은 결제 계정 문제는 별도 글로 정리했다.

## 점검 결과 요약

| 항목 | 결과 | 확인 방법 |
| --- | --- | --- |
| 관리자 MFA | Microsoft Authenticator 등록 | My Sign-ins 보안 정보 |
| 라이선스 | DEVELOPERPACK_V2_E5 25개 중 17개 사용, AAD_PREMIUM_P2 단독 1개 | Graph `subscribedSkus` |
| 서비스 플랜 | Teams, Entra ID P1/P2, Purview 계열 모두 Success | Graph `subscribedSkus` |
| Azure 구독 | 샌드박스 테넌트에 1개 자동 생성, 역할 소유자 | 포털 / `Get-AzSubscription` |
| 구독 유형 | Microsoft Azure Plan, QuotaId `PayAsYouGo_2014-09-01` | `Get-AzSubscription` |
| 지출 한도 | Off | `Get-AzSubscription` |
| vCPU (Korea Central) | Total Regional vCPUs 0 / 10 | `Get-AzVMUsage` |
| 예산 경보 | 월 30,000원, 실제 50%·100%, 예측 100% | 포털 예산 |

![샌드박스 생성 완료](/assets/images/2026-10-08-m365-sandbox-day1/01-sandbox-ready.png)

## 1. 관리자 MFA 등록

샌드박스 관리자 계정으로 `https://mysignins.microsoft.com/security-info`에 접속해 Microsoft Authenticator를 등록했다. 회사 계정 세션과 섞이지 않도록 InPrivate 창을 사용했다.

![관리자 MFA 등록](/assets/images/2026-10-08-m365-sandbox-day1/02-mfa.png)

## 2. PowerShell 모듈 설치와 실행 정책

Microsoft.Graph, Az, MicrosoftTeams, SharePoint Online 모듈을 `-Scope CurrentUser`로 설치했다. 설치는 정상 완료됐지만 `Connect-MgGraph` 실행 시 모듈 로드 단계에서 실패했다.

```powershell
$PSVersionTable.PSVersion
Get-ExecutionPolicy -List
Import-Module Microsoft.Graph.Authentication
```

![실행 정책 Restricted로 모듈 로드 실패](/assets/images/2026-10-08-m365-sandbox-day1/03-restricted.png)

- 모든 범위의 실행 정책이 `Undefined`이면 Windows 클라이언트에서는 `Restricted`가 적용된다.
- `.psm1` 스크립트 모듈을 불러오지 못해 `PSSecurityException`이 발생한다.

현재 사용자 범위만 `RemoteSigned`로 변경했다. 관리자 권한은 필요 없다.

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
Get-ExecutionPolicy -List
```

![실행 정책 변경](/assets/images/2026-10-08-m365-sandbox-day1/04-execpolicy.png)

## 3. Connect-MgGraph 로그인 실패 (Windows PowerShell 5.1)

모듈 로드 문제를 해결한 뒤에도 로그인 단계에서 세 가지 오류가 이어졌다.

### 3-1. WAM 창 핸들 오류

```text
InteractiveBrowserCredential authentication failed: A window handle must be configured.
```

![WAM 오류](/assets/images/2026-10-08-m365-sandbox-day1/05-wam.png)

- Graph SDK 2.x는 Windows에서 기본적으로 WAM(Web Account Manager)으로 로그인 창을 띄운다.
- PowerShell ISE나 관리자 콘솔처럼 부모 창 핸들을 넘기지 못하는 환경에서 이 오류가 발생한다.
- `Set-MgGraphOption -DisableLoginByWAM $true`를 실행했지만, 같은 세션에서는 반영되지 않았다.

### 3-2. 디바이스 코드 로그인 후 접근 거부

`-UseDeviceCode`로 우회했다. 샌드박스 관리자 계정으로 로그인은 됐지만 마지막 단계에서 접근이 거부됐다.

![디바이스 코드 로그인 후 접근 거부](/assets/images/2026-10-08-m365-sandbox-day1/06-devicecode-denied.png)

디바이스 코드 흐름을 차단하는 조건부 액세스 정책이 원인일 가능성이 있다. 로그인 로그로는 아직 확인하지 못했다(미확인).

### 3-3. AADSTS50197

`Disconnect-MgGraph`로 세션을 정리하고 다시 연결했지만 같은 결과였다.

![AADSTS50197](/assets/images/2026-10-08-m365-sandbox-day1/07-aadsts50197.png)

- `AADSTS50197`은 지정한 테넌트에서 사용자를 찾지 못했다는 오류다.
- 로그인 창에 주소창이 없는 것으로 보아 여전히 내장 로그인 창이 사용됐다.
- 이 PC에 연결된 회사 계정이 자동으로 선택되면서, 샌드박스 테넌트에서 사용자를 찾지 못한 것으로 판단했다.

## 4. 서비스 플랜 조회 — Graph Explorer로 대체

PowerShell 문제는 따로 해결하기로 하고, 서비스 플랜 조회는 Graph Explorer로 진행했다.

1. InPrivate 창에서 Graph Explorer에 샌드박스 관리자 계정으로 로그인한다.
2. 앱 동의 화면에서 "조직 대신 동의"는 체크하지 않는다. 본인 계정에만 동의하면 충분하다.

   ![Graph Explorer 앱 동의](/assets/images/2026-10-08-m365-sandbox-day1/08-ge-consent.png)

3. `GET https://graph.microsoft.com/v1.0/subscribedSkus`를 실행하면 403 `Authorization_RequestDenied`가 반환된다.
4. Modify permissions 탭에서 `Organization.Read.All`에 동의한 뒤 다시 실행한다.

![Organization.Read.All 동의](/assets/images/2026-10-08-m365-sandbox-day1/09-ge-permission.png)

![subscribedSkus 조회 결과](/assets/images/2026-10-08-m365-sandbox-day1/10-ge-result.png)

### 조회 결과

| SKU | 할당 가능 | 사용 | 서비스 플랜 수 |
| --- | --- | --- | --- |
| DEVELOPERPACK_V2_E5 | 25 | 17 | 87 |
| AAD_PREMIUM_P2 | 1 | 0 | 5 |

- 사용 중인 17개는 가상 사용자 16명과 관리자 1명이다.
- Entra ID P2 단독 라이선스 1개가 별도로 포함되어 있다.

| 영역 | 서비스 플랜 |
| --- | --- |
| Teams | TEAMS1, MCOSTANDARD, MCOEV, MICROSOFT_TEAMS_EVENTS |
| Entra ID | AAD_PREMIUM, AAD_PREMIUM_P2, MFA_PREMIUM |
| Purview 정보 보호 | MIP_S_CLP1, MIP_S_CLP2, MIP_S_Exchange, RMS_S_ENTERPRISE, RMS_S_PREMIUM, RMS_S_PREMIUM2 |
| Purview 보존·DLP | INFO_GOVERNANCE, RECORDS_MANAGEMENT, COMMUNICATIONS_DLP, MICROSOFTENDPOINTDLP |
| Purview 감사·eDiscovery | M365_AUDIT_PLATFORM, M365_ADVANCED_AUDITING, EQUIVIO_ANALYTICS |
| Intune | INTUNE_A, INTUNE_P2 |
| Defender for Office 365 | ATP_ENTERPRISE, THREAT_INTELLIGENCE |

87개 중 `INTUNE_O365` 하나만 `PendingActivation`이고 나머지는 모두 `Success`다. 같은 SKU의 `INTUNE_A`가 Success라서 Intune 사용에는 영향이 없을 것으로 보이지만, 아직 확인하지 않았다.

## 5. Azure 구독 조회

### 포털 확인

샌드박스 테넌트에는 구독이 하나 자동으로 생성되어 있었다. 플랜은 "Azure 플랜"으로 표시되고, 부모 관리 그룹은 Tenant Root Group이다.

![샌드박스 구독 개요](/assets/images/2026-10-08-m365-sandbox-day1/11-sub-overview.png)

청구 속성을 보면 이 구독은 샌드박스를 만들 때 연결한 개인 결제 계정으로 청구된다. 결제 계정은 회사 테넌트에 있고 구독은 샌드박스 테넌트에 있는 구조다.

![샌드박스 구독 청구 속성](/assets/images/2026-10-08-m365-sandbox-day1/12-sub-billing.png)

### Microsoft.Compute 리소스 공급자 등록

사용량 및 할당량 화면이 비어 있었는데, `Microsoft.Compute` 공급자가 등록되지 않은 상태였기 때문이다. 공급자 등록 자체는 비용이 발생하지 않는다.

![등록 전 NotRegistered](/assets/images/2026-10-08-m365-sandbox-day1/13-compute-before.png)

![등록 후 Registered](/assets/images/2026-10-08-m365-sandbox-day1/14-compute-after.png)

포털 할당량 화면에는 VM 계열별 한도(범용 계열 0/10)만 보였고, 지역 전체 vCPU 행은 찾을 수 없었다. 지역 전체 한도는 PowerShell로 조회했다.

## 6. PowerShell 7로 전환

Windows PowerShell 5.1에서 `Connect-AzAccount`도 실패했다. WAM을 끄면 5.1의 Az는 구형 IE 기반 내장 창으로 로그인 화면을 띄우는데, 보안 정보 페이지에서 지원되지 않는 브라우저로 처리된다.

![Unsupported browser](/assets/images/2026-10-08-m365-sandbox-day1/15-unsupported.png)

같은 5.1 세션에서 `Get-AzVMUsage`를 실행했을 때는 어셈블리 로드 오류도 발생했다.

```text
'Azure.Core, Version=1.51.1.0, ...' 어셈블리에서
'Azure.Identity.SharedTokenCacheCredentialOptions' 형식을 로드할 수 없습니다.
```

같은 세션에서 Graph 모듈이 먼저 로드한 Azure.Core/Azure.Identity 버전과 Az가 요구하는 버전이 맞지 않아 생긴 것으로 판단했다. .NET Framework 기반인 5.1에서는 한 세션에 같은 어셈블리의 다른 버전을 함께 올릴 수 없다.

### 정리

- PowerShell ISE는 Windows PowerShell 5.1 전용이다. PowerShell 7을 설치해도 ISE 안에서는 5.1로 실행된다.
- PowerShell 7의 사용자 모듈 경로(`Documents\PowerShell\Modules`)는 5.1(`Documents\WindowsPowerShell\Modules`)과 다르다. 그래서 PS7에서 모듈을 다시 설치해야 한다.
- Graph 작업과 Az 작업은 서로 다른 창에서 실행한다.

```powershell
winget install --id Microsoft.PowerShell --source winget
```

```powershell
# PowerShell 7 (pwsh), 일반 권한
Install-Module Az -Scope CurrentUser -Force
Update-AzConfig -EnableLoginByWam $false
Connect-AzAccount -Tenant "<샌드박스 도메인>.onmicrosoft.com"

Get-AzSubscription | Select-Object Name, TenantId, State,
  @{n='QuotaId';e={$_.SubscriptionPolicies.QuotaId}},
  @{n='SpendingLimit';e={$_.SubscriptionPolicies.SpendingLimit}}

Get-AzVMUsage -Location koreacentral | Where-Object { $_.Name.Value -eq 'cores' } |
  Select-Object @{n='Name';e={$_.Name.LocalizedValue}}, CurrentValue, Limit
```

PS7에서는 시스템 브라우저로 로그인 화면이 열려 계정을 직접 선택할 수 있었다.

![PS7 조회 결과](/assets/images/2026-10-08-m365-sandbox-day1/16-ps7-result.png)

| 항목 | 값 |
| --- | --- |
| QuotaId | PayAsYouGo_2014-09-01 |
| SpendingLimit | Off |
| Total Regional vCPUs (Korea Central) | 0 / 10 |

지출 한도가 없으므로, 이 구독에서 리소스를 만들면 사용한 만큼 연결된 결제 수단으로 청구된다.

## 7. 예산 경보 설정

지출 한도가 없는 구독이라 예산 경보를 먼저 걸었다.

| 항목 | 값 |
| --- | --- |
| 범위 | 샌드박스 구독 |
| 이름 | budget-sandbox |
| 금액 | 월 30,000원 |
| 경고 | 실제 50% (15,000원), 실제 100% (30,000원), 예측 100% |

![예산 경고 설정](/assets/images/2026-10-08-m365-sandbox-day1/17-budget-alert.png)

![예산 생성 완료](/assets/images/2026-10-08-m365-sandbox-day1/18-budget-done.png)

- 받는 사람 이메일이 없으면 각 조건에 "작업 그룹 또는 하나 이상의 이메일 주소가 필요" 오류가 표시된다.
- 예산은 비용 데이터가 집계된 뒤에 평가되므로 수 시간 지연될 수 있다. 사용을 막는 장치가 아니라 알림 장치다.

## 남은 항목

- 디바이스 코드 로그인 접근 거부 원인: 로그인 로그와 조건부 액세스 정책 확인
- `INTUNE_O365` PendingActivation 영향 확인
- ~~비상 접근 계정 생성~~ → [별도 글로 정리했다](/iam/sandbox-break/)

## 참고

- [Set up a Microsoft 365 developer sandbox subscription - Microsoft Learn](https://learn.microsoft.com/en-us/office/developer-program/microsoft-365-developer-program-get-started)
