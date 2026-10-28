---
layout: single
title: "M365·Azure 테넌트 위험 항목 조치 — 감사 로그, 공유·외부 협업, 조건부 액세스, PIM 전환"
excerpt: "준비 상태 점검에서 위험으로 판정된 항목을 실제로 조치했다. 비용이 들지 않는 설정 변경 10건을 먼저 처리하고, 조건부 액세스 3개를 보고서 전용으로 만들어 What If로 검증한 뒤 보안 기본값과 교체했다. 관리 계정의 전역 관리자는 PIM 적격으로 전환했다. 포털에서 켠 감사 로그가 반영되지 않아 PowerShell로 다시 적용한 일, PIM이 본인 할당 제거를 막는 동작, CA 저장 시 현재 사용자가 제외 대상에 자동으로 들어간 일까지 변경 이력과 함께 정리했다."
date: 2026-10-28
categories: ["IAM", "Entra ID·M365"]
permalink: "/iam/m365-readiness-remediation/"
tags: [M365, E5, Entra, PIM, ConditionalAccess, Purview, Teams, SharePoint, Sandbox, 변경관리, 실측]
---

[지난 글](/iam/m365-azure-readiness-82/)에서 E5 샌드박스 테넌트를 체크리스트로 점검했고, 위험 판정이 41건 나왔다. 이번 글은 그중 일부를 실제로 조치한 기록이다.

조치는 세 묶음으로 나눴다.

| 묶음 | 기준 | 진행 |
|---|---|---|
| A. 저위험·무과금 | 설정만 바꾸면 되고 되돌리기 쉬운 항목 | 10건 진행 |
| B. 권한·인증 | 잘못하면 로그인이 막힐 수 있는 항목 | 진행(일부 보류) |
| C. 비용 발생 가능 | 진단 설정 → Log Analytics 등 | 보류 |

모든 변경은 같은 순서를 따랐다.

1. 변경 전 화면을 캡처한다.
2. 설정을 바꾼다.
3. 변경 후 화면을 다시 조회해서 캡처한다.
4. 변경 이력에 시각, 대상, 변경 전·후 값, 수행자, 근거 캡처, 검증 결과, 원복 방법을 남긴다.

마스킹 표기: 테넌트 이름, 사용자 UPN, 개체 ID, 요청 ID, IP 주소는 이미지에서 검은 박스로 처리했다. 본문에서 관리 계정은 `admin@<tenant>`, 외부 게스트 관리자는 "게스트 관리자"로 쓴다. 비상 접근 계정 `breakglass01`은 [이전 글](/iam/sandbox-break/)에서 만든 실습용 계정이라 그대로 뒀다.

## 1. Purview 감사 로그 — 포털에서 켰는데 반영되지 않았다

지난 점검에서 1순위로 꼽은 항목이다(지난 글 x69). 감사 로그는 켠 시점부터만 쌓이고 소급되지 않는다.

![감사 검색 — 기록 시작 버튼](/assets/images/m365-readiness-remediation/r-x31-01.jpg)

Purview → 감사 화면 상단에 **Start recording user and admin activity** 버튼이 있다. 누르면 조직 설정을 먼저 완료하라는 확인 창이 뜬다.

![조직 설정 확인 창](/assets/images/m365-readiness-remediation/r-x31-02.jpg)

이 창의 **Yes**는 내부적으로 `Enable-OrganizationCustomization`을 실행한다. 한 번 실행하면 되돌릴 수 없는 작업이라, 진행 전에 비용이 발생하는지 확인했다. 비용은 없고, Exchange Online 조직 개체에 사용자 지정 설정을 허용하는 플래그를 켜는 작업이다.

![기록 시작 후 감사 검색 화면](/assets/images/m365-readiness-remediation/r-x31-03.jpg)

버튼이 사라지고 검색 조건 입력란이 활성화됐다. 화면상으로는 조치가 끝난 것처럼 보인다.

그런데 1시간 반 뒤 Cloud Shell에서 조회해 보니 `UnifiedAuditLogIngestionEnabled`가 여전히 **False**였다. 안내된 반영 시간(최대 60분)을 넘긴 상태라 PowerShell로 다시 적용했다.

```powershell
Connect-ExchangeOnline -ShowBanner:$false
Get-AdminAuditLogConfig | Select UnifiedAuditLogIngestionEnabled   # False
Set-AdminAuditLogConfig -UnifiedAuditLogIngestionEnabled $true
# WARNING: ... could take up to 60 minutes to take effect.
```

12분 뒤 다시 조회했을 때 **True**로 바뀌었다.

