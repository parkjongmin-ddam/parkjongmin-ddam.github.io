---
layout: single
title: "M365·Azure 테넌트 준비 상태 점검 — 체크리스트 기반 전수 점검과 증적 기록"
excerpt: "E5 샌드박스 테넌트를 운영 전환 관점에서 번호가 있는 체크리스트(x01~x79)로 점검하고 항목별 증적 스크린샷을 남겼다. 전역 관리자 영구 할당과 게스트 역할, MFA 등록 2명뿐인 인증 체계, 전원 허용 상태의 게스트 초대와 Anyone 공유, 정책이 전부 기본값인 Teams, 디바이스 0대인 Intune, 기본 정책만 있는 Purview DLP·민감도 레이블, 꺼져 있는 서비스 상태 알림까지 — 관리 센터 6곳(Entra·M365·Teams·SharePoint·Intune·Purview)을 돌며 확인한 결과와 조치 우선순위를 정리했다."
date: 2026-10-26
categories: ["IAM", "Entra ID·M365"]
permalink: "/iam/m365-azure-readiness-82/"
tags: [M365, E5, Entra, PIM, MFA, Teams, SharePoint, Intune, Purview, DLP, Sandbox, 실측]
---

E5 샌드박스 테넌트를 "이 상태로 운영에 들어간다면 무엇이 문제인가"라는 관점에서 점검했다. 이번에는 점검 항목에 번호를 붙인 체크리스트(x01~x79)를 만들어 순서대로 확인했고, 증적 스크린샷을 `e-x{항목번호}-{순번}.jpg` 규칙으로 저장했다. 이 글은 증적이 남은 항목들을 관리 센터·영역별로 묶어 정리한 것이다.

| 영역 | 주요 결과 |
|---|---|
| 관리자 권한·역할 | 전역 관리자 3명(게스트 1명 포함), 청구 관리자 2명 |
| 그룹 거버넌스 | 소유자는 전 그룹 존재, 만료·명명 정책·그룹 라이선스는 전부 미구성 |
| 사용자·인증 | MFA 등록 2명뿐, 로그인 이벤트에 CA "적용되지 않음", 휴면 계정 다수 |
| 외부 협업 | 게스트 초대 전원 허용, 모든 도메인 허용, SPO 공유 Anyone |
| Teams | 정책 24종 전부 Org-wide 기본값, 커스텀 정책 0개 |
| 디바이스 | Intune 등록 디바이스 0대, 업데이트 링 0개, Entra Connect 미설치 |
| Purview | 기본 DLP 3종·기본 레이블 5종만 존재, DSPM for AI 미시작 |
| 운영 | 사용 현황 보고서 데이터 없음, 서비스 상태 메일 알림 꺼짐 |

마스킹 표기: 테넌트 이름·사용자 UPN·개체 ID·IP 주소·그룹 메일 주소는 이미지에서 검은 박스로 처리했다. 비상 접근 계정 `breakglass01`은 [이전 글](/iam/sandbox-break/)에서 다룬 실습용 계정이고, Adele Vance·Patti Fernandez 등은 Microsoft 샌드박스에 포함된 가상 데모 인물이라 그대로 뒀다.

## 1. 관리자 권한·역할

### x01 — 전역 관리자 할당

Entra 관리 센터 → 역할 및 관리자 → Global Administrator → 할당 화면이다.

![전역 관리자 할당 3건](/assets/images/m365-readiness-82/e-x01-01.jpg)

전역 관리자가 3명이다. `Break Glass 01`(비상 접근 계정)과 일반 관리 계정, 그리고 **형식이 Guest인 계정 하나**가 들어 있다. 외부 테넌트에 홈을 둔 게스트가 전역 관리자면 이 테넌트의 보안 수준이 상대 테넌트의 계정 보안에 종속된다. 실습 편의로 넣은 권한이라면 운영 전에 회수하거나 내부 전용 관리 계정으로 대체해야 한다.

### x02 — 역할별 할당 수 확인

모든 역할 화면에서 역할 이름으로 검색해 과제(할당) 수를 확인했다.

![전역 역할 검색 결과](/assets/images/m365-readiness-82/e-x02-01.jpg)

![청구 역할 검색 결과](/assets/images/m365-readiness-82/e-x02-02.jpg)

