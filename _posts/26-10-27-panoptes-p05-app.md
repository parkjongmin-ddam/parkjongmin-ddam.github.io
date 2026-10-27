---
layout: single
title: "[웹 탐지] panoptes-detect P0.5 — 탐지를 전제로 설계한 보호 대상 서비스와 인증 공격 상관분석"
excerpt: "panoptes-detect의 P0.5 단계. P0의 echo 백엔드를 직접 개발한 FastAPI 서비스(panoptes-shop)로 교체하고, 로그인 실패·계정 잠금·권한 거부 같은 보안 이벤트를 JSON 한 줄 로그로 남기도록 설계했다. 앱 로그를 Wazuh로 수집해 이벤트 룰(100300번대)을 만들고, 같은 IP의 로그인 실패 8회를 묶는 상관분석 룰(100302)이 실제로 발생하는 것을 확인했다. 구현 중 겪은 Starlette 미들웨어의 ContextVar 전파 문제, Wazuh JSON 디코더의 user→dstuser 매핑, OrbStack 게이트웨이로 바뀌는 client_ip 문제도 정리했다."
date: 2026-10-27
categories: ["Security", "웹 탐지"]
permalink: "/infra/security/panoptes-p05-app/"
tags: [FastAPI, Wazuh, SIEM, 상관분석, 크리덴셜스터핑, 브루트포스, MITRE-ATTACK, 탐지룰, 실측]
---

P0에서 요청 → WAF → 감사 로그 → Wazuh alert 파이프라인을 확인했다. 그때 백엔드는 요청을 그대로 돌려주는 echo 서버였다. echo 서버로는 로그인 실패나 권한 위반 같은 비즈니스 로직 이벤트를 만들 수 없다. P1 오탐 튜닝에 들어가기 전에 보호 대상 서비스를 먼저 만들었고, 이 글은 그 과정(P0.5)을 정리한다.

> 요약
> - FastAPI + PostgreSQL로 가상 쇼핑 서비스 panoptes-shop을 만들어 WAF 뒤에 배치했다. 회원·세션 로그인, 계정 잠금, 주문 소유자 검사, 관리자 권한, 파트너 API 키, 파일 업로드 제한을 넣었다.
> - 기능보다 로그 설계를 먼저 정했다. 요청마다 JSON 한 줄을 남기고, 보안 이벤트는 `event` 코드로 구분한다. WAF가 넘긴 `X-Request-ID`를 그대로 받아 WAF 로그와 앱 로그를 같은 ID로 잇는다.
> - 앱 로그를 Wazuh로 수집하고 이벤트 룰 8개(100300~100307)를 만들었다. 기본 접근 로그는 level 0으로 두어 알림을 내지 않는다.
> - 같은 IP의 로그인 실패를 묶는 상관분석 룰 100302(8회/120초, level 10)가 실제로 발생했다. 단일 요청만 보는 WAF 룰로는 만들 수 없는 탐지다.
> - WAF를 거친 요청의 `client_ip`가 OrbStack 게이트웨이 주소(192.168.107.1)로 기록된다. IP 기반 탐지(P3) 전에 해결해야 할 항목으로 남겼다.

## 1. 왜 서비스를 직접 만들었나

탐지 운영 실습에 필요한 것은 기능이 많은 서비스가 아니라, 탐지할 거리가 로그로 남는 서비스다. 공개된 취약 앱을 가져다 쓰는 방법도 있지만 로그 형식을 바꾸기 어렵다. 직접 만들면 "어떤 이벤트를 어떤 필드로 남길지"를 먼저 정하고 코드를 그 기준에 맞출 수 있다.

설계 순서는 다음과 같았다.

1. 탐지하고 싶은 상황을 정한다(로그인 실패 급증, 계정 잠금, 남의 주문 조회, 잘못된 API 키, 업로드 위반).
2. 상황마다 이벤트 코드를 붙인다.
3. 그 이벤트가 나오도록 기능을 구현한다.