![Cloud Shell에서 True 확인](/assets/images/m365-readiness-remediation/r-x31-04.jpg)

포털 화면만 보고 완료로 기록했다면 감사 로그가 꺼진 채로 남았을 것이다. 감사처럼 소급되지 않는 설정은 화면이 아니라 설정값을 조회해서 검증해야 한다.

## 2. 고객 Lockbox

![Lockbox 변경 전](/assets/images/m365-readiness-remediation/r-x30-01.jpg)

M365 관리 센터 → 설정 → 조직 설정 → 보안 및 개인 정보 → 고객 Lockbox. **모든 데이터 액세스 요청에 승인 필요**가 꺼져 있었다. E5에 포함된 기능이라 추가 비용이 없다.

![Lockbox 변경 후](/assets/images/m365-readiness-remediation/r-x30-02.jpg)

켜 두면 Microsoft 엔지니어가 지원 과정에서 고객 데이터에 접근해야 할 때 관리자 승인을 거친다. 승인 요청이 오지 않는 한 운영에 영향은 없다.

## 3. 관리자 동의 요청 워크플로

지난 글 x39 항목이다. 사용자가 관리자 동의가 필요한 앱을 만나면 요청할 경로가 없어, 그 자리에서 막히는 상태였다.

![관리자 동의 설정 변경 전](/assets/images/m365-readiness-remediation/r-x39-01.jpg)

![관리자 동의 설정 변경 후](/assets/images/m365-readiness-remediation/r-x39-02.jpg)

| 설정 | 변경 전 | 변경 후 |
|---|---|---|
| 관리자 동의 요청 | 아니요 | 예 |
| 검토자 | 없음 | 관리 계정 1명 |
| 요청 메일 알림 / 만료 알림 | 아니요 | 예 |
| 요청 만료 | 30일 | 30일 |

운영이라면 검토자는 개인이 아니라 그룹이나 역할로 지정하는 게 맞다. 샌드박스라 관리 계정 1명으로 뒀다.

## 4. 게스트 초대 범위

지난 글 x28 항목이다. 게스트를 포함한 조직 내 모든 사용자가 게스트를 초대할 수 있었다.

![외부 협업 설정 변경 전](/assets/images/m365-readiness-remediation/r-x28-01.jpg)

![외부 협업 설정 변경 후](/assets/images/m365-readiness-remediation/r-x28-02.jpg)

두 번째 옵션인 "특정 관리자 역할에 할당된 사용자와 멤버 사용자 권한이 있는 게스트만 초대할 수 있음"으로 바꿨다. 이제 게스트는 다른 게스트를 초대할 수 없다. 허용 도메인 목록은 이번 범위에 넣지 않았다.

## 5. Teams 외부 액세스 — 개인 계정 차단

![Teams 외부 액세스 변경 전](/assets/images/m365-readiness-remediation/r-x25-01.jpg)

Teams 관리 센터 → 외부 협업 → 외부 액세스에서 **People in my org can chat and have meetings with external users who have unmanaged Microsoft accounts**를 Off로 바꿨다. 개인 Microsoft 계정(Teams 무료, Skype 계정 등)과의 채팅·모임이 차단된다.

![Teams 외부 액세스 변경 후](/assets/images/m365-readiness-remediation/r-x25-02.jpg)

외부 도메인 **Allow all external domains**는 그대로 뒀다. 허용 목록 방식으로 바꾸려면 협업하는 도메인을 먼저 정리해야 하기 때문이다. 그래서 이 항목은 위험에서 주의로만 내려갔다.

## 6. Teams 모임 정책 — 익명 참가와 로비

![Global 모임 정책 변경 전](/assets/images/m365-readiness-remediation/r-x46-01.jpg)

Global(Org-wide default) 모임 정책의 **Meeting join & lobby** 영역에서 두 가지를 바꿨다.

![Global 모임 정책 변경 후](/assets/images/m365-readiness-remediation/r-x46-02.jpg)

| 설정 | 변경 전 | 변경 후 |
|---|---|---|
| Anonymous users can join a meeting unverified | On | Off |
| Who can bypass the lobby | People in my org and guests | People in my org |

익명 사용자는 이제 이메일 코드 인증(By email code)을 거쳐야 참가할 수 있고, 게스트는 로비에서 대기한다.

## 7. SharePoint·OneDrive 기본 공유 링크

지난 글 x26 항목이다. 공유 버튼을 누르면 기본값이 "링크가 있는 모든 사용자(편집)"였고, 그 링크에는 만료가 없었다.

![공유 기본값 변경 전](/assets/images/m365-readiness-remediation/r-x26-01.jpg)

