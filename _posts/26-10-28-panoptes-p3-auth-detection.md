---
layout: single
title: "[웹 탐지] panoptes-detect P3 — 원 클라이언트 IP 보존과 임계값을 피하는 인증 공격 탐지"
excerpt: "panoptes-detect의 P3 단계. OrbStack 포트포워딩이 출발지 IP를 게이트웨이 주소로 바꾸는 문제를 실측으로 확인하고, nginx realip로 앞단 프록시 신뢰 모델을 구성했다. 이미지 기본 설정(location 수준)으로는 앱 로그만 원 IP가 되고 ModSecurity는 여전히 게이트웨이를 보는 것을 audit 로그로 확인해 http 수준으로 옮겼다. 그 과정에서 앱이 X-Forwarded-For 첫 값을 그대로 믿는 위조 취약점도 고쳤다. 이어서 분산 크리덴셜 스터핑·패스워드 스프레이·API 키 대입이 기존 IP 기준 룰을 모두 피해 가는 것을 실측하고, 상관 룰 3개(100310~100312)를 추가했다. 정적 필드인 dstuser에는 same_field가 동작하지 않는다는 점은 analysisd -t가 아니라 음성 케이스를 넣은 logtest로 드러났다."
date: 2026-10-28
categories: ["Security", "웹 탐지"]
permalink: "/infra/security/panoptes-p3-auth-detection/"
tags: [Wazuh, ModSecurity, nginx, realip, X-Forwarded-For, 크리덴셜스터핑, 패스워드스프레이, 상관분석, MITRE-ATTACK, 탐지룰, 실측]
---

P0.5에서 같은 IP의 로그인 실패 8회를 묶는 상관 룰(100302)을 만들었다. 그때 남긴 열린 항목이 두 가지였다. WAF를 거친 요청의 `client_ip`가 전부 OrbStack 게이트웨이(192.168.107.1)로 찍힌다는 것, 그리고 IP 기준 룰은 IP를 여러 개 쓰거나 횟수를 임계값 아래로 쪼개는 공격을 보지 못한다는 것이다. P3는 이 두 가지를 순서대로 다룬다. 원 IP가 없으면 두 번째 작업의 실측 자체가 불가능하기 때문이다.

> 요약
> - OrbStack 포트포워딩은 출발지 IP를 보존하지 않는다. 같은 Wi-Fi에 연결된 휴대폰에서 들어온 요청도 192.168.107.1로 기록됐다.
> - nginx realip로 "신뢰 프록시가 보낸 X-Forwarded-For만 원 IP로 인정"하는 구조를 만들었다. 이미지 기본 설정은 realip를 location 안에 두기 때문에, 앱 로그는 원 IP가 되지만 ModSecurity는 여전히 게이트웨이를 본다. http 수준으로 옮겨 해결했다.
> - 앱이 X-Forwarded-For 첫 값을 client_ip로 쓰고 있었다. 헤더 한 줄로 로그 IP를 바꿀 수 있는 구조라, WAF가 판정해서 덮어쓰는 X-Real-IP만 믿도록 바꿨다.
> - 분산 크리덴셜 스터핑, 패스워드 스프레이, API 키 대입 세 시나리오 모두 기존 룰로는 상관 알림이 0건이었다. 룰 3개(100310~100312)를 추가해 탐지로 바꿨다.
> - `same_field dstuser`로 쓴 룰은 `wazuh-analysisd -t`를 통과했지만 동작하지 않았다. dstuser는 정적 필드라 `same_user`/`different_user`를 써야 한다. 음성 케이스를 넣은 logtest로 확인했다.

## 1. 원 IP가 어디서 바뀌는지

같은 요청을 출발지 세 곳에서 보내고, User-Agent에 꼬리표를 붙여 WAF(nginx) 로그와 앱 로그를 대조했다.

