---
layout: single
title: "Okta 랩 4 — AD Agent 연동 실측, 설치부터 위임 인증까지"
excerpt: "앞선 세 편이 Okta 단독 환경의 프로토콜 검증이었다면 이번엔 온프렘 Active Directory를 붙인다. AD Agent 설치가 Device Authorization Grant로 구현되어 MFA와 충돌하지 않는 지점, Import 스캔 요약의 카운트가 매칭 판정과 별개라는 점, PARTIAL 매칭이 표시 이름 일치만으로 생성되면서 기본값이 '기존 계정 연결'이라는 사고 시나리오, 그리고 위임 인증에 토글이 존재하지 않는다는 사실까지 화면과 명령 출력으로 확인한 기록이다."
date: 2026-07-29
categories: [IAM]
tags: [Okta, Active-Directory, AD-Agent, 위임인증, Delegated-Authentication, 실측]
---

[전편]({% post_url 26-07-29-okta-saml-nameid-signed-requests %})까지 세 편은 Okta 단독 환경에서 OIDC·SAML 프로토콜 동작을 확인한 기록이다. 이번에는 온프렘 Active Directory를 Okta에 연동하는 과정을 다룬다. Okta AD Agent 설치, 사용자 Import, 위임 인증까지 실제로 수행하면서 문서에 명시되지 않았거나 화면 표시와 실제 동작이 어긋나는 지점을 기록했다.

## 1. 랩 구성

| 항목 | 값 |
|---|---|
| 도메인 | azlab.istn.co.kr (도메인 기능 수준 Windows2016Domain) |
| 에이전트 호스트 | OKTAAGT01 — Windows Server 2025 Standard Evaluation |
| Okta org | Integrator Free Plan (활성 사용자 한도 10명) |
| 대상 OU | OU=OktaLab — 사용자 5명, 그룹 2개 |

기존에 동일 AD에 Entra Connect가 붙어 있으나, 동기화 범위가 `OU=LabAccounts`로 한정되어 있어 Okta용 OU와 겹치지 않는다. 하나의 AD를 두 IdP가 서로 다른 범위로 바라보는 구성이다.

에이전트는 도메인 컨트롤러가 아닌 멤버 서버에 설치했다. Okta 문서가 DC 설치를 권장하지 않는다.

## 2. 사전 점검

Okta가 공표한 AD Agent 요구사항은 다음과 같다.

- Windows Server 2016 / 2019 / 2022 / 2025
- .NET Framework 4.6.2 이상
- TLS 1.2
- 최소 2 CPU, 8GB RAM
- AD 도메인·포리스트 기능 수준 2003 이상

실제 점검에서 확인한 값과 판단은 아래와 같다.

```powershell
Get-ComputerInfo | Select-Object OsName, OsVersion, CsDomain, CsDomainRole
(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' -Name Release).Release
```

`.NET Release` 값은 533320(4.8.1)이었다. Server 2019 이후는 요구치를 자동으로 상회하므로 이 항목은 사실상 형식적 확인이다.

TLS 점검에서 한 가지 함정이 있었다.

```powershell
[Net.ServicePointManager]::SecurityProtocol
# 결과: Tls, Tls11, Tls12
```

이 값은 **현재 PowerShell 세션의 .NET 기본값**이며, 에이전트가 실제로 협상하는 프로토콜과 무관하다. 에이전트는 별도 서비스 프로세스로 동작한다. 머신 레벨 확인은 SCHANNEL 레지스트리를 봐야 하는데, Server 2025에서는 해당 키가 아예 없었다. 키 부재는 OS 기본값 사용을 의미하며 TLS 1.2/1.3이 기본 활성이다.

포트 도달 여부보다 실제 HTTPS 요청이 더 강한 증거다.

```powershell
(Invoke-WebRequest https://{org}.okta.com -UseBasicParsing).StatusCode
# 200
```

`Test-NetConnection`은 TCP 핸드셰이크까지만 확인한다. TLS 협상 실패나 프록시 경유 문제는 잡히지 않는다.

## 3. 에이전트 등록은 Device Authorization Grant

연동 시작점은 `Directory > Directory Integrations`다.

![Admin Console의 Directory Integrations 메뉴](/assets/images/okta4/01-directory-integrations-menu.png)

