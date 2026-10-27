---
layout: single
title: "[웹 탐지] panoptes-detect P2 — 가상 패치: 앱을 고치지 않고 WAF에서 경로 순회 차단"
excerpt: "panoptes-detect의 P2 단계. P0에서 DetectionOnly로 두었던 ModSecurity를 차단 모드로 올리고, panoptes-shop의 /files 경로 순회 패턴을 막는 가상 패치 룰(1000100)을 override 설정으로 배포했다. 적용 전에는 공격이 앱까지 도달해 앱이 400으로 거부하고 CRS가 탐지만 했지만, 적용 후에는 WAF가 403으로 선차단했다. 정상 트래픽 14건은 403 없이 통과해 차단 전환으로 인한 오탐이 없음을 확인했고, 가상 패치 히트는 Wazuh 커스텀 룰 100211(level 10)로 alert에 남았다."
date: 2026-10-27
categories: ["Security", "웹 탐지"]
permalink: "/infra/security/panoptes-p2-virtual-patch/"
tags: [ModSecurity, 가상패치, WAF, Wazuh, 경로순회, MITRE-ATTACK, 탐지룰, 실측]
---

P0에서 WAF는 DetectionOnly였다. 탐지 파이프라인을 검증하는 동안은 차단이 필요 없었지만, 보호 대상 서비스(P0.5의 panoptes-shop)가 생긴 지금은 "취약점이 발견됐는데 앱 배포는 바로 못 하는" 상황을 연습할 수 있다. 이 글은 앱 코드를 수정하지 않고 WAF 룰로 공격 경로를 먼저 막는 가상 패치(virtual patching)를 적용하고 실측한 기록이다.

<!-- TODO: 가상 패치를 선택한 배경(실제 운영에서 패치 릴리스까지의 시간차 등) 보완 -->

> 요약
> - 시나리오는 `/files` 엔드포인트의 경로 순회다. `..%5c`(백슬래시 인코딩) 변형으로 `windows\win.ini`를 노리는 요청을 보냈다.
> - 가상 패치 적용 전: 공격이 WAF를 지나 앱까지 도달했고, 앱 자체 검증이 400으로 거부했다(앱 이벤트 100308). CRS는 930100 계열로 탐지만 했다.
> - `modsecurity-override.conf`에 가상 패치 룰 1000100(REQUEST_URI에 `\.\.[/\\]` 정규식)을 넣고 SecRuleEngine을 On으로 올렸다.
> - 적용 후: 같은 공격이 WAF에서 403으로 끊겼다(`is_interrupted: true`). 앱 로그에는 아무것도 남지 않는다.
> - 정상 트래픽 14건은 전부 200/201로 통과해 403이 없었다. 차단 모드 전환으로 인한 오탐이 없음을 확인했다.
> - 가상 패치 히트는 Wazuh 룰 100211(level 10, MITRE T1083)로 alert에 남는다.

## 1. 시나리오 — /files 경로 순회

panoptes-shop의 `/files/{name}`은 정적 파일을 돌려주는 엔드포인트다. 여기에 `../` 계열 변형을 섞어 상위 디렉터리의 파일을 노리는 경로 순회를 시도한다. 변형은 평문 `../`, 단일 인코딩(`%2e`), 이중 인코딩, 백슬래시(`%5c`), 널 바이트까지 준비했다.

<!-- TODO: /files 엔드포인트가 P0.5 글에는 없던 기능이라면, 언제 추가했는지 한 줄 설명 -->

## 2. 적용 전 — 앱이 마지막 방어선이 되는 상태

가상 패치 전에 공격을 보내면 요청이 WAF를 그대로 지나 앱까지 도달한다. 앱은 자체 경로 검증으로 400을 돌려주고, `event=path.traversal` 로그를 남긴다. 이 로그는 P0.5에서 만든 수집 경로를 타고 Wazuh 룰 100308(level 7)로 alert가 된다.

![앱 path.traversal 이벤트 상세 — status 400, target win.ini](/assets/images/2026-10-27-panoptes-p2-virtual-patch/09-app-path-traversal-event.jpg)

이 상태도 "방어는 된다". 하지만 공격이 매번 앱 코드까지 도달하고, 방어가 앱 구현 하나에 걸려 있다. 앱 검증에 구멍이 생기면 바로 뚫린다. WAF 감사 로그를 보면 CRS(930100 계열)는 이미 이 요청을 공격으로 보고 있었다 — 탐지 모드라 통과시켰을 뿐이다.

## 3. 가상 패치 룰 1000100

`modsecurity-override.conf`에 룰을 추가했다. REQUEST_URI에서 `\.\.[/\\]` 패턴(슬래시·백슬래시 양쪽)을 보면 즉시 403으로 끊는다.

<!-- TODO: 실제 SecRule 전문 붙여넣기 (phase, t:urlDecodeUni 등 변환 포함 여부) -->

```
SecRule REQUEST_URI "@rx \.\.[/\\]" \
    "id:1000100, ..."
```

엔진을 DetectionOnly에서 On으로 올리고, 컨테이너 안에서 둘 다 확인했다. `SecRuleEngine On`, 그리고 override 설정에 1000100이 1건 로드되어 있다.

![SecRuleEngine On + 가상 패치 룰 로드 확인](/assets/images/2026-10-27-panoptes-p2-virtual-patch/01-engine-on-vpatch-loaded.png)

## 4. 적용 후 — 프로브 실측

