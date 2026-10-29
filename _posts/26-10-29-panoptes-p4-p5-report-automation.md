---
layout: single
title: "[웹 탐지] panoptes-detect P4·P5 — 설정 영구화, 파일로 관리하는 대시보드, Playbook, 그리고 리포트 자동화"
excerpt: "panoptes-detect의 마지막 두 단계. 매니저 설정이 VM 비정상 종료로 사라진 문제를 wazuh-docker의 config-mount 방식으로 풀고, 룰 파일을 일부러 비운 뒤 재기동해 복원되는 것을 확인했다. 대시보드는 UI 클릭 대신 저장 객체 NDJSON을 스크립트로 만들어 API로 가져왔다. 룰 18개를 MITRE ATT&CK에 매핑하고 고위험 룰 9종의 Playbook을 썼다. 주간 리포트와 오탐 후보 리포트는 스크립트가 알림 파일에서 생성하고, 같은 입력으로 두 번 돌려 md5가 같음을 확인한 뒤 cron에 걸었다. 오탐 분류기는 P1에서 사람이 찾아낸 920350을 같은 결론으로 분류했다. OrbStack은 컨테이너 재시작 중 두 번째로 죽었고, 배포 절차를 Docker 재시작 없는 방식으로 바꿨다."
date: 2026-10-29
categories: ["Security", "웹 탐지"]
permalink: "/infra/security/panoptes-p4-p5-report-automation/"
tags: [Wazuh, OpenSearch-Dashboards, SIEM, Playbook, MITRE-ATTACK, 리포트, 자동화, 오탐, 실측]
---

P3까지가 "무엇을 어떻게 잡는가"였다면 P4와 P5는 "잡은 것을 어떻게 보고, 판단하고, 반복하는가"다. intent의 완료 기준은 P4가 "시나리오별 Playbook 1건 이상, 리포트 1회분", P5가 "스크립트 실행으로 리포트 재현 가능"이다. 둘을 한 글로 묶는다.

> 요약
> - 설정 영구화: `docker cp`로 넣은 매니저 설정이 OrbStack 비정상 종료 때 사라졌다. wazuh-docker 이미지의 `/wazuh-config-mount/` 방식으로 바꾸고, 매니저 안의 룰 파일을 0바이트로 비운 뒤 재기동해 저장소 내용으로 복원되는 것을 확인했다.
> - 대시보드: 패널 7개를 저장 객체 NDJSON으로 만들어 API로 가져왔다. 파일이 곧 대시보드라 복원과 재현이 된다. 숫자 타일은 룰별 집계와 검산이 맞았다.
> - ATT&CK 매핑과 Playbook: 룰 18개를 전술·기법·계층·동작(차단/탐지/앱 차단)으로 정리하고, 고위험 룰 9종에 확인→판정→조치→오탐 고려→기록 순서의 절차를 썼다.
> - 리포트 자동화: 주간 리포트(439건)와 오탐 후보 리포트를 스크립트가 생성한다. 오탐 분류기는 920350을 "정상 경로 2xx 통과 36/50"으로 후보 판정했다. P1에서 손으로 내린 결론과 같다.
> - OrbStack이 컨테이너 재시작 중 또 죽었다. 배포는 Docker 재시작 없이 컨테이너 안에서 반영하고, 마운트는 다음 기동 때의 복원 보장으로 역할을 나눴다.

## 1. 설정 영구화 (P4-0)

### 왜 필요했나

P3-3에서 OrbStack이 비정상 종료(signal 11)된 뒤 Wazuh agent가 아무것도 수집하지 않았다. 매니저가 재기동 직후 만든 그룹 설정 묶음(`merged.mg`)에 panoptes 그룹 내용이 비어 있었다. 설정은 `docker cp`로 named volume에 넣었는데, cp 직후 1분 만에 VM이 죽으면서 디스크에 반영되지 않은 쓰기가 사라진 것으로 보인다.

### 이미지가 제공하는 방식