디렉터리가 하나도 없는 상태에서는 Active Directory / LDAP Directory / LDAP Interface 세 가지 선택지가 제시된다.

![Add Active Directory 선택](/assets/images/okta4/02-add-active-directory.png)

다음 화면이 설치 요건을 명시한다. 에이전트는 Okta org를 향해 아웃바운드 HTTPS만 열면 되고, DC 자체에 설치할 필요가 없다는 점이 여기서 확인된다. 랩에서 멤버 서버를 고른 근거다.

![에이전트 설치 요건과 통신 구조](/assets/images/okta4/03-ad-installation-requirements.png)

![Download Agent](/assets/images/okta4/04-download-agent.png)

설치 마법사가 요구하는 값은 도메인, 서비스 계정 방식, 프록시, org URL 네 가지다. 이 중 등록 단계의 구현이 예상과 달랐다.

Okta 공식 문서에 실린 스크린샷은 설치 마법사가 Okta 사용자명과 비밀번호를 직접 받는 형태다.

![문서에 실린 마법사 스크린샷 — Okta Username / Password 입력란](/assets/images/okta4/05-docs-credentials-form.png)

그러나 실제 3.22.0 버전은 org URL만 입력받고, 이후 기본 브라우저를 열어 다음 주소로 이동시킨다.

```
https://{org}.okta.com/activate?user_code=XXXXXXXX
```

설치 마법사의 실제 흐름은 다음과 같다. 도메인 선택,

![Select AD Domain](/assets/images/okta4/06-installer-select-ad-domain.png)

서비스 계정 방식 선택,

![서비스 계정 — OktaService 생성 또는 재사용](/assets/images/okta4/07-installer-service-account.png)

이미 `OktaService` 계정이 있으면 마법사가 감지해 비밀번호만 요구한다.

![기존 OktaService 계정 감지](/assets/images/okta4/08-installer-existing-oktaservice.png)

프록시 설정,

![프록시 구성 — 미사용](/assets/images/okta4/09-installer-proxy.png)

그리고 org URL이다. 여기까지가 마법사가 받는 전부이고, 자격증명 입력란은 없다.

![Register Okta AD Agent — Organization URL만 입력](/assets/images/okta4/10-installer-org-url.png)

Next를 누르면 활성화 코드가 표시된다.

![Activation — user_code 표시](/assets/images/okta4/11-installer-activation-code.png)

브라우저에서 코드를 확인하고,

![브라우저의 Activate your device 화면](/assets/images/okta4/12-browser-activate-device.png)

"Okta Agent Registration would like to: Register Active Directory Agent" 동의 화면에서 Allow Access를 누르면 등록이 완료된다.

![Register Active Directory Agent 동의 화면](/assets/images/okta4/13-browser-consent-register-agent.png)

![Device activated](/assets/images/okta4/14-browser-device-activated.png)

**OAuth 2.0 Device Authorization Grant**(RFC 8628)[^1]다. 인증이 설치 프로세스 밖에서 일어나므로 두 가지 효과가 있다.

- MFA가 걸린 관리자 계정도 평소 로그인 플로우 그대로 처리된다. 본 랩의 등록 계정은 Okta Verify와 OTP가 등록되어 있었으나 별도 조치가 필요 없었다.
- 자격증명이 설치 프로세스 메모리에 들어가지 않는다.

Entra Connect가 오랫동안 설치 마법사에서 전역 관리자 자격증명을 직접 받아온 것과 대비된다. 온프렘 에이전트가 클라우드에 자신을 등록하는 문제는 device flow의 전형적 적용 사례이며, Okta는 이를 채택했다.

등록에 쓰는 관리자 계정은 반드시 Okta-sourced여야 한다. AD-sourced 계정으로는 등록할 수 없다. 순환 의존을 막기 위한 제약으로 보인다.

설치 직후 서버와 콘솔 양쪽에서 등록 결과를 확인했다.

![설치 완료 후 서비스 상태와 등록 로그](/assets/images/okta4/15-service-status-after-install.png)

![Directory Integrations에 Active Directory 인스턴스 등록됨](/assets/images/okta4/17-directory-integrations-active.png)

콘솔에는 `Active · 1`로 잡히지만 아직 `(Not yet configured)` 상태다. 에이전트 등록과 디렉터리 구성은 별개 단계다.

## 4. 서비스 계정과 Pre-Windows 2000 경고

