---
layout: single
title: "[실무 검증] Microsoft Graph 인증서 기반 App-only 접속 구성"
excerpt: "M365·Azure 테넌트 점검 스크립트의 기반이 되는 Microsoft Graph App-only 접속을 구성했다. 위임 방식 대신 App-only를 고른 이유, 리디렉션 URI를 비워 둔 이유, 클라이언트 암호 대신 자체 서명 인증서를 쓴 이유를 정리하고, 점검 항목별로 분리한 Read 전용 애플리케이션 권한 7개에 관리자 동의를 부여한 뒤 Connect-MgGraph 접속과 기본 조회까지 검증했다."
date: 2026-10-20
categories: [IAM]
tags: [M365, Entra, Microsoft Graph, App-only, Certificate, PowerShell, 실측]
---

## 개요

M365·Azure 테넌트의 설정 현황을 스크립트로 점검하기 위해, Microsoft Graph에 인증서 기반 App-only 방식으로 접속하는 조회 전용 앱을 구성했다. 이후 작성하는 점검 스크립트는 모두 이 접속을 기반으로 실행한다.

- 환경: Microsoft 365 개발자 프로그램 Instant Sandbox(E5 + Azure, 동일 테넌트)
- 도구: Entra 관리 센터, Windows PowerShell 5.1(ISE), Microsoft.Graph 모듈
- 완료 기준: 앱 등록, 자체 서명 인증서로 App-only 접속, 기본 조회 성공

> 테넌트 ID, 클라이언트 ID, 인증서 지문, 테넌트 도메인, 계정명은 마스킹했다.

## 1. 접속 방식 선택: 왜 App-only인가

Graph PowerShell 접속 방식은 크게 두 가지다.

| 구분 | 위임(Delegated) | 애플리케이션(App-only) |
|---|---|---|
| 로그인 주체 | 사용자 | 앱(서비스 주체) |
| 유효 권한 | 앱 권한과 사용자 권한의 교집합 | 앱에 부여된 권한 |
| 대화형 로그인 | 필요(MFA 포함) | 불필요 |
| 적합한 용도 | 관리자가 직접 실행하는 일회성 작업 | 반복 실행, 예약 실행, 동일 결과 재현 |

App-only를 선택한 이유는 다음과 같다.

- 점검 스크립트는 같은 조건으로 반복 실행하고, 다른 사람이 실행해도 같은 결과가 나와야 한다. 실행하는 사람의 역할이나 로그인 상태에 따라 결과가 달라지면 점검 기준을 비교할 수 없다.
- 이전 작업에서 Windows PowerShell 5.1의 WAM 로그인 창 오류와 디바이스 코드 방식 거부를 겪었다. App-only는 대화형 로그인을 거치지 않으므로 이 문제가 발생하지 않는다.
- 운영 환경의 점검 자동화(예약 실행)도 결국 App-only로 구성된다. 검증 단계에서 같은 구조를 써 보는 것이 목적에 맞다.

## 2. 앱 등록

경로: Entra 관리 센터 → Entra ID → 앱 등록 → 새 등록

![앱 등록 메뉴에서 새 등록](/assets/images/2026-10-20-m365-graph-app-only/01-app-registration-menu.png)

| 항목 | 설정값 | 이유 |
|---|---|---|
| 이름 | readiness-audit-app | 용도가 드러나는 이름. 변경이력과 감사 로그에서 식별하기 위함 |
| 지원되는 계정 유형 | 단일 테넌트만 | 자기 테넌트만 조회하는 앱이다. 다중 테넌트로 열 이유가 없고, 열어 두면 다른 테넌트에서 이 앱에 동의할 수 있는 경로가 생긴다 |
| 리디렉션 URI | 입력하지 않음 | 아래 설명 |

![애플리케이션 등록 화면](/assets/images/2026-10-20-m365-graph-app-only/02-app-register-form.png)