변형 7종을 한 번에 보내는 프로브 스크립트로 확인했다. 정상 요청은 200, 경로 순회 변형은 앱 도달 전에 403이거나 앱의 400이다.

![traversal 프로브 결과 — 정상 200, 백슬래시 변형 403](/assets/images/2026-10-27-panoptes-p2-virtual-patch/02-traversal-probe-blocking.png)

흥미로운 부분은 변형별로 끊기는 위치가 다르다는 점이다. 평문 `../`와 인코딩 변형 대부분은 (경로 정규화를 거치며) 앱의 400으로 떨어졌고, 백슬래시 변형(`..%5c`)이 가상 패치의 403에 걸렸다.

<!-- TODO: 변형별 차단 위치가 왜 갈리는지(프록시/앱의 경로 정규화 시점) 확인한 내용 보완 -->

WAF 감사 로그에서 적용 전후를 비교하면 단계가 그대로 보인다. 적용 전(A)에는 CRS 탐지 룰 목록(920440·930100·930110·930130·949110)과 함께 앱 응답 400이 기록됐고, 적용 후(B)에는 1000100 하나만 매칭되며 403으로 끝난다. 가상 패치가 CRS 평가보다 먼저 요청을 끊는다.

![audit 로그 비교 — 적용 전 CRS 탐지(400), 적용 후 1000100 단독 차단(403)](/assets/images/2026-10-27-panoptes-p2-virtual-patch/03-audit-detect-stepA-stepB.png)

## 5. 오탐 확인 — 정상 트래픽 14건

차단 모드 전환에서 가장 걱정되는 것은 정상 요청이 403으로 끊기는 오탐이다. 회원가입·로그인·주문 등 정상 흐름 14건을 보내 응답 코드를 집계했다. 200이 8건, 201이 6건 — 403은 없었다.

![정상 트래픽 14건 — 200×8, 201×6, 403 없음](/assets/images/2026-10-27-panoptes-p2-virtual-patch/04-normal-traffic-no-403.png)

가상 패치 룰이 `/files` 경로의 좁은 패턴만 보기 때문에 정상 트래픽과 겹칠 여지가 거의 없다. CRS 전체를 차단 모드로 올리는 것(P1에서 다룰 오탐 튜닝)과 달리, 가상 패치는 이렇게 좁게 시작할 수 있다는 것이 장점이다.

## 6. Wazuh에서 보기 — 100211 alert

가상 패치 히트용 Wazuh 커스텀 룰을 추가했다. ModSecurity 감사 로그에서 1000100 매칭을 찾아 level 10 alert로 올린다.

| 룰 | level | 조건 | MITRE |
| --- | --- | --- | --- |
| 100211 | 10 | 가상 패치 1000100 히트 (/files 경로 순회 차단) | T1083 |
| 100308 | 7 | 앱 이벤트 `path.traversal` (적용 전 단계) | - |

<!-- TODO: 100210 룰의 내용(대시보드 쿼리에 함께 있음) 확인해서 표에 추가 -->

Threat Hunting에서 두 단계가 나란히 보인다. 적용 전의 앱 이벤트(100308) 2건, 적용 후의 가상 패치 히트(100211) 1건.

![Threat Hunting — 100308(적용 전)과 100211(적용 후)](/assets/images/2026-10-27-panoptes-p2-virtual-patch/05-threat-hunting-vpatch-and-app.jpg)

100211 alert 상세에는 차단의 근거가 전부 남는다. `is_interrupted: true`, 매칭 파일(`modsecurity-override.conf`)과 줄 번호, 그리고 어떤 정규식이 어떤 URI에 걸렸는지까지.

![100211 상세 — is_interrupted true, override.conf 매칭](/assets/images/2026-10-27-panoptes-p2-virtual-patch/06-vpatch-alert-interrupted.jpg)

![100211 상세 — Host·URI·403 응답](/assets/images/2026-10-27-panoptes-p2-virtual-patch/07-vpatch-alert-host-uri-403.jpg)

![100211 상세 — rule.level 10, MITRE T1083 매핑](/assets/images/2026-10-27-panoptes-p2-virtual-patch/08-vpatch-alert-rule-mitre.jpg)

## 7. 정리

- 앱 코드를 수정하지 않고, WAF override 설정에 룰 하나(1000100)를 넣어 경로 순회를 선차단했다.
- 적용 전(앱 400 + CRS 탐지)과 적용 후(WAF 403, `is_interrupted`)를 감사 로그와 Wazuh alert 양쪽에서 비교 실측했다.
- 정상 트래픽 14건에 403이 없어, 좁은 가상 패치는 오탐 부담 없이 차단 모드로 올릴 수 있음을 확인했다.
- 전면 차단 모드(CRS 전체)로 가기 전의 오탐 튜닝은 P1에서 다룬다.

<!-- TODO: 열린 항목이 있으면 표로 추가 (예: 엔진 On 전환을 전체 적용했는지 /files만인지, 1000100 해제 시점 기준 등) -->

## 참고

- [OWASP — Virtual Patching Best Practices](https://owasp.org/www-community/Virtual_Patching_Best_Practices)
- [ModSecurity Reference Manual — SecRule](https://github.com/owasp-modsecurity/ModSecurity/wiki/Reference-Manual-(v3.x))
- [MITRE ATT&CK T1083 — File and Directory Discovery](https://attack.mitre.org/techniques/T1083/)