서비스 계정은 설치 마법사가 `OktaService` 계정을 생성하는 방식을 택했다. 계정은 `CN=Users` 컨테이너에 생성되며 위치를 지정할 수 없다.

설치 도중 다음 경고가 표시됐다.

> The service account is not a member of the Pre-Windows 2000 Compatible Access group and this may cause issues with incremental imports.[^2]

설치를 막지는 않는다. 영향 범위가 명확한 경고다.

- **Full import**: 영향 없음
- **Incremental import**: 삭제된 객체 감지에 영향

증분 가져오기는 마지막 동기화 이후 변경분을 판별해야 하고, 삭제를 인식하려면 `CN=Deleted Objects` 컨테이너를 읽어야 한다. `Pre-Windows 2000 Compatible Access` 그룹이 그 읽기 권한을 보유하고 있어 Okta가 멤버십을 요구한다.

조치는 간단하다. DC에서 계정 위치를 확인하고 그룹에 넣었다.

```powershell
Add-ADGroupMember -Identity "Pre-Windows 2000 Compatible Access" -Members OktaService
```

![DC에서 OktaService 계정 확인과 그룹 추가](/assets/images/okta4/18-dc-oktaservice-group-membership.png)

`DistinguishedName`이 `CN=OktaService,CN=Users,DC=azlab,...`로 나온다. 마법사가 계정을 만드는 위치를 선택할 수 없다는 앞의 서술이 여기서 확인된다.

그룹 멤버십은 액세스 토큰 발급 시점에 반영되므로 에이전트 서비스 재시작이 필요하다. 서비스 이름은 `Okta AD Agent`가 아니라 **`Okta Active Directory Service`**다. `Okta AD Agent`는 표시 이름(DisplayName)이다.

```powershell
Restart-Service "Okta Active Directory Service"
(Get-CimInstance Win32_Service -Filter "Name like '%Okta%'").StartName
# AZLAB\OktaService
# LocalSystem
```

![서비스 재시작 — 경고 메시지에 두 이름이 함께 나온다](/assets/images/okta4/19-restart-okta-ad-service.png)

재시작 시 출력되는 `Waiting for service 'Okta AD Agent (Okta Active Directory Service)' to stop...`이 두 이름의 관계를 그대로 보여준다.

Okta 관련 서비스는 두 개가 설치된다. `LocalSystem`으로 도는 쪽은 에이전트 자동 업데이트용이다.

![Okta 서비스 두 개 — 본체와 업데이트](/assets/images/okta4/16-okta-services-list.png)

`Okta.AdAgent.Update`는 `Stopped` 상태로 남아 있다. 상시 구동이 아니라 필요 시점에만 도는 구조다.

벤더 권장 방식은 레거시 호환 그룹에 서비스 계정을 넣는 것인데, 이 그룹은 필요 이상으로 광범위한 디렉터리 읽기 권한을 함께 부여한다. 실무에서 보안 검토에 걸릴 여지가 있다. 최소 권한을 원한다면 Deleted Objects 컨테이너에만 ACL을 위임하는 방법이 있다.

```
dsacls "CN=Deleted Objects,DC=azlab,DC=istn,DC=co,DC=kr" /takeownership
dsacls "CN=Deleted Objects,DC=azlab,DC=istn,DC=co,DC=kr" /G azlab\OktaService:LCRP
```

두 방식의 실제 동작 차이는 이번 세션에서 측정하지 않았다. 미측정 항목으로 남긴다.

## 5. Import 범위 설정

Directory 설정 마법사의 OU 선택 화면은 기본값이 **도메인 루트 전체 선택**이다. 루트가 선택된 상태에서는 하위 항목의 체크박스가 잠겨 개별 선택이 불가능하다. 루트를 해제해야 개별 OU를 고를 수 있다.

![OU 선택 기본 상태 — 루트가 선택되어 하위가 잠김](/assets/images/okta4/20-ou-selection-default-root.png)

무료 org의 사용자 한도가 10명이고 이미 4명을 쓰고 있었으므로 범위 통제가 필수였다. 특히 `CN=Users` 컨테이너를 포함하면 방금 생성된 `OktaService` 계정과 내장 계정이 대상에 들어간다.

Users와 Groups 두 목록이 별개로 제공되며 각각 설정해야 한다. 사용자 범위만 좁히고 그룹 범위를 방치하면 의도치 않은 그룹이 들어온다.

