---
layout: single
title: "[웹 탐지] panoptes-detect P3-3 — WAF는 응답을 못 막는다, 그리고 WAF와 앱 로그를 한 출발지로 엮기"
excerpt: "panoptes-detect P3의 마지막 묶음. intent의 P3 완료 기준과 대조하니 세 항목이 남아 있었다. 객체 권한 위반(IDOR) 실트래픽 검증, 응답 내 비밀값 노출 탐지, 계정 잠금과 WAF 탐지의 연계. 응답 본문을 검사하는 ModSecurity 룰은 감사 로그에 '403 차단'을 남기면서 실제로는 응답을 그대로 내보냈다. 커넥터가 응답 헤더를 먼저 보내기 때문이다. 탐지 전용으로 바꾸고 요청 단계 가상 패치로 막았으며, 탐지 로그 자체가 비밀값을 다시 저장하지 않도록 룰을 짰다. WAF 로그와 앱 로그를 같은 출발지로 엮는 일은 Wazuh 디코더로는 실패했고, 수집 파이프라인(Vector)에서 공통 필드를 붙이는 방식으로 해결했다. 교차 상관 룰이 동작하지 않은 마지막 원인은 룰 파일 로드 순서였다."
date: 2026-10-28
categories: ["Security", "웹 탐지"]
permalink: "/infra/security/panoptes-p3-pipeline-correlation/"
tags: [ModSecurity, Wazuh, Vector, DLP, 로그정규화, 상관분석, IDOR, 가상패치, MITRE-ATTACK, 실측]
---

[앞 글](/infra/security/panoptes-p3-auth-detection/)에서 원 IP 보존과 인증 공격 상관 룰까지 마치고 README에 P3를 "완료"로 적었다. 그런데 intent.md의 P3 완료 기준을 다시 읽어 보니 세 항목이 비어 있었다. 표시를 "진행 중"으로 되돌리고 이 세 항목을 실측했다. 이 글은 그 기록이다.

> 요약
> - 객체 권한 위반: 남의 주문 29건 조회 + 관리자 API 3회 → 100304 27건 + 100305 5건 = 32건으로 검산이 맞았다. 관리자 권한 거부 이벤트에 계정 필드가 빠져 있던 것을 고쳤다.
> - 응답 내 비밀값 노출: 응답 본문 검사 룰은 기본 설정에서 JSON을 검사하지 않는다(미탐). JSON을 추가하면 탐지는 되지만, 감사 로그에는 403으로 남고 클라이언트는 200과 본문 전체를 받는다(차단 실패). 탐지 전용으로 바꾸고 요청 단계 가상 패치로 막았다.
> - 로그 위생: 탐지 룰의 매칭 메시지와 감사 로그 응답 본문에 비밀값이 다시 저장되고 있었다. 표시 변수로 우회하고 감사 로그에서 응답 본문을 뺐다. `sanitiseMatched`는 이 버전에서 지원되지 않는다.
> - 교차 상관: WAF 로그(`transaction.client_ip`)와 앱 로그(`client_ip`)는 필드 이름이 달라 Wazuh가 엮지 못한다. 디코더로 맞추려다 JSON 해석이 통째로 사라졌다. 수집 파이프라인(Vector)에서 원본은 유지하고 공통 필드 `srcip`만 더하는 방식으로 해결했다.
> - 같은 출발지에서 WAF 가상 패치 적중과 계정 잠금이 10분 안에 함께 발생하면 묶는 룰 100330이 실트래픽에서 발생했다. 룰 조건은 처음부터 맞았는데, 룰이 든 파일이 참조 대상보다 먼저 로드되어 동작하지 않았던 것이 마지막 원인이었다.

## 1. 객체 권한 위반 실트래픽

P0.5에서 만든 룰 100304(권한 거부)와 100305(같은 IP 권한 거부 6회/60초)를 실제 트래픽으로 확인한 적이 없었다. 시뮬레이터에 `idor` 시나리오를 넣었다. bob으로 정상 로그인한 뒤 주문 ID 1~30을 순서대로 조회하고, 관리자 API를 3번 호출한다.

