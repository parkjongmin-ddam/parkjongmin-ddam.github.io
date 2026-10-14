---
layout: single
title: "[AD 보안 진단] Purple Knight 5.1 홈랩 실습 — 점수 구조, IOE 23개 판독, PingCastle과 비교"
excerpt: "AD 보안 진단 도구 실습 두 번째 편. PingCastle 실습으로 복제를 복구한 azlab 도메인에 Purple Knight 5.1 Community를 실행해 보안 점수 64%(D), IOE 23개를 받았다. 전체 점수가 모든 카테고리 점수보다 낮은 이유, Critical IOE 4개와 의도된 구성을 구분한 과정, 테스트로 만든 임시 관리자를 IOC로 확인한 과정, 결과물(HTML·XLSX) 형식, PingCastle과 겹치는 항목과 다른 항목을 정리했다."
date: 2026-10-14
categories: [Infra, ActiveDirectory]
tags: [PurpleKnight, Semperis, ActiveDirectory, AD보안, IOE, IOC, ADCS, PingCastle, 실측]
---

AD 보안 진단 도구 실습의 두 번째 편이다. [PingCastle 편]({% post_url 26-10-14-pingcastle-lab %})에서 두 DC 간 복제를 복구한 뒤, 같은 도메인에 Semperis의 Purple Knight를 실행했다.

> 요약
> - Purple Knight 5.1 Community(엔진 5.1.2608.5001), AD만 대상으로 지표 152개 선택, 1분 11초. 결과 64%(D), IOE 23개.
> - 점수 방향이 PingCastle과 반대다. PingCastle은 위험 점수(낮을수록 좋음), Purple Knight는 보안 점수(높을수록 좋음).
> - 전체 64는 카테고리 점수(80~100)보다 낮다. 전체 점수는 실패한 IOE의 심각도로 계산되고 카테고리 점수는 반영되지 않는다.
> - Critical 4개 중 DCSync 권한(Entra Connect 동기화 계정), gMSA 읽기 권한(ADFS 서버) 등은 랩 구축 때 의도한 구성이었다. 임시 관리자 IOC는 이틀 전 테스트 작업으로 확인했다.
> - 결과물은 HTML 보고서와 XLSX가 output 폴더에 자동 생성된다.

## 1. 왜 Purple Knight를 쓰는가

PingCastle로 "어디가 약한지" 점수와 영역을 파악했다면, 다음 질문은 "구체적으로 무엇이 위험하고, 어떻게 고치는가"다. Purple Knight는 이 질문에 답하는 도구다.

AD(와 Entra ID, Okta)를 검사해 위험 항목을 지표(Indicator) 단위로 나열하고, 각 항목에 심각도·설명·조치 방법을 붙여 준다. 쓰는 이유는 다음과 같다.

- **조치 중심으로 본다.** 지표마다 "왜 위험한지"와 "어떻게 고치는지"가 함께 나와서, 개선 과제로 바로 옮길 수 있다. PingCastle이 점수와 추이 중심이라면, Purple Knight는 항목별 조치 안내서에 가깝다.
- **침해 흔적(IOC)을 함께 본다.** 아직 당하지 않은 약점(IOE)뿐 아니라, 이미 누가 손댄 흔적(IOC)까지 지표로 보여 준다. 예방과 탐지를 한 도구에서 본다.
- **프레임워크에 매핑된다.** 각 지표가 MITRE ATT&CK·ANSSI·D3FEND에 연결되어 있어, 왜 위험한지 설명하고 우선순위를 정하기 좋다.
- **결과를 표로 받는다.** HTML 보고서와 함께 XLSX가 나와서, 조치 담당·일정 열을 붙이면 그대로 조치 관리표가 된다.

PingCastle과 기능이 겹치는 항목도 있지만, Purple Knight는 권한(ACL)과 변경 이력을 더 깊이 본다. 그래서 둘을 함께 쓰면 빈 곳이 줄어든다(9장에서 겹치는 항목과 다른 항목을 비교한다).

## 2. 다운로드