| 역할 | 할당 수 | 비고 |
|---|---|---|
| 전역 관리자 | 3 | 권한 있음 표시, "둘 이상의 전역 관리자" 권장은 충족 |
| 전역 읽기 권한자 | 0 | 읽기 전용 점검 계정이 없다는 뜻 |
| 청구 관리자 | 2 | 사용자 + 서비스 주체 |

점검·감사 용도라면 전역 관리자 대신 **전역 읽기 권한자**를 쓰는 게 맞는데, 현재 0명이다. 점검 계정조차 전역 관리자로 돌고 있다는 의미라 최소 권한 원칙에서 벗어나 있다.

## 2. 그룹 거버넌스

### x04 — 모든 그룹의 소유자 확인

M365 관리 센터 → 활성 팀 및 그룹에서 그룹 8개(All Company, Digital Initiative Public Relations, Lab-03, Mark 8 Project Team, Retail, Sales and Marketing, U.S. Sales 등)의 멤버십 탭을 하나씩 열어 소유자를 확인했다.

![그룹 목록과 동기화 상태](/assets/images/m365-readiness-82/e-x04-09.jpg)

![그룹 소유자 패널 1](/assets/images/m365-readiness-82/e-x04-01.jpg)

![All Company 소유자](/assets/images/m365-readiness-82/e-x04-02.jpg)

![Digital Initiative Public Relations 소유자](/assets/images/m365-readiness-82/e-x04-03.jpg)

![Lab-03 소유자](/assets/images/m365-readiness-82/e-x04-04.jpg)

![Mark 8 Project Team 소유자](/assets/images/m365-readiness-82/e-x04-05.jpg)

![Retail 소유자](/assets/images/m365-readiness-82/e-x04-06.jpg)

![Sales and Marketing 소유자](/assets/images/m365-readiness-82/e-x04-07.jpg)

![U.S. Sales 소유자](/assets/images/m365-readiness-82/e-x04-08.jpg)

**소유자 없는 그룹은 없었다.** 다만 소유자 대부분이 동일한 관리 계정 + 데모 사용자(Patti Fernandez) 조합이라, 실제 조직이라면 "소유자가 있다"보다 "소유자가 그 그룹을 책임지는 사람인가"를 봐야 하는 상태다. 소유자가 퇴사하면 고아 그룹이 되므로 그룹당 소유자 2명 이상이 권장값이다.

### x06 — 그룹 만료 정책 없음

![그룹 만료 정책 미설정](/assets/images/m365-readiness-82/e-x06-01.jpg)

Entra → 그룹 → 만료 설정이 비어 있다. 그룹 수명 미지정, 소유자 없는 그룹의 알림 연락처도 비어 있고(필수값 경고 표시), 만료 적용 대상은 **없음**이다. 만료 정책이 없으면 프로젝트가 끝난 그룹과 그 안의 SharePoint 사이트·Teams 채널이 무기한 남는다.

### x27 — 그룹 생성 권한은 전원 개방

![그룹 일반 설정](/assets/images/m365-readiness-82/e-x27-01.jpg)

사용자가 Azure Portal·API·PowerShell에서 **보안 그룹과 M365 그룹을 모두 만들 수 있는 상태**(둘 다 "예")다. 셀프 서비스 그룹 관리는 꺼져 있으면서 그룹 생성은 열려 있는, 방향이 어긋난 조합이다. 운영에서는 M365 그룹 생성을 특정 보안 그룹 구성원으로 제한하는 게 일반적이다.

### x40 — 동적 그룹은 동작하나 비어 있음

![Lab-Dyn-Sales 동적 그룹](/assets/images/m365-readiness-82/e-x40-01.jpg)

[1주차 글](/iam/m365-sandbox-week1/)에서 만든 동적 보안 그룹 `Lab-Dyn-Sales`가 남아 있다. 동적 규칙 처리 상태는 성공인데 **구성원이 0명**이다. 규칙 조건에 맞는 사용자가 없어진 상태로, 실습 원복의 흔적이다. 비어 있는 동적 그룹은 라이선스·정책 할당 대상이 되면 조용히 아무 일도 안 하는 함정이 되므로 정리 대상이다.

### x43 — 명명 정책·차단 단어 없음

![그룹 명명 정책 없음](/assets/images/m365-readiness-82/e-x43-01.jpg)

![차단된 단어 목록 없음](/assets/images/m365-readiness-82/e-x43-02.jpg)

