---
layout: single
title: "[웹 탐지] panoptes-detect P0 — ModSecurity CRS 감사 로그를 Wazuh alert로 잇는 베이스라인"
excerpt: "웹 보안 탐지 운영 실습 panoptes-detect의 첫 단계(P0). Mac mini M4의 OrbStack 위에 ModSecurity v3 + OWASP CRS 4.30.0(DetectionOnly)과 Wazuh 4.14.9 single-node를 올리고, 요청 → WAF → 감사 로그 → Wazuh agent → manager 룰 → alert까지 전 구간을 확인했다. 수집 경로는 agent 로컬 설정이 아니라 그룹 agent.conf로 배포했고, SQLi 요청이 CRS 942100으로 탐지되어 커스텀 룰 100201(level 6, MITRE T1190) alert로 남는 것을 확인했다. 구성 중 겪은 인증서 생성 실패, admin 예약 계정 비밀번호 변경, 해시 오타로 인한 401 등 트러블슈팅과 P1 이후로 넘긴 열린 항목도 정리했다."
date: 2026-10-26
categories: ["Security", "웹 탐지"]
permalink: "/infra/security/panoptes-p0-baseline/"
tags: [ModSecurity, OWASP-CRS, Wazuh, WAF, SIEM, OrbStack, MITRE-ATTACK, 탐지룰, 실측]
---

웹 보안 탐지 운영(WAF·Bot·API·인증 공격 탐지)을 직접 구성해 보는 실습 프로젝트 panoptes-detect의 첫 기록이다. P0의 목표는 탐지 품질이 아니라 파이프라인이 끝까지 이어지는지 확인하는 것이다. 요청 하나가 WAF를 지나 감사 로그로 남고, Wazuh agent가 이를 수집해 manager 룰에 매칭되고, 대시보드에서 alert로 조회되는 전 구간을 확인했다.

> 요약
> - Mac mini M4(arm64)의 OrbStack 위에 ModSecurity v3.0.17 + OWASP CRS 4.30.0(Paranoia Level 1, DetectionOnly)과 Wazuh 4.14.9 single-node(manager·indexer·dashboard)를 Docker로 구성했다.
> - WAF 감사 로그(JSON)는 Mac에 설치한 Wazuh agent가 수집한다. 수집 경로는 agent 로컬 설정이 아니라 manager의 그룹 설정(`panoptes-waf` 그룹의 `agent.conf`)으로 배포했다.
> - 커스텀 룰 2개를 추가했다. 100200(level 3)은 ModSecurity 감사 이벤트 전체, 100201(level 6)은 CRS 942xxx(SQLi) 매칭이며 MITRE T1190에 매핑했다.
> - smoke 테스트 결과 SQLi 요청 1건이 942100 → 949110(이상 점수 8 ≥ 5)으로 탐지되어 100201 alert가 됐다. 정상 요청 2건도 920350(Host가 숫자 IP) 때문에 100200 alert로 남았다. P1 오탐 튜닝의 첫 사례다.
> - WAF 로그의 `client_ip`가 실제 클라이언트가 아니라 OrbStack 게이트웨이 주소로 기록되는 문제를 열린 항목으로 남겼다.

## 1. 실습 배경과 P0 범위

WAF는 차단 장비이기도 하지만, 탐지 운영 관점에서는 로그 생산자다. WAF가 남긴 이벤트를 SIEM으로 모아 룰로 분류하고, 오탐을 줄이고, 공격 유형별로 대응 기준을 만드는 것이 탐지 운영의 실무다. 이 프로젝트는 그 흐름을 단계별로 구성한다.

SIEM으로 Wazuh를 선택한 이유는 다음과 같다.