Purple Knight는 Semperis 사이트에서 신청서를 제출하면 다운로드 안내 메일이 온다. 신청서의 이메일·회사명은 가렸다.

![다운로드 신청서](/assets/images/2026-10-14-purpleknight-lab/01-download-form.png)

![다운로드 안내 메일](/assets/images/2026-10-14-purpleknight-lab/02-download-mail.png)

다운로드 페이지에 버전(5.1 Community, 2026년 8월), 파일 크기(225MB), SHA256이 나와 있다. 페이지 상단에는 지표별 심각도가 이전보다 세분화되었다는 안내가 있다. 점수 계산 방식이 버전에 따라 바뀌어 왔기 때문에, 점수는 같은 버전끼리만 비교하는 것이 맞다.

![다운로드 페이지](/assets/images/2026-10-14-purpleknight-lab/03-download-page.png)

## 3. 해시 확인과 VM 복사

Host PC에서 받은 ZIP의 해시가 페이지 값과 일치했다. VM으로 옮기려고 `Copy-VMFile`을 실행했더니 `0x80070015 장치가 준비되지 않았습니다`로 실패했다.

![해시 확인과 Copy-VMFile 오류](/assets/images/2026-10-14-purpleknight-lab/04-hash-copy-error.png)

게스트 서비스 인터페이스가 꺼져 있었다. 그런데 `Enable-VMIntegrationService -Name "Guest Service Interface"`도 "지정된 이름의 통합 구성 요소를 찾을 수 없습니다"로 실패했다. Host가 한국어판 Windows라 통합 서비스 이름이 `게스트 서비스 인터페이스`로 되어 있었다. 이름을 패턴으로 골라 켜고 다시 복사했다.

```powershell
Get-VMIntegrationService -VMName Win11_user |
  Where-Object { $_.Name -match "게스트 서비스|Guest Service" } |
  Enable-VMIntegrationService

Copy-VMFile -Name Win11_user -FileSource Host -CreateFullPath `
  -SourcePath $zip.FullName -DestinationPath "C:\ADAudit\PurpleKnight\PurpleKnight.zip"