그룹 명명 정책(접두사·접미사)과 차단 단어 목록이 모두 비어 있다. 그룹 생성이 전원 개방(x27)인 상태에서 명명 규칙까지 없으니, 사용자가 어떤 이름으로든 그룹을 만들 수 있다. "CEO", "HelpDesk" 같은 이름의 그룹을 아무나 만들 수 있는 상태라는 뜻이다.

### x72 — 그룹 기반 라이선스 할당 없음

![Lab-Dyn-Sales 라이선스 할당 없음](/assets/images/m365-readiness-82/e-x72-02.jpg)

동적 그룹에 라이선스 할당이 없다. 1주차에 실습했던 그룹 기반 자동 할당을 원복한 상태 그대로다. E5 라이선스 상세를 보면 17/25 할당이 전부 사용자 직접 할당이다.

![E5 라이선스 할당 현황](/assets/images/m365-readiness-82/e-x72-01.jpg)

운영 규모가 커지면 직접 할당 대신 그룹 기반 할당으로 옮기는 게 관리 비용 면에서 유리하다.

## 3. 사용자·인증

### x37 — 사용자 19명, 마지막 로그인 대부분 8월

![사용자 목록 1](/assets/images/m365-readiness-82/e-x37-01.jpg)

![사용자 목록 2](/assets/images/m365-readiness-82/e-x37-02.jpg)

구성원 19명(+게스트). 마지막 대화형 로그인 시간이 **2026년 8월 17일에 몰려 있다** — 테넌트 생성 시 데모 데이터가 들어온 날이다. 즉 대부분이 한 번도 실제 로그인한 적 없는 계정이다. 운영 테넌트였다면 90일 미로그인 계정 비활성화 같은 휴면 계정 프로세스 대상이다.

### x38 — MFA 등록 2명뿐

인증 방법 → 사용자 등록 세부 정보 화면이다.

![MFA 등록 세부 정보](/assets/images/m365-readiness-82/e-x38-01.jpg)

다단계 인증 가능 사용자는 둘뿐이다 — Authenticator 앱 푸시를 등록한 `Break Glass 01`과 패스키(동기화됨)+Authenticator를 등록한 관리 계정. 나머지 데모 사용자 전원이 다단계 인증 **불가능**, SSPR도 불가능이다. MFA 필수 정책을 켜기 전에 등록 캠페인으로 등록률부터 올려야 잠금 사고가 없다.

### x19 — 로그인 이벤트: CA가 한 번도 적용되지 않음

![로그인 이벤트 지난 7일](/assets/images/m365-readiness-82/e-x19-01.jpg)

지난 7일 대화형 로그인 전부에서 **조건부 액세스: 적용되지 않음**이다. 조건부 액세스 정책이 없는 테넌트라는 사실이 로그에서도 그대로 확인된다. 인증 요구 사항은 다단계 인증으로 찍혀 있는데, 이건 보안 기본값이 관리자 로그인에 MFA를 요구한 결과다. 정책 0개 상태에서 보안 기본값 하나로 버티고 있는 구조다.

### x07·x08 — 게스트 계정의 활동과 스폰서

![게스트 로그인 모니터링](/assets/images/m365-readiness-82/e-x07-01.jpg)

![게스트 초대 상태와 스폰서](/assets/images/m365-readiness-82/e-x08-01.jpg)

역할이 들어간 게스트 계정의 모니터링 탭에는 로그인 3회가 찍혀 있다. 초대 상태는 수락됨, 스폰서는 1명(사용자) 지정돼 있다. 스폰서가 있다는 건 다행이지만, 스폰서 지정은 책임자 표시일 뿐 권한을 제한하지 않는다. 전역 관리자 역할(x01)이 남아 있는 한 회수가 우선이다.

### x09 — Entra 권장 사항 7건

![Entra 권장 사항](/assets/images/m365-readiness-82/e-x09-01.jpg)

Entra ID 개요의 권장 사항 탭이다. 완료 4건, 활성 3건.

| 상태 | 권장 사항 | 점수 |
|---|---|---|
| 활성 | 조건부 액세스 정책의 내부 위험 조건으로 테넌트 보호 (P2) | 0/5 |
| 활성 | 사용자가 신뢰할 수 없는 애플리케이션에 동의하도록 허용 안 함 | 0/4 |
| 활성 | 셀프 서비스 암호 재설정 사용 | 0.16/1 |
| 완료 | 둘 이상의 전역 관리자 지정 / 암호 해시 동기화 / 암호 만료 안 함 / 최소 권한의 관리 역할 | — |

