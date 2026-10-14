---
layout: single
title: "[AD 보안 진단] BloodHound CE 홈랩 실습 — 공격 경로를 그래프로 보는 이유와 Pathfinding 판독"
excerpt: "AD 보안 진단 도구 실습 세 번째 편. PingCastle·Purple Knight가 '어떤 설정이 위험한가'를 점검한다면, BloodHound는 그 설정들이 이어져서 '일반 계정이 어떤 길로 Domain Admins까지 가는가'를 그래프로 보여 준다. 왜 이런 도구가 필요한지부터, BloodHound CE를 Docker로 설치하고 공식 샘플 데이터로 Pathfinding을 돌려 경로를 읽는 과정, 그리고 azlab 실데이터 수집이 Defender AMSI에 막힌 과정까지 정리했다."
date: 2026-10-14
categories: [Infra, ActiveDirectory]
tags: [BloodHound, SharpHound, ActiveDirectory, AD보안, 공격경로, AttackPath, AMSI, Pathfinding, 실측]
---

AD 보안 진단 도구 실습의 세 번째 편이다. [PingCastle]({% post_url 26-10-14-pingcastle-lab %})과 [Purple Knight]({% post_url 26-10-14-purpleknight-lab %})에 이어 BloodHound CE를 다룬다.

> 요약
> - BloodHound는 점검 도구가 아니라 **경로 분석 도구**다. 계정·그룹·권한·세션의 관계를 그래프로 만들어, 일반 계정에서 Domain Admins까지 이어지는 공격 경로를 찾는다.
> - Host PC의 Docker Desktop에 BloodHound CE v9.8.0을 bloodhound-cli로 설치했다.
> - 공식 샘플 데이터(PHANTOM.CORP)로 Pathfinding을 돌려 경로를 읽었다. 에지 필터에 따라 '병목'이 다르게 보인다는 점을 직접 확인했다.
> - azlab 실데이터 수집은 SharpHound가 Defender AMSI에 막혀 보류했다. 이 차단 자체가 운영 관점의 교훈이 됐다.

## 1. 왜 BloodHound를 쓰는가

앞의 두 도구와 BloodHound는 답하는 질문이 다르다.

| 도구 | 답하는 질문 |
| --- | --- |
| PingCastle | "우리 AD는 전체적으로 얼마나 위험하고, 어느 영역이 약한가?" |
| Purple Knight | "구체적으로 어떤 설정·권한이 위험하고, 어떻게 고치는가?" |
| BloodHound | "그 약점들이 이어져서, 일반 계정이 어떤 길로 최고 권한까지 갈 수 있는가?" |

AD 권한은 한 줄로 끝나지 않고 **여러 단계로 이어진다.** 예를 들면 이렇다.

- 김 사원은 Domain Users 소속이다. (정상)
- Domain Users는 어떤 서버의 로컬 관리자다. (정상처럼 보임)
- 그 서버에 도메인 관리자가 로그인한 세션이 남아 있다. (흔한 일)

세 가지는 각각 떼어 놓고 보면 문제로 보이지 않는다. 그런데 이어 놓으면, 김 사원의 계정으로 그 서버를 장악하고 → 남은 관리자 세션의 자격 증명을 탈취해 → 도메인 관리자가 되는 **경로**가 된다. PingCastle이나 Purple Knight의 항목별 점검표로는 이 "연결"이 잘 드러나지 않는다. 각 항목은 통과로 나올 수도 있다.

BloodHound는 이 관계를 **그래프(노드와 에지)**로 만들어, 사람 눈으로는 찾기 어려운 다단계 경로를 자동으로 찾아 준다. 방어자는 이 경로를 보고, 여러 경로가 공통으로 지나는 **병목(choke point)** 하나를 끊어 여러 경로를 한 번에 줄인다. 공격자가 쓰는 도구를 방어자 관점에서 거꾸로 쓰는 셈이다.

## 2. 구성

| 요소 | 역할 |
| --- | --- |
| BloodHound CE 서버 | 웹 UI + 데이터베이스(PostgreSQL, Neo4j). Host PC의 Docker로 실행 |
| SharpHound | AD용 수집기. DC에 질의해 관계 데이터를 JSON(ZIP)으로 만든다 |
| AzureHound | Entra ID·Azure용 수집기(이번에는 사용 안 함) |

수집기가 데이터를 모으고(ZIP), 그 ZIP을 서버에 올리면(File Ingest), 서버가 그래프로 저장하고, UI에서 경로를 조회하는 구조다.

## 3. 설치

Host PC의 Docker Desktop에 BloodHound CLI로 설치했다. 공식 Quickstart가 권장하는 방법이다.

```powershell
New-Item -ItemType Directory C:\bhce -Force | Out-Null; cd C:\bhce
curl.exe -L -o bloodhound-cli-windows-amd64.zip https://github.com/SpecterOps/bloodhound-cli/releases/latest/download/bloodhound-cli-windows-amd64.zip
tar -xf bloodhound-cli-windows-amd64.zip
.\bloodhound-cli install
```