wazuh-docker 이미지의 `/etc/cont-init.d/0-wazuh-init`을 읽어 보니 기동 시 이런 복사를 한다.

```
mount_files() {
  if [ -e "$WAZUH_CONFIG_MOUNT" ]
  then
    exec_cmd_stdout "cp --verbose -r $WAZUH_CONFIG_MOUNT/* $WAZUH_INSTALL_PATH"
  ...
```

`/wazuh-config-mount/` 아래에 마운트한 파일이 `/var/ossec/`의 같은 경로로 복사된다. 기존 파일은 소유자·권한을 유지하고 내용만 바뀐다. 공식 compose가 `ossec.conf`를 넣는 방식과 같다.

업스트림 compose는 건드리지 않고 `docker-compose.override.yml`을 두었다. 경로는 상대경로라 사용자명이 들어가지 않는다.

```yaml
services:
  wazuh.manager:
    volumes:
      - ../../panoptes-detect/wazuh/rules/panoptes_rules.xml:/wazuh-config-mount/etc/rules/panoptes_rules.xml:ro
      - ../../panoptes-detect/wazuh/rules/panoptes_app_rules.xml:/wazuh-config-mount/etc/rules/panoptes_app_rules.xml:ro
      - ../../panoptes-detect/wazuh/rules/panoptes_waf_vpatch_rules.xml:/wazuh-config-mount/etc/rules/panoptes_waf_vpatch_rules.xml:ro
      - ../../panoptes-detect/wazuh/rules/panoptes_xcorr_rules.xml:/wazuh-config-mount/etc/rules/panoptes_xcorr_rules.xml:ro
      - ../../panoptes-detect/wazuh/groups/panoptes-waf/agent.conf:/wazuh-config-mount/etc/shared/panoptes-waf/agent.conf:ro
```

### 복원 실측

마운트가 정말 복원하는지는 망가뜨려 봐야 안다. 매니저 안의 교차 상관 룰을 비우고 재시작했다.

```
$ docker exec single-node-wazuh.manager-1 sh -c ': > /var/ossec/etc/rules/panoptes_xcorr_rules.xml; wc -c ...'
0 /var/ossec/etc/rules/panoptes_xcorr_rules.xml

$ docker compose restart wazuh.manager && sleep 20 && sh scripts/wazuh_verify.sh
same     wazuh/rules/panoptes_app_rules.xml
same     wazuh/rules/panoptes_rules.xml
same     wazuh/rules/panoptes_waf_vpatch_rules.xml
same     wazuh/rules/panoptes_xcorr_rules.xml
same     wazuh/groups/panoptes-waf/agent.conf
ok       ruleset load
ok       merged.mg localfile=4
```

검증 스크립트는 매니저 안 파일과 저장소 파일의 md5, 룰셋 로드(`wazuh-analysisd -t`), 그룹 묶음의 수집 대상 수를 한 번에 본다. 첫 버전은 agent.conf의 컨테이너 경로를 잘못 매핑해(`etc/groups/` → 실제는 `etc/shared/`) 정상인데도 `DIFF`를 냈다. 복사 로그에는 정상이었으니 스크립트 쪽을 의심할 수 있었다.

## 2. 대시보드를 파일로 (P4-1)

대시보드를 UI에서 클릭해 만들면 재현이 안 된다. 저장 객체(visualization, search, dashboard)를 NDJSON으로 만드는 스크립트를 쓰고, 대시보드 API로 가져왔다.

```
$ python3 scripts/build_dashboard.py > wazuh/dashboard/panoptes-dashboard.ndjson
```

가져오기는 로그인한 브라우저 세션에서 `fetch('/api/saved_objects/_import?overwrite=true', ...)`로 했다. 비밀번호를 스크립트에 넣지 않아도 된다.

```
{"status":200,"success":true,"count":8,"errors":[]}
```

![Saved Objects — 가져온 panoptes 객체 8개](/assets/images/2026-10-29-panoptes-p4-p5-report-automation/04-saved-objects-panoptes.jpg)