활성 3건이 전부 이번 점검에서 확인한 공백(CA 없음, 앱 동의 정책, SSPR 미사용)과 일치한다. 포털이 공짜로 주는 점검 결과이니 운영 전환 전 체크리스트에 그대로 얹으면 된다.

### x29·x39 — 앱 동의 설정

![사용자 동의 설정](/assets/images/m365-readiness-82/e-x29-01.jpg)

![관리자 동의 요청 꺼짐](/assets/images/m365-readiness-82/e-x39-01.jpg)

사용자 동의는 "Microsoft에서 동의 설정을 관리하도록 허용(권장)"으로 되어 있다 — 저위험 권한에 한해 검증된 게시자 앱 동의를 허용하는 중간 단계 설정이다. 문제는 **관리자 동의 요청 워크플로가 꺼져 있다**는 것(아니요, 검토자 없음). 사용자가 동의할 수 없는 앱을 만나면 관리자에게 요청을 보낼 경로가 없으므로, 그림자 IT로 우회하거나 관리자 계정을 빌리는 쪽으로 흐르기 쉽다. 검토자를 지정하고 켜 두는 게 맞다.

## 4. 외부 협업

### x28 — 게스트 초대: 전원 허용, 모든 도메인

External Identities → 외부 협업 설정이다.

![외부 협업 설정](/assets/images/m365-readiness-82/e-x28-01.jpg)

- 게스트 초대 제한: **조직 내 모든 사용자(게스트·비관리자 포함)가 초대 가능** — 가장 포괄적
- 셀프 서비스 등록: 아니요
- 협업 제한: **모든 도메인에 초대 허용** — 가장 포괄적

게스트가 게스트를 초대할 수 있고, 초대 가능한 도메인 제한도 없다. 운영에서는 최소한 "멤버 권한이 있는 사용자만"으로 내리고, 필요하면 허용 도메인 목록으로 좁혀야 초대 경로가 추적된다.

### x53 — 테넌트 간 액세스 기본값

![테넌트 간 액세스 설정](/assets/images/m365-readiness-82/e-x53-01.jpg)

| 유형 | 적용 대상 | 상태 |
|---|---|---|
| B2B Collaboration 인바운드 | 외부 사용자·그룹 / 애플리케이션 | 모두 허용 |
| B2B 직접 연결 | 외부 사용자·그룹 / 애플리케이션 | 모두 차단 |
| 신뢰 설정 (MFA·규격 디바이스 신뢰) | — | 사용 안 함 |

B2B Collaboration이 기본값(모두 허용)이라 x28의 "모든 도메인 허용"과 겹쳐 외부 협업이 사실상 무제한이다. 직접 연결(공유 채널의 기반)만 차단되어 있는데, Teams 쪽에서는 공유 채널 외부 초대가 켜져 있어(x45) 정합성이 안 맞는다 — 직접 연결이 차단이면 공유 채널 외부 초대는 실제로 동작하지 않는다. 어느 쪽이 의도인지 정해서 맞춰야 한다.

### x44 — Teams 게스트 액세스

![Teams 게스트 액세스 1](/assets/images/m365-readiness-82/e-x44-01.jpg)

![Teams 게스트 액세스 2](/assets/images/m365-readiness-82/e-x44-02.jpg)

게스트 액세스는 Service default: On. 게스트의 사설 통화·화상 회의·화면 공유(전체 화면)·Meet now가 전부 허용이다. 그나마 **External participants can get control: Off**라 외부 참가자가 화면 제어권을 받을 수는 없다. 게스트 협업을 쓸 거라면 이 상태도 통용되지만, 화면 공유를 "단일 창"으로 좁히는 조직도 많다.

### x45 — 공유 채널: 외부 초대 켜짐

![Teams 정책의 공유 채널 설정](/assets/images/m365-readiness-82/e-x45-01.jpg)

Teams 정책(Global)에서 공유 채널 만들기·외부 사용자 초대·외부 공유 채널 참가가 전부 On이다. 위 x53에서 본 것처럼 B2B 직접 연결이 차단이라 지금은 동작하지 않는 설정인데, 누군가 직접 연결을 열면 그 즉시 외부 공유 채널이 전부 살아난다. 쓰지 않을 거면 여기도 꺼서 이중으로 잠그는 게 안전하다.