- 무료 오픈소스이고 single-node Docker Compose 구성이 공식 제공되어, Mac mini 한 대로 꾸리는 실습 환경에 부담 없이 올릴 수 있다.
- agent(수집)·manager(디코더·룰 엔진)·indexer(저장)·dashboard(조회)가 한 스택에 들어 있다. ELK처럼 수집부터 탐지까지 직접 조립하지 않아도 되므로, 파이프라인이 끝까지 이어지는지 확인하는 것이 목표인 P0에 맞다.
- 룰이 부모–자식 계층 구조라, 이번처럼 이벤트 전체(100200)에서 SQLi 분류(100201)로 단계적으로 좁혀 가는 탐지 룰 작성 연습에 적합하다. MITRE ATT&CK 매핑도 룰에 직접 넣을 수 있다.
- 그룹 단위 중앙 설정 배포(`agent.conf`), 룰 검증 도구(`wazuh-logtest`) 같은 운영 기능이 기본 제공된다. 이 글에서도 둘 다 사용했다.

P0는 그중 가장 앞단이다. 범위는 다음과 같다.

- WAF는 차단하지 않고 탐지만 한다(DetectionOnly). 차단 정책은 오탐 튜닝 이후에 다룬다.
- 백엔드는 요청을 그대로 돌려주는 echo 서버를 임시로 둔다. 보호 대상 서비스는 이후 단계에서 교체한다.
- 탐지 룰은 "이벤트가 들어온다"와 "SQLi가 분류된다" 두 가지만 만든다.

## 2. 구성 요소와 버전

| 구성 요소 | 값 |
| --- | --- |
| 실행 환경 | Mac mini M4 (arm64), OrbStack |
| WAF 이미지 | `owasp/modsecurity-crs:nginx` (digest 고정) |
| ModSecurity / connector | v3.0.17 / ModSecurity-nginx v1.0.4 |
| OWASP CRS | 4.30.0 (Paranoia Level 기본값 1, DetectionOnly) |
| 백엔드 | `mendhak/http-https-echo` (P0 임시) |
| Wazuh | 4.14.9 single-node Docker (manager, indexer, dashboard) |
| Wazuh agent | 4.14.9 macOS arm64, 이름 `macmini-waf`, ID 001 |

WAF 이미지는 태그가 아니라 sha256 digest로 고정했다. `nginx` 태그는 CRS 릴리스에 따라 갱신되므로, 같은 결과를 재현하려면 이미지가 바뀌지 않아야 한다.

## 3. 데이터 흐름

```
client → waf:8080 → backend
          └ logs/modsec/audit.log (JSON, RelevantOnly)
               └ Wazuh agent (그룹 panoptes-waf의 agent.conf로 수집 경로 배포)
                    └ manager: json 디코더 → panoptes_rules.xml → alerts
```

- WAF는 감사 로그를 JSON 형식으로 남기고, 기록 대상은 `RelevantOnly`다. 경고·오류가 발생했거나 지정한 응답 코드에 해당하는 트랜잭션만 감사 로그에 쓰인다.
- Wazuh agent는 Mac 호스트에 설치했다. WAF 컨테이너가 마운트한 로그 디렉터리를 호스트 경로에서 읽는다.
- manager는 Wazuh 기본 json 디코더로 필드를 분리하고, 커스텀 룰 파일 `panoptes_rules.xml`로 분류한다.

## 4. Wazuh agent 등록과 그룹 설정

agent는 `macmini-waf`라는 이름으로 등록했고, `default`와 `panoptes-waf` 두 그룹에 속한다.

![Endpoints — macmini-waf agent](/assets/images/2026-10-26-panoptes-p0-baseline/02-agents-macmini-waf.jpg)

![Groups — default, panoptes-waf](/assets/images/2026-10-26-panoptes-p0-baseline/03-groups-list.jpg)

수집할 로그 경로는 agent의 로컬 `ossec.conf`에 넣지 않고, manager의 그룹 설정 파일(`wazuh/groups/panoptes-waf/agent.conf`)에 넣었다. 그룹 설정은 manager가 해당 그룹의 agent에 배포하므로, agent가 늘어나도 설정을 한 곳에서 관리할 수 있다.