```
[idor] IP 198.51.100.70 → bob 로그인 200
  /orders/1~30 응답 분포: {404: 29, 200: 1}
  /admin/users 403
  /admin/users 403
  /admin/users 403
```

```
100304  x27  L6 panoptes-app: authorization denied (reason role, user )
100305  x5   L9 panoptes-app: repeated authorization failures from same IP (enumeration / IDOR probing)
```

27 + 5 = 32 = 남의 주문 29 + 관리자 API 3. 100305는 6·12·18·24·30번째에 발생했다.

알림 설명 끝이 `user )`로 비어 있다. 관리자 권한 거부(`reason=role`) 이벤트에 앱이 `user` 필드를 넣지 않고 있었다. 앞 글에서 없는 계정 실패가 `username` 필드로 남아 dstuser가 비었던 것과 같은 종류의 문제다. 고치고 테스트에 `user=bob` 확인을 넣었다.

한 가지는 확인하지 못했다. 코드상 존재하지 않는 주문 ID를 조회하면 보안 이벤트 없이 404만 돌아간다. 정상 트래픽 스크립트가 만든 주문이 이미 30건 넘게 있어서, 이번에 조회한 ID는 전부 실존 주문이었다. 그래서 "없는 ID 탐색은 이벤트가 남지 않는다"는 동작은 이번 실측 범위 밖이다.

## 2. 응답 내 비밀값 노출

### 시나리오

운영에 실수로 남은 디버그 엔드포인트를 재현했다. `/debug/config`는 `LEAK_DEMO=true`일 때만 설정 덤프를 응답하고 기본은 404다. 응답 값은 전부 가짜다. AWS 공식 문서의 예시 액세스 키와 형식만 흉내 낸 개인키 문자열이고, 실제 설정값(`SESSION_SECRET` 등)이 섞이지 않는지 테스트로 확인했다.

### A단계: 룰은 있는데 검사가 안 된다

응답 본문에서 클라우드 키·개인키 형식을 찾으면 차단하는 룰(1000200, phase 4, deny)을 넣고 요청했다.

```
A 200 270
{"service":"panoptes-shop","debug":true,"storage":{"aws_access_key_id":"AKIA...
```

200에 본문이 그대로 나왔고 감사 로그에 1000200은 0건이었다. 이유는 설정에 있었다.

```
SecResponseBodyAccess on
SecResponseBodyMimeType text/plain text/html text/xml
```

응답 본문 검사 대상이 세 형식뿐이고 앱 응답은 `application/json`이다. 룰이 아무리 맞아도 검사 자체가 일어나지 않는다. 이미지 기본값이 그렇다.

### B단계: 탐지는 되는데 차단이 안 된다

검사 형식에 `application/json`을 추가하고 다시 요청했다.

```
B 200 270
{"service":"panoptes-shop","debug":true,"storage":{"aws_access_key_id":"AKIA...
```

클라이언트가 받은 것은 A와 바이트 수까지 같다. 그런데 감사 로그는 다르게 말한다.

```
403 ['1000200'] body_in_audit= True match_in_audit= True
```

감사 로그에는 403으로 차단했다고 남았는데, 클라이언트는 200과 270바이트를 받았다. Wazuh에서 같은 이벤트를 열면 `http_code 403`과 `Content-Length 270`이 나란히 보인다.

![100220 — 감사 로그는 403, Content-Length 270](/assets/images/2026-10-28-panoptes-p3-pipeline-correlation/07-dlp-100220-deny-logged-403.jpg)

nginx 오류 로그에 답이 있었다.

```
[error] ModSecurity: Access denied with code 403 (phase 4). ... while sending to client
[alert] header already sent while sending response to client
```

