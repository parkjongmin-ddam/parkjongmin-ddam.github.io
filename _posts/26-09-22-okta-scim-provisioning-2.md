---
layout: single
title: "Okta SCIM 프로비저닝 검증 (2) — 장애·퇴사·복직·그룹 전파 체인"
excerpt: "1편이 Okta가 SCIM 서버에 보내는 요청의 형태였다면, 이번엔 그 요청이 실패했을 때다. 연결 장애 중 할당은 Retry로 복구되지만 404는 안 된다는 것, AD Disable 한 번에 Okta가 1초 안에 여섯 가지를 연쇄 처리하되 앱 비활성화 푸시가 실패하면 재시도 없이 관리자에게 수동 위임된다는 것, 복직은 자동이 아니라 Okta 수동 Activate를 포함한 4단계라는 것, 그리고 AD 기점 그룹 멤버십 변경은 앱 그룹 PUT을 촉발하지만 Unassign과 Import 링크는 다음 동기화까지 기다린다는 것까지 — 라이프사이클 이벤트에서 Okta가 자동으로 하는 것과 관리자가 해야 하는 것의 경계를 실측한 기록이다."
date: 2026-09-22
categories: [IAM]
tags: [Okta, SCIM, Provisioning, Lifecycle, Active-Directory, Deprovisioning, 실측]
---

## 1. 배경

[1편]({% post_url 26-09-22-okta-scim-provisioning %})에서 Okta가 SCIM 서버에 보내는 요청의 형태를 봤다. 이 글은 그 요청이 **실패했을 때**, 그리고 AD에서 시작된 변경(비활성화·복귀·그룹 멤버십)이 Okta를 거쳐 앱까지 어떻게 도달하는지를 본다.

구성·마스킹 규칙은 1편과 동일하다. AD 쪽은 Okta AD Agent로 연결된 랩 도메인(마스킹)이고, 사용자·그룹 모두 AD-sourced다.

질문은 하나다. **라이프사이클 이벤트에서 Okta가 자동으로 하는 것과 관리자가 해야 하는 것의 경계가 어디인가.**

## 2. 연결 장애 중 할당 → 복구 후 Retry

- 터널 주소가 바뀐 상태(Okta는 구 주소 사용)에서 사용자를 할당하면 배너 "Error while verifying if user exists: null"이 뜬다. HTTP 오류가 아니라 응답 부재다. 서버 로그에 요청이 없다
- Base URL 갱신 → Tasks → Retry Selected → filter `GET` → `POST` 201로 정상 처리된다
- [1편 8절]({% post_url 26-09-22-okta-scim-provisioning %})(앱 리소스 부재 404)은 Retry로 복구 불가였지만, 연결 장애는 Retry로 복구된다. **같은 Tasks 목록이라도 실패 원인에 따라 결과가 갈린다**

## 3. 퇴사 체인 — AD Disable → Okta → 앱

`Disable-ADAccount` → Incremental Import → Okta 사용자 Deactivated(자동, 확인 화면 없음). System Log에는 1초 내에 다음이 연쇄로 찍힌다.

```
Remove user's application membership (SCIM 앱)       SUCCESS
Deactivate Okta User                                 SUCCESS
Clear user session                                   SUCCESS
Successfully deleted member of an app group          SUCCESS
Delete user triggered by import process (AD AppUser) SUCCESS
Push user deactivation to external application       FAILURE: Bad Gateway
```

- 마지막 푸시가 터널 502로 실패했다. 서버에 요청이 도달하지 않았다
- 결과: Okta 쪽은 전부 정리됐으나 **앱 계정은 active:true로 잔존한다**
- Tasks에는 "Application accounts need deprovisioning — Go to third-party apps and manually disable user accounts"가 남는다. **Retry가 없다.** Mark All Complete / Don't create deprovisioning tasks만 제공된다
- 비활성화 푸시는 1회 시도, 실패 시 재시도 없음, 관리자 수동 위임이다. Okta 쪽 할당이 이미 제거돼 재트리거 수단도 없다. 이 Tasks 또는 System Log의 deprovision FAILURE를 모니터링하지 않으면 SaaS에 활성 계정이 남은 채 대시보드는 정상으로 보인다
- 부수 관찰: AD 비활성화 시 Okta는 사용자 비활성화뿐 아니라 **AD AppUser 링크를 삭제**한다(4절 복직 절차가 꼬이는 원인)

