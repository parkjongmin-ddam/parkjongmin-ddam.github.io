---
layout: single
title: "M365·Azure 테넌트 위험 항목 조치 (2) — 협업 도메인 허용 목록, 구독 Owner PIM 전환, 그룹 라이선스"
excerpt: "지난 조치 후 남은 항목 중 비용이 들지 않는 것을 마저 처리했다. 외부 협업을 협력사 도메인 1개로 좁히면서 Teams·Entra 초대·SharePoint·테넌트 간 액세스 네 곳을 같은 기준으로 맞췄고, Azure 구독 Owner를 PIM 적격으로 바꿨다. 테넌트 간 기본 인바운드는 사용자만 막으면 저장이 거부되는 점, 같은 역할이 상시로 있으면 적격 활성화가 'already exists'로 실패하는 점, 활성화 직후에도 포털이 이전 토큰으로 권한 없음을 보여 주는 점을 확인했다. 위험 판정은 15건에서 10건으로 줄었다."
date: 2026-10-28
categories: ["IAM", "Entra ID·M365"]
permalink: "/iam/m365-readiness-remediation-2/"
tags: [M365, E5, Entra, PIM, AzureRBAC, B2B, CrossTenantAccess, Teams, SharePoint, Intune, 변경관리, 실측]
---

[지난 글](/iam/m365-readiness-remediation/)에서 위험 판정을 41건에서 15건으로 줄였다. 남은 항목 중 과금 없이 처리할 수 있는 것을 같은 날 오후에 마저 진행했다.

| 묶음 | 항목 | 내용 |
|---|---|---|
| 협업 도메인 허용 목록 | x25, x52, x53 | Teams 외부 액세스, Entra 게스트 초대, SharePoint 외부 공유, 테넌트 간 액세스 |
| 그룹 거버넌스 | x43 | 명명 정책 차단 단어 |
| 운영 기본값 | x66, x70, x72 | Windows 업데이트 링, 에이전트 사용자 범위, 그룹 기반 라이선스 |
| 특권 권한 | x82 | Azure 구독 Owner PIM 적격 전환 |
| 검토 기록 | x17, x76 | 메시지 센터, 서비스 상태 권고 |

작업 방식은 지난 글과 같다. 변경 전 캡처 → 변경 → 다시 조회해서 캡처 → 변경 이력 기록 순서다.

마스킹 표기: 테넌트 이름, 사용자 UPN, 개체 ID는 검은 박스로 처리했다. 본문에서 관리 계정은 `admin@<tenant>`, 허용한 협력사 도메인은 `partner.example`로 쓴다.

## 1. 협업 도메인 허용 목록 (x25·x52·x53)

지난 글에서 "협업 대상 도메인 미정"으로 남겨 둔 항목이다. 협력사 1개 도메인만 허용하기로 정했다. 이 테넌트에는 그 도메인의 게스트가 이미 1명 있어서, 조치 후에도 이 게스트가 계속 쓸 수 있어야 한다.

외부 협업 경로는 네 군데에서 따로 설정한다. 한 곳만 막으면 다른 경로로 들어온다.

| 경로 | 설정 위치 | 변경 전 | 변경 후 |
|---|---|---|---|
| Teams 채팅·모임 | Teams 관리 센터 → 외부 액세스 | 모든 외부 도메인 허용 | `partner.example`만 허용 |
| 게스트 초대 | Entra → 외부 협업 설정 → 협업 제한 | 모든 도메인 초대 허용 | `partner.example`만 허용 |
| 파일·사이트 공유 | SharePoint 관리 센터 → 공유 | 도메인 제한 없음 | `partner.example`만 허용 |
| Entra 테넌트 B2B 인바운드 | Entra → 테넌트 간 액세스 설정 | 기본값 모두 허용 | 기본값 차단, 협력사 테넌트만 허용 |

### Entra 게스트 초대 (x52)

![외부 협업 설정 — 변경 전 협업 제한](/assets/images/m365-readiness-remediation-2/r-g-x52-01.jpg)

협업 제한을 **지정된 도메인으로의 초대만 허용(가장 제한적)**으로 바꾸고 대상 도메인을 넣었다.

![외부 협업 설정 — 변경 후](/assets/images/m365-readiness-remediation-2/r-g-x52-02.jpg)

