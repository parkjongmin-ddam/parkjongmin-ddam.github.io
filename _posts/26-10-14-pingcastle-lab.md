---
layout: single
title: "[AD 보안 진단] PingCastle 홈랩 실습 — 규칙 하나를 따라가 97일간 끊긴 DC 복제를 찾기까지"
excerpt: "AD 보안 진단 도구 3종(PingCastle·Purple Knight·BloodHound CE) 실습의 첫 편. azlab 도메인에 PingCastle 4.0.0.31을 실행해 위험 점수 85를 받았다. 결과를 읽던 중 'DC 비활성' 규칙을 따라 repadmin을 돌려 보니 두 DC 간 복제가 2026-07-09 이후 양방향으로 끊겨 있었다. DC 컴퓨터 계정 비밀번호 불일치(SEC_E_WRONG_PRINCIPAL)와 재부팅 후 네트워크 프로필 오판정(1722)을 차례로 해결하고 재진단한 결과, Stale Objects가 51에서 26으로 내려갔고 첫 진단에서 계정 10개가 빠져 있었다는 것도 확인했다."
date: 2026-10-14
categories: ["Security", "AD 보안 진단"]
permalink: "/infra/activedirectory/pingcastle-lab/"
tags: [PingCastle, ActiveDirectory, AD보안, repadmin, netdom, 복제오류, Kerberos, Defender, 실측]
---

AD 보안 진단 도구 세 가지(PingCastle, Purple Knight, BloodHound CE)를 홈랩에서 순서대로 실행해 보는 실습의 첫 편이다. 이번 글은 PingCastle을 다룬다. 실행 과정, 결과 읽는 법, 그리고 결과에 나온 규칙 하나를 따라가다 두 DC 간 복제가 97일째 끊겨 있던 것을 찾아 복구한 과정까지 정리했다.

> 요약
> - PingCastle 4.0.0.31(Basic Edition)로 azlab 도메인을 진단한 결과 전체 위험 점수 85. 전체 점수는 4개 지표의 합이 아니라 최댓값(Privileged Accounts 85)이다.
> - Stale Objects의 `S-DC-Inactive`(DC 비활성)·`S-PwdLastSet-DC`(DC 비밀번호 미변경) 규칙을 따라 `repadmin`을 실행하니 DC01↔DC02 복제가 2026-07-09 이후 양방향으로 실패하고 있었다.
> - 원인은 DC01 컴퓨터 계정 비밀번호 불일치(2148074274, SEC_E_WRONG_PRINCIPAL). KDC 중지 → `netdom resetpwd` → 재부팅으로 복구했다. 재부팅 후에는 네트워크 프로필이 Private으로 잡혀 1722가 이어졌고, DNS를 상대 DC 1순위로 바꿔 해결했다.
> - 재진단 결과 Stale Objects 51 → 26. 첫 진단은 DC02만 아는 데이터로 계산되어 사용자 10개·컴퓨터 1대가 빠져 있었다.

## 1. 왜 PingCastle을 쓰는가

AD는 사용자·컴퓨터·그룹·권한·정책이 수천에서 수십만 개 얽혀 있어서, 보안 상태를 사람이 눈으로 훑어 파악하기 어렵다. 어디서부터 봐야 할지 기준이 필요하다.

PingCastle은 그 기준을 "점수"로 주는 도구다. AD를 한 번 읽어서 위험을 0~100점으로 표시하고, 위험을 네 영역(오래된 객체, 특권 계정, 신뢰 관계, 이상 징후)으로 나눠 보여 준다. 쓰는 이유는 다음과 같다.

- **현황을 한 장으로 파악한다.** 처음 맡은 AD나 정기 점검에서, 지금 어디가 약한지 빠르게 본다. 병원 종합검진 결과지에 가깝다.
- **추이를 비교한다.** 설치 없이 실행 파일 하나로 돌아가고 결과를 XML로 남기므로, 분기마다 같은 방식으로 실행해 점수 변화를 추적할 수 있다. 개선 전후를 숫자로 보고하기 좋다.
- **경영진·고객 보고에 쓴다.** 점수와 네 영역 요약은 비전문가에게 설명하기 쉽다.

