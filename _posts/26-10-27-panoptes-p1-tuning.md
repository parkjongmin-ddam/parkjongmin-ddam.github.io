---
layout: single
title: "[웹 탐지] panoptes-detect P1 — 오탐은 룰을 끄는 게 아니라 원인을 없애서 잡는다"
excerpt: "panoptes-detect의 P1 단계. 공격 페이로드 없는 정상 사용 흐름(회원가입·로그인·주문·파트너 API)을 WAF에 흘려 어떤 CRS 룰에 걸리는지 집계했다. 특수문자가 든 정상 입력은 SQLi·XSS 룰에 걸리지 않았고, 실질 오탐은 숫자 IP Host를 잡는 920350 하나였다. 룰을 끄는 대신 원인(IP 직접 접속)을 없애 오탐 0건과 탐지 유지 둘 다 확인했다. 도중에 urllib이 Host 헤더를 덮어쓴다고 잘못 판단했던 과정과, RelevantOnly 감사 로그 때문에 정상 요청이 안 보이는 것을 실패로 오인한 경험도 함께 적는다."
date: 2026-10-27
categories: ["Security", "웹 탐지"]
permalink: "/infra/security/panoptes-p1-tuning/"
tags: [ModSecurity, CRS, WAF, 오탐, 튜닝, libinjection, Wazuh, 실측]
---

P0에서 탐지 파이프라인을, P0.5에서 보호 대상 서비스를 만들었다. 차단 모드로 올리기 전에 정상 트래픽이 WAF 룰에 걸리는지 확인해야 한다. 차단 모드에서 오탐은 곧 정상 사용자의 403이다. 이 글은 오탐을 수집하고 조치한 P1 기록이다.

> 요약
> - 정상 사용 흐름 14건을 WAF에 보내 CRS 룰 매칭을 룰 ID별로 집계했다. 아포스트로피·따옴표·`=`·`+`·`#`가 든 정상 입력은 SQLi(942xxx)·XSS(941xxx) 룰에 걸리지 않았다.
> - 실질 오탐은 920350(Host 헤더가 숫자 IP) 하나였다. 검증 환경에서 `127.0.0.1:8080`으로 접속했기 때문이다.
> - 룰을 비활성하지 않았다. WAF에 서비스 도메인을 설정하고 트래픽이 도메인 Host로 접속하게 바꿔 원인을 없앴다. 예외 룰 0개.
> - 양방향으로 확인했다. 도메인 Host는 920350 0건, 숫자 IP Host는 계속 탐지. 오탐 해소와 탐지 유지를 동시에 만족한다.
> - 중간에 "urllib이 Host 헤더를 덮어쓴다"고 잘못 판단했다. 나중에 따로 검증하니 urllib도 지정한 Host를 그대로 보냈다. 감사 로그가 RelevantOnly라 룰에 안 걸린 정상 요청은 기록되지 않는데, 그 "안 보임"을 실패로 읽은 것이 원인이었다.

## 1. 오탐을 어떻게 모았나

오탐은 "정상 트래픽이 룰에 걸리는 것"이다. 그러니 정상 트래픽부터 있어야 한다. `scripts/normal_traffic.py`가 공격 페이로드 없이 서비스를 실제로 쓰는 흐름을 만든다.

- 회원가입 → 로그인 → 주문 생성·조회 → 로그아웃
- 파트너 API 키로 상품 조회

여기에 특수문자가 든 정상 입력을 일부러 섞었다. 사용자 이름 `O'Brien`, 따옴표가 든 주문 메모, `=`·`+`·`#`가 든 값. SQLi·XSS 룰이 단순 특수문자에 반응하는지 보려는 것이다.

보낸 뒤 Wazuh에서 `panoptes_source=modsecurity` 알림을 룰 ID·메시지별로 집계했다.

## 2. 결과: 오탐은 한 종류

| 룰 | 메시지 | 판정 |
| --- | --- | --- |
| 920350 | Host header is a numeric IP address | 오탐(검증 환경에서 IP로 접속) |

그 외 매칭은 없었다. 특수문자 정상 입력은 942(SQLi)·941(XSS) 룰에 걸리지 않았다. CRS 4.x의 SQLi 탐지는 libinjection 기반이라 단순 특수문자 조합만으로는 반응하지 않는다는 것을 실측으로 확인했다. 흔히 "WAF는 아포스트로피만 봐도 막는다"고 하지만, 적어도 이 구성(CRS 4.30.0, Paranoia Level 1)에서는 그렇지 않았다.

## 3. 920350 분석

CRS 920350은 요청의 Host 헤더가 도메인명이 아니라 숫자 IP일 때 매칭된다. 봇이나 스캐너는 대개 도메인 없이 IP로 직접 두드리므로 그 신호를 잡는 룰이다.

검증 환경에서는 `http://127.0.0.1:8080`으로 접속했으니 Host가 `127.0.0.1:8080`이다. 룰은 설계대로 동작한 것이고, 오탐인 이유는 "실제 서비스는 도메인으로 접속한다"는 전제가 검증 환경에 없었기 때문이다.