```xml
<agent_config>
  <localfile>
    <log_format>json</log_format>
    <location>/Users/jongminpark/lab/panoptes-detect/logs/modsec/audit.log</location>
    <label key="panoptes_source">modsecurity</label>
  </localfile>
</agent_config>
```

![panoptes-waf 그룹의 agent.conf](/assets/images/2026-10-26-panoptes-p0-baseline/04-group-agent-conf.jpg)

- `log_format`을 `json`으로 지정하면 manager에서 json 디코더가 적용된다.
- `label`은 alert에 `data.panoptes_source` 필드로 붙는다. 이후 수집원이 늘어날 때(WAF 외 앱 로그, 인증 로그 등) 출처를 구분하는 용도다.

그룹을 할당하고 약 1분 안에 agent 로그에 다음 순서의 메시지가 남았다. 배포된 설정을 받아 재로드한 뒤 감사 로그를 읽기 시작했다는 뜻이다.

```
Agent is reloading due to shared configuration changes
Analyzing file: .../audit.log
```

## 5. 커스텀 룰

룰 파일은 `wazuh/rules/panoptes_rules.xml` 하나다.

| rule.id | level | 조건 | 비고 |
| --- | --- | --- | --- |
| 100200 | 3 | `transaction.producer.modsecurity` 필드가 있는 json 이벤트 | ModSecurity 감사 이벤트 전체 |
| 100201 | 6 | 100200 중 CRS 942xxx(SQLi) 룰 ID 포함 | MITRE T1190 매핑 |

100201의 조건을 만들면서 확인한 제약이 하나 있다. ModSecurity 감사 로그에서 매칭된 룰 목록은 `transaction.messages`라는 객체 배열이다. 디코딩 단계의 룰 엔진은 이 배열 안의 개별 필드(`messages[].details.ruleId` 같은)를 조건으로 쓸 수 없어서, 룰 ID 조건은 로그 원문에 대한 정규식으로 작성했다.

반면 indexer에 저장된 alert에서는 `data.transaction.messages.details.*`가 다중값 필드로 조회된다. 룰 조건으로는 못 쓰지만 대시보드 검색과 필터에는 쓸 수 있다.

룰은 `wazuh-logtest`에 실제 감사 로그 한 줄을 넣어 디코딩 결과와 매칭 룰을 단계별로 확인한 뒤 적용했다. 룰을 추가하기 전에는 alert가 0건이었는데, 기본 설정에서는 룰에 매칭된 이벤트만 alert로 저장되기 때문이다.

## 6. 검증

`scripts/p0_smoke.py`로 요청 3건을 보냈다. 헬스체크, 루트 경로, SQLi 패턴이 들어간 쿼리스트링이다.

| rule.id | level | uri | 매칭된 CRS 룰 |
| --- | --- | --- | --- |
| 100200 | 3 | `/healthz` | 920350(Host가 숫자 IP)만 매칭 |
| 100200 | 3 | `/` | 920350만 매칭 |
| 100201 | 6 | `/?id=1' OR '1'='1` | 942100(libinjection SQLi), 949110(이상 점수 8 ≥ 5) |

Threat Hunting에서 `rule.groups:panoptes`로 거르면 3건이 조회된다.

![Threat Hunting — panoptes 룰 alert 3건](/assets/images/2026-10-26-panoptes-p0-baseline/05-threat-hunting-panoptes.jpg)

SQLi alert의 상세를 보면, 감사 로그의 트랜잭션 정보와 CRS 매칭 정보가 필드로 분리되어 있다. `messages.details.file`에 920·942·949 룰 파일 3개가 함께 나온다. SQLi 요청도 Host가 `127.0.0.1:8080`이었기 때문에 920350(warning, 3점)이 같이 매칭됐고, 942100(critical, 5점)과 합쳐 이상 점수 8이 되어 차단 판정 룰 949110의 임계값 5를 넘었다. DetectionOnly 모드라 실제 차단은 하지 않는다(`is_interrupted: false`).