## 4. 복직 체인 — AD Enable → Okta

앱 관리자의 수동 처리를 재현하기 위해 서버 저장소에서 해당 계정을 active:false로 직접 수정해 두고 진행했다.

- `Enable-ADAccount` → Incremental Import → 확인 화면에 "신규 AD 사용자"로 등장하고, 기존 Okta 계정과 EXACT match가 제안된다("1 need review · 4 confirmed" — 이 사용자만 링크가 끊겨 있었다)
- EXACT로 Confirm → 실패: "App assignment attempted for user 00u… but user is in inactive status INACTIVE". **Deactivated 사용자에게는 AD 링크를 걸 수 없다**
- People → 사용자 상세(Deactivated 상태에서는 Activate/Delete 버튼만 있다) → Activate → "Pending user action"(Provisioned). Active로 바로 가지 않는다
- 다시 Confirm → 성공. "Add user to application membership — Active Directory SUCCESS"
- SCIM 앱 할당은 복구되지 않는다(3절에서 Individual 할당이 제거됐기 때문. 그룹 기반 할당이었다면 자동 복귀했을 것이다)
- 로그인: 접두어만 넣으면 "지원팀에 연락" 오류, 전체 UPN으로 성공. 로그인 후에도 Pending이 유지되고 Activate 이벤트가 없다. 위임 인증 사용자는 Okta 비밀번호 설정 절차가 없어 Provisioned에 머문다. 실사용은 정상이다
- 정리하면 **복직은 자동이 아니다**: AD Enable → Import → Okta 수동 Activate → Import 확정 → 앱 재할당

## 5. AD 그룹 멤버 변경 → 앱 그룹 전파

에이전트 VM 미기동 시 Agent Monitors에 "Disruption — Agent connection is down"이 뜨고, 기동 후 Operational로 돌아온다. AD 기점 변경은 전부 DC에서 `Remove-ADGroupMember` / `Add-ADGroupMember`로 만들고, Directory Integrations에서 Incremental Import를 수동 실행해 전파시켰다.

![DC에서 AD 그룹 멤버 변경 — Remove/Add-ADGroupMember 실행](/assets/images/okta02/01-ad-group-member-change.png)

![Directory Integrations — Import Now 실행](/assets/images/okta02/03-import-now.png)

![Incremental Import 다이얼로그 — 그룹·OU 변경도 반영된다는 문구](/assets/images/okta02/02-incremental-import-dialog.png)

- (추가) AD 그룹에 앱 미할당 사용자 추가 → Import → 앱 그룹 `GET`×2 → `PUT`×2, members 변화 없음(미할당 사용자는 제외). AD 기점 변경은 동기화를 촉발하지만 [1편 10절]({% post_url 26-09-22-okta-scim-provisioning %})의 "할당된 사용자만" 규칙이 그대로 적용된다

![Import 후 Okta 그룹 People — 미할당 사용자 포함 4명](/assets/images/okta02/04-okta-group-4-members.png)

![(추가) 서버 로그 — 그룹 GET/PUT ×2, members는 3명 그대로](/assets/images/okta02/05-group-put-unchanged.png)

- (제거) AD 그룹에서 할당된 사용자 제거 → Import → `PUT`(변경 전 3명) → `PUT`(2명). 즉시 전파된다

![(제거) 후 다시 Import Now](/assets/images/okta02/06-import-after-remove.png)

![(제거) 서버 로그 — PUT 변경 전 3명 → PUT 2명](/assets/images/okta02/07-group-put-3-to-2.png)

- (원복) 재추가 → Import → `PUT` 3명 ×2

![(원복) DC에서 재추가 — AD 그룹 멤버 4명 확인](/assets/images/okta02/08-ad-group-re-add.png)

- [1편 14절]({% post_url 26-09-22-okta-scim-provisioning %})(Import 링크는 그룹 푸시를 촉발하지 않음)과 대비된다. **AD 기점 멤버십 변경은 촉발한다**
- "GET→PUT 2회" 패턴의 첫 PUT은 제거 케이스에서는 변경 전 목록, 추가 케이스에서는 변경 후 목록이었다. 서버 입장에서는 멱등이라 무해하나, 대규모 그룹에서는 전체 목록이 2회씩 쓰인다는 뜻이다