이 설정은 초대를 보내는 시점에만 평가된다. 이미 초대를 수락한 게스트에게는 영향이 없다.

### Teams 외부 액세스 (x25)

![Teams 외부 액세스 — 변경 전 Allow all external domains](/assets/images/m365-readiness-remediation-2/r-g-x25-01.jpg)

**Allow only specific external domains**로 바꾸고 도메인을 추가했다. 저장하면 "조직 전체에 영향이 있고 즉시 원복되지 않는다"는 확인 창이 한 번 더 뜬다.

![Teams 외부 액세스 — 변경 후 허용 도메인 1개](/assets/images/m365-readiness-remediation-2/r-g-x25-02.jpg)

비관리(개인) Microsoft 계정 채팅은 지난 조치에서 이미 꺼 뒀다.

### SharePoint 도메인 제한 (x52)

![SharePoint 공유 — 변경 전 도메인 제한 해제](/assets/images/m365-readiness-remediation-2/r-g-x52-03.jpg)

More external sharing settings → **Limit external sharing by domain**을 체크하고 Add domains에서 **Allow only specific domains**를 골랐다.

Add domains 창에서 Save를 눌러도 페이지 맨 아래의 Save를 한 번 더 눌러야 반영된다. 지난 글의 사이트 생성 설정처럼 다시 불러와서 값이 남아 있는지 확인했다.

![SharePoint 공유 — 새로 고침 후 허용 도메인 유지](/assets/images/m365-readiness-remediation-2/r-g-x52-04.jpg)

### 테넌트 간 액세스 (x53)

순서가 중요하다. 기본 인바운드를 먼저 막으면 협력사 테넌트도 같이 막힌다. 그래서 협력사 테넌트를 조직 설정에 먼저 추가하고, 인바운드를 명시적으로 허용한 뒤 기본값을 바꿨다.

![테넌트 간 액세스 — 변경 전 기본 설정](/assets/images/m365-readiness-remediation-2/r-g-x53-01.jpg)

조직 추가 창에 도메인을 넣으면 해당 Entra 테넌트의 이름과 테넌트 ID가 조회된다. 조회가 된다는 건 상대가 Entra 테넌트라는 뜻이고, 이 경우 테넌트 간 액세스 설정이 적용된다. 조회되지 않는 도메인(개인 메일 등)은 이 설정이 아니라 위의 협업 제한으로만 통제된다.

![조직 설정 — 협력사 테넌트 추가](/assets/images/m365-readiness-remediation-2/r-g-x53-02.jpg)

추가 직후에는 인바운드가 "기본값에서 상속됨"이다. 이 상태로 기본값을 차단하면 협력사도 차단된다. 인바운드 액세스 → B2B Collaboration을 **사용자 지정 설정**으로 바꾸고, 외부 사용자 및 그룹과 애플리케이션을 모두 **액세스 허용**으로 저장했다.

그다음 기본 설정의 인바운드 B2B Collaboration을 차단했다. 여기서 한 번 실패했다.

| 시도 | 결과 |
|---|---|
| 외부 사용자 및 그룹만 차단, 애플리케이션은 허용 | 저장 시 "업데이트 중" 알림이 뜬 뒤 실패. 알림: "애플리케이션 및 사용자의 액세스 유형에 대해 충돌하는 구성이 있습니다. 두 액세스 유형이 모두 일치해야 합니다." |
| 사용자·애플리케이션 모두 차단 | 저장 성공 |

화면에는 저장 버튼이 비활성화되고 진행 알림이 떠서 성공한 것처럼 보였다. 기본 설정 표를 다시 열어 보니 "모두 허용" 그대로였고, 알림 패널에서 실패 사유를 확인했다.

![테넌트 간 액세스 — 기본 인바운드 B2B 모두 차단](/assets/images/m365-readiness-remediation-2/r-g-x53-03.jpg)

B2B 직접 연결은 원래 차단이었고, Teams 공유 채널 외부 초대도 지난 조치에서 꺼 둬서 그대로 뒀다.

## 2. 그룹 명명 정책 차단 단어 (x43)

지난 글에서는 접두사 `GRP-`만 넣고, 차단 단어는 CSV 업로드 방식이라 미뤘다. 첫 행이 헤더이고 한 줄에 단어 하나인 CSV를 만들었다.