설치가 끝나면 터미널에 admin 초기 비밀번호가 출력된다. 잊으면 `.\bloodhound-cli config get default_password`로 다시 볼 수 있고, `.\bloodhound-cli resetpwd`로 재설정할 수 있다. 기본 설정은 이 PC(127.0.0.1)에서만 접속되고, 첫 로그인에서 비밀번호를 바꾸게 되어 있다.

**설치 전 걸린 것 두 가지**
- Docker Desktop이 실행 중이어야 한다. 꺼져 있으면 `dockerDesktopLinuxEngine` 파이프를 찾지 못한다는 오류가 난다.
- 공식 최소 사양은 RAM 8GB, 디스크 10GB다. 이번 랩은 데이터가 작아 그보다 적은 여유로도 동작했지만, 여유 메모리가 부족하면 쓰지 않는 VM을 먼저 내리는 게 안전하다.

## 4. 샘플 데이터로 먼저 익히기

실제 데이터를 수집하기 전에, 공식 샘플 데이터(PHANTOM.CORP)로 화면을 익혔다. 수집 과정 없이 경로 분석만 바로 해 볼 수 있어 처음 익히기에 좋다.

```powershell
curl.exe -L -o C:\bhce\ad_sampledata.zip https://raw.githubusercontent.com/SpecterOps/BloodHound-Docs/main/docs/assets/sample-data/ad_sampledata.zip
```

왼쪽 메뉴의 Quick Upload에 ZIP을 올린다.

![업로드 창](/assets/images/2026-10-14-bloodhound-lab/01-upload-dialog.png)

![업로드 완료](/assets/images/2026-10-14-bloodhound-lab/02-upload-done.png)

Administration → File Ingest에서 분석 상태를 볼 수 있다. 31개 파일이 Complete로 바뀌면 끝이다. 올린 직후에는 Ingesting 상태이고, 1~2분 뒤 Complete가 된다.

![File Ingest 완료](/assets/images/2026-10-14-bloodhound-lab/03-ingest-complete.png)

## 5. Pathfinding: 경로 읽기

Explore → Pathfinding에서 출발점과 도착점을 넣으면, 그 사이를 잇는 경로를 그래프로 그려 준다.

- 출발점: `BOB@PHANTOM.CORP` (일반 사용자)
- 도착점: `DOMAIN ADMINS@PHANTOM.CORP` (최고 권한 그룹)

### 5-1. 기본 결과 — 세션 탈취 경로

![기본 필터 경로](/assets/images/2026-10-14-bloodhound-lab/04-path-default.png)

기본 설정(모든 에지 포함)으로 나온 경로는 1장에서 설명한 그 패턴이다.

```
BOB → (MemberOf) → DOMAIN USERS
     → (AdminTo) → ADMINSERVER01 / FILESERVER01 / DF-WIN10-DEV01
     → (HasSession) → 관리자 6명
     → (MemberOf) → DOMAIN ADMINS
```

- **AdminTo**: Domain Users가 서버 3대의 로컬 관리자다.
- **HasSession**: 그 서버에 도메인 관리자들이 로그인한 세션이 남아 있다.

즉 일반 사용자가 서버를 장악하고, 거기 남은 관리자 세션의 자격 증명을 노리는 경로다. 끊어야 할 병목은 **Domain Users의 서버 로컬 관리자 권한**과 **일반 서버에 남는 관리자 세션**이다.

### 5-2. 에지 필터 — 같은 질문, 다른 경로

여기서 BloodHound의 중요한 성질을 하나 확인했다. BloodHound는 기본적으로 **최단 경로**를 보여 준다. 그래서 어떤 관계(에지) 종류를 포함하느냐에 따라 보이는 경로가 달라진다.

오른쪽 깔때기 아이콘에서 Path Edge Filtering을 연다.

![에지 필터](/assets/images/2026-10-14-bloodhound-lab/05-edge-filter.png)

여기서 `AdminTo`와 `HasSession`을 끄면(= 세션 탈취 경로를 제외하면), 전혀 다른 경로가 드러난다.

![필터 적용 후 경로](/assets/images/2026-10-14-bloodhound-lab/06-path-filtered.png)

```
BOB → (MemberOf) → DOMAIN USERS
     → (ADCSESC3 / ADCSESC6b) → PHANTOM.CORP
     → (Contains) → ... → DOMAIN ADMINS
```

이번에는 **AD 인증서 서비스(AD CS)의 설정 약점**을 이용한 경로다. `ADCSESC3`/`ADCSESC6b`는 인증서 템플릿·CA 설정 약점을 이용해 다른 계정을 사칭할 수 있는 경로의 이름이다.