```
$ docker compose logs waf --since 5m | grep p3-
waf-1  | 192.168.107.1 - - [28/Oct/2026:09:57:33 +0000] "GET /health HTTP/1.1" 200 41 "-" "p3-local" "-"
waf-1  | 192.168.107.1 - - [28/Oct/2026:09:57:39 +0000] "GET /health HTTP/1.1" 200 41 "-" "p3-lan" "-"
waf-1  | 192.168.97.2 - - [28/Oct/2026:09:57:44 +0000] "GET /health HTTP/1.1" 200 41 "-" "p3-inner" "-"
```

| 출발지 | WAF가 본 IP | 앱 client_ip |
| --- | --- | --- |
| Mac → 127.0.0.1:8080 | 192.168.107.1 | 192.168.107.1 |
| Mac → 자기 LAN IP | 192.168.107.1 | 192.168.107.1 |
| 컨테이너(app) → waf 직접 | 192.168.97.2 | 192.168.97.2 |

포트포워딩을 거치지 않은 요청(p3-inner)은 보낸 컨테이너의 IP가 정확히 찍혔다. nginx와 앱은 받은 IP를 그대로 쓰고 있고, 바뀌는 지점은 Mac의 8080 포트에서 컨테이너로 넘기는 OrbStack 포트포워딩 구간이다.

다만 위 두 요청은 모두 Mac 자신이 보낸 것이다. 다른 기기에서 들어오는 요청도 같은지 확인하려고, 같은 Wi-Fi의 휴대폰 브라우저로 접속했다.

```
$ docker compose logs waf --since 2m | grep /health
waf-1  | 192.168.107.1 - - [28/Oct/2026:10:01:21 +0000] "GET /health HTTP/1.1" 200 41 "-" "Mozilla/5.0 (iPhone; CPU iPhone OS 27_0_1 like Mac OS X) ... CriOS/156.0.8078.46 Mobile/15E148 Safari/604.1" "-"
```