## 5. Teams 운영 — 전부 기본값

### x13 — 사용자 정책 24종 전부 Global

![사용자별 정책 목록](/assets/images/m365-readiness-82/e-x13-01.jpg)

임의 사용자의 정책 탭이다. 정책 24종이 **전부 Global(Org-wide default)**, 정책 패키지 None. 커스텀 정책이 하나도 없다는 뜻이다. 아래 항목들에서 그 기본값의 내용을 확인했다.

### x22·x23 — 회의 정책과 녹화·전사

![회의 정책 목록](/assets/images/m365-readiness-82/e-x22-01.jpg)

![녹화·전사·Copilot 설정](/assets/images/m365-readiness-82/e-x23-01.jpg)

회의 정책은 기본 6종 그대로(커스텀 0). Global 정책의 녹화·전사 블록을 열어 보면 — 회의 녹화 On, **녹화·전사·Copilot에 대한 참가자 동의 요구 Off**, 전사 On, 녹화 자동 만료 120일, Copilot은 "전사 저장 시 사용 가능". 녹화 동의 요구가 꺼져 있는 건 지역 규제에 따라 문제가 될 수 있는 지점이라, 운영 전 법무 검토 대상으로 분류했다.

### x48 — 이벤트 정책: 웨비나·타운홀 Everyone

![이벤트 정책 목록](/assets/images/m365-readiness-82/e-x48-03.jpg)

![이벤트 정책 상세 1](/assets/images/m365-readiness-82/e-x48-02.jpg)

![이벤트 정책 상세 2](/assets/images/m365-readiness-82/e-x48-01.jpg)

웨비나·타운홀 모두 On이고 참가 대상이 **Everyone**, 녹화 허용 유형도 Public, **외부 발표자 사전 검증은 "No verification needed"**다. 조직 외부 누구나 참가·발표 가능한 조합이라, 전사 공지성 이벤트를 쓸 게 아니라면 참가 대상을 "Everyone in your organization"으로 내리는 게 기본값이어야 한다.

### x49 — 메시징 정책: 외부 채팅에 파일·Loop 자동 공유

![메시징 정책 목록](/assets/images/m365-readiness-82/e-x49-04.jpg)

![메시징 정책 상세 1](/assets/images/m365-readiness-82/e-x49-03.jpg)

![메시징 정책 상세 2](/assets/images/m365-readiness-82/e-x49-01.jpg)

![메시징 정책 상세 3](/assets/images/m365-readiness-82/e-x49-02.jpg)

메시지 삭제·편집 허용, 읽음 확인 사용자 제어, Giphy PG 등은 통상 기본값이다. 눈에 띄는 건 맨 아래 — **"Automatically share files and Loop links with all people in external chats: Enabled"**. 외부 사용자와의 채팅에서 파일·Loop 링크가 참가자 전원에게 자동 공유된다는 설정으로, SPO 공유가 Anyone(x26)인 현 상태와 결합하면 내부 문서가 외부로 흘러가는 마찰이 가장 적은 경로가 된다.

### x24·x50·x51 — 앱과 업데이트

![앱 관리](/assets/images/m365-readiness-82/e-x24-01.jpg)

![조직 전체 앱 설정 1](/assets/images/m365-readiness-82/e-x24-02.jpg)

![조직 전체 앱 설정 2](/assets/images/m365-readiness-82/e-x24-03.jpg)

![앱 설정 정책](/assets/images/m365-readiness-82/e-x50-01.jpg)

![Teams 업데이트 정책](/assets/images/m365-readiness-82/e-x51-01.jpg)

앱 카탈로그 3,780개에 대해 **제3자 앱 "All third-party apps available"**, 커스텀 앱 설치·프리뷰 상호작용까지 전부 On이다. 사용자가 아무 제3자 앱이나 설치해 데이터 접근 동의를 줄 수 있는 상태다. 운영에서는 "허용 목록" 방식(기본 차단 + 심사 후 허용)으로 뒤집는 게 표준이다. 앱 설정 정책은 기본 2종(Global, FirstLineWorker), 업데이트 정책은 Microsoft controlled로 기본값이다.

## 6. SharePoint·OneDrive

### x26 — 외부 공유: 둘 다 Anyone

SharePoint 관리 센터 → Policies → Sharing이다.

![SPO 외부 공유 수준](/assets/images/m365-readiness-82/e-x26-01.jpg)