**여기서 배운 점**: "병목이 어디인가"는 어떤 에지를 보느냐에 따라 달라진다. 이 샘플 환경에서는
- 세션 탈취 경로(AdminTo + HasSession)가 더 짧아서 기본 화면에 먼저 나오고,
- 그것을 제외해야 AD CS 경로가 보인다.

그래서 실무에서는 **한 경로를 끊고 다시 조회해서 남은 경로를 확인하는 반복**이 필요하다. 한 번 조회한 그래프가 전부라고 보면 안 된다.

## 6. azlab 실데이터 수집 — AMSI에 막히다

샘플로 사용법을 익힌 뒤, azlab 실제 데이터를 수집해 올리려 했다. 수집기는 버전을 맞추기 위해 BloodHound 서버의 Download Collectors에서 받는다.

![Download Collectors](/assets/images/2026-10-14-bloodhound-lab/07-download-collectors.png)

SharpHound v2.17.0을 받아 작업 VM에서 DC만 조회하는 방식(DCOnly)으로 실행했다. DCOnly는 각 PC에 접속해 세션을 열거하지 않고 DC에 LDAP 질의만 하므로 부하와 탐지 위험이 가장 작다.

```powershell
.\SharpHound.exe --CollectionMethods DCOnly --Domain azlab.istn.co.kr --OutputDirectory C:\ADAudit\SharpHound
```

그런데 실행이 어셈블리 로드 단계에서 실패했다.

```
ERROR|Error running SharpHound: 파일이나 어셈블리 'SharpHoundRPC, ...'
... 프로그램을 잘못된 형식으로 로드하려고 했습니다.
```

처음에는 32비트/64비트 문제로 의심했지만, 32비트로 실행해도 같았다. Defender 탐지 기록을 보니 원인이 분명했다.

```powershell
Get-MpThreatDetection | Sort InitialDetectionTime -Desc | Select -First 1 InitialDetectionTime, Resources
# InitialDetectionTime : 2026-10-14 ...
# Resources : {amsi:_\Device\...\ADAudit\SharpHound\SharpHound.exe}
```

- 탐지 경로가 `file:`이 아니라 **`amsi:`**다.
- 탐지명은 `Trojan:Win32/Ravartar!rfn`.

SharpHound는 내장 구성 요소(SharpHoundRPC 등)를 메모리에서 로드하는데, .NET은 이때 AMSI로 내용을 검사한다. Defender가 이 단계에서 로드를 막은 것이다.

**폴더 예외가 통하지 않은 이유**: 폴더 예외는 디스크에 있는 파일 검사에만 적용된다. 메모리에서 일어나는 AMSI 검사는 디스크 예외와 무관하다. `Add-MpPreference`로 탐지 ID를 허용하려 했으나 권한 문제(0xc0000142)로 실패했다.

여기서 azlab 실데이터 수집은 보류했다. 랩 VM의 보호 설정을 조정하면 진행할 수 있지만, 이 글의 목적은 도구 사용법과 경로 분석 개념을 익히는 것이라 공식 샘플 기준으로 마무리했다.

**이 차단 자체가 실무 교훈이다.** AD 진단·수집 도구는 공격 도구와 기능이 겹쳐서, 운영 환경에서는 백신·EDR이 AMSI 단계에서 막는다. 그래서 실제로 수집하려면 보안팀과 사전에 협의해 탐지 예외를 승인받고, 수집이 끝나면 예외를 되돌리는 절차가 필요하다. 도구를 받아 실행하는 것보다, 이 협의와 통제가 실무의 핵심이다.

## 7. 정리

- BloodHound는 점검 도구가 아니라 경로 분석 도구다. 개별 항목은 정상이어도 이어지면 위험해지는 다단계 경로를 그래프로 찾는다.
- 기본은 최단 경로를 보여 주므로, 에지 필터에 따라 병목이 달라진다. 한 경로를 끊고 재조회하는 반복이 필요하다.
- 수집은 DCOnly처럼 영향이 작은 방식부터 쓰고, 수집 데이터는 공격자에게 설계도가 되므로 암호화 보관해야 한다.
- 운영 환경에서는 AMSI·EDR 탐지까지 보안팀과 협의하는 것이 도구 실행보다 먼저다. 이번 실습에서 그 벽을 직접 만났다.

세 도구를 모두 돌려 본 소감은, 셋이 경쟁 관계가 아니라 역할이 다르다는 것이다. PingCastle로 현황 점수를 잡고, Purple Knight로 항목별 약점과 조치를 정하고, BloodHound로 그 약점들이 실제로 이어지는 경로를 확인하는 순서로 함께 쓸 때 빈 곳이 줄어든다.

## 참고

- [BloodHound CE Quickstart](https://bloodhound.specterops.io/get-started/quickstart/community-edition-quickstart)
- [SharpHound 수집 문서](https://bloodhound.specterops.io/collect-data/ce-collection/sharphound)
- [BloodHound Edges 레퍼런스](https://bloodhound.specterops.io/resources/edges/overview)