### 리디렉션 URI(엔드포인트)를 등록하지 않은 이유

리디렉션 URI는 사용자가 브라우저에서 로그인한 뒤 인증 코드나 토큰을 돌려받을 주소다. 즉 사용자가 개입하는 흐름(인증 코드 흐름 등)에서만 필요하다.

App-only 접속은 OAuth 2.0 클라이언트 자격 증명 흐름을 사용한다. 이 흐름에서는 브라우저 이동이 없다. 스크립트가 토큰 엔드포인트에 직접 요청하고 응답으로 액세스 토큰을 받는다.

```
POST https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token
  client_id             = <client-id>
  scope                 = https://graph.microsoft.com/.default
  grant_type            = client_credentials
  client_assertion_type = urn:ietf:params:oauth:client-assertion-type:jwt-bearer
  client_assertion      = <개인 키로 서명한 JWT>
```

토큰 엔드포인트 주소는 테넌트 ID로 정해지는 고정 주소라서 앱에 따로 등록하지 않는다. 앱 등록 화면의 "엔드포인트" 메뉴는 이 주소들을 보여 주기만 하고, 설정하는 곳이 아니다. 사용하지 않는 리디렉션 URI를 등록해 두면 의도하지 않은 로그인 흐름이 열려 있는 상태가 되므로, 필요 없으면 비워 두는 것이 맞다.

## 3. 자격 증명: 왜 클라이언트 암호가 아니라 인증서인가

App-only 앱의 자격 증명은 클라이언트 암호(Secret)와 인증서 중 하나를 쓴다.

| 구분 | 클라이언트 암호 | 인증서 |
|---|---|---|
| 형태 | 문자열 | 공개 키(앱에 업로드) + 개인 키(로컬 보관) |
| 노출 경로 | 스크립트, 환경 변수, 히스토리에 문자열로 남기 쉬움 | 개인 키는 인증서 저장소 안에 있고 스크립트에는 지문만 들어감 |
| 토큰 요청 시 전달 | 암호 문자열 자체를 전송 | 개인 키로 서명한 assertion만 전송 |
| MS 권장 | 개발·테스트 용도 | 운영 환경 권장 |

스크립트를 블로그나 팀 문서에 공유할 때, 인증서 방식은 스크립트에 지문만 남으므로 지문을 마스킹해도 비밀 정보가 섞여 나갈 위험이 없다. 이것도 인증서를 고른 이유다.

### 인증서 생성

```powershell
$cert = New-SelfSignedCertificate -Subject "CN=readiness-audit-app" `
  -CertStoreLocation Cert:\CurrentUser\My `
  -KeyExportPolicy Exportable -KeySpec Signature `
  -KeyAlgorithm RSA -KeyLength 2048 -HashAlgorithm SHA256 `
  -NotAfter (Get-Date).AddMonths(6)

Export-Certificate -Cert $cert -FilePath "$HOME\readiness-audit-app.cer"
$cert | Select-Object Subject, Thumbprint, NotAfter, HasPrivateKey
```

![인증서 생성 실행 결과](/assets/images/2026-10-20-m365-graph-app-only/03-cert-create.png)

| 파라미터 | 값 | 이유 |
|---|---|---|
| Subject | CN=readiness-audit-app | 앱 이름과 맞춰 저장소에서 바로 찾을 수 있게 함 |
| CertStoreLocation | CurrentUser\My | 실행 사용자 범위로 한정. LocalMachine에 두면 해당 PC의 다른 관리자도 개인 키를 쓸 수 있음 |
| KeySpec | Signature | client assertion(JWT) 서명 용도 |
| KeyAlgorithm / KeyLength / Hash | RSA 2048 / SHA256 | Entra ID 인증서 자격 증명에서 일반적으로 쓰는 조합 |
| KeyExportPolicy | Exportable | 다른 실행 환경이나 PC 교체 시 .pfx로 옮길 수 있게 함. 대신 .pfx를 내보내면 암호를 걸고 별도로 보관해야 함 |
| NotAfter | 6개월 | 검증 기간에 맞춘 짧은 유효기간. 앱 인증서 만료 남은 일수 점검의 실측 대상으로도 사용 |