SharePoint·OneDrive 모두 **Anyone(Most permissive)** — 로그인 없는 익명 링크 공유가 가능한 최상위 개방 단계다. 이번 점검에서 가장 위험한 기본값이다. 운영 전환 시 "New and existing guests" 이하로 내리는 게 1순위다.

### x52 — 추가 공유 설정

![SPO 추가 공유 설정](/assets/images/m365-readiness-82/e-x52-01.jpg)

More external sharing settings를 펼치면 —

- 도메인별 공유 제한: 미사용
- 특정 보안 그룹만 외부 공유: 미사용
- **게스트가 소유하지 않은 항목 공유 허용: 체크됨**
- 게스트 액세스 자동 만료: 미사용
- 인증 코드 재인증 주기: 미사용

게스트가 자기 소유도 아닌 항목을 재공유할 수 있고, 게스트 액세스가 만료되지도 않는다. Anyone 공유(x26)와 겹치면 "한 번 나간 링크는 영원히 산다"가 된다.

### x56~x58 — 사이트 현황

![사이트 생성 설정](/assets/images/m365-readiness-82/e-x56-01.jpg)

![활성 사이트](/assets/images/m365-readiness-82/e-x57-01.jpg)

![삭제된 사이트 없음](/assets/images/m365-readiness-82/e-x58-01.jpg)

사이트 생성은 사용자에게 Allow(기본 경로 /sites/). 활성 사이트 9개, 저장소 사용량 21.00 MB / 1.24 TB. 삭제된 사이트는 없다. 샌드박스 규모라 문제는 없지만, 그룹 생성 개방(x27)과 마찬가지로 사이트 생성도 운영에서는 제한 대상이다.

### x60·x61 — 동기화 설정과 보고서 접근

![OneDrive 동기화 설정](/assets/images/m365-readiness-82/e-x60-01.jpg)

![OneDrive 보고서 접근 불가](/assets/images/m365-readiness-82/e-x61-01.jpg)

동기화는 도메인 가입 PC 제한·파일 형식 차단 모두 미사용 — 아무 PC에서나 동기화 가능하다. 한 가지 눈에 띄는 건 Reports → OneDrive accounts가 **"Access needed"**로 막힌 것. 전역 관리자인데도 보고서 페이지가 역할 요구를 띄우는 건 보고서 열람 권한이 별도 경로로 평가되기 때문으로 보이며, 점검 자동화 시 계정에 어떤 역할을 붙일지 정할 때 참고할 지점이다.

## 7. 디바이스 — Intune에 아무것도 없다

### x64·x66 — 디바이스 0대, 업데이트 링 0개

![Intune Windows 디바이스 없음](/assets/images/m365-readiness-82/e-x64-01.jpg)

![Windows 업데이트 링 없음](/assets/images/m365-readiness-82/e-x66-01.jpg)

Intune에 등록된 Windows 디바이스가 0대, 업데이트 링 정책도 0개다. E5에 Intune이 포함되어 있지만 디바이스 관리는 아예 시작하지 않은 상태다. 조건부 액세스에서 "규격 디바이스 요구"를 쓰려면 Intune 등록이 선행돼야 하므로, CA 전환 로드맵에 디바이스 온보딩이 같이 들어가야 한다.

### x12 — Entra Connect 미설치 (클라우드 전용)

![Entra Connect 미설치](/assets/images/m365-readiness-82/e-x12-01.jpg)

Entra Connect 동기화는 설치 안 됨, 동기화 실행 이력 없음, 페더레이션·Seamless SSO·통과 인증 전부 사용 안 함. **순수 클라우드 전용 테넌트**임이 확정된다. 온-프레미스 AD와의 하이브리드 구성은 없으므로 하이브리드 고려사항은 이 테넌트에서는 해당 없음으로 분류한다.

## 8. Purview — 기본 정책만 존재

### x78 — DLP: Microsoft가 만들어 둔 기본 3종

![DLP 정책 3종](/assets/images/m365-readiness-82/e-x78-01.jpg)

| 정책 | 모드 |
|---|---|
| Default DLP policy - Protect sensitive M365 Copilot interactions | Test with notifications |
| Default policy for Teams | On |
| Default policy for devices | On |

직접 만든 DLP 정책은 없고 Microsoft 기본 제공 3종뿐이다. 일부 민감 정보 유형만 커버되는 수준이라, 조직 데이터 분류 기준에 맞는 정책은 운영 전 별도로 설계해야 한다.