패널은 운영자가 아침에 한 번 보고 판단할 수 있는 구성으로 7개다.

| 패널 | 답하는 질문 |
| --- | --- |
| 가상 패치 차단 / DLP 탐지 / 교차 상관 (숫자 타일) | 차단·탐지·고위험이 몇 건인가 |
| 룰별 알림 추이 | 언제 무엇이 늘었나 |
| 출처별(WAF/앱) | 어느 계층에서 잡히는가 |
| 출발지 상위 10 | 어느 IP가 시끄러운가 |
| MITRE 전술 분포 | 공격 단계별 분포 |
| 룰별 건수 (표) | 무슨 룰이 몇 건, level은 |
| 고위험 알림 (level ≥ 10) | 바로 볼 것 |

![대시보드 상단 — 숫자 타일 9/3/1, 룰별 추이, 출처별](/assets/images/2026-10-29-panoptes-p4-p5-report-automation/01-dashboard-top-kpi-timeline.jpg)

숫자 타일은 검산했다. 가상 패치 차단 9 = 100211 6건 + 100221 3건, DLP 탐지 3 = 100220, 교차 상관 1 = 100330.

![출발지 상위, MITRE 전술 분포](/assets/images/2026-10-29-panoptes-p4-p5-report-automation/02-dashboard-topsrc-mitre.jpg)

"출발지 상위"는 해석에 주의가 필요하다. 정규화 필드 `srcip` 기준이라 P3-3에서 수집 경로를 바꾼 시점(10/28 21:06) 이후 알림만 집계된다. 전체 집계에서 1위였던 API 키 대입 출발지(198.51.100.60, 120건)는 정규화 전이라 이 패널에 없다. 패널 설명에 적어 두었다.

![룰별 건수 표, 고위험 알림 목록](/assets/images/2026-10-29-panoptes-p4-p5-report-automation/03-dashboard-rules-table-highrisk.jpg)

## 3. ATT&CK 매핑과 Playbook (P4-2, P4-3)

룰 18개를 전술·기법·계층·동작으로 정리했다. 동작은 세 가지로 구분한다. 차단(요청이 앱에 닿기 전 WAF가 끊음), 탐지(알림만), 앱 차단(앱이 거부하고 이벤트 기록).

| 전술 | 기법 | 룰 | 동작 |
| --- | --- | --- | --- |
| Initial Access | T1190 | 100201 CRS SQLi, 100221 디버그 가상 패치, 100304/100305 권한 거부, 100330 교차 | 탐지 / 차단 / 앱 차단 / 탐지 |
| Credential Access | T1110, .003, .004 | 100301~100303, 100306, 100310~100312 | 탐지, 잠금은 앱 차단 |
| Credential Access | T1552 | 100220 응답 내 비밀값 | 탐지 전용(차단 불가 실측) |
| Discovery | T1083 | 100210/100211 경로 탐색, 100308 앱 경로 탐색 | 탐지 / 차단 / 앱 차단 |

비어 있는 곳도 적었다. DoS·봇(T1498/T1499), 탈취 계정의 정상 사용(T1078), 스캐닝(T1595), 계정 열거(응답 코드 차이)다.

Playbook은 고위험 룰 9종에 대해 같은 틀로 썼다. 확인 → 판정 → 조치 → 오탐 고려 → 기록. 예를 들어 100330(같은 출발지 WAF 공격 + 계정 잠금)은 이렇다.

1. 확인: 출발지, 잠긴 계정, 10분 안의 WAF 룰
2. 성공 여부: 그 계정의 `auth.login.success`가 있으면 계정 탈취 의심으로 격상
3. 조치: 세션 무효화, 비밀번호 재설정 유도, 출발지 WAF 차단 후보
4. 오탐 고려: 보안 점검 스캐너와 QA 계정이 같은 출발지에서 돌면 발생
5. 기록: 출발지, 계정, 공격 유형, 성공 여부, 조치, 통지 여부

