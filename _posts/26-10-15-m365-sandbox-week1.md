---
layout: single
title: "M365 E5 샌드박스 1주차 실측 — Teams 저장 위치, 그룹 기반 라이선스, Azure RBAC와 Elevate access"
excerpt: "E5 샌드박스에서 1주차 구조 개념을 직접 확인했다. 채널 유형별 파일 저장 위치(표준은 팀 사이트 폴더, 비공개·공유는 별도 사이트, 1:1 채팅은 OneDrive), 부서 속성 하나로 동적 그룹과 Entra ID P2가 자동 부여·회수되는 흐름, 구독 Owner가 리소스 그룹으로 상속되고 RG 권한은 옆으로 퍼지지 않는 RBAC 범위, Global Admin도 Elevate access 전에는 Azure 구독이 보이지 않는 것까지 실측으로 정리했다."
date: 2026-10-15
categories: [IAM]
tags: [M365, E5, Entra, Teams, SharePoint, Azure, RBAC, Sandbox, 실측]
---

M365 E5 개발자 샌드박스에서 1주차 구조 개념을 직접 확인했다. 확인한 항목은 네 가지다.

| 영역 | 확인한 것 | 결과 |
|---|---|---|
| Teams | 채널 유형별 파일 저장 위치 | 표준은 팀 사이트 폴더, 비공개·공유는 별도 사이트, 1:1 채팅은 OneDrive |
| Identity | 동적 그룹 기반 라이선스 부여·회수 | 부서 속성 변경만으로 Entra ID P2가 자동 부여되고, 원복 후 약 10분 안에 회수됨 |
| Azure | RBAC 상속, RG 범위 분리, Elevate access | 구독 권한은 RG로 상속, RG 권한은 옆 RG로 퍼지지 않음, Global Admin도 Elevate 전에는 구독이 안 보임 |
| 인증 | 보안 기본값 상태 | 사용 중 |

환경 점검은 [이전 글](/iam/m365-sandbox-day1/)에, 비상 접근 계정 구성은 [별도 글](/iam/sandbox-break/)에 정리했다. 이번 실습에는 비용이 드는 리소스를 만들지 않았다.

## 1. Teams: 파일은 실제로 어디에 저장되는가

### 팀과 채널 만들기

새 Teams(teams.cloud.microsoft)에서는 채팅과 채널이 한 목록에 합쳐져 있다. 팀은 채팅 목록 위쪽 메뉴의 **새 팀**에서 만든다.

![새 팀 메뉴](/assets/images/2026-10-15-m365-sandbox-week1/01-teams-new-team.png)

팀 유형은 비공개로 두었다. 새 화면은 팀을 만들 때 첫 번째 채널 이름을 함께 받는다. 여기서 만든 채널이 표준 채널이 된다.

![팀 만들기](/assets/images/2026-10-15-m365-sandbox-week1/02-teams-create-team.png)

나머지 채널은 팀 이름 옆 **… → 채널 추가**에서 만든다.

![채널 추가](/assets/images/2026-10-15-m365-sandbox-week1/03-teams-add-channel.png)

채널 유형은 비공개와 공유를 각각 골랐다.

![비공개 채널 만들기](/assets/images/2026-10-15-m365-sandbox-week1/04-teams-private-channel.png)

![공유 채널 만들기](/assets/images/2026-10-15-m365-sandbox-week1/05-teams-shared-channel.png)

![채널 3종 생성 확인](/assets/images/2026-10-15-m365-sandbox-week1/06-teams-channel-list.png)

### 채널별 SharePoint 위치 확인

예전 Teams의 "파일" 탭은 새 화면에서 **공유** 탭으로 바뀌었다. 각 채널의 공유 탭에 `test.txt`를 올리고, **… → SharePoint에서 열기**로 실제 저장 위치를 열었다.

![비공개 채널 공유 탭](/assets/images/2026-10-15-m365-sandbox-week1/07-private-files-tab.png)

![SharePoint에서 열기](/assets/images/2026-10-15-m365-sandbox-week1/08-private-open-sharepoint.png)

비공개 채널은 팀 사이트가 아니라 `Lab-03-비공개-채널`이라는 별도 사이트로 열린다. 오른쪽 위에 Private channel 표시가 있다.