### x79 — 민감도 레이블: 기본 5종, 게시 정책 1건

![민감도 레이블 5종](/assets/images/m365-readiness-82/e-x79-02.jpg)

![레이블 게시 정책](/assets/images/m365-readiness-82/e-x79-01.jpg)

Personal / Public / General / Confidential / Highly Confidential — Microsoft가 만들어 주는 기본 레이블 체계 그대로이고, 게시 정책도 Global sensitivity label policy 1건뿐이다. 레이블이 "존재"하는 것과 사용자들이 실제로 "붙이는" 것은 다른 문제라, 운영 전환 시 기본 레이블 자동 적용과 하위 레이블 설계가 과제로 남는다.

### x69 — DSPM for AI 미시작, Purview 감사 활성화 필요

![DSPM for AI 시작 전](/assets/images/m365-readiness-82/e-x69-01.jpg)

Purview의 DSPM for AI 첫 화면에서 Get started 4단계가 전부 미완료인데, 그 1번이 **"Activate Microsoft Purview Audit — Required"**다. 감사 레코딩이 아직 켜지지 않았다는 사실이 여기서도 확인된다. 감사는 소급되지 않으므로 점검 중 가장 먼저 눌러야 하는 버튼이라는 결론은 그대로다.

## 9. 운영·모니터링

### x05·x65 — 사용 현황 보고서: 데이터 없음

![Teams 사용 현황 데이터 없음](/assets/images/m365-readiness-82/e-x05-01.jpg)

![사용 현황 개요 데이터 없음](/assets/images/m365-readiness-82/e-x65-01.jpg)

![서비스 상태 교차 확인](/assets/images/m365-readiness-82/e-x05-02.jpg)

M365 사용 현황 보고서가 Teams·전체 개요 모두 "데이터 없음"이다. 실사용자가 없는 샌드박스라 당연한 결과지만, 서비스 상태 화면에는 마침 "Admins may see multiple usage reports not updating"(MO1481173) 권고도 떠 있어서, 데이터 없음이 테넌트 특성인지 서비스 이슈인지 교차 확인이 필요했던 항목이다.

### x76 — 서비스 상태: 권고 7건, 메일 알림은 꺼짐

![서비스 상태 개요](/assets/images/m365-readiness-82/e-x76-02.jpg)

![서비스 상태 메일 알림 꺼짐](/assets/images/m365-readiness-82/e-x76-01.jpg)

활성 문제 7건이 전부 "권고" 수준(Exchange 회신 불가, Teams 연락처 표시, Purview 감사 로그 지연 등)이다. 문제는 **서비스 상태 메일 알림이 꺼져 있다**는 것 — 관리자가 포털에 들어와야만 장애를 알 수 있는 상태다. 알림 수신 체크 하나로 해결되는 항목이라 즉시 조치 대상으로 분류했다.

### x75 — 릴리스 채널: 표준 릴리스

![릴리스 기본 설정](/assets/images/m365-readiness-82/e-x75-01.jpg)

조직 설정 → 릴리스 기본 설정은 "모두에게 공개하는 표준 릴리스"다. 운영이라면 IT·파일럿 그룹만 대상 지정 릴리스로 선행시키는 구성이 권장된다. 화면의 "대상 릴리스가 2027년 1월에 사용 중지" 공지처럼 이 메뉴 자체가 개편 예정이라, 전환 전 메시지 센터 추적이 필요한 항목이기도 하다.

### x18·x35 — 지원 이력과 도메인

![서비스 요청 기록 없음](/assets/images/m365-readiness-82/e-x18-01.jpg)

![사용자 지정 도메인](/assets/images/m365-readiness-82/e-x35-01.jpg)

Microsoft 지원 요청 이력 0건, 사용자 지정 도메인은 1개(기본·사용 가능, 페더레이션 없음)다. 도메인 구성이 단순하다는 건 전환 변수도 적다는 뜻이라 긍정적인 항목이다.

### x70 — 에이전트: 카탈로그 361개, 에이전트 ID는 0

![M365 에이전트 목록](/assets/images/m365-readiness-82/e-x70-01.jpg)

![Entra Agent ID 없음](/assets/images/m365-readiness-82/e-x70-02.jpg)