앱에는 공개 키(.cer)만 업로드한다. 개인 키는 PC 밖으로 나가지 않는다.

![내보낸 .cer 파일](/assets/images/2026-10-20-m365-graph-app-only/04-cert-cer-file.png)

```
Subject       : CN=readiness-audit-app
Thumbprint    : D0F6****************************4BC4
NotAfter      : 2027-04-20 오전 10:53:38
HasPrivateKey : True
```

`HasPrivateKey`가 True여야 한다. .cer만 가져온 인증서는 False로 표시되며, 이 경우 assertion에 서명할 수 없어서 접속이 실패한다.

### 확인하다 겪은 점

처음 인증서 저장소를 조회했을 때 `CN=<GUID>` 형식에 유효기간이 10년인 인증서가 하나 나왔다. Windows가 장치 등록이나 조직 계정 연결 과정에서 자동으로 만든 것으로 보이며, 이번 작업과는 관계가 없다. 저장소에 개인 키가 있는 인증서가 이미 있다는 이유만으로 작업이 끝났다고 판단하면 안 되고, Subject와 지문으로 대상을 정확히 확인해야 한다.

### 인증서 업로드

경로: 앱 → 인증서 및 암호 → 인증서 탭 → 인증서 업로드

앱 개요 화면의 "인증서 또는 비밀 추가" 링크로도 같은 화면에 들어갈 수 있다.

![앱 개요의 인증서 또는 비밀 추가](/assets/images/2026-10-20-m365-graph-app-only/05-app-add-credential.png)

업로드한 뒤 포털에 표시된 지문이 로컬 인증서 지문과 같은지 확인했다.

![업로드된 인증서 확인](/assets/images/2026-10-20-m365-graph-app-only/06-cert-uploaded.png)

## 4. API 권한

경로: 앱 → API 사용 권한 → 권한 추가 → Microsoft API 탭 → Microsoft Graph → 애플리케이션 사용 권한

권한을 추가하기 전 상태는 다음과 같다. 앱 등록 시 기본으로 들어간 위임 권한 `User.Read` 하나만 있다.

![권한 추가 전 기본 상태](/assets/images/2026-10-20-m365-graph-app-only/07-api-permissions-default.png)

권한 추가를 누르면 API 선택 화면이 열린다. Microsoft API 탭에서 Microsoft Graph를 고른다.

![Microsoft Graph 선택](/assets/images/2026-10-20-m365-graph-app-only/08-select-microsoft-graph.png)

권한 유형은 위임된 권한이 아니라 **애플리케이션 사용 권한**을 골라야 한다. App-only 접속에서 유효한 것은 애플리케이션 권한이다.

![애플리케이션 사용 권한 선택](/assets/images/2026-10-20-m365-graph-app-only/09-application-permission-type.png)

| 권한 | 유형 | 사용하는 점검 항목 |
|---|---|---|
| Organization.Read.All | 애플리케이션 | 테넌트 정보, SKU·서비스 플랜 |
| User.Read.All | 애플리케이션 | 사용자 목록, 비활성 Guest 비율 |
| Group.Read.All | 애플리케이션 | Owner 없는 그룹·Team, 그룹 만료 정책 |
| RoleManagement.Read.Directory | 애플리케이션 | 전역 관리자 수, 특권 역할 영구 할당 |
| Policy.Read.All | 애플리케이션 | 조건부 액세스 정책·예외, Guest 초대 설정 |
| Application.Read.All | 애플리케이션 | 앱 자격 증명 만료, Owner 없는 앱 등록 |
| AuditLog.Read.All | 애플리케이션 | 로그인 활동, 미사용 자격 증명, CA 미적용 로그인 |