![비공개 채널 사이트](/assets/images/2026-10-15-m365-sandbox-week1/09-private-site.png)

공유 채널도 같은 방식으로 확인했다.

![공유 채널 공유 탭](/assets/images/2026-10-15-m365-sandbox-week1/10-shared-files-tab.png)

![공유 채널 SharePoint에서 열기](/assets/images/2026-10-15-m365-sandbox-week1/11-shared-open-sharepoint.png)

![공유 채널 사이트](/assets/images/2026-10-15-m365-sandbox-week1/12-shared-site.png)

확인한 주소는 다음과 같다. 테넌트 이름은 `<tenant>`로 바꿨다.

| 채널 | 저장 위치 |
|---|---|
| 표준 | `https://<tenant>.sharepoint.com/sites/Lab-03/Shared Documents/표준-채널` |
| 비공개 | `https://<tenant>.sharepoint.com/sites/Lab-03--` 또는 `Lab-03--2` (별도 사이트) |
| 공유 | `https://<tenant>.sharepoint.com/sites/Lab-03--` 또는 `Lab-03--2` (별도 사이트) |

- 표준 채널은 팀 사이트의 문서 라이브러리 안 **폴더**다.
- 비공개·공유 채널은 채널마다 **별도 사이트**가 생긴다.
- 별도 사이트 주소에 한글 채널명이 들어가지 않고 `--`, `--2`만 붙었다. 주소만으로는 어느 채널인지 알 수 없다. 사이트 표시 이름(`Lab-03-비공개-채널`, `Lab-03-공유-채널`)은 한글 그대로 나온다. 채널 이름을 영문으로 정하는 규칙이 필요한 이유다.

### 1:1 채팅 파일

테스트 유저와의 1:1 채팅에서 파일을 보냈다. 첨부할 때 "이 장치에서 업로드"를 골라야 새 파일로 저장된다. "OneDrive에서 첨부"는 기존 파일 링크만 공유한다.

![1:1 채팅 파일 전송](/assets/images/2026-10-15-m365-sandbox-week1/13-chat-file.png)

파일은 팀 사이트가 아니라 **보낸 사람의 OneDrive**, `Microsoft Teams 채팅 파일` 폴더에 저장되고 받는 사람에게 공유된다. 이 폴더는 처음 채팅 파일을 올릴 때 만들어진다.

![OneDrive 채팅 파일 폴더](/assets/images/2026-10-15-m365-sandbox-week1/14-onedrive-chat-files.png)

OneDrive에는 `Meetings`, `Recordings` 폴더도 자동으로 생겨 있었다. 일반 회의 녹화가 주최자 OneDrive의 `Recordings`에 저장되는 구조와 맞다. 녹화는 직접 해 보지 않았다.

![OneDrive 루트](/assets/images/2026-10-15-m365-sandbox-week1/15-onedrive-root.png)

### 정리

| 위치 | 저장소 |
|---|---|
| 표준 채널 | 팀 SharePoint 사이트의 채널 폴더 |
| 비공개 채널 | 채널별 별도 SharePoint 사이트 |
| 공유 채널 | 채널별 별도 SharePoint 사이트 |
| 1:1·그룹 채팅 | 보낸 사람 OneDrive의 `Microsoft Teams 채팅 파일` |
| 일반 회의 녹화 | 주최자 OneDrive의 `Recordings` (폴더 존재만 확인) |

"Teams 파일은 Teams에 저장된다"는 설명은 틀렸다. Teams는 SharePoint와 OneDrive를 보여 주는 화면이다. 그래서 파일 권한·보존·복구 문의는 SharePoint나 OneDrive 쪽에서 확인해야 한다.

## 2. Identity: 동적 그룹 기반 라이선스

부서 속성 하나로 그룹 가입과 라이선스 부여·회수가 연쇄로 일어나는지 확인했다.

### 비용 확인

샌드박스에는 E5와 별도로 Microsoft Entra ID P2 1개가 있다. 이 라이선스를 써도 비용이 드는지 먼저 확인했다. **사용자 제품**(구매 목록)은 0개였다.