![SQLi alert 상세 — 트랜잭션·CRS 매칭 필드](/assets/images/2026-10-26-panoptes-p0-baseline/06-alert-detail-fields.jpg)

![SQLi alert 상세 — 룰·MITRE 필드](/assets/images/2026-10-26-panoptes-p0-baseline/07-alert-detail-rule-mitre.jpg)

100201에 MITRE 매핑을 넣었기 때문에 MITRE ATT&CK 대시보드에도 Initial Access / Exploit Public-Facing Application(T1190)으로 집계된다.

![MITRE ATT&CK 대시보드](/assets/images/2026-10-26-panoptes-p0-baseline/08-mitre-attack-dashboard.jpg)

참고로 Overview의 24시간 alert 수(Medium 48, Low 148)에는 panoptes 룰 외에 Wazuh 기본 룰이 만든 alert도 포함되어 있다. 이 실습의 alert만 보려면 `rule.groups:panoptes`로 거른다.

![Wazuh Overview](/assets/images/2026-10-26-panoptes-p0-baseline/01-wazuh-overview.jpg)

## 7. 트러블슈팅

| 증상 | 원인 | 조치 |
| --- | --- | --- |
| `unzip`이 "filename not matched"로 아무것도 풀지 않음 | zsh 대화형 모드는 `#`을 주석으로 처리하지 않아, 줄 끝 주석 문구가 인자로 전달됨 | 명령에 줄 끝 주석을 쓰지 않음. 필요하면 `setopt interactivecomments` |
| docker 명령이 `.orbstack/run/docker.sock` 연결 실패 | docker context가 OrbStack인데 OrbStack이 실행 중이 아님 | `open -a OrbStack` |
| smoke 테스트에서 Connection reset | WAF 기동 직후(health: starting)에 요청 | 스크립트에 `/healthz` 200 대기(최대 30초) 추가 |
| Wazuh 인증서 생성 중 `root-ca-manager.pem` Permission denied, 이어서 마운트 경로 mkdir 실패 | 인증서 생성기가 인증서 폴더 소유자를 바꾼 뒤 마지막 복사 단계에서 실패 | `root-ca.pem/.key`를 `root-ca-manager.pem/.key`로 직접 복사하고 소유자를 복원한 뒤 기동 |
| 대시보드에서 admin 비밀번호 변경 시 `Resource 'admin' is reserved` | admin은 예약 계정이라 UI·API로 변경 불가 | `internal_users.yml` 해시 교체, compose의 `INDEXER_PASSWORD` 변경, `securityadmin.sh` 적용 |
| 비밀번호 변경 후 새 비밀번호로 401 | `hash.sh`는 확인 입력이 없어 오타가 그대로 해시됨 | `htpasswd -nBC 12 admin`(2회 입력)으로 해시를 다시 만들어 적용 |
| `launchctl bootstrap` 두 번째 실행 시 `Input/output error(5)` | 이미 등록된 서비스를 다시 등록 | 무시. `launchctl print system/com.wazuh.agent`로 running 확인 |

두 가지는 따로 적어 둔다.

### admin 비밀번호 변경

Wazuh single-node Docker의 admin은 indexer 보안 플러그인의 예약 계정이다. 대시보드나 API에서 바꾸려고 하면 `Resource 'admin' is reserved` 오류가 난다. 변경하려면 세 곳을 함께 바꿔야 한다.

1. indexer 보안 설정 `internal_users.yml`의 admin 해시를 새 해시로 교체한다.
2. docker compose의 `INDEXER_PASSWORD`를 새 비밀번호로 바꾼다. manager·dashboard가 indexer에 접속할 때 쓰는 값이다.
3. `securityadmin.sh`로 보안 설정을 indexer에 반영한다.

### 해시 오타로 인한 401