한계도 분명하다. PingCastle은 "설정이 위험한가"를 점검하는 도구이지, "지금 공격당하고 있는가"를 탐지하지는 않는다. 그래서 침해 흔적(IOC)은 Purple Knight로, 권한이 이어지는 공격 경로는 BloodHound로 보완한다. 이 글은 그 첫 단계다.

## 2. 실습 환경

Hyper-V 홈랩(azlab.istn.co.kr)에서 진행했다. 진단 대상 DC 2대와 AD CS 발급 CA, 작업용 클라이언트만 켰다. 오프라인 루트 CA(ROOTCA)는 그대로 꺼 두었다.

![Hyper-V VM 목록](/assets/images/2026-10-14-pingcastle-lab/00-hyperv-vms.png)

| VM | 역할 | 비고 |
| --- | --- | --- |
| 2022_DC01 | DC (Windows Server 2022), FSMO 5개 보유 | 192.168.219.191 |
| 2025_DC02 | DC (Windows Server 2025) | 호스트 이름 `WIN-RFQOQTNHTS0`, 192.168.219.201 |
| ISCA01 | 엔터프라이즈 발급 CA | AD CS 점검 대상 |
| Win11_user | 작업 VM (WIN11-CL01) | 도구 실행 위치. DC에서는 실행하지 않음 |

시작 전에 DC 2대와 ISCA01의 체크포인트를 만들었다. 진단 자체는 읽기 전용이지만, 이후 약점을 일부러 만들어 재진단하는 단계를 위해 되돌릴 지점을 남겨 둔 것이다.

```powershell
Checkpoint-VM -Name 2022_DC01 -SnapshotName "before-ad-audit"
Checkpoint-VM -Name 2025_DC02 -SnapshotName "before-ad-audit"
Checkpoint-VM -Name ISCA01    -SnapshotName "before-ad-audit"
```

![체크포인트 생성 확인](/assets/images/2026-10-14-pingcastle-lab/01-checkpoints.png)

## 3. 작업 VM 준비

작업 폴더를 만들고, Defender 예외는 도구 폴더에만 걸었다.

![작업 폴더 생성과 Defender 예외](/assets/images/2026-10-14-pingcastle-lab/02-workdir-exclusion.png)

### 트러스트 오류처럼 보였던 네트워크 미연결

Win11_user에 로그온하자 "워크스테이션과 주 도메인 사이의 트러스트 관계에 이상이 있습니다"가 나왔다. 오래 저장 상태로 두었던 VM이라 컴퓨터 계정 비밀번호가 어긋났다고 판단했다.

![트러스트 오류 로그온 화면](/assets/images/2026-10-14-pingcastle-lab/03-trust-error.png)

로컬 관리자 비밀번호가 기억나지 않아 Hyper-V에서 vNIC를 끊고(`Disconnect-VMNetworkAdapter`) 캐시된 도메인 자격 증명으로 로그온했다. 그런데 `Test-ComputerSecureChannel -Repair`는 "서버를 사용할 수 없습니다"로 실패했고, `nltest /sc_verify`는 `ERROR_NO_LOGON_SERVERS`였다. 확인해 보니 vNIC의 `SwitchName`이 비어 있었다. 끊은 네트워크를 다시 연결하지 않은 것이 원인이었다.

```powershell
Connect-VMNetworkAdapter -VMName Win11_user -SwitchName External
```

재연결 후 `nltest /sc_verify`는 `NERR_Success`였다. 처음 로그온 화면의 오류는 DC가 막 부팅된 시점이었던 영향으로 보이며, 정확한 원인은 확정하지 못했다.

![nltest sc_verify 정상](/assets/images/2026-10-14-pingcastle-lab/04-nltest.png)

## 4. 다운로드: Defender가 Trojan으로 격리

PingCastle은 GitHub 릴리스(netwrix/pingcastle)에서 받았다. 4.0.0.31 ZIP을 Host PC와 VM 양쪽 브라우저가 모두 차단했다.

![브라우저 다운로드 차단](/assets/images/2026-10-14-pingcastle-lab/05-defender-browser-block.png)