공통 원칙은 두 가지다. SIEM 알림만으로 판단하지 않고 원본 로그로 재확인한다. 차단 조치 뒤에는 정상 트래픽에 403이 없는지 확인한다.

## 4. 리포트 자동화 (P4-4, P5)

### 주간 리포트

`scripts/weekly_report.py`는 Wazuh의 알림 파일(일자별 보관 파일 포함)을 받아 기간별 집계를 Markdown으로 만든다. 판단이나 권고는 넣지 않는다. 판단은 Playbook으로 사람이 한다.

```
| 항목 | 건수 |
|---|---|
| 전체 알림 | 439 |
| level ≥ 10 (상관·차단·잠금) | 30 |
| 가상 패치 차단 (100211+100221) | 9 |
| DLP 탐지, 차단 아님 (100220) | 3 |
| 교차 상관 WAF+잠금 (100330) | 1 |
| 계정 잠금 (100303) | 5 |
| 고유 출발지 | 18 |
```

439라는 숫자는 손으로 더한 집계표와 대조했다. 처음 암산한 456은 틀렸고, 다시 더하니 3 + 67 + 369 = 439로 스크립트와 일치했다. level ≥ 10 30건은 대시보드 고위험 패널의 "1–30 of 30"과 같다.

### 오탐 후보 분류

`scripts/fp_triage.py`는 네 가지 기준으로 후보를 낸다. 룰을 끄거나 예외를 넣는 일은 하지 않는다.

| 기준 | 판단 근거 |
| --- | --- |
| A | CRS 룰이 매칭됐지만 요청이 2xx로 끝났고 경로가 정상 흐름 경로 |
| B | 허용 목록(모니터링·NAT·점검) 출발지에서 발생한 고위험 알림 |
| C | 단일 출발지·단일 계정이 임계값에 맞춰 발생한 잠금·반복 실패 |
| D | 감사 이벤트 중 룰 매칭 0건 비율 (오탐이 아니라 수집 노이즈) |

실제 데이터(10/26~10/29)로 돌린 A 결과다.

```
| CRS 룰 | 매칭 | 2xx 통과 | 정상경로 통과 | 주요 경로 | 판정 힌트 |
| 920350 | 50 | 36 | 36 | /auth/login×16, /orders×16 | 오탐 후보 |
| 930100 | 3 | 0 | 0 | /files/..%5c..%5cwindows%5cwin.ini×3 | 정탐 가능성 |
| 930110 | 3 | 0 | 0 | (같음) | 정탐 가능성 |
| 1000100 | 1 | 0 | 0 | (같음) | panoptes 룰 — 후보 아님 |
```

920350은 P1에서 사람이 로그를 보며 "검증 환경에서 IP로 접속해 생긴 오탐"이라고 결론 내린 룰이다. 분류기가 같은 결론을 냈다. 경로 탐색 계열은 전부 403에 공격 경로라 정탐으로 갈린다.

C 기준에는 한계가 보였다. 분산 스터핑 시뮬레이션에서 생긴 alice 잠금 2건이 "오입력 가능"으로 나왔다. 같은 시간대의 100310(분산 스터핑)을 함께 보면 공격인데, 분류기는 단일 룰만 본다. 힌트 문구에 "같은 시간대 100310/100311/100330 확인"을 넣었고, 다음 개선 항목으로 적었다.

D는 76%였다. 감사 이벤트 221건 중 167건이 룰 매칭 없는 4xx 기록이다. 공격 시뮬레이션의 401·423 응답이 WAF 감사 로그와 앱 로그 양쪽에 남아 100200이 앱 이벤트의 복사본처럼 쌓인다. 수집 범위를 줄이는 결정은 데이터를 더 본 뒤에 하기로 하고 보고만 했다.

### 재현성과 주기 실행

