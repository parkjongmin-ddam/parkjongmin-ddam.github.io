---
title: "온프레미스 AD를 M365에 연결하기 — Entra Connect 하이브리드 동기화(PHS) 구축 전 과정"
date: 2026-07-06
categories: [Infra, ActiveDirectory]
tags: [EntraConnect, AzureAD, EntraID, PHS, 하이브리드, M365, PasswordHashSync, OU필터링, HyperV, 홈랩]
description: "홈랩 온프레미스 AD를 Microsoft 365 테넌트에 하이브리드로 연결했다. onmicrosoft.com 대체 UPN 접미사 정리, 개인 MSA(#EXT#)와 조직 계정의 차이, Entra Connect의 Custom 설치와 OU 필터링, PHS 로그인 검증까지 — 그리고 그 과정에서 밟은 함정들(IE ESC JavaScript 오류, 도메인 혼동, OU 필터가 하위까지 포함하는 동작)."
---

# 온프레미스 AD를 M365에 연결하기 — Entra Connect 하이브리드 동기화(PHS) 구축 전 과정

> 환경: Hyper-V 홈랩 (도메인 azlab.istn.co.kr, DC01/DC02, 별도 Entra Connect 서버 AADC01)
> 목표: 온프레미스 사용자(user01~05)를 Microsoft 365 테넌트에 동기화하고, 온프레미스 암호로 클라우드 로그인(PHS)까지 검증

## 0. 무엇을 만드는가

온프레미스 AD 계정을 클라우드(Microsoft Entra ID)로 동기화하고, 온프레미스 비밀번호 그대로 클라우드에 로그인되게 만드는 것이 목표다. 이 구조를 하이브리드 ID라 부르고, 핵심 도구가 Microsoft Entra Connect(구 Azure AD Connect)다.

인증 방식은 세 가지 중 **Password Hash Synchronization(PHS)**를 선택했다. ADFS 페더레이션이 본업이라 오히려 그건 익숙하고, 클라우드가 인증 주체가 되는 PHS 모델을 새로 익히는 것이 학습 목적이었다.

## 1. 온프레미스 UPN 정리 — 라우팅 불가 도메인 대응

온프레미스 사용자 UPN은 `user01@azlab.istn.co.kr`이다. 그런데 `azlab.istn.co.kr`은 공용 인터넷에 등록된 도메인이 아니라 테넌트에 검증 등록이 불가능한 라우팅 불가(non-routable) 도메인이다. 하위 도메인이라 `istn.co.kr`의 공용 DNS를 제어할 수도 없다.

이 상태로 동기화하면 UPN 접미사가 검증된 도메인(`____.onmicrosoft.com`)으로 자동 대체되어 온-클라우드 로그인 이름이 달라진다. 해결은 온프레미스에 `onmicrosoft.com`을 대체 UPN 접미사로 추가하고, 사용자 UPN을 거기 맞추는 것이다.

```powershell
Set-ADForest -Identity azlab.istn.co.kr -UPNSuffixes @{Add="peyzddamoutlook.onmicrosoft.com"}

1..5 | ForEach-Object {
    Set-ADUser "user0$_" -UserPrincipalName "user0$_@peyzddamoutlook.onmicrosoft.com"
}
```

![온프레미스 DC와 Entra Connect 서버 간 UPN 정보 일치 확인](/assets/images/entra-connect-hybrid/upn-suffix-match.png)

이러면 온프레미스와 클라우드의 로그인 이름이 일치한다. Microsoft가 권장하는 non-routable 도메인 대응 표준 방식이다.

## 2. 테넌트 확인과 다운로드 경로

### 2-1. 개인 계정(#EXT#)과 테넌트 도메인 확인

Azure를 개인 Microsoft 계정(outlook.com 등)으로 가입하면, 그 계정은 테넌트에 게스트(External)로 들어간다. Entra 관리 센터 홈에서 **정확한 테넌트 도메인(Primary domain)**을 확인할 수 있다.