일곱 개 권한을 하나씩 검색해 추가했다.

![Organization.Read.All 추가](/assets/images/2026-10-20-m365-graph-app-only/10-perm-organization.png)

![User.Read.All 추가](/assets/images/2026-10-20-m365-graph-app-only/11-perm-user.png)

![Group.Read.All 추가](/assets/images/2026-10-20-m365-graph-app-only/12-perm-group.png)

![RoleManagement.Read.Directory 추가](/assets/images/2026-10-20-m365-graph-app-only/13-perm-rolemanagement.png)

![Policy.Read.All 추가](/assets/images/2026-10-20-m365-graph-app-only/14-perm-policy.png)

![Application.Read.All 추가](/assets/images/2026-10-20-m365-graph-app-only/15-perm-application.png)

![AuditLog.Read.All 추가](/assets/images/2026-10-20-m365-graph-app-only/16-perm-auditlog.png)

권한 구성 원칙은 다음과 같다.

- 모두 `.Read` 권한만 부여했다. 이 앱의 역할은 조회와 판독이다. 위험 상태를 만드는 변경 작업은 관리자 계정으로 포털이나 대화형 세션에서 따로 수행한다. 조회 자격 증명과 변경 자격 증명을 분리해 두면, 인증서가 유출되더라도 테넌트 설정은 바뀌지 않는다.
- `Directory.Read.All` 하나로 대부분을 덮을 수도 있지만, 점검 항목별로 필요한 권한을 따로 부여했다. 점검 기준을 정리할 때 "이 항목을 보려면 어떤 권한이 필요한가"를 항목별로 적어 두기 위해서다. 운영 환경에 같은 앱을 요청할 때도 권한별로 근거를 댈 수 있다.
- 앱 등록 시 기본으로 들어가는 위임 권한 `User.Read`는 그대로 두었다. App-only 토큰에는 포함되지 않으므로 결과에 영향을 주지 않는다.
- 이 7개로 부족한 항목(예: PIM Schedule Instance 조회)이 있으면 실제 조회에서 확인한 뒤 추가한다. 필요할 것 같다는 이유로 미리 넣어 두지 않았다.

### 관리자 동의를 따로 해야 하는 이유

권한을 추가한 직후 상태 열에 주황색 경고와 함께 "허용되지 않음"이 표시된다. 애플리케이션 권한은 동의할 사용자가 없기 때문에 항상 관리자 동의가 필요하다. 권한 목록에 추가하는 것은 "이 앱이 이 권한을 요청한다"는 선언일 뿐이고, 실제 부여는 관리자 동의를 해야 이루어진다.

표 위의 "✓ <테넌트>에 대한 관리자 동의 허용"을 실행하면 상태가 "부여됨"으로 바뀐다. 이 버튼은 일반 버튼이 아니라 링크 형태로 표시되어 찾기 어려웠다. 권한 이름을 클릭하면 권한 상세 패널이 열리는데, 이 패널에는 동의 버튼이 없다.

![관리자 동의 후 부여됨 상태](/assets/images/2026-10-20-m365-graph-app-only/17-perm-granted.png)

## 5. 접속 및 기본 조회

```powershell
Disconnect-MgGraph -ErrorAction SilentlyContinue

Connect-MgGraph -ClientId "<client-id>" `
  -TenantId "<tenant-id>" `
  -CertificateThumbprint "<thumbprint>" -NoWelcome

Get-MgContext | Select-Object AuthType, AppName, TenantId
(Get-MgContext).Scopes | Sort-Object
```

```
AuthType AppName             TenantId
-------- -------             --------
 AppOnly readiness-audit-app ********-****-****-****-************

Application.Read.All
AuditLog.Read.All
Group.Read.All
Organization.Read.All
Policy.Read.All
RoleManagement.Read.Directory
User.Read.All
```

![App-only 접속 테스트](/assets/images/2026-10-20-m365-graph-app-only/18-connect-test.png)