![사용자 제품 0개](/assets/images/2026-10-15-m365-sandbox-week1/21-license-products-empty.png)

**라이선스** 화면에는 E5 17/25, Entra ID P2 0/1이 나온다. 구매 목록에 없고 라이선스 목록에만 있으니 개발자 프로그램이 제공한 라이선스다. 할당만으로는 청구가 생기지 않는다.

![라이선스 목록 (변경 전)](/assets/images/2026-10-15-m365-sandbox-week1/22-license-list-before.png)

### 부서 변경

테스트 유저의 원래 부서는 `HR`이었다.

![변경 전 부서](/assets/images/2026-10-15-m365-sandbox-week1/23-user-dept-before.png)

속성 → 작업 정보에서 부서를 `Lab-Sales`로 바꿨다. 사용자 목록에서 여러 명을 고르고 **편집**을 누르면 일괄 속성 편집 창이 열린다. 이 창은 현재 값을 보여 주지 않으니, 변경 전 값은 사용자 개요에서 따로 확인해야 한다.

![부서 변경](/assets/images/2026-10-15-m365-sandbox-week1/24-user-edit-dept.png)

### 동적 그룹 생성

그룹 → 모든 그룹 → 새 그룹을 선택했다.

![새 그룹](/assets/images/2026-10-15-m365-sandbox-week1/25-group-new.png)

보안 그룹, 멤버 자격 유형은 **동적 사용자**로 했다. 동적 쿼리를 저장하기 전에는 **만들기**가 비활성 상태다.

![새 그룹 설정](/assets/images/2026-10-15-m365-sandbox-week1/26-group-form.png)

규칙은 `(user.department -eq "Lab-Sales")`다.

![동적 구성원 규칙](/assets/images/2026-10-15-m365-sandbox-week1/27-group-rule.png)

만든 직후에는 동적 규칙 처리 상태가 "시작되지 않음", 구성원 0명이다. 마지막 멤버 자격 변경이 2000.1.1로 표시되는데, 한 번도 처리되지 않았다는 뜻이다.

![처리 전](/assets/images/2026-10-15-m365-sandbox-week1/28-group-processing.png)

약 1분 뒤 처리 상태가 "성공"으로 바뀌고 구성원이 1명이 됐다.

![구성원 1명](/assets/images/2026-10-15-m365-sandbox-week1/29-group-member-1.png)

### 그룹에 라이선스 할당

Entra 관리 센터에서는 라이선스를 할당할 수 없었다. 사용자 라이선스 화면에 "라이선스 할당 추가, 제거 및 재처리는 M365 관리 센터 내에서만 사용할 수 있습니다"라는 안내가 나온다. 그래서 M365 관리 센터 → 청구 → 라이선스 → Microsoft Entra ID P2 → **라이선스 할당**에서 그룹을 지정했다. 새 화면에는 "그룹" 탭이 따로 없고, 같은 검색창에서 사용자와 그룹을 함께 고른다.

![그룹에 라이선스 할당](/assets/images/2026-10-15-m365-sandbox-week1/30-license-assign-group.png)

할당 대상은 그룹 `Lab-Dyn-Sales` 하나뿐이고, P2는 1/1이 됐다.

![P2 할당 대상](/assets/images/2026-10-15-m365-sandbox-week1/31-license-p2-group.png)

![라이선스 목록 (변경 후)](/assets/images/2026-10-15-m365-sandbox-week1/32-license-list-after.png)

그런데 Entra의 테스트 유저 라이선스 화면에서는 P2의 할당 경로가 "직접"으로 표시됐다.

![테스트 유저 라이선스 (할당 경로 직접)](/assets/images/2026-10-15-m365-sandbox-week1/33-user-license-p2.png)

### 원복 후 자동 회수

부서를 `HR`로 되돌렸다. 처리 상태 "성공", 구성원 0명으로 바뀌었다.

![구성원 0명](/assets/images/2026-10-15-m365-sandbox-week1/34-group-member-0.png)

라이선스는 구성원보다 늦게 처리됐다. 약 10분 뒤 테스트 유저에서 P2가 빠지고 E5만 남았다.

![P2 회수](/assets/images/2026-10-15-m365-sandbox-week1/35-user-license-revoked.png)