## 2. 서비스 구성

| 항목 | 값 |
| --- | --- |
| 프레임워크 | FastAPI 0.115 + Uvicorn (Python 3.12) |
| DB | PostgreSQL 16 |
| 비밀번호 해시 | argon2 |
| 세션 | 서버측 세션 테이블 + 쿠키(HttpOnly, SameSite=Lax) |
| 컨테이너 | python:3.12-slim, 비특권 사용자(uid 10001) |

| 영역 | 엔드포인트 | 보안 동작 |
| --- | --- | --- |
| 회원 | `/auth/signup`, `/auth/login`, `/auth/logout` | 로그인 실패 누적 시 계정 잠금(5회, 10분) |
| 주문 | `/orders`, `/orders/{id}` | 본인 주문만 조회. 남의 주문은 존재를 숨기려 404로 응답 |
| 관리자 | `/admin/users` | role=admin만 허용 |
| 파트너 API | `/partner/products` | `X-API-Key` 인증, DB에는 SHA-256 해시만 저장 |
| 파일 | `/me/avatar` | 이미지 형식·크기 제한 |

컨테이너 네트워크는 세 구역으로 나눴다. 외부 포트는 WAF만 연다. 앱은 WAF와 DB 사이에만 있고, DB는 앱에서만 접근할 수 있다.

```
client → waf → app → db
  edge   edge·dmz   dmz·internal   internal
```

## 3. 로그 설계

요청마다 JSON 한 줄을 stdout과 파일에 남긴다.

| 필드 | 내용 |
| --- | --- |
| `request_id` | WAF가 넘긴 `X-Request-ID`. 없으면 앱이 생성 |
| `client_ip` | `X-Forwarded-For`의 첫 값(WAF 뒤에 있을 때만 신뢰) |
| `method`, `path`, `status`, `latency_ms` | 요청 메타 |
| `user_id` | 인증된 경우 |
| `event` | 보안 이벤트 코드 |

| event | 발생 조건 |
| --- | --- |
| `auth.login.success` | 로그인 성공 |
| `auth.login.failure` | 로그인 실패(사유: unknown_user / bad_password / locked) |
| `auth.lockout` | 계정 잠금 발생 |
| `authz.denied` | 소유자 불일치, role 부족 |
| `apikey.invalid` | API 키 없음·불일치 |
| `upload.rejected` | 파일 형식·크기 위반 |

비밀번호, 세션 값, API 키 원문은 어떤 로그에도 남기지 않는다. 테스트에서 회원가입·로그인에 쓴 비밀번호 문자열이 로그 전체에 없는지 확인하는 항목을 따로 두었다.

WAF를 거친 실제 로그 예시는 다음과 같다.

```json
{"ts":"2026-10-27T10:29:11.643111+00:00","logger":"panoptes.app","request_id":"6f345073e681b770","client_ip":"192.168.107.1","method":"POST","path":"/auth/login","status":401,"latency_ms":68.0,"event":"auth.login.failure","reason":"bad_password","user":"<user-a>","attempts":1}
```

## 4. 구현 중 확인한 두 가지

pytest로 기능·보안 동작·로그 위생 10개 항목을 검증했다. 처음에는 테스트 대부분이 실패했고, 원인은 두 가지였다.

**타임존 비교 오류.** 테스트는 SQLite로 돌렸는데, SQLite는 `DateTime(timezone=True)` 값을 타임존 없이(naive) 돌려준다. 앱의 현재 시각은 UTC aware라 세션 만료 비교에서 `can't compare offset-naive and offset-aware datetimes`가 났다. PostgreSQL은 aware로 돌려주므로 운영에서는 문제가 없지만, 비교 직전에 UTC aware로 맞추는 보정 함수를 두어 양쪽에서 동작하게 했다.