![Entra 관리 센터 홈 화면 — 테넌트 Primary domain 확인](/assets/images/entra-connect-hybrid/entra-home.png)

### 2-2. Connect Sync 다운로드 위치

최신 Entra Connect Sync는 다운로드 센터가 아니라 Entra 관리 센터 포털 안에서만 받는 방식으로 바뀌었다. 왼쪽 메뉴에서 Entra Connect를 찾는다.

![Entra 관리 센터 홈에서 Entra Connect 메뉴 선택](/assets/images/entra-connect-hybrid/entra-menu-connect.png)

Connect Sync 페이지에 들어가면 "Not installed" 상태와 함께 다운로드 안내가 나온다.

![Connect Sync 페이지 — Not installed 상태](/assets/images/entra-connect-hybrid/connect-sync-not-installed.png)

포털 개편 안내(다운로드 센터에서 포털로 이전)도 함께 나온다.

![New Entra Connect Sync Versions on Entra Portal Only 안내](/assets/images/entra-connect-hybrid/portal-only-notice.png)

Get started의 Manage 탭 하단에서 **"Download Connect Sync Agent"**를 받는다. 위쪽 "Download Provisioning agent"는 Cloud Sync용이므로 주의.

![Get started > Manage 탭의 Download Connect Sync Agent](/assets/images/entra-connect-hybrid/download-connect-sync-agent.png)

혹시 다운로드 센터 페이지로 연결되면 언어를 English로 두고 Download한다.

![Microsoft Download Center — 언어 English로 Download](/assets/images/entra-connect-hybrid/download-center.png)

## 3. 동기화 전용 관리자 계정 만들기