| 시각 | 동작 | 결과 |
|---|---|---|
| 09:45 | 동적 그룹 생성 | 처리 시작되지 않음 |
| 09:46 | 규칙 처리 | 구성원 1명 |
| 09:50 | 그룹에 P2 할당 | P2 0/1 → 1/1 |
| 09:53 | 부서 원복 | 구성원 0명 |
| 약 10:04 | 라이선스 재처리 | 테스트 유저 P2 회수 |

원복 후 회수됐으므로 P2는 그룹 상속으로 부여된 것이다. 직접 할당이었다면 그룹에서 빠져도 회수되지 않는다. 확인한 점은 세 가지다.

- 할당 경로는 Entra 사용자 화면의 "할당 경로" 열보다 **M365 관리 센터의 제품별 할당 대상**을 기준으로 판단해야 한다.
- 구성원 변경과 라이선스 재처리는 따로 처리된다. 구성원은 1분 안에 바뀌었지만 라이선스 회수는 10분 가까이 걸렸다.
- 라이선스 관리 위치가 M365 관리 센터로 옮겨졌다. 운영 문서에 적을 경로도 M365 관리 센터 기준으로 써야 한다.

## 3. Azure: RBAC 상속과 Elevate access

### 리소스 그룹과 역할 할당

리소스 그룹 `rg-lab-a`, `rg-lab-b`를 Korea Central에 만들었다. 리소스 그룹 자체에는 요금이 없다.

![리소스 그룹 2개](/assets/images/2026-10-15-m365-sandbox-week1/41-rg-list.png)

`rg-lab-a` → 액세스 제어(IAM) → 추가 → 역할 할당 추가로 테스트 유저에게 Reader를 줬다.

![역할 할당 추가](/assets/images/2026-10-15-m365-sandbox-week1/42-rg-iam-add.png)

한국어 포털에서 Reader는 **독자**로 번역돼 있다. "읽기 권한자"로 검색하면 서비스별 읽기 역할만 나오고 기본 Reader는 나오지 않는다. 영문 `Reader`로 검색하거나, 역할 ID `acdd72a7-3385-48ef-bd42-f606fba81ae7`로 확인하면 된다.

![독자(Reader) 역할](/assets/images/2026-10-15-m365-sandbox-week1/43-role-reader.png)

### 상속과 범위 확인

`rg-lab-a`의 역할 할당 화면이다.

![rg-lab-a 역할 할당](/assets/images/2026-10-15-m365-sandbox-week1/44-rg-a-assignments.png)

`rg-lab-b`에는 테스트 유저가 없다.

![rg-lab-b 역할 할당](/assets/images/2026-10-15-m365-sandbox-week1/45-rg-b-assignments.png)

| 할당 | rg-lab-a | rg-lab-b |
|---|---|---|
| 관리자 Owner | 구독(상속됨) | 구독(상속됨) |
| Microsoft-Developer-Program Owner | 구독(상속됨) | 구독(상속됨) |
| 테스트 유저 Reader | 이 리소스 | 없음 |

- 구독에 준 Owner는 아래 리소스 그룹으로 **상속**된다.
- 리소스 그룹에 준 역할은 **다른 리소스 그룹으로 퍼지지 않는다**.
- 테스트 유저의 Reader는 상태가 "적격 시간 제한", 종료일이 1년 뒤로 들어갔다. P2가 있는 테넌트에서는 Azure 역할 할당도 PIM 기본값인 **적격**으로 들어간다. Entra 역할에서 비상 계정을 할당할 때와 같은 기본값이다. 바로 쓸 권한이 필요하면 할당 유형 탭에서 "활성"을 골라야 한다.
- `Microsoft-Developer-Program`은 개발자 프로그램이 샌드박스를 관리하려고 만든 서비스 주체다. 이름만으로 용도를 알기 어려운 서비스 주체가 구독 Owner로 있는 경우의 예시이기도 하다. 실제 고객 환경이라면 Owner 식별 대상이다.

### Elevate access 전후 비교

Global Admin이지만 Azure 역할이 없는 비상 계정(breakglass01)으로 로그인했다. 구독이 하나도 보이지 않는다.