![사용자 동기화 범위를 oktalab OU로 한정](/assets/images/okta4/21-ou-selection-users-oktalab.png)

![그룹 동기화 범위도 별도로 지정](/assets/images/okta4/22-ou-selection-groups-oktalab.png)

같은 화면 하단에 `Okta username format`이 있다. 기본값 `User Principal Name (UPN)`을 그대로 뒀고, 이 선택이 뒤의 매칭 판정에서 다시 등장한다.

![구성 완료 — username format은 UPN](/assets/images/okta4/23-agent-configured-username-format.png)

프로필 속성은 기본 포함 항목(`userPrincipalName`, `mail`, `givenName`, `sn`) 외에 `department`와 `title`을 추가했다. 검색 결과에 `departmentNumber`, `msDS-PhoneticDepartment` 같은 유사 속성이 함께 노출되므로 이름을 확인하고 골라야 한다.

![Build User Profile — 가져올 속성 선택](/assets/images/okta4/24-build-user-profile-attributes.png)

오른쪽 `Base Schema (required)`는 해제할 수 없고, 추가한 항목만 `Custom Schema`에 쌓인다.

## 6. 스캔 요약과 매칭 판정은 별개 단계다

구성이 끝나면 Import 탭에서 수동 실행이 가능해진다. 아직 아무것도 읽지 않은 상태다.

![Import Results — 실행 전](/assets/images/okta4/25-import-results-before-run.png)

Incremental과 Full 중 Full을 선택했다. 다이얼로그 안내에 "AD에서 삭제된 그룹은 full import에서만 Okta에서 제거된다"는 문장이 있다. 4절의 삭제 감지 이슈와 같은 맥락이다.

![Import 유형 선택 — Full import](/assets/images/okta4/26-full-import-dialog.png)

실행 직후 표시된 요약은 다음과 같았다.

```
5 users scanned!
  5 new users imported
  0 existing users updated
  0 existing users unchanged
  0 users removed

2 groups scanned!
  2 new groups imported
  0 existing groups updated
  0 existing groups unchanged
  0 groups removed
```

![스캔 요약 팝업](/assets/images/okta4/27-scan-summary-popup.png)

`existing users updated`가 0이므로 기존 Okta 계정과의 매칭이 없었다고 읽기 쉽다. **그렇지 않다.**

이어지는 확인 화면에서는 5명 중 3명이 `1 PARTIAL Okta user match found`로 분류됐다. 요약의 `new users imported`는 **AD에서 새로 읽어온 레코드 수**일 뿐이며, 기존 Okta 사용자와의 매칭 판정은 확인 단계에서 별도로 수행된다.

Import는 두 단계로 나뉜다.

1. **스캔** — AD에서 객체를 읽어 pending 상태로 적재
2. **확인(Confirm)** — 각 레코드를 신규 생성 / 기존 계정 연결 / 무시 중 하나로 확정

요약 팝업만 보고 판단하면 안 된다. 실제로 팝업을 닫은 시점의 카운터는 `5 imported users need review · 0 imported users confirmed`였다.

## 7. PARTIAL 매칭의 근거는 표시 이름 하나뿐이다

확인 화면의 분류는 다음과 같았다.

| AD 사용자 | 판정 |
|---|---|
| user1 | 1 PARTIAL Okta user match found |
| user2 | 1 PARTIAL Okta user match found |
| user3 | 1 PARTIAL Okta user match found |
| user4 | NO Okta user matches found |
| user5 | NO Okta user matches found |

![확인 화면 — PARTIAL 3명과 NO match 2명](/assets/images/okta4/28-confirm-partial-and-no-match.png)

앞선 세 명은 이전 편에서 Okta-sourced로 만들어 둔 테스트 페르소나와 표시 이름이 같다. 대조군인 뒤 두 명은 대응하는 Okta 계정이 없다.

주목할 점은 매칭 근거다. 세 명의 식별 값은 전부 다르다.

| 필드 | AD 측 | 기존 Okta 측 |
|---|---|---|
| Username | user1@azlab.istn.co.kr | user1@{org}.okta.com |
| Email | user1@azlab.istn.co.kr | (별도 개인 메일 주소) |