개인 MSA(#EXT# 게스트) 계정으로는 Entra Connect 설치가 안 된다. 동기화 구성에는 테넌트 내부(Member) 전역 관리자가 필요하므로, 새로 만든다.

Basics — UPN과 비밀번호 설정 (UPN: `syncadmin@peyzddamoutlook.onmicrosoft.com`)

![syncadmin 계정 생성 — Basics 탭](/assets/images/entra-connect-hybrid/syncadmin-create.png)

Assignments — Global Administrator 역할 부여

![syncadmin 계정에 Global Administrator 역할 부여](/assets/images/entra-connect-hybrid/syncadmin-roles.png)

만든 뒤 반드시 한 번 로그인해 MFA를 등록한다. 새 관리자 계정은 "임시 비밀번호 + MFA 미등록" 상태라, 이걸 먼저 정리하지 않으면 Entra Connect 마법사가 로그인할 때 막힌다.

![syncadmin 계정 MFA 등록](/assets/images/entra-connect-hybrid/syncadmin-mfa.png)

## 4. 마법사 시작 — Welcome부터 필수 구성 요소까지

Welcome — 라이선스 동의 체크

![Entra Connect 마법사 — Welcome 라이선스 동의](/assets/images/entra-connect-hybrid/wizard-welcome.png)

Express Settings — 반드시 Customize를 선택한다. Express는 OU 필터링을 못 하고 전체 포리스트를 동기화한다.

![Express Settings — Customize 선택](/assets/images/entra-connect-hybrid/wizard-customize.png)

Install required components — 체크박스는 모두 비운 채 Install (LocalDB 자동 설치)

![Install required components — 체크박스 비운 채 설치](/assets/images/entra-connect-hybrid/wizard-required-components.png)

User Sign-In — 인증 방식으로 **Password Hash Synchronization**을 선택한다. 이번 구성의 핵심 선택지이며, Enable single sign-on은 체크하지 않는다.

![User Sign-In — Password Hash Synchronization 선택](/assets/images/entra-connect-hybrid/wizard-user-signin-phs.png)

## 5. 클라우드/온프레미스 연결

### 5-1. Connect to Entra ID

USERNAME에 syncadmin 전체 UPN을 입력한다.

![Connect to Microsoft Entra ID — USERNAME 입력 화면](/assets/images/entra-connect-hybrid/connect-entra-username.png)

Next를 누르면 로그인 팝업이 뜬다.

> **함정 메모** — 이 팝업이 "JavaScript is required to sign in"으로 뜨며 로그인이 안 되는 경우가 있다. 원인은 Windows Server의 IE Enhanced Security Configuration(IE ESC). 팝업이 IE 엔진으로 뜨는데 IE ESC가 JavaScript를 차단하기 때문이다. 아래로 IE ESC를 끄고 서버를 재부팅한 뒤 다시 시도하면 정상 렌더링된다.

```powershell
$admin = "HKLM:\SOFTWARE\Microsoft\Active Setup\Installed Components\{A509B1A7-37EF-4b3f-8CFC-4F3A74704073}"
$user  = "HKLM:\SOFTWARE\Microsoft\Active Setup\Installed Components\{A509B1A8-37EF-4b3f-8CFC-4F3A74704073}"
Set-ItemProperty -Path $admin -Name IsInstalled -Value 0
Set-ItemProperty -Path $user  -Name IsInstalled -Value 0
```

![로그인 팝업 — Microsoft 계정 Sign in](/assets/images/entra-connect-hybrid/connect-entra-signin-popup.png)

syncadmin 계정으로 로그인하면 자격 증명 검증이 진행된다.

![syncadmin 계정 자격 증명 검증 진행](/assets/images/entra-connect-hybrid/connect-entra-verify.png)

### 5-2. Connect Directories (온프레미스 AD)

FOREST에 `azlab.istn.co.kr`을 확인하고 Add Directory.

![Connect Directories — 온프레미스 포리스트 추가](/assets/images/entra-connect-hybrid/connect-directories-forest.png)

AD forest account — "Create new AD account"를 선택하고 온프레미스 Enterprise Admin(`AZLAB\adm-jmpark`)을 입력한다. 여기는 클라우드 계정이 아니라 온프레미스 관리자다. 동기화 전용 서비스 계정(`MSOL_`)이 자동 생성된다.

![AD forest account — 온프레미스 관리자 계정 입력](/assets/images/entra-connect-hybrid/connect-directories-onprem-admin.png)

> **함정 메모** — 여기서 "Cannot establish a connection to the Domain Controller"가 나면 (a) AADC01의 DNS가 DC를 가리키는지(`Test-NetConnection <DC IP> -Port 389`가 True인지), (b) 입력 계정이 포리스트 루트에 서비스 계정을 만들 권한(Enterprise Admin)이 있는지 확인한다.

연결이 성공하면 다음 단계로 넘어간다.

![Connect Directories 성공 화면](/assets/images/entra-connect-hybrid/connect-directories-success.png)

## 6. Entra sign-in configuration

UPN 접미사 표에서 `azlab.istn.co.kr`은 영구히 검증 불가이므로, 하단 **"Continue without matching all UPN suffixes to verified domains"**를 체크해야 진행된다. user01~05는 이미 `onmicrosoft.com` 접미사를 쓰므로 실제 로그인엔 문제없다. USER PRINCIPAL NAME은 `userPrincipalName` 기본값.

![Microsoft Entra sign-in configuration](/assets/images/entra-connect-hybrid/entra-signin-config.png)

## 7. OU 필터링 — 그리고 예상보다 넓게 잡힌 함정

이번 구성의 핵심은 동기화 범위 제한이다. "Sync selected domains and OUs"를 선택하고, 트리에서 LabAccounts OU만 체크한다.

![Domain/OU Filtering — LabAccounts OU 선택](/assets/images/entra-connect-hybrid/ou-filtering.png)

> **주의** — LabAccounts OU 하위에는 Admins / Service / Users 서브 OU가 있고, 상위 OU를 체크하면 하위가 전부 포함된다. 그래서 이 구성으로 동기화하면 의도한 user01~05 외에 adm-jmpark(관리자), svc-* (서비스) 계정까지 클라우드로 올라간다. user 계정만 원한다면 LabAccounts가 아니라 그 안의 Users 서브 OU만 체크해야 한다. 필요 이상의 계정(특히 관리자·서비스 계정)이 클라우드로 올라가는 건 공격 표면 확대이므로, 실무에서는 범위를 최소로 잡는 게 원칙이다.

## 8. 나머지 화면과 설치

Uniquely identifying your users — 기본값 ("Users are represented only once" + "Let Azure manage the source anchor")

![Uniquely identifying your users — 기본값](/assets/images/entra-connect-hybrid/identifying-users.png)

Filter users and devices — 기본값 "Synchronize all users and devices" (앞의 OU 필터와 AND로 동작하므로 여기서 또 좁힐 필요 없음)

![Filter users and devices — 기본값](/assets/images/entra-connect-hybrid/filter-users-devices.png)

Optional features — PHS만 체크된 상태 유지 (writeback 등은 체크 안 함)

![Optional features — Password Hash Synchronization만 체크](/assets/images/entra-connect-hybrid/optional-features-phs.png)

Ready to configure — "Start the synchronization process..." 체크, Staging mode는 체크 안 함 → Install

![Ready to configure — 동기화 시작 체크 후 Install](/assets/images/entra-connect-hybrid/ready-to-configure.png)

Configuration complete — 구성 성공, 동기화 시작

![Configuration complete — 구성 성공](/assets/images/entra-connect-hybrid/configuration-complete.png)

## 9. 검증 — 동기화와 PHS 로그인

① 동기화 스케줄러 상태 (AADC01):

```powershell
Get-ADSyncScheduler
# SyncCycleEnabled : True, StagingModeEnabled : False 확인
Start-ADSyncSyncCycle -PolicyType Delta   # 즉시 동기화 (Result: Success)
```

② 포털에서 계정 확인 — Entra ID → Users에 user01~05가 나타나고 "Directory synced: Yes"로 표시된다. (앞서 OU 필터에서 LabAccounts를 통째로 잡았기 때문에 adm-jmpark, svc-* 계정도 함께 보인다 — 7장의 함정 그대로다.)

③ 결승선 — PHS 로그인 테스트:

시크릿(InPrivate) 브라우저로 office.com 접속 → `user01@peyzddamoutlook.onmicrosoft.com` / 온프레미스 AD 비밀번호로 로그인.

이 계정의 비밀번호는 온프레미스 AD에만 설정했고 클라우드에 직접 만든 적이 없다. 그런데 그 온프레미스 비밀번호로 클라우드 로그인이 되면 → Password Hash Sync가 정상 동작한다는 증거다. 온프레미스 암호 = 클라우드 암호가 된 것, 이것이 하이브리드 ID의 핵심이다.

## 10. 정리 — 오늘의 교훈

- 라우팅 불가 도메인은 `onmicrosoft.com` 대체 UPN 접미사로 온-클라우드 이름을 일치시킨다
- 개인 MSA(#EXT# 게스트)로는 동기화 관리가 안 된다 — 내부 Member 전역 관리자를 따로 만들고 미리 한 번 로그인(비번 변경 + MFA)해둔다
- 서버의 로그인 팝업 JavaScript 오류는 IE ESC — 끄고 재부팅
- Connect Directories의 자격 증명은 온프레미스 Enterprise Admin (클라우드 계정 아님)
- OU 필터는 체크한 OU의 하위 전체를 포함 — 범위는 최소 OU로 좁게 잡는다
- PHS 검증은 "온프레미스 암호로 클라우드 로그인이 되는가"로 확인한다

ADFS 페더레이션을 오래 다뤘지만, 인증 주체가 클라우드로 넘어가는 PHS 모델을 처음부터 손으로 구성해보니 하이브리드 ID의 반대편 그림이 선명해졌다. 다음은 이 위에서 Conditional Access, PIM 같은 SC-300 범위로 이어갈 수 있다.