```
Blocked Words
admin
administrator
ceo
cfo
hr
payroll
security
it-support
helpdesk
legal
finance
executive
microsoft
office365
official
```

관리자 역할이나 공식 창구처럼 보이는 이름으로 M365 그룹이 생기는 것을 막는 목록이다. 그룹 생성은 이미 관리자만 하도록 막아 뒀지만, 생성 권한이 다시 열릴 때를 대비한 2차 기준이다.

![명명 정책 — 업로드 전](/assets/images/m365-readiness-remediation-2/r-g-x43-01.jpg)

![명명 정책 — 차단 단어 저장 완료](/assets/images/m365-readiness-remediation-2/r-g-x43-02.jpg)

## 3. 운영 기본값

### Windows 업데이트 링 (x66)

관리 장치가 0대라 지금은 적용 대상이 없다. 장치를 등록하는 순간 기본 정책이 걸리도록 링을 먼저 만들어 뒀다.

![업데이트 링 — 변경 전 0개](/assets/images/m365-readiness-remediation-2/r-g-x66-01.jpg)

| 설정 | 값 |
|---|---|
| 이름 | WUR-Default-Broad |
| 품질 업데이트 지연 | 7일 |
| 기능 업데이트 지연 | 30일 |
| 자동 업데이트 동작 | 유지 관리 시간에 자동 설치(활성 시간 08~17시) |
| 할당 | 모든 디바이스 |

![업데이트 링 설정](/assets/images/m365-readiness-remediation-2/r-g-x66-02.jpg)

![업데이트 링 생성 후](/assets/images/m365-readiness-remediation-2/r-g-x66-03.jpg)

파일럿 링과 광범위 링을 나누는 건 장치가 생긴 뒤에 한다.

### 에이전트 사용자 범위 (x70)

점검 때 에이전트 361개가 모두 "사용 가능"이었다. M365 관리 센터 → 에이전트 → 설정에서 두 가지를 봤다.

![에이전트 및 플러그인 액세스 — 외부 게시자 이미 차단](/assets/images/m365-readiness-remediation-2/r-g-x70-01.jpg)

외부 게시자가 만든 에이전트는 이미 막혀 있었다. Microsoft와 조직에서 만든 에이전트만 허용 상태다.

![사용자 액세스 — 변경 전 모든 사용자](/assets/images/m365-readiness-remediation-2/r-g-x70-02.jpg)

사용자 액세스를 **특정 사용자 또는 그룹**으로 바꾸고 관리 계정만 넣었다.

![사용자 액세스 — 변경 후 관리 계정만](/assets/images/m365-readiness-remediation-2/r-g-x70-03.jpg)

에이전트 승인 절차는 아직 없어서 판정은 주의로 남겼다.

### 그룹 기반 라이선스 (x72)

E5 17개가 전부 사용자별 직접 할당이었다. 보안 그룹 `LIC-M365-E5`를 만들고 그룹에 E5를 할당했다. 구성원은 우선 관리 계정 1명만 넣었다.

![라이선스 — 변경 전 직접 할당만](/assets/images/m365-readiness-remediation-2/r-g-x72-01.jpg)

![라이선스 — 그룹 할당 추가](/assets/images/m365-readiness-remediation-2/r-g-x72-02.jpg)

이미 직접 할당이 있는 사용자를 같은 SKU 그룹에 넣어도 라이선스가 추가로 소모되지 않는다. 그룹 상속이 반영된 걸 확인한 뒤 직접 할당을 지울 예정이다. 데모 사용자 16명은 로그인 차단 상태라 그룹으로 옮길지 결정이 남아 있어 주의로 뒀다.

## 4. Azure 구독 Owner PIM 전환 (x82)

구독 범위 Owner가 관리 계정 상시 활성 1건, 개발자 프로그램 서비스 주체 1건이었다. 관리 계정만 PIM 적격으로 바꿨다.

![구독 IAM — 변경 전 상시 활성 Owner](/assets/images/m365-readiness-remediation-2/r-g-x82-01.jpg)

### 적격 할당 추가

IAM → 역할 할당 추가 → 권한 있는 관리자 역할 → 소유자로 들어갔다.