위 절차를 마쳤는데도 새 비밀번호로 401이 났다. 저장된 해시와 입력한 비밀번호를 대조해 보니 일치하지 않았다. `hash.sh`는 비밀번호를 한 번만 입력받기 때문에 오타가 나도 그대로 해시가 만들어진다. 확인 입력을 받는 `htpasswd -nBC 12 admin`(bcrypt, cost 12)으로 해시를 다시 만들어 적용한 뒤 해결됐다.

## 8. 열린 항목

| 항목 | 내용 | 처리 단계 |
| --- | --- | --- |
| 클라이언트 IP | WAF 로그의 `client_ip`가 실제 클라이언트(127.0.0.1)가 아니라 OrbStack 게이트웨이(192.168.107.1)로 기록된다. Windows PC 등 외부 호스트에서 보낸 요청도 같은지 확인이 필요하다. | IP 기반 탐지(P3) 전에 원 IP 보존 방법 정리 |
| 정상 요청 alert | 헬스체크·정상 요청도 920350 때문에 level 3 alert가 된다. | P1 정탐·오탐 튜닝 첫 사례 |
| 포트 노출 | Wazuh 대시보드(443)·indexer(9200)·API(55000)가 Mac의 모든 인터페이스에 열려 있다. | 필요 시 127.0.0.1 바인딩 검토 |

클라이언트 IP 문제는 이후 단계에 직접 영향을 준다. 무차별 대입, 크리덴셜 스터핑, 봇 탐지는 대부분 출발지 IP 단위로 빈도를 센다. 모든 요청이 게이트웨이 주소 하나로 기록되면 이런 룰은 의미가 없어진다.

## 9. 실습 종료 시 agent 제거

Mac에 설치한 agent는 실습을 마치면 아래 순서로 제거한다.

```bash
sudo launchctl bootout system /Library/LaunchDaemons/com.wazuh.agent.plist
sudo /bin/rm -r /Library/Ossec
sudo /bin/rm -f /Library/LaunchDaemons/com.wazuh.agent.plist
sudo /bin/rm -rf /Library/StartupItems/WAZUH
sudo /usr/bin/dscl . -delete "/Users/wazuh"
sudo /usr/bin/dscl . -delete "/Groups/wazuh"
sudo /usr/sbin/pkgutil --forget com.wazuh.pkg.wazuh-agent
```

## 10. 정리

- P0에서 요청 → WAF → 감사 로그 → agent → manager 룰 → alert 전 구간을 확인했다. 이후 단계는 이 파이프라인 위에 룰과 수집원을 추가하는 작업이 된다.
- 수집 경로는 그룹 `agent.conf`로 배포했다. agent 로컬 설정을 손대지 않아도 되고, `label`로 수집원을 구분할 수 있다.
- ModSecurity 감사 로그의 `transaction.messages`는 객체 배열이라 디코딩 단계 룰 조건으로 개별 필드를 쓸 수 없다. 룰 조건은 원문 정규식으로, 조회는 indexer의 다중값 필드로 나눠서 쓴다.
- 룰은 `wazuh-logtest`로 디코딩과 매칭을 먼저 확인한 뒤 적용했다.
- 정상 요청도 alert가 되는 상태로 시작했다. 다음 글(P1)은 920350부터 정탐·오탐을 나누고 튜닝하는 과정을 다룬다.

## 참고

- [OWASP CRS Documentation](https://coreruleset.org/docs/)
- [coreruleset/modsecurity-crs-docker](https://github.com/coreruleset/modsecurity-crs-docker)
- [Wazuh — Centralized configuration (agent.conf)](https://documentation.wazuh.com/4.14/user-manual/reference/centralized-configuration.html)
- [Wazuh — Custom rules](https://documentation.wazuh.com/4.14/user-manual/ruleset/rules/custom.html)
- [Wazuh — wazuh-logtest](https://documentation.wazuh.com/4.14/user-manual/reference/tools/wazuh-logtest.html)
- [MITRE ATT&CK T1190 — Exploit Public-Facing Application](https://attack.mitre.org/techniques/T1190/)