![공유 기본값 변경 후](/assets/images/m365-readiness-remediation/r-x26-02.jpg)

| 설정 | 변경 전 | 변경 후 |
|---|---|---|
| 기본 링크 유형 | Anyone with the link | Specific people |
| 기본 권한 | Edit | View |
| Anyone 링크 만료 | 없음 | 30일 |

조직 수준의 외부 공유 범위(Anyone)는 바꾸지 않았다. 이 값을 낮추면 이미 나간 Anyone 링크가 모두 무효화되므로, 영향 범위를 먼저 확인해야 한다. 이번에는 기본값과 만료만 손봐서, 사용자가 의도하지 않게 Anyone 편집 링크를 만드는 경로를 막는 데까지만 했다.

## 8. OneDrive 보존 — 삭제된 사용자

![OneDrive 보존 변경 전](/assets/images/m365-readiness-remediation/r-x59-01.jpg)

SharePoint 관리 센터 → 설정 → OneDrive **Retention**. 사용자 계정을 삭제했을 때 OneDrive를 남겨 두는 기간이 기본값 30일이었다. 퇴사자 자료 인수인계가 30일 안에 끝나지 않는 경우가 많아 365일로 늘렸다.

![OneDrive 보존 변경 후](/assets/images/m365-readiness-remediation/r-x59-02.jpg)

## 9. 그룹 만료 정책 — Lab-03에만 적용

지난 글 x06 항목이다.

![그룹 만료 변경 전](/assets/images/m365-readiness-remediation/r-x06-01.jpg)

![그룹 만료 변경 후](/assets/images/m365-readiness-remediation/r-x06-02.jpg)

그룹 수명 180일, 소유자 없는 그룹의 알림 연락처는 관리 계정으로 지정했다. 적용 범위는 **모두**가 아니라 **선택됨 → Lab-03 1개**로 제한했다.

샌드박스의 샘플 팀들은 실제 활동이 없어서 갱신되지 않는다. 범위를 "모두"로 하면 180일 뒤 샘플 팀과 그 SharePoint 사이트가 함께 삭제된다. 삭제 후 30일 안에는 복원할 수 있지만, 실습 자료가 사라질 위험을 지는 이유가 없다. 그래서 정책 동작을 확인할 그룹 하나에만 걸었다. 이 항목도 판정은 주의로 남는다.

## 10. 보존 정책 2개 — Teams는 별도 정책이어야 한다

보존 정책이 하나도 없었다.

![보존 정책 없음](/assets/images/m365-readiness-remediation/r-x80-01.jpg)

처음에는 정책 하나에 모든 위치를 넣으려 했다. 그런데 마법사의 위치 선택 단계에서 Teams 채널 메시지나 Teams 채팅을 켜면 Exchange·SharePoint·OneDrive가 자동으로 꺼진다. Teams 위치는 다른 위치와 한 정책에 묶을 수 없다. 그래서 두 개로 나눴다.

![기본 보존 정책 검토](/assets/images/m365-readiness-remediation/r-x80-02.jpg)

![기본 보존 정책 생성 완료](/assets/images/m365-readiness-remediation/r-x80-03.jpg)

![Teams 보존 정책 검토](/assets/images/m365-readiness-remediation/r-x80-04.jpg)

![Teams 보존 정책 생성 완료](/assets/images/m365-readiness-remediation/r-x80-05.jpg)

| 정책 | 위치 | 설정 |
|---|---|---|
| Readiness-Retain-1Y | Exchange 사서함, SharePoint 사이트, OneDrive, M365 그룹 | 생성일 기준 1년 보존, 만료 시 조치 없음 |
| Readiness-Retain-1Y-Teams | Teams 채널 메시지, Teams 채팅 | 동일 |

**만료 시 조치 없음(Do nothing)**을 고른 이유는 이번 목적이 삭제가 아니라 보존이기 때문이다. 삭제 정책을 넣으면 1년이 지난 데이터가 자동으로 지워진다. 정책이 실제 위치에 적용되기까지는 최대 7일이 걸린다.

## 11. 조건부 액세스 — 보고서 전용, 검증, 교체

여기부터 배치 B다. 테넌트는 보안 기본값으로 MFA를 강제하고 있었고, 조건부 액세스(CA) 정책은 0개였다(지난 글 x19).

![CA 정책 없음](/assets/images/m365-readiness-remediation/r-ca-01.jpg)

### 정책 3개를 보고서 전용으로 생성