| 단계 | 선택 | 이유 |
|---|---|---|
| 조건 | 사용자가 모든 역할을 할당할 수 있도록 허용 | 적격 Owner가 이 구독의 유일한 사람 Owner가 된다. 기존 상시 Owner와 권한 범위를 같게 맞췄다 |
| 할당 유형 | 적격 | |
| 할당 기간 | 시간 제한 1년 | 영구 적격은 PIM 기본 정책에서 선택할 수 없었다 |

![적격 할당 검토](/assets/images/m365-readiness-remediation-2/r-g-x82-02.jpg)

### 상시 Owner를 남긴 채로는 활성화를 시험할 수 없다

계획은 적격 활성화가 되는 걸 먼저 확인하고 상시 Owner를 지우는 것이었다. 그런데 상시 Owner가 남아 있는 상태에서 적격을 활성화하자 실패했다.

![활성화 실패 — The Role assignment already exists](/assets/images/m365-readiness-remediation-2/r-g-x82-06.jpg)

같은 주체·같은 범위·같은 역할의 활성 할당이 이미 있으면 PIM 활성화 요청이 거부된다. 결국 상시 Owner를 먼저 지워야 검증할 수 있다. 실패에 대비해 복구 경로를 먼저 확인했다.

- 전역 관리자를 PIM으로 활성화해 둔다.
- 적격 활성화가 안 되면 "Azure 리소스에 대한 액세스 관리"를 '예'로 올려 루트 UAA를 받고, Owner를 다시 할당한 뒤 '아니요'로 내린다(지난 글 16장의 절차).
- 개발자 프로그램 서비스 주체의 Owner는 그대로 두므로 구독 자체는 영향이 없다.

참고로 Entra PIM은 본인 활성 할당 제거를 막았지만(지난 글 12장), Azure RBAC는 본인 Owner 할당도 IAM에서 바로 지울 수 있었다.

![상시 Owner 제거 전](/assets/images/m365-readiness-remediation-2/r-g-x82-03.jpg)

![역할 할당 제거 확인](/assets/images/m365-readiness-remediation-2/r-g-x82-04.jpg)

제거 직후 IAM에 "requestor does not have permissions" 경고가 뜨고 할당 목록이 비었다. 상시 Owner가 실제로 빠졌다는 뜻이다.

![제거 직후 — 권한 없음](/assets/images/m365-readiness-remediation-2/r-g-x82-05.jpg)

### 활성화 후에도 바로 열리지 않았다

적격 Owner를 4시간 활성화했다. PIM 활성 할당 탭에는 "활성화됨"으로 나왔다.

![PIM 활성 할당 — 소유자 활성화됨](/assets/images/m365-readiness-remediation-2/r-g-x82-07.jpg)

그런데 같은 탭에서 IAM을 다시 열면 여전히 권한 없음이었다. 포털이 활성화 전에 받은 토큰을 계속 쓰고 있었기 때문이다. 포털 페이지 전체를 새로 불러오니 정상으로 조회됐다.

![활성화 후 IAM — 활성 시간 제한 + 적격 시간 제한](/assets/images/m365-readiness-remediation-2/r-g-x82-08.jpg)

| 주체 | 상태 | 종료 |
|---|---|---|
| 관리 계정 | 활성 시간 제한 | 활성화 4시간 후 |
| 관리 계정 | 적격 시간 제한 | 2027-10-28 |
| 개발자 프로그램 서비스 주체 | 영구 활성 | 영구 |

적격 할당은 1년짜리라 만료 14일 전부터 "연장"을 쓸 수 있다. 그 전에 누르면 "An assignment expiring in next 14 days can only be extended" 안내가 뜬다.

## 5. 검토 기록 (x17·x76)

설정 변경이 아니라 기록을 남기는 항목이다.

![메시지 센터](/assets/images/m365-readiness-remediation-2/r-g-x17-01.jpg)

![서비스 상태 — 활성 권고](/assets/images/m365-readiness-remediation-2/r-g-x76-01.jpg)

메시지 센터 9건과 서비스 상태 권고 6건을 표로 정리했다. 열은 영향 판단, 조치, 담당, 기한, 상태다. 이 테넌트에 영향이 있는 것만 추리면 아래와 같다.