username도 email도 겹치지 않는다. 위 스크린샷에서 각 행의 좌우 값을 직접 비교하면 확인된다. 겹치는 것은 **first name + last name** 조합뿐이다. 그것만으로 부분 매칭 후보가 생성됐다.

운영 관점에서 이 동작에는 위험이 있다. 확인 화면의 **기본 선택값이 "기존 계정에 연결"**이다. 관리자가 목록을 그대로 두고 Confirm을 누르면 표시 이름이 같은 다른 사람의 Okta 계정이 AD 계정과 병합된다. 동명이인이 존재하는 규모의 조직에서는 현실적인 사고 시나리오다. 병합 이후에는 잘못된 사용자가 해당 AD 계정의 그룹 기반 앱 접근 권한을 갖게 된다.

각 항목의 드롭다운에는 네 가지 선택지가 있다.

- PARTIAL Okta user match (기본값, 연결)
- NEW Okta user
- EXISTING Okta user I specify
- IGNORE this user for now

본 랩에서는 소스 분리를 유지하기 위해 세 명 모두 `NEW Okta user`로 전환했다. 전환하면 우측 카드가 `NEW Okta user`로 바뀌고 AD 측 값이 그대로 복사된다.

![NEW Okta user로 전환한 상태](/assets/images/okta4/29-assign-to-new-okta-user.png)

그 결과 동일 표시 이름의 계정이 소스별로 두 개씩 공존한다. username 접미사가 각각 `@azlab.istn.co.kr`과 `@{org}.okta.com`이라 충돌은 발생하지 않는다.

확인 대화상자는 확정 직전 다음을 명시한다.

```
3 new Okta users will be created from Active Directory users
0 existing Okta users will be assigned to Active Directory users
0 Active Directory users will be ignored
```

`Auto-activate users after confirmation` 체크박스가 함께 제공되며 **기본값이 체크**다. 아래는 앞서 대조군 2명을 먼저 확정할 때의 화면으로, 체크 상태가 기본값이라는 점이 드러난다.

![확인 대화상자 — Auto-activate가 기본 체크 상태](/assets/images/okta4/30-confirm-dialog-auto-activate.png)

메일 서버가 없는 랩 환경에서는 해제하는 편이 낫다. 해제하면 사용자가 `Staged` 상태로 적재된다.

![Import된 5명 모두 Staged](/assets/images/okta4/31-imported-users-staged.png)

프로필 속성도 의도한 대로 넘어왔다. 5절에서 추가한 `title`이 AD 값 그대로 표시된다.

![AD에서 가져온 title 속성](/assets/images/okta4/32-title-attribute-from-ad.png)

## 8. AD-sourced 그룹은 콘솔에서 편집할 수 없다

그룹 2개와 멤버십이 그대로 재현됐다. 다만 그룹 상세 화면에 다음 안내가 표시된다.

> This group's membership cannot be modified because the group is managed automatically by Okta

![okta-lab-users — 멤버십 편집 불가](/assets/images/okta4/33-ad-group-okta-lab-users.png)

![okta-lab-admins — 동일한 제약](/assets/images/okta4/34-ad-group-okta-lab-admins.png)

`Assign people` 버튼이 비활성이다. AD-sourced 그룹의 멤버십은 Okta 콘솔에서 추가·삭제할 수 없다.

같은 org 안에서 이전 편에 만든 Okta-sourced 그룹은 자유롭게 편집된다. **소스에 따라 관리 권한이 갈리는 구조**다.

앱 할당을 그룹 기반으로 설계하면 접근 권한의 실질적 통제권이 AD 관리자에게 이관된다는 뜻이다. Okta 관리자는 "어떤 그룹이 어떤 앱을 쓰는가"를 정하고, "누가 그 그룹에 속하는가"는 AD 측이 정한다. 권한 분리 설계로 볼 수도 있고, 사고 시 대응 경로가 둘로 나뉘는 문제로 볼 수도 있다.

사용자 상세 화면에도 `Profile sourced by Active Directory` 라벨이 표시되어 소스가 명시된다.

## 9. 위임 인증에는 토글이 없다

`Security > Delegated Authentication` 화면에 Active Directory 인스턴스가 `Disabled`로 표시되어 있었다. 이것을 위임 인증 상태로 읽고 활성화를 시도했으나 편집이 되지 않았다.