M365 관리 센터의 에이전트 메뉴에는 마켓플레이스 카탈로그 361개가 보이지만 활성 사용자·세션은 전부 0이고, Entra의 Agent ID(에이전트 자격 증명) 역시 0개다. AI 에이전트가 아직 아무것도 돌지 않는다는 확인이다. 다만 Teams 제3자 앱 전면 허용(x24) 상태라, 에이전트가 "0개로 유지된다"는 보장은 없다 — 앱 거버넌스를 닫는 것이 에이전트 거버넌스의 선행 조건이 된다.

### x32 — 액세스 검토 없음

![액세스 검토 없음](/assets/images/m365-readiness-82/e-x32-01.jpg)

Identity Governance의 액세스 검토가 0건이다. 게스트에 역할이 들어가 있는 테넌트(x01)에서 액세스 검토가 없다는 건, 그 권한이 적절한지 주기적으로 묻는 장치가 없다는 뜻이다. P2에 포함된 기능이므로 게스트·관리자 역할 대상 분기 검토부터 만드는 게 적절하다. 화면의 공지대로 2026년 1월 15일부터 게스트 대상 Governance 기능에 Azure 구독 연결이 필요해진 점도 전환 계획에 반영해야 한다.

## 10. 점검 자동화 앱 상태

### x11·x14 — readiness-audit-app: 인증서 전용, 소유자 1명

![앱 인증서·비밀](/assets/images/m365-readiness-82/e-x11-01.jpg)

![앱 소유자](/assets/images/m365-readiness-82/e-x14-01.jpg)

점검 자동화용으로 등록한 `readiness-audit-app`은 [인증서 기반 app-only 구성](/iam/m365-graph-app-only/) 그대로다 — 인증서 1건(CN=readiness-audit-app, 2026.10.20~2027.4.20), **클라이언트 비밀 0건**. 비밀 없이 인증서만 쓰는 상태는 의도한 구성이다. 소유자는 1명인데, 소유자 계정이 잠기면 앱 관리가 같이 막히므로 운영이라면 소유자 2명 이상이 권장이다. 인증서 만료(2027년 4월)는 갱신 일정에 등록했다.

## 정리 — 운영 전환 전 조치 목록

| 우선순위 | 항목 | 현재 → 목표 |
|---|---|---|
| 1 | Purview 감사 (x69) | 미활성 → 레코딩 시작 (소급 불가, 즉시) |
| 2 | 게스트 전역 관리자 (x01) | 역할 보유 → 회수, 내부 관리 계정으로 대체 |
| 3 | SPO 외부 공유 (x26·x52) | Anyone·재공유 허용·무만료 → New/existing guests 이하, 게스트 재공유 차단, 액세스 만료 설정 |
| 4 | 조건부 액세스 (x19) | 적용 이력 0 → 보고 전용 정책 생성·검증 후 보안 기본값과 교체 |
| 5 | MFA·SSPR 등록 (x38·x09) | 2명 → 등록 캠페인 후 MFA 필수, SSPR 활성화 |
| 6 | 게스트 초대 범위 (x28) | 전원·전 도메인 → 멤버 이상, 필요시 도메인 허용 목록 |
| 7 | Teams 제3자 앱 (x24) | 전면 허용 → 기본 차단 + 심사 허용 목록 |
| 8 | 외부 채팅 파일 자동 공유 (x49) | Enabled → 비활성화 검토 |
| 9 | 서비스 상태 메일 알림 (x76) | 꺼짐 → 수신 설정 (즉시, 무비용) |
| 10 | 그룹 거버넌스 (x06·x27·x43) | 만료·명명 정책 없음, 생성 전원 개방 → 만료 정책·명명 규칙·생성 제한 |

이 외에 관리자 동의 요청 워크플로(x39), 액세스 검토(x32), 휴면 계정 정리(x37), Intune 디바이스 온보딩(x64), 공유 채널 설정 정합성(x45·x53), 이벤트 정책 참가 범위(x48), 조직 DLP·레이블 설계(x78·x79)가 후순위 과제로 남는다.

샌드박스라서 전부 기본값이어도 사고가 없었을 뿐, 같은 상태의 테넌트가 운영이라면 1~3번은 점검 당일 조치 대상이다. 다음 글에서는 `readiness-audit-app`으로 이 체크리스트를 스크립트화해서, 화면 캡처 없이 같은 결과를 떠내는 과정을 정리할 예정이다.