## 6. 비활성 멤버와 Push now

- 사용자 Unassign → 사용자 `GET`/`PUT active:false`만 발생하고 그룹 PUT은 없다([1편 11절]({% post_url 26-09-22-okta-scim-provisioning %}) 재현)
- Push now → 그룹 `GET`×2 → `PUT`(변경 전 3명) → `PUT`(**2명, 비활성 사용자 제외**)

![Push Groups — Push now로 강제 동기화](/assets/images/okta02/09-push-now.png)

![서버 로그 — Unassign 시 사용자 PUT active:false만, Push now 후 PUT members 2명(비활성 제외)](/assets/images/okta02/10-unassign-push-now-log.png)

- 비활성 앱 계정은 강제 동기화 시 members에서 제외된다. Unassign 직후에는 앱 그룹에 비활성 계정이 남는 창이 있고, 다음 동기화(Push now 또는 멤버십 이벤트)에서 정리된다
- 재할당 → filter → `GET`/`PUT active:true` → 그룹 `GET`/`PUT` 3명 복귀([1편 12절]({% post_url 26-09-22-okta-scim-provisioning %}) 패턴)

![서버 로그 — 재할당 시 PUT active:true 후 그룹 PUT 3명 복귀](/assets/images/okta02/11-reassign-restore-log.png)

## 7. 정리 — Okta가 하는 것 / 관리자가 하는 것

| 이벤트 | Okta 자동 | 관리자 수동 |
|---|---|---|
| 연결 장애 중 할당 실패 | Tasks 기록 | Retry (복구됨) |
| 앱 쪽 계정 삭제 후 프로필 푸시 | 404 → Tasks 기록 | Unassign → 재할당 (Retry는 무효) |
| AD Disable | Okta 비활성화·세션 종료·할당 제거·그룹 제거·AD 링크 해제·앱 비활성화 푸시 1회 | 푸시 실패 시 앱에서 직접 비활성화 (Retry 없음) |
| AD Enable | Import 시 EXACT 매치 제안 | Okta Activate → Import 확정 → 앱 재할당 |
| AD 그룹 멤버 변경 | Import 후 앱 그룹 PUT | — |
| Unassign 후 앱 그룹 | 다음 동기화 때 제외 | 즉시 정리하려면 Push now |
| Import로 링크된 사용자의 그룹 | — | Push now |

- 프로비저닝의 강점은 생성·변경 자동화이고, 약점은 **비활성화 실패의 복구가 자동이 아니라는 점**이다. 퇴사 처리 자동화는 Tasks 모니터링 없이는 완성되지 않는다
- AD Disable/Enable은 Okta에서 퇴사·재입사와 같은 무게다. 휴직자 처리를 AD Disable로 하면 복귀마다 수동 4단계를 밟게 된다
- 그룹 동기화가 따라오는 조건은 경로마다 다르다(할당·AD 변경은 즉시, Unassign·Import 링크는 다음 동기화). "앱 쪽 그룹이 왜 이런가"는 어느 경로로 만들어졌는지를 먼저 봐야 한다

## 8. 실습 중 실수

- 제거와 추가 AD 변경을 Import 없이 연달아 실행해 순서를 다시 잡았다. AD 기점 실험은 **변경 1건 → Import 1회**를 지켜야 한다
- Push now를 캡처용으로 두 번 눌러 로그에 동기화가 두 번 남았다. 두 번째가 무변경(2명·2명)이라 해석에는 지장이 없었으나, 조작 횟수는 기록해야 한다
- 에이전트 VM을 켜지 않고 Import를 시도했다. 이전 랩에서도 한 실수다

## 9. 미실측

- Import 시 Imported User Name 공란의 원인(To Okta 매핑)
- To Okta "앱에서 제거된 사용자" 처리 설정과 실제 동작
- Staged 사용자 활성화 경로 비교
- PATCH 모드, 5xx 재시도 간격, 에이전트 다운 상태에서 Import Now 오류 메시지