| 정책 | 대상 | 리소스 | 조건 | 제어 |
|---|---|---|---|---|
| CA01-Require MFA for admins | 관리 역할 14개 | 모든 리소스 | — | MFA 필요 |
| CA02-Block legacy authentication | 모든 사용자 | 모든 리소스 | 클라이언트 앱: Exchange ActiveSync, 기타 클라이언트 | 액세스 차단 |
| CA03-Require MFA for all users | 모든 사용자 | 모든 리소스 | — | MFA 필요 |

세 정책 모두 제외 대상은 `breakglass01` 하나다. CA01의 역할 14개는 전역, 권한 있는 역할, 보안, 사용자, Exchange, SharePoint, Teams, 조건부 액세스, 청구, 애플리케이션, 클라우드 애플리케이션, 기술 지원팀, 인증, 권한 있는 인증 관리자다.

![CA01 구성 화면](/assets/images/m365-readiness-remediation/r-ca-02.jpg)

![보고서 전용 정책 3개](/assets/images/m365-readiness-remediation/r-ca-03.jpg)

### 보고서 전용 결과가 로그에 남지 않았다

정책을 켜기 전에 로그인 로그의 **보고 전용** 탭에서 판정 결과를 보려고 했다. 정책을 만든 뒤에 발생한 로그인을 열었는데 결과가 **해당 없음**이었다.

![로그인 로그 보고 전용 탭 — 해당 없음](/assets/images/m365-readiness-remediation/r-ca-04.jpg)

관리 계정과 `breakglass01`의 로그인 모두 같은 결과였다. 보안 기본값이 켜져 있는 동안에는 CA 정책이 평가되지 않아, 보고서 전용 정책도 판정을 남기지 않는 것으로 보인다. 이 경우 보안 기본값에서 CA로 넘어가기 전에 보고서 전용 단계로 영향을 미리 볼 수 없다.

### What If로 대신 검증

대신 CA의 **가상(What If)** 도구로 계정별 적용 결과를 확인했다. 조건은 Windows, 브라우저, Exchange Online 접속이다.

![What If — 관리 계정](/assets/images/m365-readiness-remediation/r-ca-05.jpg)

관리 계정에는 CA01과 CA03이 적용된다. CA02는 레거시 클라이언트가 조건이라 브라우저 로그인에는 해당하지 않는다.

![What If — breakglass01](/assets/images/m365-readiness-remediation/r-ca-06.jpg)

`breakglass01`에는 적용되는 정책이 없다. 제외 설정이 의도대로 동작한다. 게스트 계정은 What If 대상으로 고를 수 없어서, MFA 등록 여부로 대신 확인했다(등록됨).

### 보안 기본값 해제와 정책 적용

보안 기본값과 CA는 동시에 쓸 수 없다. 보안 기본값을 먼저 끄고 곧바로 CA를 켰다. 두 작업 사이에는 MFA 강제가 없는 공백이 생기므로 이어서 처리해야 한다.

![보안 기본값 해제](/assets/images/m365-readiness-remediation/r-ca-07.jpg)

![CA 정책 3개 켬](/assets/images/m365-readiness-remediation/r-ca-08.jpg)

### 저장할 때 현재 사용자가 제외 대상에 들어갔다

정책을 켜고 저장하면 잠금 방지 경고가 나온다.

- 이 정책에서 현재 사용자를 제외합니다 **(기본 선택)**
- 내 계정이 이 정책의 영향을 받는다는 것을 이해합니다

기본값 그대로 저장하면 지금 로그인한 관리 계정이 그 정책의 제외 대상에 추가된다. CA01과 CA02를 이렇게 저장해서 제외 대상이 2명이 됐다. 관리 계정이 관리자 MFA 정책과 레거시 인증 차단에서 빠진 상태다.

정책 세부 정보의 **제외된 ID**가 "사용자 2명"으로 나오는 것을 보고 발견했다. 두 정책에서 관리 계정을 제외 목록에서 뺐다.

![CA01 제외 1명](/assets/images/m365-readiness-remediation/r-ca-09.jpg)

![CA02 제외 1명](/assets/images/m365-readiness-remediation/r-ca-10.jpg)

이 경고는 정책을 만들 때뿐 아니라 상태를 바꿔 저장할 때마다 다시 나온다. CA를 수정한 뒤에는 제외된 ID 개수를 확인하는 것을 습관으로 들여야 한다.

## 12. 전역 관리자 PIM 적격 전환

관리 계정이 전역 관리자 **영구 활성** 상태였다(지난 글 x01).

![PIM 활성 할당 3건](/assets/images/m365-readiness-remediation/r-x01-01.jpg)

### 적격 할당 추가