```
$ sh scripts/run_reports.sh 2026-10-26 2026-10-29
generated: docs/reports/2026-W44.md docs/reports/2026-W44-fp.md

$ md5 -q docs/reports/2026-W44.md docs/reports/2026-W44-fp.md > /tmp/r1
$ sh scripts/run_reports.sh 2026-10-26 2026-10-29 > /dev/null
$ md5 -q docs/reports/2026-W44.md docs/reports/2026-W44-fp.md | diff /tmp/r1 - && echo "재현 OK"
재현 OK
```

cron에 매주 월요일 09:10으로 걸었다. Mac이 꺼져 있으면 그 주는 건너뛰고 다음 주에 "지난 7일"만 집계되므로, 빠진 기간은 기간을 명시해 수동으로 채운다.

## 5. OrbStack이 또 죽었다

공개 전환 정리로 agent.conf의 수집 경로를 사용자 홈이 아닌 `/opt/panoptes/logs`(심볼릭 링크)로 바꾸고 매니저를 재시작하는 순간, OrbStack이 두 번째로 비정상 종료됐다(signal 11). 이번엔 `docker compose restart --no-deps wazuh.manager` 직후였다. 로그에는 `vmnet unresponsive`가 그날 OrbStack 첫 기동 때부터 찍혀 있었다.

두 번 모두 매니저 컨테이너의 네트워크 재연결 시점과 겹친다. OrbStack은 고칠 수 없으니 배포 절차를 바꿨다.

| 변경 | 반영 방법 | Docker 재시작 |
| --- | --- | --- |
| agent.conf | `docker cp` + 소유자·시각 갱신 → 매니저가 묶음 자동 재생성 | 없음 |
| 룰 | `docker cp` + 컨테이너 안 `wazuh-control restart` | 없음(프로세스만) |

마운트는 다음 컨테이너 기동 때의 복원을 보장하고, 당장의 반영은 컨테이너 안에서 한다. `docker compose up -d`가 파일 변경만으로는 컨테이너를 다시 만들지 않는다는 점도 이때 확인했다. `Running` 한 줄만 찍히고 복사는 일어나지 않는다.

복구 후 심볼릭 링크 경로가 실제로 수집되는지 확인했다.

```
$ sudo grep "Analyzing file" /Library/Ossec/logs/ossec.log | tail -n 2
... Analyzing file: '/opt/panoptes/logs/normalized/modsec.log'.
... Analyzing file: '/opt/panoptes/logs/normalized/app.log'.

$ (스프레이 시뮬레이션 후)
6 100301 /opt/panoptes/logs/normalized/app.log
1 100311 /opt/panoptes/logs/normalized/app.log
```

알림의 `location`에서 사용자명이 사라졌다. 이전 글들의 캡처에서 매번 가려야 했던 값이다.

## 6. 정리

- 설정은 저장소 파일이 원본이어야 한다. `docker cp`는 복사본을 만들 뿐이고, 복사본은 사라질 수 있다.
- 대시보드도 파일로 관리하면 복원과 변경 추적이 된다. 가져오기는 로그인 세션의 API 호출이면 충분하다.
- 리포트는 집계만, 판단은 Playbook으로. 자동 분류기는 사람이 내린 결론(920350)을 재현했지만, 단일 룰만 보는 한계도 함께 드러냈다.
- 재현성은 같은 입력으로 두 번 돌려 비교해야 확인된다.
- 환경의 불안정(OrbStack)은 절차로 우회한다. 재시작이 위험하면 재시작하지 않는 배포 경로를 만든다.

이로써 intent의 P0~P5가 끝났다. 남은 것은 열린 질문(저장소 공개, 경계 방화벽 계층)과 비어 있는 탐지 영역(DoS·봇, 탈취 계정 사용)이다.

## 참고

- [wazuh-docker — 컨테이너 설정 마운트](https://github.com/wazuh/wazuh-docker)
- [OpenSearch Dashboards — Saved objects API](https://docs.opensearch.org/latest/dashboards/)
- [MITRE ATT&CK — Enterprise Matrix](https://attack.mitre.org/matrices/enterprise/)