외부 기기도 192.168.107.1이다. OrbStack 저장소에도 같은 증상의 이슈가 열려 있다([orbstack/orbstack#710](https://github.com/orbstack/orbstack/issues/710)). 메인테이너는 예상된 동작은 아니지만 내부 제약 때문에 고치기 어렵다는 취지로 답했다. 설정으로 해결할 문제가 아니라고 판단했다.

## 2. 앞단 프록시 신뢰 모델

운영 환경의 WAF는 보통 CDN이나 L7 LB 뒤에 있다. 클라이언트와 직접 연결되지 않으니 원 IP는 앞단이 붙여 주는 X-Forwarded-For로 받는다. 검증 환경에도 같은 구조를 적용했다. OrbStack 게이트웨이를 "앞단 프록시"로 보고, 거기서 온 요청에 한해 X-Forwarded-For를 원 IP로 인정한다.

이 구조에는 부수 효과가 하나 있다. Mac 한 대에서도 요청마다 X-Forwarded-For를 바꿔 출발지 IP 여러 개를 재현할 수 있다. 뒤에서 다룰 분산 공격 시나리오가 이걸 쓴다. 반대로 신뢰 범위 안에서는 헤더 위조가 가능하다는 한계가 있다. 운영에서는 LB/CDN 대역만 신뢰 대상으로 지정해야 하는 이유다.

owasp/modsecurity-crs 이미지는 realip용 환경변수를 이미 제공한다.

```
SET_REAL_IP_FROM=127.0.0.1
REAL_IP_HEADER=X-REAL-IP
REAL_IP_RECURSIVE=on
```

기본값은 신뢰 대상이 127.0.0.1이라 아무 효과가 없는 상태였다. compose에서 값을 바꿨다.

```yaml
SET_REAL_IP_FROM: "${WAF_TRUSTED_PROXY:-192.168.107.1}"
REAL_IP_HEADER: "X-Forwarded-For"
REAL_IP_RECURSIVE: "on"
```

## 3. 앱이 X-Forwarded-For 첫 값을 믿고 있었다

설정을 바꾸기 전에 WAF가 앱으로 넘기는 헤더를 확인했다.

```
proxy_set_header ${REAL_IP_PROXY_HEADER} $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

`$proxy_add_x_forwarded_for`는 클라이언트가 보낸 X-Forwarded-For 뒤에 접속 IP를 덧붙인다. 그런데 앱은 이 헤더의 첫 값을 client_ip로 쓰고 있었다. 첫 값은 클라이언트가 마음대로 정할 수 있다. 공격자가 `X-Forwarded-For: 1.2.3.4` 한 줄을 넣으면 앱 로그의 IP가 바뀌고, 같은 IP를 묶는 상관 룰(100302)도 피할 수 있다. P0.5에서 만든 테스트도 이 동작을 정상으로 고정하고 있었다.

반면 `X-Real-IP`는 WAF가 realip 판정 결과(`$remote_addr`)로 덮어써서 보낸다. 클라이언트가 같은 이름의 헤더를 보내도 무시된다. 앱이 이 값만 믿도록 바꿨다. 원 IP 판정을 WAF 한 곳에서만 하게 하려는 것이다. 하위 서비스가 X-Forwarded-For를 각자 해석하면 위조할 수 있는 지점이 그만큼 늘어난다.

```python
def client_ip(request: Request) -> str:
    if settings.TRUST_PROXY:
        real = request.headers.get("x-real-ip")
        if real:
            return real.strip()
    return request.client.host if request.client else "-"
```

테스트는 세 가지로 바꿨다. X-Real-IP가 그대로 기록되는지, X-Forwarded-For 위조가 무시되는지, 두 헤더가 함께 오면 X-Real-IP가 우선하는지.

## 4. 1차 적용: 앱은 원 IP, ModSecurity는 게이트웨이

환경변수만 바꾼 상태에서 요청 네 건을 보냈다. 마지막 요청은 Host를 숫자 IP로 보내 CRS 920350(숫자 IP Host)이 걸리게 했다. ModSecurity가 감사 로그에 어떤 IP를 남기는지 보려는 것이다.

```
$ docker compose exec waf sh -c 'grep -n real_ip /etc/nginx/includes/proxy_backend.conf'
19:set_real_ip_from 192.168.107.1;
21:real_ip_header X-Forwarded-For;
22:real_ip_recursive on;

$ tail -n 4 logs/app/app.log
{"ts":"2026-10-28T10:31:43.875047+00:00",...,"client_ip":"192.168.107.1",...}
{"ts":"2026-10-28T10:31:48.083660+00:00",...,"client_ip":"203.0.113.10",...}
{"ts":"2026-10-28T10:31:52.029737+00:00",...,"client_ip":"192.168.97.2",...}
{"ts":"2026-10-28T10:31:56.746160+00:00",...,"client_ip":"203.0.113.20",...}

$ tail -n 1 logs/modsec/audit.log | python3 -c "...print(t['client_ip'], ruleIds)"
192.168.107.1 ['920350']
```

| 요청 | 앱 client_ip | ModSecurity client_ip |
| --- | --- | --- |
| X-Forwarded-For 없음 | 192.168.107.1 | - |
| 신뢰 프록시 + XFF 203.0.113.10 | 203.0.113.10 | - |
| 컨테이너 + 위조 XFF 1.2.3.4 | 192.168.97.2 (위조 무시) | - |
| 신뢰 프록시 + XFF 203.0.113.20 (920350 유발) | 203.0.113.20 | **192.168.107.1** |

앱 로그만 보면 해결된 것처럼 보인다. 그러나 ModSecurity 감사 로그에는 여전히 게이트웨이가 남았다. Wazuh에서 같은 요청을 열어 보면, 요청 헤더에 X-Forwarded-For 203.0.113.20이 있는데도 `transaction.client_ip`는 192.168.107.1이다.

![realip 1차 — ModSecurity client_ip 192.168.107.1](/assets/images/2026-10-28-panoptes-p3-auth-detection/07-realip-before-modsec-clientip.jpg)

![realip 1차 — 같은 요청의 X-Forwarded-For 203.0.113.20](/assets/images/2026-10-28-panoptes-p3-auth-detection/08-realip-before-xff-header.jpg)

원인은 realip 설정 위치였다. nginx 설정 구조를 확인했다.

```
$ docker compose exec waf nginx -T | grep -n -E "include|modsecurity|server \{|location|real_ip|http \{"
(출력 일부)
13:http {
24:    include /etc/nginx/conf.d/*.conf;
143:server {
151:    location / {
159:        include includes/proxy_backend.conf;
234:set_real_ip_from 192.168.107.1;
236:real_ip_header X-Forwarded-For;
237:real_ip_recursive on;
272:modsecurity on;
```

`modsecurity on`은 http 수준(conf.d)에 있고, realip 지시어는 location 안에서 include되는 `proxy_backend.conf`에 있다. location 수준 realip는 요청 처리 후반에 적용된다. 그래서 프록시 헤더(X-Real-IP)에는 반영되지만 그보다 먼저 도는 ModSecurity에는 반영되지 않는다. 이대로 두면 WAF 알림의 IP와 앱 알림의 IP가 어긋나서, 둘을 IP로 엮는 상관분석이 깨진다.

## 5. 2차 적용: realip를 http 수준으로

conf.d의 파일은 http 블록 안에서 include된다. 같은 지시어를 담은 템플릿을 conf.d에 추가했다. P2 때처럼 읽기 전용 마운트가 템플릿 렌더링과 부딪히지 않도록 템플릿 경로(`/etc/nginx/templates/conf.d/`)에 마운트했다.

```nginx
# waf/conf/realip.conf.template
set_real_ip_from ${SET_REAL_IP_FROM};
real_ip_header ${REAL_IP_HEADER};
real_ip_recursive ${REAL_IP_RECURSIVE};
```

```
$ tail -n 3 logs/app/app.log
{"ts":"2026-10-28T10:35:35.144365+00:00",...,"client_ip":"203.0.113.10",...}
{"ts":"2026-10-28T10:35:40.523390+00:00",...,"client_ip":"192.168.97.2",...}
{"ts":"2026-10-28T10:36:28.441651+00:00",...,"client_ip":"203.0.113.20",...}

$ tail -n 1 logs/modsec/audit.log | python3 -c "..."
203.0.113.20 ['920350']
```

ModSecurity도 원 IP(203.0.113.20)를 기록한다. Wazuh에서도 같다.

![realip 2차 — ModSecurity client_ip 203.0.113.20](/assets/images/2026-10-28-panoptes-p3-auth-detection/09-realip-after-modsec-clientip.jpg)

nginx 접근 로그 첫 칸은 2차 적용 후에도 192.168.107.1이었다. 로그 형식을 확인해 보니 `$remote_addr`가 아니라 `$realip_remote_addr`였다.

```
log_format main '$realip_remote_addr - $remote_user [$time_local] "$request" '
                '$status $body_bytes_sent "$http_referer" '
                '"$http_user_agent" "$http_x_forwarded_for"';
```

`$realip_remote_addr`는 realip 적용 전의 접속 IP다. 접근 로그는 실제로 연결한 프록시 IP를 첫 칸에, 원 IP를 마지막 칸(X-Forwarded-For)에 함께 남기는 형식이라 바꾸지 않았다.

## 6. 기존 룰이 놓치는 인증 공격

원 IP를 재현할 수 있게 됐으니, 기존 IP 기준 룰이 놓치는 패턴을 실측했다. 시뮬레이터(`scripts/auth_attack_sim.py`)는 본인 검증 환경에만 보내고, 틀린 비밀번호만 쓰고, 출발지 IP는 문서용 예약 대역(RFC 5737)만 쓴다.

| 시나리오 | 내용 | ATT&CK |
| --- | --- | --- |
| stuffing | IP 12개 → 계정 alice, IP당 1회 | T1110.004 Credential Stuffing |
| spray | IP 1개 → 계정 7개(실존 3·미존재 4), 같은 비밀번호 | T1110.003 Password Spraying |
| apikey | IP 1개 → 잘못된 API 키 15회 | T1110 Brute Force |

```
[stuffing] 12개 IP → 계정 alice, IP당 1회
  401  203.0.113.100
  401  203.0.113.101
  401  203.0.113.102
  401  203.0.113.103
  423  203.0.113.104
  423  203.0.113.105
  ...
  423  203.0.113.111

[spray] IP 198.51.100.50 → 계정 7개, 계정당 1회 (같은 비밀번호)
  401  admin
  423  alice
  401  bob
  401  dave
  401  erin
  401  frank
  401  grace

[apikey] IP 198.51.100.60 → 잘못된 API 키 15회
  401
  ... (15회 모두 401)
```

Wazuh 알림을 룰별로 묶어 봤다.

```
100200  x34  L3 panoptes: ModSecurity audit event
100301  x18  L5 panoptes-app: login failure (reason unknown_user, user )
100303  x1   L10 panoptes-app: account lockout (user alice)
100306  x15  L5 panoptes-app: invalid API key (reason unknown)
```

| 시나리오 | 발생한 알림 | 판정 |
| --- | --- | --- |
| stuffing | 개별 실패(100301), 계정 잠금(100303) 1건 | 미탐. IP당 1회라 100302(같은 IP 8회)를 피함 |
| spray | 개별 실패 7건 | 미탐. 7회는 100302 임계 8회 미만이고, 계정당 1회라 잠금도 안 걸림 |
| apikey | 개별 이벤트(100306) 15건 | 미탐. 같은 IP 반복을 묶는 룰 자체가 없음 |

stuffing에서 계정 잠금 알림이 하나 나오기는 했다. 하지만 잠금 알림만으로는 한 사람이 비밀번호를 잊은 것인지, IP 12개가 한 계정을 노린 것인지 구분할 수 없다.

결과를 보면서 따로 확인한 것이 두 가지 있다.

첫째, 100200(WAF 감사 이벤트) 34건은 공격 탐지가 아니다. 34 = 12 + 7 + 15로 공격 요청 전부와 개수가 같다. 감사 로그를 직접 세어 보니 매칭된 룰이 하나도 없었다.

```
Counter({(401, 0): 25, (423, 0): 9})
SecAuditLogRelevantStatus "^(?:5|4(?!04))"
```

감사 로그 설정이 404를 뺀 4xx 응답을 기록하기 때문에 401/423 응답이 남은 것이다.

둘째, 100301 설명 끝이 `user )`로 비어 있다. 없는 계정으로 실패하면 앱이 계정명을 `user`가 아니라 `username` 필드로 남기고 있었다. P0.5에서 확인했듯이 Wazuh json 디코더는 `user`만 `dstuser`로 매핑한다. 이대로면 계정 기준 상관 룰을 만들어도 실제 공격에서 흔한 "없는 계정 대입"이 통째로 빠진다. 앱의 실패·가입 이벤트 필드를 `user`로 통일했다.

## 7. 상관 룰 3개 — 그리고 동작하지 않은 1차 버전

집계 기준을 바꾼 룰 세 개를 추가했다.

| 룰 | 조건 | 대상 |
| --- | --- | --- |
| 100310 | 같은 계정 + 서로 다른 IP의 실패 6회 / 300초 | 분산 크리덴셜 스터핑 (T1110.004) |
| 100311 | 같은 IP + 서로 다른 계정의 실패 5회 / 300초 | 패스워드 스프레이 (T1110.003) |
| 100312 | 같은 IP의 잘못된 API 키 10회 / 60초 | API 키 대입 (T1110) |

1차 버전은 계정 비교에 `same_field dstuser`와 `different_field dstuser`를 썼다. 설정 검사는 통과했다.

```
$ docker exec single-node-wazuh.manager-1 /var/ossec/bin/wazuh-analysisd -t; echo "exit=$?"
exit=0
```

그런데 logtest에서는 100310이 끝내 발생하지 않았다.

```
100301 ×10 → 100311 → 100306 ×9 → 100312
```

같은 계정·다른 IP 실패 6건을 넣었는데 100301만 나왔다. 100311은 발생했지만, 실제로 계정을 비교해서 발생한 것인지는 이 결과만으로 알 수 없었다.

Wazuh 문서에 답이 있었다. `same_field`/`not_same_field` 같은 동적 필터는 정적 필드(user, srcip, dstip 등)에는 동작하지 않으므로 전용 옵션을 써야 한다. json 디코더가 `user`를 넣는 `dstuser`는 정적 필드다. 계정 비교를 전용 옵션으로 바꿨다. `client_ip`는 정적 필드로 매핑되지 않는 동적 필드라서, 기존 100302의 `same_field client_ip`는 그대로 정상이다.

```xml
<rule id="100310" level="10" frequency="6" timeframe="300">
  <if_matched_sid>100301</if_matched_sid>
  <same_user />
  <different_field>client_ip</different_field>
  ...
</rule>

<rule id="100311" level="10" frequency="5" timeframe="300">
  <if_matched_sid>100301</if_matched_sid>
  <same_field>client_ip</same_field>
  <different_user />
  ...
</rule>
```

이번에는 logtest 입력에 음성 케이스를 넣었다. "같은 IP가 같은 계정을 반복"하는 입력에서는 두 룰 모두 발생하면 안 된다.

| 구간 | 입력 | 기대 |
| --- | --- | --- |
| A (음성) | 같은 IP·같은 계정 6회 | 100310 없음 |
| B (양성) | 다른 IP 6개·같은 계정 | 6번째에 100310 |
| C (음성) | 같은 IP·같은 계정 5회 | 100311 없음 |
| D (양성) | 같은 IP·다른 계정 5개 | 5번째에 100311 |
| E (양성) | 같은 IP·잘못된 API 키 10회 | 10번째에 100312 |

```
$ docker exec -i single-node-wazuh.manager-1 /var/ossec/bin/wazuh-logtest < wazuh/tests/p3_2_logtest.jsonl 2>&1 \
    | grep -E "id: '10031|id: '10030[16]'" | uniq -c
  11 	id: '100301'
   1 	id: '100310'
   9 	id: '100301'
   1 	id: '100311'
   9 	id: '100306'
   1 	id: '100312'
```

A의 6건과 B의 앞 5건이 100301 11건이고, B의 6번째에서 100310이 발생했다. C의 5건과 D의 앞 4건이 100301 9건이고, D의 5번째에서 100311이 발생했다. 음성 구간에서는 상관 룰이 하나도 나오지 않았다.

## 8. 실트래픽으로 다시

같은 시뮬레이터를 다시 돌렸다.

![상관 룰 알림 목록 — 100310 2건, 100311, 100312](/assets/images/2026-10-28-panoptes-p3-auth-detection/01-auth-correlation-list.jpg)

| 룰 | 건수 | 해석 |
| --- | --- | --- |
| 100310 | 2 | alice 대상 실패 12건 → 6건마다 발생 |
| 100311 | 1 | 계정 7개 중 5번째 |
| 100312 | 1 | 15건 중 10번째 |
| 100302 | 0 | IP 기준 임계 미달은 그대로 |

stuffing만 놓고 보면 alice 대상 실패는 11건이다. 5번째 시도는 실패가 아니라 잠금 이벤트(100303)로 기록되기 때문이다. 100310의 두 번째 발생은 spray에서 시도한 alice 1건이 더해진 결과다. 목록의 두 번째 100310이 spray의 IP(198.51.100.50)로 찍힌 이유다. 룰이 시나리오가 아니라 계정 단위로 묶으니 의도한 동작이다.

건수 검산도 맞았다. 상관 룰이 발생한 이벤트는 개별 룰(100301) 대신 상관 룰로 알림이 나간다. 이번 실행의 로그인 실패 18건이 100301 15건 + 100310 2건 + 100311 1건으로 나뉘었다. 상관 룰은 한 번 발생하면 카운트가 초기화된다. 앞서 시뮬레이터를 두 번 연달아 돌렸을 때 100312가 잘못된 키 30건 중 10·20·30번째에 발생했다. 공격이 이어지면 알림도 반복된다는 뜻이다.

100310 상세에는 묶인 이전 이벤트(`previous_output`)와 ATT&CK 매핑이 남는다. 이전 이벤트들의 client_ip가 203.0.113.103, .105처럼 서로 다르다.

![100310 상세 — 계정 alice, 출발지 203.0.113.106](/assets/images/2026-10-28-panoptes-p3-auth-detection/02-stuffing-100310-fields.jpg)

![100310 상세 — frequency 6, T1110.004 Credential Stuffing](/assets/images/2026-10-28-panoptes-p3-auth-detection/03-stuffing-100310-rule-mitre.jpg)

100311이 발생한 이벤트는 존재하지 않는 계정 `frank`의 실패다. 앱 필드를 고치기 전이라면 이 이벤트의 dstuser는 비어 있었을 것이다.

![100311 상세 — 출발지 198.51.100.50, 계정 frank(unknown_user)](/assets/images/2026-10-28-panoptes-p3-auth-detection/04-spray-100311-fields.jpg)

![100311 상세 — frequency 5, T1110.003 Password Spraying](/assets/images/2026-10-28-panoptes-p3-auth-detection/05-spray-100311-rule-mitre.jpg)

![100312 상세 — frequency 10, T1110 Brute Force](/assets/images/2026-10-28-panoptes-p3-auth-detection/06-apikey-100312-rule-mitre.jpg)

## 9. 남은 것

| 항목 | 내용 |
| --- | --- |
| 계정 열거 | 실존 계정이 잠기면 423, 없는 계정은 계속 401로 응답한다. spray 결과의 응답 코드만 보고 alice가 실존 계정임을 알 수 있다. 탐지 범위 밖의 앱 설계 문제라 기록만 했다. |
| 임계값 | 6회/5회/10회는 시뮬레이터 기준값이다. 실제 서비스라면 정상 사용자의 오입력 분포를 보고 정해야 한다. |
| 신뢰 범위 | 신뢰 프록시 범위 안에서는 X-Forwarded-For 위조로 출발지를 바꿀 수 있다. 검증 환경의 전제이고, 운영에서는 LB/CDN 대역만 지정한다. |
| 다중 신뢰 대역 | http 수준 템플릿은 값을 하나만 받는다. 이미지의 쉼표 분리 처리는 location 파일에만 적용된다. |

## 10. 정리

- OrbStack 포트포워딩이 외부 기기의 출발지 IP까지 게이트웨이로 바꾸는 것을 실측했다. 앞단 프록시 신뢰 모델로 원 IP를 복원했다.
- realip를 location 수준에 두면 앱 로그만 원 IP가 되고 ModSecurity는 게이트웨이를 본다. 앱 로그만 확인했다면 해결된 것으로 오판했을 문제다. audit 로그의 client_ip까지 확인해서 드러났다.
- "X-Forwarded-For 첫 값 신뢰"는 흔한 구현이지만 로그 IP 변조와 IP 기준 탐지 우회로 이어진다. 원 IP 판정은 WAF 한 곳에서만 한다.
- IP 기준 룰 하나로는 분산 스터핑, 스프레이, API 키 대입을 하나도 잡지 못했다. 집계 기준을 계정과 IP로 나눈 상관 룰 3개로 바꿔 잡았다.
- 설정 검사 통과가 룰 동작을 보장하지 않는다. 정적 필드에 `same_field`를 쓴 실수는 음성 케이스를 넣은 logtest로 드러났다.
- 로그 필드 이름 하나(`username`과 `user`)가 SIEM 상관분석에 사각지대를 만들 수 있다.

다음 단계(P4)에서는 지금까지의 룰을 대시보드와 주간 리포트로 묶고, 100310~100312 대응 절차(Playbook)를 정리한다.

## 참고

- [OrbStack Issue #710 — Remote IP is always the Orbstack host](https://github.com/orbstack/orbstack/issues/710)
- [nginx — ngx_http_realip_module](https://nginx.org/en/docs/http/ngx_http_realip_module.html)
- [Wazuh — Rules Syntax](https://documentation.wazuh.com/4.14/user-manual/ruleset/ruleset-xml-syntax/rules.html)
- [MITRE ATT&CK T1110.004 — Credential Stuffing](https://attack.mitre.org/techniques/T1110/004/)
- [MITRE ATT&CK T1110.003 — Password Spraying](https://attack.mitre.org/techniques/T1110/003/)
- [RFC 5737 — IPv4 Address Blocks Reserved for Documentation](https://www.rfc-editor.org/rfc/rfc5737)