**보안 이벤트가 로그에 안 실림.** 핸들러가 ContextVar에 이벤트를 넣고 미들웨어가 읽는 구조였는데, 이벤트가 로그에 나오지 않았다. Starlette의 `BaseHTTPMiddleware`는 엔드포인트를 별도 컨텍스트에서 실행하므로 엔드포인트에서 설정한 ContextVar 값이 미들웨어로 돌아오지 않는다. 같은 Request 객체를 공유하는 `request.state`로 바꾸자 10개 테스트가 모두 통과했다.

## 5. 앱 로그를 Wazuh로 수집

P0에서 만든 수집 구조를 그대로 썼다. 앱이 `/var/log/panoptes/app.log`에도 로그를 쓰고, 호스트의 `logs/app`에 마운트한다. manager의 `panoptes-waf` 그룹 `agent.conf`에 경로를 추가해 agent로 배포했다.

```xml
<localfile>
  <log_format>json</log_format>
  <location>/Users/&lt;user&gt;/lab/panoptes-detect/logs/app/app.log</location>
  <label key="panoptes_source">app</label>
</localfile>
```

앱은 비특권 사용자로 돌기 때문에 마운트한 로그 디렉터리에 쓰기 권한이 필요하다. 검증 환경에서는 디렉터리 권한을 열어 두고 진행했다.

## 6. 앱 이벤트 룰

| 룰 | level | 조건 | MITRE |
| --- | --- | --- | --- |
| 100300 | 0 | `logger=panoptes.app` (기본 접근 로그, 알림 없음) | - |
| 100301 | 5 | `event=auth.login.failure` | T1110 |
| 100302 | 10 | 같은 `client_ip`의 100301이 120초 안에 8회 | T1110 |
| 100303 | 10 | `event=auth.lockout` | T1110 |
| 100304 | 6 | `event=authz.denied` | T1190 |
| 100305 | 9 | 같은 `client_ip`의 100304가 60초 안에 6회 | T1190 |
| 100306 | 5 | `event=apikey.invalid` | T1110 |
| 100307 | 5 | `event=upload.rejected` | - |

상관분석 룰은 `if_matched_sid`로 하위 이벤트를 지정하고, `same_field`로 묶을 기준(`client_ip`)을, `frequency`·`timeframe`으로 횟수와 시간 범위를 정한다.

```xml
<rule id="100302" level="10" frequency="8" timeframe="120">
  <if_matched_sid>100301</if_matched_sid>
  <same_field>client_ip</same_field>
  <description>panoptes-app: repeated login failures from same IP (brute force / credential stuffing)</description>
  <mitre><id>T1110</id></mitre>
</rule>
```

`wazuh-logtest`로 먼저 확인했다. 이벤트가 없는 `/health` 요청은 100300(level 0)에 매칭되어 알림이 생기지 않았다. 수집은 되지만 보안 이벤트가 아니면 알림을 내지 않는 구조가 의도대로 동작했다.

## 7. 상관분석 검증

같은 출발지에서 두 계정(`<user-a>`, `<user-b>`)을 번갈아 가며 로그인 실패를 10회 발생시켰다. 계정 하나에 실패를 몰지 않고 여러 계정에 나눠 시도하는 크리덴셜 스터핑에 가까운 형태다.

![인증 이벤트 alert 목록 — 100301·100302·100303](/assets/images/2026-10-27-panoptes-p05-app/01-auth-correlation-list.jpg)

- 100301: 로그인 실패가 개별 alert로 쌓였다.
- 100303: 두 계정이 각각 잠금 임계값(5회)에 도달해 잠금 alert 2건이 생겼다.
- 100302: 같은 IP의 실패가 8회에 도달하자 상관분석 alert 1건이 생겼다.

![100302 상세 — previous_output과 frequency 8](/assets/images/2026-10-27-panoptes-p05-app/02-bruteforce-100302-detail.jpg)