`-TenantId`는 반드시 지정한다. 지정하지 않거나 잘못 지정하면 같은 PC에 로그인되어 있는 다른 테넌트로 접속할 수 있다.

판정 기준과 결과:

| 확인 항목 | 기준 | 결과 |
|---|---|---|
| AuthType | AppOnly | 통과 |
| AppName | readiness-audit-app | 통과 |
| TenantId | Sandbox 테넌트 | 통과 |
| Scopes | 동의한 Application 권한 7개 모두 표시, User.Read 미표시 | 통과 |

`Scopes`는 토큰에 실제로 들어간 역할(roles 클레임)을 보여 준다. 포털에서 권한을 추가했어도 관리자 동의를 하지 않았다면 여기에 나타나지 않는다. 포털 화면보다 이 출력이 실제 상태에 가깝다.

### 기본 조회

```powershell
Get-MgOrganization  | Format-Table DisplayName
Get-MgUser -Top 5   | Format-Table DisplayName, UserPrincipalName
Get-MgSubscribedSku | Format-Table SkuPartNumber, ConsumedUnits
Get-MgDirectoryRole | Format-Table DisplayName
```

```
SkuPartNumber       ConsumedUnits
-------------       -------------
DEVELOPERPACK_V2_E5            17
AAD_PREMIUM_P2                  0

DisplayName
-----------
Directory Readers
Global Administrator
Billing Administrator
```

![기본 조회 결과](/assets/images/2026-10-20-m365-graph-app-only/19-basic-query.png)

네 개 모두 결과가 나와 접속 구성이 완료됐다.

처음에는 `Select-Object`만 써서 네 명령을 한 번에 실행했는데, 첫 번째 결과 외에는 화면에 제대로 출력되지 않았다. PowerShell은 한 번에 출력되는 여러 객체를 첫 번째 객체의 형식에 맞춰 표시하기 때문이다. 명령마다 `Format-Table`을 붙여 따로 출력했다.

## 6. 조회 결과에서 확인한 점

- `Get-MgDirectoryRole`은 테넌트에서 한 번이라도 할당되어 활성화된 역할만 반환한다. 위 결과의 3개는 테넌트의 전체 역할 목록이 아니며, 역할 할당 현황을 판독하는 데 쓸 수 없다. 전역 관리자 수와 특권 역할 영구 할당은 roleManagement API(Assignment/Eligibility Schedule Instance)로 조회해야 한다.
- SKU 목록에 `AAD_PREMIUM_P2`가 별도로 있지만 할당 수는 0이다. E5에 Entra ID P2 서비스 플랜이 이미 포함되어 있으므로 PIM과 Access Review 검증에는 영향이 없다. 별도 SKU가 존재하는 이유는 확인하지 못했다.

## 7. 정리

| 결정 | 이유 |
|---|---|
| App-only | 실행자와 관계없이 같은 결과를 내야 하고, 대화형 로그인 문제를 피하기 위함 |
| 단일 테넌트 | 자기 테넌트 전용 조회 앱 |
| 리디렉션 URI 없음 | 클라이언트 자격 증명 흐름은 브라우저 리디렉션을 쓰지 않음 |
| 인증서 자격 증명 | 비밀 문자열이 스크립트에 남지 않음, MS 운영 권장 |
| 유효기간 6개월 | 검증 기간에 맞춘 짧은 기간, 인증서 만료 점검의 실측 대상 |
| Read 권한만, 항목별 분리 | 조회와 변경 자격 증명 분리, 항목별 필요 권한을 근거로 남김 |
| 관리자 동의 | 애플리케이션 권한은 관리자 동의를 해야 부여됨 |

다음 글에서는 이 접속으로 역할 할당 기준선을 조회한 뒤, 전역 관리자 과다나 영구 할당 같은 위험 상태를 직접 만들어 점검 기준대로 잡히는지 확인한다.