![Elevate 전 구독 0개](/assets/images/2026-10-15-m365-sandbox-week1/46-subs-before-elevate.png)

Entra → 개요 → 속성 → **Azure 리소스에 대한 액세스 관리**를 "예"로 바꿨다.

![Azure 리소스에 대한 액세스 관리](/assets/images/2026-10-15-m365-sandbox-week1/47-elevate-toggle.png)

다시 로그인하자 구독이 1개 보이고, 부모 관리 그룹은 `Tenant Root Group`이다. 상단에 "전역 관리자는 여기에서 정책 설정을 업데이트하여 이 목록의 모든 구독을 관리할 수 있습니다" 안내가 나온다.

![Elevate 후 구독 1개](/assets/images/2026-10-15-m365-sandbox-week1/48-subs-after-elevate.png)

확인 후 토글을 "아니요"로 되돌렸다.

- Entra 역할(Global Admin)과 Azure RBAC는 별개다. Global Admin도 Elevate access 전에는 Azure 구독을 볼 수 없다.
- Elevate access는 루트(/) 범위에 User Access Administrator를 부여한다. 그래서 테넌트의 모든 관리 그룹과 구독에 대한 권한 부여가 가능해진다. 작업이 끝나면 바로 해제해야 한다.
- 구독의 부모가 `Tenant Root Group`으로 나와서, Tenant → 루트 관리 그룹 → 구독 계층도 함께 확인됐다.

## 4. 보안 기본값

보안 기본값은 사용 중이었다.

![보안 기본값](/assets/images/2026-10-15-m365-sandbox-week1/51-security-defaults.png)

보안 기본값과 조건부 액세스(CA) 정책은 함께 쓸 수 없다. 보안 기본값에는 예외를 둘 수 없어서, 비상 계정도 MFA 대상이다. 비상 계정을 CA 정책에서 예외 처리하는 구성은 CA로 전환한 뒤에 할 수 있다.

## 정리

| 영역 | 흔한 오해 | 실측 |
|---|---|---|
| Teams | 파일은 Teams에 저장된다 | 표준 채널은 팀 사이트 폴더, 비공개·공유는 별도 사이트, 채팅은 OneDrive |
| Identity | 라이선스는 사용자에게 직접 준다 | 부서 속성 → 동적 그룹 → 그룹 라이선스로 자동 부여·회수 |
| Azure | Global Admin은 Azure 리소스도 관리한다 | Elevate access 전에는 구독이 보이지 않음 |
| Azure | Tenant와 Subscription은 같다 | 구독은 Tenant Root Group 아래에 있고, 권한은 구독에서 RG로 상속 |

운영 메모:

- 채널 이름은 영문으로 정한다. 한글 이름은 SharePoint 사이트 주소에서 빠진다.
- Azure 역할 이름은 문서에 영문 이름이나 역할 ID로 적는다. 한국어 포털에서는 Reader가 "독자"로 표시된다.
- P2 테넌트에서는 Entra 역할과 Azure 역할 모두 할당 기본값이 "적격"이다. 할당 유형을 확인해야 한다.
- 라이선스 할당·회수·재처리는 M365 관리 센터에서 한다.

## 참고

- [Shared channels in Microsoft Teams - Microsoft Learn](https://learn.microsoft.com/en-us/microsoftteams/shared-channels)
- [Private channels in Microsoft Teams - Microsoft Learn](https://learn.microsoft.com/en-us/microsoftteams/private-channels)
- [Dynamic membership rules for groups - Microsoft Learn](https://learn.microsoft.com/en-us/entra/identity/users/groups-dynamic-membership)
- [Assign licenses to groups - Microsoft 365 admin](https://learn.microsoft.com/en-us/microsoft-365/admin/manage/assign-licenses-to-users)
- [Elevate access to manage all Azure subscriptions and management groups - Microsoft Learn](https://learn.microsoft.com/en-us/azure/role-based-access-control/elevate-access-global-admin)
- [Azure built-in roles - Microsoft Learn](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles)
- [Security defaults in Microsoft Entra ID - Microsoft Learn](https://learn.microsoft.com/en-us/entra/fundamentals/security-defaults)