![Delegated Authentication — Password Settings와 Agents 연결 상태](/assets/images/okta4/35-delegated-authentication-agents.png)

화면 상단 설명은 "delegated authentication uses Active Directory to authenticate your users"라고만 적고, 켜고 끄는 컨트롤은 어디에도 없다. 그 아래 Agents 표에 `1 of 1 connected`가 있을 뿐이다.

바로 아래 안내 문구에 조건이 명시되어 있다.

> Agentless Desktop SSO requires an Active Directory instance and your org's Desktop SSO mode must be set to "On".

즉 그 `Disabled`는 위임 인증이 아니라 **Agentless Desktop SSO 상태**였다. 화면 배치상 오독하기 쉽다.

토글을 찾는 대신 실측으로 확인했다. 사용자 한 명을 활성화하고 시크릿 창에서 AD 비밀번호로 로그인을 시도했다.

**로그인이 성공했다.**

Okta는 AD 통합을 구성하는 것만으로 위임 인증이 기본 동작한다. LDAP 연동처럼 별도 토글로 켜고 끄는 구조가 아니다. AD-sourced 사용자의 비밀번호 검증은 에이전트를 경유해 DC에서 이뤄진다.

같은 화면에서 AD Password Sync 안내도 확인했다. 위임 인증과 목적이 다른 별개 기능이다.

| 방식 | 인증 시점 동작 | 에이전트 위치 |
|---|---|---|
| 위임 인증 | 로그인마다 DC에 검증 요청 | 멤버 서버 |
| AD Password Sync | Okta 보관 사본으로 검증 | **모든 DC** |

Password Sync는 DC의 비밀번호 필터가 변경 시점에 값을 가로채 Okta로 전송한다. 에이전트나 DC 장애 시에도 로그인이 유지되는 대신 비밀번호가 클라우드에 복제된다. Okta가 사전 문의를 요구하는 고급 기능으로 분류하고 있다.

같은 AD에 붙어 있는 Entra Connect의 PHS와 비교하면 접근 방식이 다르다. PHS는 커넥터가 주기적으로 해시의 해시를 동기화하며 DC에 에이전트를 두지 않는다. Password Sync는 DC에 필터를 설치하고 변경 시점에 푸시한다. 동일 목적에 대한 두 벤더의 설계 차이다.

## 10. 미측정 항목

이번 세션에서 확인하지 못한 것들을 남긴다.

- **Incremental import 동작** — `Pre-Windows 2000 Compatible Access` 멤버십 유무를 변수로 두고 삭제 감지 차이를 측정해야 한다. 최소 권한 ACL 위임 방식과의 비교도 포함
- **`EXISTING Okta user I specify` 옵션의 제약 범위** — 이미 다른 AD 계정과 연결된 사용자나 관리자 계정도 지정 가능한지
- **AD 표시 이름 변경 후 재Import** — 표시 이름이 유일한 매칭 근거라는 판단을 통제 실험으로 확정
- **인증 이벤트의 System Log 기록 형태** — Okta-sourced 로그인과 AD 위임 로그인의 로그 레벨 차이
- **Desktop SSO** — IWA 에이전트 또는 Agentless 방식
- **그룹 기반 앱 할당** — AD 그룹이 앱 접근 제어에 그대로 쓰이는지

## 정리

이번 연동에서 문서만으로는 예측되지 않았던 지점은 네 가지다.

1. 에이전트 등록이 Device Authorization Grant로 구현되어 MFA와 충돌하지 않는다
2. Import 스캔 요약의 카운트는 매칭 판정 결과가 아니다
3. PARTIAL 매칭은 표시 이름 일치만으로 생성되며 기본값이 연결이다
4. 위임 인증은 별도 토글 없이 기본 동작하고, 화면의 `Disabled`는 다른 기능의 상태다

3번은 사고로 이어질 수 있는 기본값이라 별도로 강조해 둔다. 대규모 조직의 첫 Import에서 확인 화면을 검토 없이 넘기면 계정 병합이 발생한다.

---

[^1]: RFC 8628, OAuth 2.0 Device Authorization Grant — <https://datatracker.ietf.org/doc/html/rfc8628>
[^2]: Okta 설치 관리자 경고 다이얼로그에 첨부된 문서 링크 — About Okta service account permissions, <https://help.okta.com/en/prod/Content/Topics/Directory/ad-agent-about-service-account.htm>