ModSecurity-nginx 커넥터는 응답 본문 검사가 끝날 때까지 응답 헤더를 붙잡아 두지 않는다. phase 4에서 차단을 결정할 때는 헤더가 이미 나간 뒤라 상태 코드를 바꿀 수 없다. 이 동작을 고치는 PR([ModSecurity-nginx#384](https://github.com/owasp-modsecurity/ModSecurity-nginx/pull/384))이 있지만 병합되지 않았다.

탐지 운영 관점에서 이건 두 가지 문제다. 분석가가 Wazuh에서 "1000200, 403"을 보면 막았다고 판단한다. 실제로는 유출됐다. 응답 단계 룰을 deny로 두면 잘못된 안심을 준다. 그리고 비밀값이 세 곳에 다시 저장된다. 감사 로그의 응답 본문, 감사 로그의 매칭 메시지, nginx 오류 로그의 매칭 값. 지금은 가짜 값이라 괜찮지만 실제 운영이라면 탐지 로그가 유출 지점 하나를 더 만드는 셈이다.

### 로그 가리기는 지원되지 않는다

ModSecurity에는 매칭 값을 로그에서 가리는 `sanitiseMatched` 동작이 있다. 컨테이너 안에서 실험 룰로 시험했다.

```
nginx: [emerg] "modsecurity_rules_file" directive Rules error. ... Action: SanitiseMatched is not yet supported.
```

libmodsecurity 3.0.17에서 지원되지 않는다. 설정 검사를 먼저 돌린 덕에 서비스는 멈추지 않았다.

### C단계: 탐지 전용 + 표시 변수

룰을 두 개로 나눴다.

```
SecRule RESPONSE_BODY "@rx (클라우드 키·개인키 패턴)" \
    "id:1000200,phase:4,pass,nolog,setvar:'tx.panoptes_dlp_hit=1'"

SecRule TX:panoptes_dlp_hit "@eq 1" \
    "id:1000202,phase:4,pass,log,auditlog,\
    msg:'panoptes dlp (detect only): secret pattern in response body',\
    tag:'panoptes/dlp'"
```

1000200은 비밀값을 찾아도 기록하지 않고 표시 변수만 세운다. 1000202가 그 변수를 보고 기록한다. 1000202의 매칭 값은 "1"이라 로그에 비밀값이 들어가지 않는다. 감사 로그에서 응답 본문(part E)도 뺐다. 이후 모든 이벤트에서 감사 로그로 응답 본문을 볼 수 없게 되는 트레이드오프가 있다.

```
C 200 270
['1000202'] AKIA_anywhere_in_audit= False resp_body_in_audit= False
오류 로그 AKIA 0건
```

![100220 탐지 전용 — 1000202, 표시 변수 매칭](/assets/images/2026-10-28-panoptes-p3-pipeline-correlation/05-dlp-100220-detect-only-1000202.jpg)

![100220 탐지 전용 — http_code 200, 응답은 전달됨](/assets/images/2026-10-28-panoptes-p3-pipeline-correlation/06-dlp-100220-detect-only-http200.jpg)

Wazuh 룰 100220의 설명에는 "NOT blocked, response delivered"를 넣었다. 분석가가 차단으로 오해하지 않게 하려는 것이다.

### D단계: 알려진 경로는 요청 단계에서 막는다

응답 단계에서 못 막으니, 알려진 노출 경로는 요청이 앱에 닿기 전에 끊어야 한다. P2와 같은 방식의 가상 패치다.

```
SecRule REQUEST_FILENAME "@beginsWith /debug/" \
    "id:1000201,phase:1,deny,status:403,log,\
    msg:'panoptes vpatch: debug endpoint access',\
    t:none,t:urlDecodeUni,t:lowercase"
```

```
D 403 146 /debug/config
D 403 146 /DEBUG/config
D 403 146 /%64ebug/config
D 200 41  /health
```

세 변형 모두 WAF의 403 페이지(146바이트)만 받았다. 노출 본문(270바이트)은 나가지 않았다.

![100221 — /%64ebug/config 403](/assets/images/2026-10-28-panoptes-p3-pipeline-correlation/08-vpatch-100221-uri-403.jpg)

![100221 — is_interrupted true, 디코딩 후 /debug/config 매칭](/assets/images/2026-10-28-panoptes-p3-pipeline-correlation/09-vpatch-100221-interrupted.jpg)

![DLP 알림 목록 — 100220 탐지 2건, 100221 차단 3건](/assets/images/2026-10-28-panoptes-p3-pipeline-correlation/04-dlp-list.jpg)

## 3. WAF 로그와 앱 로그를 한 출발지로 엮기

### 문제

"같은 출발지에서 WAF 공격 탐지와 계정 잠금이 함께 일어나면 등급을 올린다"는 룰을 만들려면 두 로그의 출발지를 비교해야 한다. WAF 감사 로그는 `transaction.client_ip`, 앱 로그는 `client_ip`다. Wazuh의 `same_field`는 같은 이름의 필드끼리만 비교한다.

### 안 된 방법: 디코더

기본 json 디코더의 자식 디코더로 `"client_ip":"..."`를 정규식으로 뽑아 정적 필드 `srcip`에 넣는 디코더를 시험했다. 설정 검사는 통과했다.

```
name: 'json'
srcip: '198.51.100.50'
id: '1002'
```

`srcip`는 채워졌는데 `client_ip`, `dstuser`, `event`가 전부 사라졌고, 로그인 실패가 100301 대신 일반 룰 1002로 떨어졌다. 자식 디코더가 매칭되면 부모 json 디코더가 만든 동적 필드가 남지 않았다. 이대로 적용했으면 P3의 탐지가 조용히 멈췄을 것이다. 바로 롤백했다.

### 채택: 수집 파이프라인 정규화

원천 로그를 바꾸지 않고 수집 단계에서 공통 필드를 붙이는 방식이다. 앱이 WAF의 필드 이름을 알게 하는 대안도 있었지만, 보호 대상 서비스가 보안 장비의 스키마에 묶이는 구조라 피했다.

```
waf  → logs/modsec/audit.log ─┐
                               ├─ Vector → logs/normalized/*.log → Wazuh agent → manager
app  → logs/app/app.log ───────┘
```

Vector가 원본 JSON을 그대로 두고 세 필드만 더한다.

| 필드 | 값 |
| --- | --- |
| `srcip` | WAF: `transaction.client_ip`, 앱: `client_ip` |
| `panoptes_source` | `modsecurity` / `app` |
| `panoptes_schema` | `v1` |

Vector를 띄우기 전에, 정규화된 모양의 로그를 손으로 만들어 logtest에 넣었다. 디코더 실험에서 "설정 검사 통과 ≠ 동작"을 겪었기 때문이다.

```
name: 'json'
client_ip: '198.51.100.50'
dstuser: 'grace'
event: 'auth.login.failure'
srcip: '198.51.100.50'
id: '100301'
```

JSON 필드 해석이 유지된 채 `srcip`가 추가됐고 기존 룰도 그대로 매칭됐다. 그다음 Vector 컨테이너를 띄워 원본 증가분(WAF 1, 앱 15)과 정규화본 건수가 같은지 확인하고, Wazuh agent의 수집 경로를 정규화본으로 바꿨다.

파이프라인은 파일 입출력만 하므로 네트워크를 붙이지 않았고(`network_mode: none`), 원본은 읽기 전용으로 마운트했다. `read_from: end`로 기존 로그를 다시 읽지 않아, 수집 경로를 바꿀 때 과거 이벤트가 중복 알림으로 쏟아지지 않는다.

### 룰 100330

Wazuh에는 "A 룰 다음에 B 룰"을 직접 잇는 옵션이 없다. 그래서 WAF 공격 룰(100201·100210·100211·100220·100221)과 앱 계정 잠금(100303)을 `panoptes_corr` 그룹으로 묶고, 그 그룹 안에서 같은 `srcip`의 이벤트가 10분 안에 2건이되 `panoptes_source`가 서로 다르면 발생하게 했다. 출처가 다르다는 조건이 없으면 "같은 IP에서 잠금 2회"도 묶인다.

```xml
<rule id="100330" level="13" frequency="2" timeframe="600">
  <if_matched_group>panoptes_corr</if_matched_group>
  <same_srcip />
  <different_field>panoptes_source</different_field>
  ...
</rule>
```

### logtest에서 발생하지 않았다

음성·양성 8줄을 넣었다. A(같은 IP 잠금 2회), B(WAF → 같은 IP 잠금), C(WAF → 다른 IP 잠금), D(잠금 → 같은 IP WAF). 기대는 B와 D에서만 발생이다. 결과는 어디서도 발생하지 않았다.

조건을 하나씩 떼어 낸 변형 룰 8종을 돌렸다.

| 조건 | 결과 |
| --- | --- |
| 그룹만 | 2번째 줄부터 매번 발생 → if_matched_group + frequency 2는 정상 |
| `same_srcip` | A·B·D 발생, C 미발생 → JSON에서 온 srcip에 동작. 정적 필드로 잡힘 |
| `same_field srcip` | 미발생 → 정적 필드에 same_field는 안 먹음(앞 글의 dstuser와 같은 규칙) |
| `different_field srcip` | 매번 발생 → 정적 필드에는 비교 없이 통과 |
| `same_field panoptes_source` | A만 발생 → 동적 필드 비교 정상 |
| `different_field panoptes_source` | 출처가 바뀌는 지점마다 발생 → 정상 |
| `same_srcip` + `different_field panoptes_source` | **B·D만 발생** |

마지막 변형은 100330과 조건이 똑같다. 그런데 변형은 되고 100330은 안 됐다. 차이는 룰이 든 파일뿐이었다. 변형은 실험용 파일 `zz_exp.xml`에 있어서 모든 룰 파일 중 마지막에 로드됐고, 100330은 `panoptes_app_rules.xml`에 있어서 WAF 룰 파일보다 먼저 로드됐다. 100330을 읽는 시점에 `panoptes_corr` 그룹에 속한 룰은 같은 파일의 100303뿐이고 WAF 룰 5개는 아직 읽기 전이다. if_matched_group 룰은 로드 시점까지 읽힌 그룹 룰에만 연결되는 것으로 보인다.

100330을 `panoptes_xcorr_rules.xml`로 옮겼다. 이름이 `w` 뒤 `x`라 네 파일 중 마지막에 읽힌다. 룰 내용은 한 글자도 바꾸지 않았다.

```
   2 id: '100303'     A: 미발생
   1 id: '100211'     B: WAF
   1 id: '100330'     B: 발생
   1 id: '100211'     C: WAF
   2 id: '100303'     C: 다른 IP 잠금 미발생, D: 잠금
   1 id: '100330'     D: 발생
```

### 실트래픽

1차 시도는 실패했다. 가상 패치 적중은 203.0.113.104에서 보냈는데, 시뮬레이터의 분산 스터핑은 IP를 .100부터 순서대로 바꾸고 잠금은 누적 실패 횟수에 따라 몇 번째 IP에서 걸릴지 달라진다. 이번엔 .101에서 걸렸다. 출발지가 다르니 100330이 안 나온 것이 맞다. 룰은 음성으로 올바르게 동작했고, 틀린 것은 실측 설계였다.

2차는 출발지를 하나로 고정했다. 198.51.100.77에서 가상 패치 요청 1건과 bob 로그인 실패 5회를 보냈다.

```
1 100211 198.51.100.77 modsecurity
4 100301 198.51.100.77 app
1 100330 198.51.100.77 app
```

로그인 실패 5건이 100301 4건(1번째 실패 + 잠긴 뒤 3건) + 100330 1건(2번째 시도의 잠금)으로 나뉘었다. 상관 룰이 발생한 이벤트는 개별 룰(100303) 대신 상관 룰로 알림이 나간다.

![교차 상관 목록 — 21:51 같은 출발지(100330 발생), 21:49 다른 출발지(미발생)](/assets/images/2026-10-28-panoptes-p3-pipeline-correlation/01-corr-list-srcip-source.jpg)

목록에서 1차·2차가 나란히 보인다. 21:49의 100211(.104)과 100303(.101)은 출발지가 달라 묶이지 않았고, 21:51의 100211과 100330은 같은 .77이다. 21:04 행은 정규화 전이라 `srcip`가 비어 있다.

![100330 상세 — srcip, panoptes_source, dstuser bob](/assets/images/2026-10-28-panoptes-p3-pipeline-correlation/02-corr-100330-fields.jpg)

![100330 상세 — frequency 2, T1190 + T1110](/assets/images/2026-10-28-panoptes-p3-pipeline-correlation/03-corr-100330-rule-mitre.jpg)

## 4. 중간에 겪은 것

작업 중 OrbStack이 비정상 종료됐다(signal 11). 재기동 뒤 수집 경로를 바꿨는데 알림이 한 건도 안 나왔다. 원인은 매니저가 재기동 직후 만든 다중 그룹 설정 묶음(`merged.mg`)에 panoptes-waf 그룹 내용이 비어 있었던 것이다. agent 쪽 `agent.conf`가 수집 대상 0개였다. `docker cp`로 설정을 다시 넣어도 묶음이 갱신되지 않았고, 소유자·권한을 기본 그룹 파일에 맞추고 수정 시각을 갱신하자 다시 만들어졌다. 원인이 권한이었는지 수정 시각이었는지는 수정 전 상태를 확인하지 않아 가를 수 없다.

`agent_groups -S`가 `synchronized`라고 해도 설정이 맞게 배포됐다는 뜻은 아니었다. agent가 매니저의 현재 묶음과 같은 것을 갖고 있다는 뜻일 뿐이다. 배포 확인은 묶음 내용과 agent 로그의 `Analyzing file`로 해야 했다. 매니저 설정을 `docker cp`가 아니라 마운트로 영구화하는 일은 P4로 넘겼다.

## 5. 정리

- 설정 검사 통과는 동작을 보장하지 않는다. 디코더, 룰 옵션, 파일 로드 순서 모두 음성·양성 logtest로 확인해야 했다.
- WAF 응답 단계 룰은 탐지까지다. 차단은 요청 단계 가상 패치와 앱 수정으로 한다. 감사 로그의 "403"을 그대로 믿으면 안 된다.
- 탐지 로그가 비밀값의 2차 유출 경로가 되지 않도록 룰을 설계한다.
- 로그 정규화는 원천이 아니라 수집 단계에서 한다. Wazuh 디코더만으로는 JSON 해석과 필드 정규화를 함께 할 수 없었다.
- 교차 상관 룰은 참조하는 룰 파일보다 뒤에 로드되어야 한다.

다음은 P4다. 대시보드, 주간 리포트, 룰 17개의 Playbook과 ATT&CK 매핑을 정리하고, 매니저 설정 영구화부터 처리한다.

## 참고

- [ModSecurity-nginx PR #384 — phase 4 response body intervention](https://github.com/owasp-modsecurity/ModSecurity-nginx/pull/384)
- [ModSecurity Reference Manual (v3) — SecResponseBodyMimeType, SecAuditLogParts](https://github.com/owasp-modsecurity/ModSecurity/wiki/Reference-Manual-(v3.x))
- [Wazuh — Rules Syntax](https://documentation.wazuh.com/4.14/user-manual/ruleset/ruleset-xml-syntax/rules.html)
- [Vector — Remap transform (VRL)](https://vector.dev/docs/reference/configuration/transforms/remap/)
- [MITRE ATT&CK T1552 — Unsecured Credentials](https://attack.mitre.org/techniques/T1552/)