WAF 설정도 확인했다. `proxy_set_header Host $host`라서 nginx는 클라이언트가 보낸 Host를 그대로 룰 평가와 백엔드 전달에 쓴다. 즉 판정 대상은 클라이언트가 보내는 Host 그 자체다.

## 4. 조치: 룰이 아니라 원인을 없앤다

두 가지 선택지가 있었다.

1. 920350을 비활성(또는 점수 완화)한다.
2. 정상 트래픽이 정상답게, 즉 도메인 Host로 접속하게 만든다.

1번은 쉽지만 "IP로 직접 때리는 스캐너"에 대한 미탐 구멍을 만든다. 2번을 택했다.

- compose의 WAF에 `SERVER_NAME=shop.panoptes.lab` 추가
- 트래픽 스크립트가 `Host: shop.panoptes.lab`을 보내도록 수정

```python
conn = http.client.HTTPConnection(ADDR, PORT, timeout=5)
h = {"Host": HOST, "User-Agent": "panoptes-normal/1.0"}
conn.request(method, path, body=data, headers=h)
```

결과적으로 예외 룰 0개로 오탐이 사라졌다.

## 5. 양방향 검증

오탐 조치는 "정상이 통과하는가"만 보면 반쪽이다. "공격은 여전히 잡히는가"를 같이 봐야 한다.

| 접속 방식 | 920350 | 의미 |
| --- | --- | --- |
| Host=shop.panoptes.lab | 0건 | 정상 사용자 통과(오탐 해소) |
| Host=127.0.0.1:8080 | 17건 / 14요청 | IP 직접 접근은 탐지 유지(미탐 없음) |

WAF 컨테이너의 자체 헬스체크도 확인했다. 25초 동안 요청 없이 관찰해도 920350이 발생하지 않아, 헬스체크용 예외 룰은 필요 없었다.

## 6. 잘못 판단했던 과정

처음 트래픽 스크립트는 urllib을 썼다. Host를 도메인으로 바꾼 뒤 집계를 보니 도메인 Host 요청이 로그에 보이지 않았고, 숫자 IP Host 매칭만 남아 있었다. "urllib이 지정한 Host 헤더를 접속 주소로 덮어쓰나 보다"라고 판단하고 http.client로 바꿨다.

나중에 이 판단만 따로 검증했다. urllib도 명시한 Host 헤더를 그대로 보낸다. 당시 상황은 두 가지가 겹친 것이었다.

- 집계에 Host를 바꾸기 전 실행분이 섞여 있었다.
- 감사 로그가 `RelevantOnly`라서, 룰에 걸리지 않은 2xx 요청은 기록되지 않는다. 도메인 Host 요청은 920350에 안 걸리니 로그에 없는 것이 정상이었다.

"안 보이는 것"을 실패로 읽은 것이다. 이후 판단은 로그 유무가 아니라 대조 테스트(도메인 Host vs IP Host를 같은 조건에서 보내 비교)로 하게 됐다. http.client로 바꾼 것 자체는 해롭지 않아 그대로 두었고, 문서에는 오판 과정을 정정으로 남겼다.

## 7. 실무에서 920350을 다루는 방식

룰을 통째로 끄지 않고 경로·목적별로 관리하는 패턴이다.

| 케이스 | 처리 |
| --- | --- |
| 헬스체크·LB 프로브 | 특정 경로(`/health`, `/healthz`)에 한해 예외 |
| 모니터링·업타임 체커 | 출발지 IP 화이트리스트 |
| 내부 서비스 간 통신 | 내부 대역 별도 정책, 또는 WAF를 외부 경계에만 배치 |
| IP 접근이 정상인 API | detection-only나 점수 완화(완전 비활성 아님) |
| 그 외 IP 직접 접근 | 스캐너 가능성, 탐지 유지 |

원칙은 세 가지다. 룰 전체 비활성은 피한다. 예외는 경로·출발지·Host 조합으로 가장 좁게 둔다. 차단과 탐지를 분리한다. CRS는 `ctl:ruleRemoveById`와 경로 조건부 예외를 제공하고, Cloudflare WAF Exception이나 AWS WAF Scope-down statement도 같은 개념이다.

## 8. 정리

- 정상 트래픽 14건 기준 실질 오탐은 920350 하나였고, 특수문자 정상 입력은 SQLi·XSS 룰에 걸리지 않았다.
- 룰을 끄지 않고 원인(IP 직접 접속)을 없애 오탐 0건과 탐지 유지를 양방향으로 확인했다.
- 감사 로그가 정상 요청을 남기지 않는 설정에서는 "로그가 없음"이 "요청이 안 감"을 뜻하지 않는다. 판단은 대조 테스트로 한다.
- 이 결과를 근거로 P2에서 차단 모드로 전환했다.

## 참고

- [OWASP CRS — Rule 920350 (REQUEST-920-PROTOCOL-ENFORCEMENT)](https://github.com/coreruleset/coreruleset/blob/main/rules/REQUEST-920-PROTOCOL-ENFORCEMENT.conf)
- [OWASP CRS — False Positives and Tuning](https://coreruleset.org/docs/concepts/false_positives_tuning/)
- [libinjection](https://github.com/libinjection/libinjection)