먼저 관리 계정에 전역 관리자 **영구 적격** 할당을 추가했다. 순서가 반대면 활성 할당을 지우는 순간 적격 할당을 추가할 권한도 같이 사라진다.

![적격 할당 추가](/assets/images/m365-readiness-remediation/r-x01-02.jpg)

### 본인 활성 할당은 본인이 지울 수 없다

이어서 같은 계정으로 활성 할당을 제거하려 하자 PIM이 막았다.

```
역할 할당을 제거하지 못함
You cannot update self assignment for this role. Use another administrator
account or have another administrator update your assignment.
```

![본인 할당 제거 차단](/assets/images/m365-readiness-remediation/r-x01-03.jpg)

관리자가 실수로 자기 권한을 지워 테넌트에서 잠기는 것을 막는 동작이다. 다른 전역 관리자로 해야 해서 `breakglass01`로 별도 브라우저 창(InPrivate)에서 로그인해 제거했다. 비상 계정 로그인이 실제로 되는지 확인하는 기회도 됐다.

![활성 할당 2건](/assets/images/m365-readiness-remediation/r-x01-04.jpg)

이제 관리 계정은 관리 작업 전에 PIM → 내 역할에서 전역 관리자를 활성화한다. 활성화 시간은 작업 예상 시간에 맞춰 4시간으로 잡았다.

![GA 활성화](/assets/images/m365-readiness-remediation/r-x01-05.jpg)

게스트 관리자의 전역 관리자 활성 할당(지난 글 2순위)은 이번에 회수하지 않고 보류했다. 그래서 x01은 여전히 주의다.

## 13. 결과

| 판정 | 조치 전 (10/26) | 조치 후 (10/28) |
|---|---|---|
| 위험 | 41 | 29 |
| 주의 | 7 | 11 |
| 정상 | 18 | 27 |
| 측정 불가 | 16 | 15 |

조치한 항목은 16개다. 그중 9개가 위험·측정 불가에서 정상으로 바뀌었다. 감사 로그, Lockbox, 관리자 동의, 게스트 초대, 모임 정책, 기본 공유 링크, OneDrive 보존, 보존 정책, CA 제외 대상이다. 원래 정상이던 CA 보고 전용 정책 수 항목은 정상을 유지했다.

나머지 6개는 주의로 남았다. 이유는 다음과 같다.

| 항목 | 남은 부분 |
|---|---|
| 전역 관리자 할당, 비상 계정 외 특권 계정 (x01 외 1건) | 게스트 관리자 회수 보류 |
| 그룹 만료 (x06) | 적용 범위가 Lab-03 하나 |
| CA 미적용 로그인 비율 (x19) | 정책을 켠 뒤 7일치 로그인 표본이 아직 없음 |
| Teams 외부 액세스 | 외부 도메인 전체 허용 유지 |
| SPO 외부 공유 범위 (x26) | 조직 수준 Anyone 유지 |

다음 확인 일정이 둘 있다.
- **11/4 이후:** 보존 정책이 위치에 실제로 적용됐는지, CA 미적용 로그인 비율 재측정
- **비상 계정 2개 운영:** 비상 계정이 하나뿐이라 점검표의 위험 판정이 그대로다. 두 번째 계정을 만들면 CA 3개 정책에 제외를 추가해야 한다.

## 정리 — 이번에 확인한 것

- **화면 완료가 설정 완료는 아니다.** 감사 로그는 포털에서 버튼이 사라졌는데도 1시간 반 동안 False였다. 소급되지 않는 설정은 PowerShell로 값을 조회해서 검증한다.
- **보안 기본값이 켜져 있으면 보고서 전용 CA가 평가되지 않는다.** 교체 전 영향 확인은 What If로 계정별로 한다.
- **CA 저장 시 잠금 방지 경고의 기본값은 "현재 사용자 제외"다.** 저장할 때마다 확인하고, 저장 후 제외된 ID 개수를 본다.
- **PIM은 본인 활성 할당 제거를 막는다.** 적격 할당을 먼저 추가하고, 활성 할당 제거는 다른 전역 관리자(비상 계정)로 한다.
- **Teams 보존은 별도 정책이다.** 한 정책에 다른 위치와 함께 넣을 수 없다.
- **그룹 만료는 범위부터 정한다.** "모두"로 걸면 갱신되지 않는 그룹이 180일 뒤 사이트와 함께 삭제된다.

변경 이력은 CSV 13행(배치 A 10건, 배치 B 3건)으로 남겼다. 각 행에 근거 캡처 파일명과 원복 방법이 함께 들어 있어, 운영 테넌트의 변경 관리 대장 양식으로 그대로 쓸 수 있다.