```

VM에서 압축을 풀고 실행 파일의 서명을 확인했다. `Valid`, 서명자는 SEMPERIS INC.였다. 압축을 풀면 `PK Community 5.1` 폴더 아래에 `PurpleKnight.exe`가 있다.

```powershell
Unblock-File .\PurpleKnight.zip
Expand-Archive .\PurpleKnight.zip -DestinationPath . -Force
$pk = (Get-ChildItem . -Filter PurpleKnight.exe -Recurse | Select -First 1).FullName
Get-AuthenticodeSignature $pk | Select Status, @{n='Signer';e={$_.SignerCertificate.Subject}}
```

![압축 해제와 서명 확인](/assets/images/2026-10-14-purpleknight-lab/11-signature.png)

## 4. 실행

실행하면 버전(5.1.2608.5001, Community Edition)이 표시된 시작 화면이 뜨고, 라이선스 동의 → 환경 → 지표 → 진행 → 요약 5단계로 진행된다.

![시작 화면](/assets/images/2026-10-14-purpleknight-lab/12-splash.png)

![라이선스 동의](/assets/images/2026-10-14-purpleknight-lab/13-agreement.png)

환경은 Active Directory만 선택했다. 포리스트 목록에 azlab.istn.co.kr이 자동으로 잡혔고, 하단 상태 표시줄에 Entra ID(ME-ID)와 Okta는 Disconnected로 나온다. 두 환경은 앱 등록 같은 추가 준비가 필요해 이번 범위에서 뺐다.

![환경 선택](/assets/images/2026-10-14-purpleknight-lab/14-environment.png)

지표 화면에서는 사용 가능한 153개 중 152개가 기본 선택되어 있었다. AD Infrastructure Security(49개)만 일부 선택 표시였고, 빠진 하나는 Critical인 Zerologon 확인이다. DC에 실제로 요청을 보내는 점검이라 기본에서 빠져 있는 것으로 보인다. 기본 선택 그대로 실행했다.

![지표 선택](/assets/images/2026-10-14-purpleknight-lab/15-indicators.png)

| 카테고리 | 선택 / 전체 |
| --- | --- |
| AD Delegation | 24 / 24 |
| Account Security | 40 / 40 |
| AD Infrastructure Security | 48 / 49 (Zerologon 미선택) |
| Group Policy Security | 16 / 16 |
| Kerberos Security | 20 / 20 |
| Hybrid | 4 / 4 |
| 합계 | 152 / 153 |

![실행 진행](/assets/images/2026-10-14-purpleknight-lab/05-progress.png)

전체 1분 11초가 걸렸다. 실행 계정은 도메인 관리자(adm-jmpark)였다. PingCastle은 일반 사용자 권한으로 실행했으니 두 도구의 실행 조건이 다르다. Purple Knight는 관리자 권한이 필요 없다고 안내하지만, 관리자 계정은 읽을 수 있는 정보가 더 많아 결과가 달라질 수 있다.

![Summary 화면](/assets/images/2026-10-14-purpleknight-lab/06-summary.png)

## 5. 결과물

종료 화면의 "Report saved to output folder"대로 output 폴더에 두 파일이 생겼다.

| 파일 | 내용 |
| --- | --- |
| `Security_Assessment_Report_<forest>_<일시>.html` | 보고서. 점수, IOE 목록, 카테고리별 결과, 지표별 상세, 점수 계산 방법, ANSSI 스코어카드 |
| `Security_Assessment_Report_<forest>_<일시>.xlsx` | Assessment summary 시트, Indicators results 시트(지표 152개 × 28열: 상태, 점수, 심각도, 가중치, MITRE ATT&CK·ANSSI·D3FEND 매핑, 설명, 결과 메시지, 조치 방법), IOE별 상세 시트 |

XLSX에 지표별 상세 시트가 따로 있어서, 조치 담당·일정 열을 붙이면 그대로 조치 관리표로 쓸 수 있다. 종료 화면에는 CSV로 따로 저장하는 버튼도 있다.

## 6. 점수 구조

![보고서 개요](/assets/images/2026-10-14-purpleknight-lab/07-report-overview.png)

| 구분 | 값 |
| --- | --- |
| 평가 | 146 |
| IOE 발견 | 23 |
| 통과 | 123 |
| 해당 없음 | 6 |
| 미선택 | 1 (Zerologon) |
| 실행 실패 | 0 |

![카테고리 점수](/assets/images/2026-10-14-purpleknight-lab/10-category-scores.png)

| 카테고리 | 점수 |
| --- | --- |
| AD Delegation | 80 (C-) |
| Account Security | 92 (B-) |
| AD Infrastructure Security | 89 (C+) |
| Group Policy Security | 100 (A+) |
| Kerberos Security | 97 (B+) |
| Hybrid | N/A |
| **전체** | **64 (D)** |

전체 점수가 어느 카테고리 점수보다도 낮다. 보고서 부록 2(Scoring Method)에 계산 방식이 나와 있다.

- 점수에는 실패한 IOE만 반영된다. 통과·미선택·실행 실패한 지표는 영향이 없다.
- 심각도가 높을수록 감점이 크다. Critical·High는 적은 수의 객체만으로도 최대 감점에 도달한다. Informational은 점수에 영향이 없다.
- 각 IOE는 0~99점으로 매겨지고, 해당 객체가 많을수록 점수가 내려간다.
- 같은 심각도의 IOE가 여러 개면 뒤로 갈수록 영향이 조금씩 줄어든다(decay).

카테고리 점수는 같은 방식으로 카테고리 안에서만 계산되고 전체 점수 계산에는 들어가지 않는다. 그래서 카테고리 점수의 평균과 전체 점수는 관계가 없다. PingCastle의 "전체 점수 = 4개 지표 중 최댓값"과 구조가 다르다.

Hybrid가 N/A인 이유는 해당 지표들이 Entra Connect의 Seamless SSO 계정(AZUREADSSOACC)을 점검하기 때문이다. azlab은 Entra Connect를 비밀번호 해시 동기화(PHS)로만 쓰고 Seamless SSO는 켜지 않아 "해당 없음"이 되었다.

## 7. Critical IOE 4개

![Critical IOE](/assets/images/2026-10-14-purpleknight-lab/08-critical-ioes.png)

| 지표 | 결과 | 판독 |
| --- | --- | --- |
| AdminSDHolder object with permission changes | 2026-07-02 05:25(UTC) 변경 | 도메인 생성(05:08) 17분 뒤의 변경이다. 초기 구성 과정에서 생긴 것으로 보이나 변경 내용을 확인해야 한다. PingCastle은 AdminSDHolder 이상 0으로 판정했다 |
| Non-default principal with DCSync rights | `MSOL_xxxxxxxx` | Entra Connect PHS 동기화 계정이다. 동기화에 필요한 정상 권한이지만, 이 계정과 Entra Connect 서버를 Tier 0으로 관리해야 한다는 근거가 된다 |
| DC with Print Spooler remotely accessible | DC 2대 | PingCastle은 DC01만 잡았다. 두 도구의 판정 방식 차이로 보인다 |
| Privileged user with weak password policy | 관리자 2명 | 기본 도메인 정책 최소 길이 7. PingCastle A-MinPwdLen과 같은 항목 |

DCSync 권한처럼 도구가 Critical로 표시해도 실제로는 설계상 필요한 권한일 수 있다. 결과는 "고치라는 명령"이 아니라 "확인하라는 신호"로 읽어야 한다.

## 8. 나머지 IOE

![추가 IOE 목록](/assets/images/2026-10-14-purpleknight-lab/09-additional-ioes.png)

**High**

| 지표 | 결과 | 판독 |
| --- | --- | --- |
| ADCS ESC5 - PKI object with vulnerable ACL | ISCA01 컴퓨터 계정이 자기 CA 등록 서비스 객체에 쓰기 권한 | 기본 구성인지 확인 필요 |
| CertiGhost chase fallback enabled (CVE-2026-54121) | ISCA01 | CA 정책 모듈 EditFlags의 `EDITF_ENABLECHASECLIENTDC`가 켜져 있으면, 패치되지 않은 CA가 요청자가 지정한 호스트를 DC인지 확인하지 않고 신뢰하는 권한 상승 취약점(보고서 설명 기준). PingCastle에는 없는 지표 |
| Computer account password last set over 90 days ago | WIN10-CL01, AADC01 | 평소 꺼 두는 랩 VM |
| DC supporting RC4 or DES | DC 2대 | 지원 암호화 유형에 RC4 포함 |
| LDAP channel binding not required | DC01 미요구, DC02는 점검 연결 재설정 | DC02 결과는 판정 불가 상태 |
| LDAP signing not required | DC01 | PingCastle A-DCLdapSign과 같은 항목 |
| Non-privileged principal able to set SPN / UPN | 4건씩 | SQL 클러스터 CNO(SQLCLUSTER)와 AG 리스너, 도메인 가입 위임 계정(svc-adjoin), ADFS gMSA의 ADFS 컨테이너 권한. 모두 구축 때 의도한 위임 |
| Non-privileged user with access to gMSA password | ADFS01$, ADFS02$ | ADFS 팜 노드가 gMSA 비밀번호를 읽는 것은 정상 동작 |
| Privileged account with password never expires | 1 | 실습용 관리 계정 |
| Schema Admins not empty | 1 | 내장 Administrator |
| Unprotected privileged account can be delegated | 2 | PingCastle P-Delegated와 같은 항목 |

**Medium 이하**

| 지표 | 결과 |
| --- | --- |
| Privileged group membership changes in the last 7 days (Medium) | `lab.tier0test`가 Domain Admins에 추가된 뒤 제거 |
| Risky Pre-Windows 2000 Compatible Access membership (Medium) | Okta 서비스 계정, ISCA01, Authenticated Users(도메인 생성 시 기본) |
| Authenticated Users can add DNS records (Low) | azlab.istn.co.kr 영역 |
| Ephemeral admin (Low) | 48시간 안에 관리자 그룹에 추가·제거된 계정 1 |
| AD object created within the last 10 days (Info) | `adm-backup`, `lab.tier0test` |
| Protected Users group not in use (Info) | 관리자 2명 |
| User with password never expires (Info) | 14개 |

### IOC 확인: 임시 관리자

`lab.tier0test`가 2026-10-12에 Domain Admins에 추가되었다가 바로 제거된 기록, 같은 날 `adm-backup`이 만들어진 기록이 잡혔다. 실제 환경이라면 공격자가 권한을 잠깐 얻고 흔적을 지운 패턴과 구분해야 하는 항목이다. 이 랩에서는 10월 12일에 직접 진행한 테스트 작업으로 확인해 정상으로 판정했다. 운영에서는 변경 요청 기록, 작업자, 시각을 대조해서 판정한다.

## 9. PingCastle과 비교

같은 날 같은 도메인을 두 도구로 본 결과다.

| 구분 | 항목 |
| --- | --- |
| 두 도구 공통 | Print Spooler, LDAP 서명, Schema Admins, Protected Users·위임 불가 플래그, 비밀번호 무기한, 최소 비밀번호 길이, Pre-Windows 2000 그룹, DNS 레코드 생성 권한, 90일 넘은 컴퓨터 비밀번호 |
| Purple Knight만 | AdminSDHolder 변경 이력, DCSync 권한, gMSA 비밀번호 읽기 권한, SPN·UPN 쓰기 ACE, CertiGhost, ADCS ESC5, DC RC4 지원, LDAP 채널 바인딩, 특권 그룹 변경 이력(IOC) |
| PingCastle만 | LAPS 미설치, AD 백업 103일, DC 감사 정책, RPC 강제 인증(Coerce), NTLMv1 허용, AD 휴지통 미활성, 내장 Administrator 최근 사용 |

| 비교 | PingCastle | Purple Knight |
| --- | --- | --- |
| 점수 의미 | 위험 점수, 낮을수록 좋음 | 보안 점수, 높을수록 좋음 |
| 전체 점수 | 4개 지표 중 최댓값 | 실패 IOE의 심각도·영향 객체 수로 계산, 카테고리 점수 미반영 |
| 이번 결과 | 85 (복제 복구 후에도 85) | 64% (D) |
| 결과물 | HTML, XML | HTML, XLSX (CSV 별도 저장) |
| 강한 영역 | 설정·위생 상태(백업, LAPS, 감사, 프로토콜) | 권한(ACL)과 변경 이력, 프레임워크 매핑 |
| LAPS 미설치 | 15점 감점 | 노출 여부만 보는 지표라 "해당 없음" |

LAPS처럼 같은 사실을 두고 한쪽은 감점하고 한쪽은 점검 대상이 아니라고 판정하는 경우가 있다. 두 도구를 함께 쓰면 빈 곳이 줄어든다.

## 10. 정리

- Purple Knight 점수는 높을수록 좋다. PingCastle과 방향이 반대라 보고할 때 단위를 함께 적어야 한다.
- 전체 점수는 실패한 IOE의 심각도로 정해지고 카테고리 점수와는 따로 계산된다.
- Critical·High 결과에도 설계상 필요한 권한(DCSync 동기화 계정, gMSA 읽기, 클러스터·가입 위임)이 섞여 있다. 의도한 구성은 사유를 기록해 예외로 관리하고, 나머지를 개선 대상으로 남긴다.
- 특권 그룹 변경 이력 같은 IOC는 침해의 증거가 아니라 확인 대상이다. 작업 기록과 대조해 판정한다.
- 결과물은 HTML과 XLSX다. XLSX는 조치 관리표의 출발점으로 쓰기 좋다.

다음 글에서는 BloodHound CE로 같은 도메인의 Tier 0 경로를 확인한다.

## 참고

- [Purple Knight](https://www.semperis.com/purple-knight/)
- [Semperis — Purple Knight Scoring Improves Understanding of Identity System Vulnerabilities](https://semperis.com/blog/pk-scoring-improves-understanding-of-identity-system-security-vulnerabilities)
- [ANSSI AD checklist](https://www.cert.ssi.gouv.fr/uploads/ad_checklist.html)