| 게시물 | 판단 | 조치 |
|---|---|---|
| Microsoft 제공 SMS·음성 인증 이전 안내 (2027-02-01 시행) | 영향 있음 | 인증 방법 정책에서 SMS·음성 사용자를 확인하고 Authenticator·패스키로 전환. 기한 2027-01-15 |
| Windows Hello for Business·macOS Platform SSO 단독 MFA 인정 | 참고 | CA01·CA03의 MFA 충족 수단이 늘어난다. What If로 확인 |
| Teams 기본 모임 템플릿 | 모니터링 | 롤아웃 후 지난 조치의 모임 정책 값이 유지되는지 재확인 |
| Purview 감사 결과 조회 지연 권고 | 모니터링 | 감사 검색이 늦게 나오면 이 권고부터 확인 |
| 사용량 보고서 갱신 지연 권고 | 모니터링 | 워크북 사용량 지표(x05·x65)가 측정 불가인 원인 |

서비스 상태 메일 알림은 지난 조치에서 켜 뒀으니 x76은 정상으로 바꿨다. x17은 기한이 지난 조치 필요 게시물 전체를 정리하지 못해서 주의로 뒀다.

## 6. 결과

| 판정 | 조치 전 (10/26) | 1차 조치 후 | 2차 조치 후 (10/28 오후) |
|---|---|---|---|
| 위험 | 41 | 15 | 10 |
| 주의 | 7 | 8 | 6 |
| 정상 | 18 | 43 | 50 |
| 측정 불가 | 16 | 16 | 16 |

이번에 바뀐 항목은 10개다.

| 항목 | 전 | 후 |
|---|---|---|
| x25 Teams 외부 도메인 | 주의 | 정상 |
| x43 그룹 명명 정책 | 주의 | 정상 |
| x52 게스트 초대·SharePoint 도메인 | 주의 | 정상 |
| x53 테넌트 간 액세스 | 위험 | 정상 |
| x66 업데이트 링 | 위험 | 정상 |
| x76 서비스 상태 | 주의 | 정상 |
| x82 구독 Owner | 주의 | 정상 |
| x17 메시지 센터 | 위험 | 주의 |
| x70 에이전트 | 위험 | 주의 |
| x72 그룹 라이선스 | 위험 | 주의 |

남은 위험 10건은 이번 범위 밖이다.

| 분류 | 항목 |
|---|---|
| 과금 승인 필요 | x32, x42, x54 |
| 사람이 직접 해야 함 | x36 (두 번째 비상 계정, FIDO2) |
| 샌드박스·라이선스 예외 | x18, x60, x61, x63, x73, x81 |

## 정리 — 이번에 확인한 것

- **외부 협업은 네 군데를 같이 바꾼다.** Teams 외부 액세스, Entra 협업 제한, SharePoint 도메인 제한, 테넌트 간 액세스가 각각 다른 경로를 통제한다.
- **테넌트 간 액세스는 조직 추가 → 명시적 허용 → 기본값 차단 순서다.** 추가 직후는 기본값 상속이라, 기본값을 먼저 막으면 협력사도 같이 막힌다.
- **기본 인바운드는 사용자와 애플리케이션을 같은 값으로 맞춰야 저장된다.** 한쪽만 바꾸면 저장이 거부되는데, 화면만 봐서는 성공처럼 보인다. 알림 패널과 설정 표를 다시 확인한다.
- **같은 역할이 상시로 있으면 적격 활성화는 실패한다.** 적격 검증을 먼저 하고 상시를 지우는 순서는 쓸 수 없다. 복구 경로(전역 관리자 활성화 + 루트 권한 상승)를 먼저 확보하고 상시 할당을 지운다.
- **PIM 활성화 직후 포털은 이전 토큰을 쓴다.** 권한 없음이 보이면 PIM 활성 할당 탭에서 상태를 먼저 확인하고, 포털을 새로 불러온 뒤 다시 판단한다.
- **Entra PIM과 Azure RBAC는 본인 할당 제거 동작이 다르다.** Entra 역할은 본인 활성 할당 제거를 막고, Azure 구독 Owner는 IAM에서 본인 할당도 지울 수 있다.

변경 이력은 CSV 49행이 됐다. 1차 35행에 이번 조치 13행과 사후 테스트 1행이 더해졌다. 각 행에 근거 캡처 파일명과 원복 방법이 함께 들어 있다.