탐지명은 `Trojan:Win32/Tecabans.STV!cl`, 심각도 5였다. 다운로드 URL은 `release-assets.githubusercontent.com`(GitHub 공식 릴리스 저장소)이었고, 같은 탐지명이 PingCastle 3.5.1.33·4.0.0.20에서도 보고된 GitHub 이슈(#357)가 있다. `!cl`은 클라우드 기반 휴리스틱 탐지로 알려져 있다. 탐지 기록의 URL 중 서명 토큰 부분은 가렸다.

![Defender 탐지 기록](/assets/images/2026-10-14-pingcastle-lab/06-defender-detection.png)

예외 폴더(`C:\ADAudit\PingCastle`)로 `curl`을 써서 직접 받았는데도 한 번 더 격리되었다. 예외 목록을 확인하니 Step 0에서 `SharpHound` 폴더만 등록하고 PingCastle 폴더는 등록하지 않은 상태였다.

![curl 다운로드](/assets/images/2026-10-14-pingcastle-lab/07-curl-download.png)

예외를 추가한 뒤 다시 받아 파일이 남는 것을 확인했다.

```powershell
Add-MpPreference -ExclusionPath C:\ADAudit\PingCastle, C:\ADAudit\PurpleKnight
curl.exe -sS -L -o PingCastle.zip "https://github.com/netwrix/pingcastle/releases/download/4.0.0.31/PingCastle_4.0.0.31.zip"
```

![예외 추가 후 재다운로드](/assets/images/2026-10-14-pingcastle-lab/08-exclusion-redownload.png)

실행 전에 Authenticode 서명을 확인했다. `Valid`, 서명자는 Netwrix Corporation이었다.

```powershell
Get-AuthenticodeSignature .\PingCastle.exe | Select Status, @{n='Signer';e={$_.SignerCertificate.Subject}}
```

![서명 확인](/assets/images/2026-10-14-pingcastle-lab/09-signature.png)

AD 점검 도구는 공격자의 정찰 도구와 기능이 겹쳐서 이런 탐지가 흔하다. 운영 환경이라면 보안팀과 해시·서명 기준으로 예외를 승인받고 점검이 끝나면 예외를 지우는 절차가 필요하다.

## 5. 실행

일반 도메인 사용자 권한으로 실행했다. 보고서의 `IsPrivilegedMode`는 `false`였다.

```powershell
.\PingCastle.exe --healthcheck --server azlab.istn.co.kr --level Full
```

객체 약 223개, 실행 시간은 1분 남짓이었다. 끝나면 현재 폴더에 HTML 보고서와 XML(추이 비교·가공용)이 생긴다.

![실행 시작](/assets/images/2026-10-14-pingcastle-lab/10-run-start.png)

![실행 완료](/assets/images/2026-10-14-pingcastle-lab/11-run-end.png)

## 6. 결과 읽기

### 전체 점수는 최댓값

![보고서 상단](/assets/images/2026-10-14-pingcastle-lab/12-report-top.png)

| 지표 | 점수 | 매칭 규칙 |
| --- | --- | --- |
| **전체 (Domain Risk Level)** | **85** | |
| Stale Objects | 51 | 13 |
| Privileged Accounts | **85** | 7 |
| Trusts | 0 | 0 |
| Anomalies | 83 | 19 |

전체 85는 네 지표의 합이 아니라 가장 높은 Privileged Accounts 85와 같다. 보고서에도 "It is the maximum score of the 4 indicators"라고 적혀 있다. 지표별 점수는 그 지표에서 걸린 규칙 점수의 합(최대 100)이다. Anomalies의 경우 15+15+10+10+10+10+5+5+2+1 = 83이다.

### Risk model

![Risk model](/assets/images/2026-10-14-pingcastle-lab/13-risk-model.png)

색은 구간을 뜻한다. 흰색 0, 노랑 1~10, 주황 10~30, 빨강 30 초과. 빨강은 Anomalies의 Pass-the-credential 하나였다. 이 모델에 묶인 규칙이 LAPS 미설치 15, 원격 Spooler 노출 10, RPC 강제 인증(Coerce) 인터페이스 10으로 합이 35다.

Basic Edition에서는 Maturity Level과 MITRE ATT&CK 매핑 섹션이 라이선스 전용으로 잠겨 있다.

![라이선스 전용 섹션](/assets/images/2026-10-14-pingcastle-lab/14-license-sections.png)

### Privileged Accounts (85)

![Privileged Accounts 규칙](/assets/images/2026-10-14-pingcastle-lab/16-privileged-rules.png)

| 규칙 | 점수 | 내용 |
| --- | --- | --- |
| P-AdminLogin | 20 | 내장 Administrator 계정을 21일 전에 사용 |
| P-Delegated | 20 | "위임 불가" 플래그가 없는 관리자 2명 |
| P-ServiceDomainAdmin | 15 | Domain Admins에 비밀번호 무기한 계정 2개 |
| P-SchemaAdmin | 10 | Schema Admins 그룹이 비어 있지 않음 |
| P-RecycleBin | 10 | AD 휴지통 미활성 |
| P-ProtectedUsers | 10 | Protected Users에 없는 관리자 2명 |

대상 관리자는 실습용 관리 계정과 내장 Administrator 두 개였다.

### Anomalies (83)

![Anomalies 규칙](/assets/images/2026-10-14-pingcastle-lab/18-anomalies-rules.png)

| 규칙 | 점수 | 내용 |
| --- | --- | --- |
| A-BackupMetadata | 15 | 마지막 AD 백업 103일 전 |
| A-LAPS-Not-Installed | 15 | LAPS 미설치 |
| A-MinPwdLen | 10 | Default Domain Policy 최소 길이 7 |
| A-AuditDC | 10 | DC 감사 정책이 주요 이벤트를 수집하지 않음 |
| A-DC-Spooler | 10 | DC01에서 Spooler 원격 접근 가능 |
| A-DC-Coerce | 10 | 강제 인증에 취약할 수 있는 RPC 인터페이스 2개 |
| A-DCLdapSign | 5 | LDAP 서명 미강제 허용 |
| A-HardenedPaths | 5 | Hardened Paths 보안 수준 하향 |
| A-PreWin2000Other | 2 | Pre-Windows 2000 호환 그룹에 구성원 추가 |
| A-WeakRSARootCert2 | 1 | 신뢰된 인증서 1개의 RSA 키가 상대적으로 약함 |

Spooler와 LDAP 서명 항목은 DC01(2022)에서만 걸리고 DC02(2025)에서는 걸리지 않았다. 같은 도메인 안에서도 DC의 OS 버전과 설정 이력에 따라 결과가 다르다.

### Stale Objects (51)와 Trusts (0)

![Stale Objects 규칙](/assets/images/2026-10-14-pingcastle-lab/15-stale-rules.png)

| 규칙 | 점수 | 내용 |
| --- | --- | --- |
| S-PwdLastSet-90 | 15 | 3개월 넘게 비밀번호를 바꾸지 않은 컴퓨터 1대 |
| S-OldNtlm | 15 | LAN Manager 인증 수준이 NTLMv1·LM 허용 |
| S-PwdLastSet-DC | 5 | 비밀번호를 바꾸지 않은 DC 1대 |
| S-OS-W10 | 5 | 지원 종료된 Windows 10/11 에디션 1대 |
| S-DC-Inactive | 5 | 비활성 DC 1대 |
| S-DC-SubnetMissing | 5 | DC IP 2개가 사이트 서브넷에 없음 |
| S-PwdNeverExpires | 1 | 비밀번호 무기한 계정 9개 |

Trusts는 0이다. azlab은 단일 포리스트·단일 도메인이고 외부 트러스트가 없어서 점검 대상이 없다. 위험이 없다는 뜻이 아니라 범위 밖이라는 뜻이다.

![Trusts](/assets/images/2026-10-14-pingcastle-lab/17-trusts.png)

양호하게 나온 항목도 있었다. MachineAccountQuota 0, 두 DC 모두 SMB 서명 필수·SMB1 미지원, Guest 비활성, AdminSDHolder 이상 0, GPP 비밀번호 0.

## 7. 규칙 하나를 따라가다: DC 비활성

Stale Objects에서 `S-DC-Inactive`와 `S-PwdLastSet-DC`가 같은 DC를 가리키고 있었다. XML을 열어 보니 DC01의 마지막 로그온과 컴퓨터 계정 비밀번호 변경일이 둘 다 2026-07-02에 멈춰 있었다. DC01은 오늘 켜져 있었는데도 그랬다. DC 컴퓨터 계정의 정보가 갱신되지 않는다면 복제를 의심할 만하다.

### 7-1. 복제 상태 확인

```text
PS> repadmin /replsummary

Source DSA          largest delta    fails/total %%   error
 DC01             >60 days            5 /   5  100  (2148074274) The target principal name is incorrect.
 WIN-RFQOQTNHTS0  >60 days            5 /   5  100  (8524) The DSA operation is unable to proceed because of a DNS lookup failure.

Destination DSA     largest delta    fails/total %%   error
 DC01             >60 days            5 /   5  100  (8524) The DSA operation is unable to proceed because of a DNS lookup failure.
 WIN-RFQOQTNHTS0  >60 days            5 /   5  100  (2148074274) The target principal name is incorrect.
```

`repadmin /showrepl DC01`에서는 5개 파티션 모두 "88 consecutive failure(s)", 마지막 성공 2026-07-09였다. 양방향으로 약 97일 동안 복제되지 않은 상태였다. tombstoneLifetime은 180이라 아직 한계(7/9 기준 2027년 1월 초) 안쪽이었다.

azlab DC01은 7월에 이름을 실수로 바꿨다가 netdom으로 복구한 이력이 있다. 그때도 복제 오류 8524를 겪었다. 관련 글: [도메인 컨트롤러 이름을 실수로 바꿨다]({% post_url 26-07-06-aD2 %})

| 방향 | 오류 | 의미 |
| --- | --- | --- |
| DC02 → DC01 | 8524 | DC01이 DC02의 `<DSA GUID>._msdcs` 레코드를 찾지 못함 |
| DC01 → DC02 | 2148074274 (0x80090322) | DC02가 DC01용으로 받은 Kerberos 티켓을 DC01이 복호화하지 못함 |

### 7-2. DNS: nslookup 결과에 속을 뻔했다

두 DC 모두 DNS 서버가 자기 자신(127.0.0.1, ::1)만 가리키고 있었다. 상대 DC의 GUID CNAME을 `nslookup`으로 조회하자 공인 IP(54.230.62.x)가 나왔다.

```text
Name:    istn.co.kr
Addresses:  54.230.62.74 ...
Aliases:  c250bd0e-...._msdcs.azlab.istn.co.kr.istn.co.kr
```

별칭 끝에 `.istn.co.kr`이 한 번 더 붙어 있다. 트레일링 닷 없이 조회하면 검색 접미사를 붙인 이름부터 시도하고, 그중 하나가 상위 공개 도메인의 와일드카드 레코드에 걸린 것이다. 원래 이름은 조회되지도 않았다. 처음에는 이것을 "로컬에 레코드가 없다"는 신호로 해석했는데, `Resolve-DnsName`에 트레일링 닷을 붙여 다시 조회하니 양쪽 모두 정상이었다.

```powershell
Resolve-DnsName c250bd0e-1667-4f6a-840a-072d42f19e12._msdcs.azlab.istn.co.kr. -DnsOnly
# CNAME win-rfqoqtnhts0.azlab.istn.co.kr → A 192.168.219.201
```

DNS 레코드 누락은 원인이 아니었다. 8524의 마지막 실패 시각(09:00:04)이 DC 부팅 직후라, DNS 서버가 AD 통합 영역을 로드하기 전에 시도한 것으로 보인다. 이후 재시도에서는 재현되지 않았다. 내부 AD 도메인이 와일드카드를 쓰는 공개 도메인의 하위 이름이면 `nslookup` 결과가 엉뚱하게 나올 수 있다는 점은 기록해 둔다.

### 7-3. Kerberos: 컴퓨터 계정 비밀번호 비교

2148074274를 확인하려고 두 DC 각각에서 컴퓨터 계정의 `PasswordLastSet`을 조회했다.

```powershell
Get-ADComputer DC01 -Server DC01 -Properties PasswordLastSet
Get-ADComputer DC01 -Server WIN-RFQOQTNHTS0 -Properties PasswordLastSet
```

| 계정 | DC01이 가진 값 | DC02가 가진 값 |
| --- | --- | --- |
| DC01 | 2026-10-12 | 2026-07-02 |
| DC02 | 2026-10-14 09:14 | 2026-07-03 |

DC02의 KDC는 DC01의 7월 비밀번호로 서비스 티켓을 만든다. DC01은 그 사이 비밀번호를 여러 번 바꿔서 현재 값과 직전 값만 갖고 있으니 그 티켓을 풀지 못한다. 반대 방향은 DC01의 DB에 DC02의 최신 비밀번호가 있어 문제가 없다.

### 7-4. 복구

**DC02 → DC01 방향.** DNS가 정상이니 바로 재시도했다. 처음에는 `8453 Replication access was denied`가 나왔는데, 관리자 권한이 아닌 PowerShell(UAC 필터된 토큰)에서 실행한 탓이었다. 관리자 권한 창에서는 성공했다.

```powershell
repadmin /replicate DC01 WIN-RFQOQTNHTS0 "DC=azlab,DC=istn,DC=co,DC=kr"
repadmin /syncall DC01 /Ade
```

**DC01 → DC02 방향.** DC01의 비밀번호를 DC02에 다시 맞췄다. KDC를 멈추는 이유는 작업 중에 DC01이 자기 DB 값으로 티켓을 만들지 않고 DC02에서 받게 하기 위해서다.

```powershell
Stop-Service kdc
Set-Service kdc -StartupType Manual
klist purge
netdom resetpwd /server:WIN-RFQOQTNHTS0 /userd:AZLAB\<관리자계정> /passwordd:*
Restart-Computer
# 재부팅 후
Set-Service kdc -StartupType Automatic
Start-Service kdc
```

`netdom`을 PowerShell ISE에서 실행했더니 "Type the password associated with the domain user:"에서 멈췄다. ISE는 콘솔 프로그램의 대화형 입력을 받지 못한다. 일반 PowerShell 콘솔에서 다시 실행해 해결했다.

![ISE에서 netdom 비밀번호 입력 대기](/assets/images/2026-10-14-pingcastle-lab/19-netdom-ise-wait.png)

재부팅 후 DC02에서 `repadmin /syncall WIN-RFQOQTNHTS0 /Ade`는 오류 없이 끝났다. DC01 → DC02 방향이 복구되었다.

### 7-5. 재부팅 후 1722: 네트워크 프로필

이번에는 DC02 → DC01 방향이 `1908`, 이어서 `1722 The RPC server is unavailable`로 실패했다. 콘솔 창 제목이 "Select ..."로 바뀌어 명령이 멈춘 것처럼 보인 일도 있었는데, 이는 창을 클릭해 빠른 편집 모드의 선택 상태가 된 것이었다(Esc로 해제).

![콘솔 선택 모드](/assets/images/2026-10-14-pingcastle-lab/20-console-select-mode.png)

DNS 해석은 정상이었고(`Resolve-DnsName` → 192.168.219.201), DC01의 네트워크 프로필이 `Private`으로 잡혀 있었다. DC는 `DomainAuthenticated`여야 한다. DNS가 자기 자신만 가리키는 DC는 부팅 직후 네트워크 위치 인식(NLA)이 AD·DNS가 준비되기 전에 판정을 끝내 버려 이런 일이 생길 수 있다. AD 관련 방화벽 규칙 상당수가 Domain 프로필에만 열려 있다.

`Restart-Service NlaSvc`는 타임아웃으로 실패했다. DNS를 상대 DC 1순위, 루프백 2순위로 바꾸고 어댑터를 껐다 켰다. 네트워크가 끊기므로 Hyper-V 콘솔에서 실행했다.

```powershell
Set-DnsClientServerAddress -InterfaceAlias Ethernet -ServerAddresses 192.168.219.201,127.0.0.1
Disable-NetAdapter -Name Ethernet -Confirm:$false
Enable-NetAdapter -Name Ethernet
Get-NetConnectionProfile | Format-Table InterfaceAlias, NetworkCategory
# Ethernet  DomainAuthenticated
```

여러 명령을 한 번에 실행하면 PowerShell이 첫 출력(`Status` 열 하나짜리 표)의 형식을 뒤 출력에도 적용해 결과가 빈 줄로만 보인다. 확인용 명령은 `Format-Table`을 붙이거나 한 줄씩 실행하는 편이 낫다.

프로필이 바뀐 뒤 파티션 5개를 하나씩 복제했고 모두 성공했다. DC02도 DNS를 DC01 1순위, 루프백 2순위로 맞췄다.

```text
PS> repadmin /replsummary

Source DSA          largest delta    fails/total %%   error
 DC01                      18m:42s    0 /   5    0
 WIN-RFQOQTNHTS0              :09s    0 /   5    0

Destination DSA     largest delta    fails/total %%   error
 DC01                         :09s    0 /   5    0
 WIN-RFQOQTNHTS0           18m:42s    0 /   5    0
```

## 8. 재진단

복제를 복구한 뒤 같은 조건으로 PingCastle을 다시 실행해 XML 두 개를 규칙 단위로 비교했다.

| 지표 | 1차 (09:26) | 2차 (10:27) |
| --- | --- | --- |
| 전체 | 85 | 85 |
| Stale Objects | 51 | **26** |
| Privileged Accounts | 85 | 85 |
| Anomalies | 83 | 83 |

사라진 규칙은 `S-PwdLastSet-DC`(DC01 비밀번호가 오늘 날짜로 바뀜), `S-DC-Inactive`(DC01 lastLogon이 10-12로 반영됨), `S-PwdLastSet-90`(3개월 넘은 컴퓨터 1대, 복제로 최신 비밀번호 정보가 반영된 것으로 보임)이다. Stale Objects가 25점 내려갔지만, 최댓값인 Privileged가 그대로라 전체 점수는 바뀌지 않았다.

예상하지 못한 차이도 있었다.

| 항목 | 1차 | 2차 |
| --- | --- | --- |
| 사용자 계정 | 21 | 31 |
| 컴퓨터 계정 | 10 | 11 (Windows Server 2025 1대 추가) |
| 비밀번호 무기한 계정 | 9 | 15 |

1차 진단은 Win11_user가 인증하던 DC02의 데이터로 계산되었다. 7월 9일 이후 DC01에서만 만들어진 사용자 10개와 컴퓨터 1대가 DC02에는 없었으니 결과에서 빠졌다. 복제가 끊긴 상태에서 돌린 진단은 조회한 DC가 아는 범위만 보여 준다. 1차 결과는 불완전한 기준점이었고, 이후 비교 기준은 2차 결과로 바꿨다.

## 9. 개선 과제 후보

2차 결과에서 위험도와 운영 영향도를 같이 보고 고른 후보다. 다음 실습에서 적용 후 재진단할 예정이다.

| 우선순위 | 과제 | 예상 효과 | 운영 영향 |
| --- | --- | --- | --- |
| 1 | 관리자 2명 Protected Users 추가 + "위임 불가" 플래그 | Privileged −30 | 낮음 |
| 2 | AD 휴지통 활성화 | Privileged −10 | 비가역, 영향 없음 |
| 3 | DC01 Spooler 중지 | Anomalies −10 | 낮음 |
| 보류 | NTLMv1 차단, LDAP 서명 강제 | | 인증 영향 검토 후 |

## 10. 정리

- PingCastle 전체 점수는 최댓값이라 한 지표를 크게 개선해도 전체 점수가 그대로일 수 있다. 지표별 점수와 규칙 단위로 추이를 봐야 한다.
- 점수보다 규칙의 근거를 따라가는 것이 중요했다. `S-DC-Inactive` 5점짜리 규칙이 97일간의 복제 단절로 이어졌다.
- AD 진단 도구는 조회한 DC의 시점을 보여 준다. 진단 전에 `repadmin /replsummary`로 복제 상태부터 확인해야 결과를 믿을 수 있다.
- DC의 DNS를 자기 자신만 가리키게 두면 부팅 직후 문제가 생기기 쉽다. 상대 DC 1순위, 루프백 2순위로 구성했다.
- AD 점검 도구는 백신 오탐이 흔하다. 출처(공식 릴리스)와 서명을 확인하고, 예외는 필요한 폴더에만 걸고 실습 후 지운다.

다음 글은 같은 환경에서 Purple Knight를 실행한다.

## 참고

- [PingCastle Healthcheck 문서](https://pingcastle.com/documentation/healthcheck/)
- [netwrix/pingcastle Releases](https://github.com/netwrix/pingcastle/releases)
- [netwrix/pingcastle Issue #357 — Trojan:Win32/Tecabans.STV!cl](https://github.com/netwrix/pingcastle/issues/357)