100302 상세의 `previous_output`에는 묶인 이전 이벤트들이 그대로 남는다. `rule.frequency: 8`과 함께 어떤 요청들이 하나의 알림으로 묶였는지 확인할 수 있다. 개별 계정 기준으로는 잠금 임계값에 못 미친 시도라도, 출발지 기준으로 묶으면 공격 패턴으로 보인다. WAF는 요청 하나씩 판단하므로 이런 탐지는 SIEM 단계에서 만든다.

## 8. user 필드가 비어 나온 문제

처음 alert의 설명은 `login failure (reason bad_password, user )`처럼 사용자명이 비어 있었다. Wazuh의 JSON 디코더가 로그의 `user` 키를 정적 필드 `dstuser`로 매핑하기 때문이다. alert의 `data` 아래에도 `user`가 아니라 `dstuser`로 들어가 있었다. 룰 설명의 `$(user)`를 `$(dstuser)`로 바꾸자 `user <user-b>`처럼 표시됐다. 위 목록 캡처에는 수정 전(`user )`)과 수정 후(사용자명 표시) alert가 함께 남아 있다.

## 9. 트러블슈팅

| 증상 | 원인 | 조치 |
| --- | --- | --- |
| `.env`의 `SESSION_SECRET`에 `$(openssl rand -hex 32)` 문자열이 그대로 들어감 | heredoc을 `<<'EOF'`(따옴표)로 열면 명령 치환이 일어나지 않음 | `<<EOF`로 바꿔 실행 |
| 앱 로그에 보안 이벤트 누락 | `BaseHTTPMiddleware`에서 ContextVar 미전파 | `request.state` 사용 |
| 세션 만료 비교 TypeError(테스트) | SQLite가 naive datetime 반환 | 비교 직전 UTC aware로 보정 |
| alert 설명에 사용자명 공란 | JSON 디코더의 `user` → `dstuser` 매핑 | 룰 설명을 `$(dstuser)`로 수정 |

## 10. 열린 항목

| 항목 | 내용 | 처리 단계 |
| --- | --- | --- |
| client_ip | WAF를 거친 요청이 모두 OrbStack 게이트웨이(192.168.107.1)로 기록됨. 앱의 `X-Forwarded-For` 처리는 정상이고, WAF가 받는 시점에 이미 원 IP가 바뀐 상태 | P3 전 원 IP 보존 |
| 외부 클라이언트 | Windows PC(유선, Hyper-V External 스위치)에서 Mac mini(무선)로 접속이 되지 않아 외부 호스트 기준 IP 기록은 아직 확인하지 못함 | 네트워크 정리 후 |

지금 구조에서는 100302의 "같은 IP" 조건이 사실상 "WAF를 거친 모든 요청"과 같다. 검증 환경에서 상관분석이 동작하는 것은 확인했지만, 실제로 IP 단위 탐지가 의미를 가지려면 원 IP 보존이 먼저다.

## 11. 정리

- 보호 대상 서비스를 직접 만들어, 탐지하고 싶은 상황에서 이벤트 코드부터 정하고 로그를 설계했다.
- WAF가 넘긴 `X-Request-ID`를 앱이 그대로 쓰도록 해 WAF 로그와 앱 로그를 같은 ID로 연결했다.
- 앱 이벤트 룰과 상관분석 룰을 만들고, 같은 IP의 로그인 실패 8회가 하나의 상위 alert(100302)로 묶이는 것을 실측했다.
- 다음 글(P1)은 정상 트래픽이 WAF 룰에 걸리는 오탐을 찾고 줄이는 과정을 다룬다.

## 참고

- [Wazuh — Centralized configuration (agent.conf)](https://documentation.wazuh.com/4.14/user-manual/reference/centralized-configuration.html)
- [Wazuh — Custom rules](https://documentation.wazuh.com/4.14/user-manual/ruleset/rules/custom.html)
- [Wazuh — wazuh-logtest](https://documentation.wazuh.com/4.14/user-manual/reference/tools/wazuh-logtest.html)
- [MITRE ATT&CK T1110 — Brute Force](https://attack.mitre.org/techniques/T1110/)
