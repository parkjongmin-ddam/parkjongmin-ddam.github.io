---
layout: single
title: "[SQL Server] AlwaysOn AG Failover 검증 — 수동·자동 장애조치와 노드 복구를 눈으로 확인하기"
excerpt: "구축한 2노드 AlwaysOn AG가 실제로 작동하는지 검증한 기록. 수동 장애조치로 역할 전환·데이터 보존·Listener 이동을 확인하고, 주 노드를 강제로 죽여 자동 장애조치와 데이터 손실 0을 검증한 뒤, 죽은 노드를 되살려 자동 재동기화까지 확인함."
date: 2026-07-08
categories: [Infra, SQL Server]
tags: [sql-server, alwayson, availability-group, failover, wsfc, listener, high-availability, 고가용성, 장애조치]
---

## 들어가며

[지난 글](/)에서 Hyper-V 랩에 2노드 AlwaysOn AG를 구축했음. 아홉 개의 트러블슈팅을 뚫고 AG-TEST + Listener까지 완성했지만, 거기까지는 **"구성이 됐고 동기화가 건강하다"**까지였음. 정작 중요한 질문 — **"진짜 서버가 죽으면 자동으로 넘어가느냐, 데이터는 안 잃느냐"** — 는 아직 확인 전이었음.

이 글은 그 검증 기록임. AG의 가치는 결국 장애 상황에서 드러나기 때문에, 아래 3가지를 순서대로 확인했음.

1. **수동 장애조치** — 계획된 전환(패치·점검 등)이 매끄럽게 되는가
2. **자동 장애조치** — 주 노드가 갑자기 죽었을 때 사람 개입 없이 넘어가는가
3. **노드 복구** — 죽었던 노드가 살아나면 자동으로 따라잡는가

검증에 쓸 샘플 테이블은 1편에서 만든 `dbo.FailoverTest`임. 각 단계마다 데이터를 한 줄씩 추가해서, 장애조치 후에도 그 데이터가 그대로 보이는지로 **데이터 손실 여부**를 확인함.

**검증 시작 시점의 상태**

| 복제본 | 역할 | 동기화 | 비고 |
|---|---|---|---|
| SQL01 | PRIMARY | HEALTHY | 주 복제본 |
| SQL02 | SECONDARY | HEALTHY | 동기 커밋, 자동 장애조치 |

---

## 목차

1. [검증 전 상태 확인](#1-검증-전-상태-확인)
2. [Failover 1 — 수동 장애조치](#2-failover-1--수동-장애조치)
3. [Failover 2 — 자동 장애조치](#3-failover-2--자동-장애조치)
4. [Failover 3 — 죽은 노드 복구·재동기화](#4-failover-3--죽은-노드-복구재동기화)
5. [핵심 정리 — 쿼리를 어느 서버에서 실행하는가](#5-핵심-정리--쿼리를-어느-서버에서-실행하는가)

---

## 1. 검증 전 상태 확인

장애조치 테스트, 특히 자동 장애조치는 노드를 강제로 죽이는 작업이라 먼저 두 가지를 확인함.

**① AG가 건강한지 (DB 레벨)**

```sql
SELECT
    ar.replica_server_name AS 복제본,
    DB_NAME(drs.database_id) AS DB명,
    drs.synchronization_state_desc AS 동기화상태,
    drs.is_commit_participant AS 커밋참여,
    drs.synchronization_health_desc AS 건강도
FROM sys.dm_hadr_database_replica_states drs
JOIN sys.availability_replicas ar ON drs.replica_id = ar.replica_id;
```

양 노드가 `SYNCHRONIZED` + `커밋참여 1` + `HEALTHY`로 나와야 함. 특히 **자동 장애조치는 보조가 SYNCHRONIZED 상태여야만 발동**하므로 이 확인이 필수임. (SYNCHRONIZING이면 아직 조건 미충족)

![DB 레벨 동기화 상태 — 양 노드 SYNCHRONIZED / 커밋참여 1 / HEALTHY](/assets/images/26-07-08-failover/01-db-sync-check.png)
*그림 1-1. DB 레벨 동기화 확인 — SQL01·SQL02 모두 SYNCHRONIZED, 커밋참여 1, HEALTHY*

같은 상태를 SSMS의 **Always On Dashboard**(AG 우클릭 → Show Dashboard)로도 확인할 수 있음. GUI로 한눈에 보고 싶을 때 유용함.

![Always On Dashboard — AG-TEST hosted by SQL01, 양 복제본 Synchronized](/assets/images/26-07-08-failover/03-dashboard.png)
*그림 1-2. Dashboard — Primary SQL01, 양 복제본 Synchronous commit / Synchronized / No Data Loss*

> **참고**: `sys.dm_hadr_availability_replica_states`에서 보조 복제본의 `operational_state_desc`가 NULL로 나올 수 있는데, 이건 원격 복제본의 운영상태를 주에서 못 가져오는 표시상의 문제일 뿐임. `synchronization_health_desc = HEALTHY`이고 DB 레벨이 SYNCHRONIZED면 정상.

![AG 전체 상태 — SQL02의 운영상태(operational_state_desc)만 NULL](/assets/images/26-07-08-failover/02-ag-state-check.png)
*그림 1-3. AG 전체 상태 확인 — 건강도는 양쪽 HEALTHY지만 SQL02의 운영상태 컬럼만 NULL(표시상 문제)*

**② 체크포인트 생성**

강제 종료 테스트 전에 롤백 지점을 만들어둠. Hyper-V 호스트에서:

```powershell
Checkpoint-VM -Name "SQL01" -SnapshotName "s4-ag-complete"
Checkpoint-VM -Name "SQL02" -SnapshotName "s4-ag-complete"
```

> AG는 두 노드가 동기화된 상태로 동작하므로, 롤백할 때도 **양 노드를 같은 체크포인트로 함께** 되돌려야 함. 한쪽만 롤백하면 클러스터 상태가 어긋남.

---

## 2. Failover 1 — 수동 장애조치

가장 안전한 것부터. SSMS 마법사로 SQL02를 주 복제본으로 승격시킴. 실무에서 **계획된 유지보수**(주 노드 패치, 하드웨어 점검) 시 쓰는 방식임.

### 기준 데이터 추가

장애조치 직전에 현재 주(SQL01)에서 데이터를 한 줄 추가함. 이 데이터가 장애조치 후 SQL02에서도 보이면 = 동기화 정상.

```sql
-- SQL01(현재 주)에서
USE TestAG;
INSERT INTO dbo.FailoverTest (note) VALUES (N'수동 장애조치 직전 - SQL01에서 작성');
GO
SELECT * FROM dbo.FailoverTest;
```

![수동 장애조치 직전 데이터 추가 — SQL01에서 2번째 행 INSERT](/assets/images/26-07-08-failover/04-manual-baseline-data.png)
*그림 2-1. SQL01에서 "수동 장애조치 직전" 행 추가 — 현재 2건*

### 장애조치 실행

Object Explorer → SQL01 → Always On High Availability → Availability Groups → **AG-TEST** 우클릭 → **Failover...**

![AG-TEST 우클릭 → Failover 메뉴](/assets/images/26-07-08-failover/05-failover-menu.png)
*그림 2-2. AG-TEST 우클릭 → Failover... 선택*

마법사 진행:
- **Select New Primary Replica** → **SQL02** 선택
  - Failover readiness가 **"No data loss"**(초록)인지 확인
- **Connect to Replica** → SQL02에 Connect (Trust Server Certificate 체크)
- **Summary** → Finish

![Failover 마법사 Introduction](/assets/images/26-07-08-failover/06-wizard-intro.png)
*그림 2-3. Failover 마법사 시작 — Perform a planned failover*

![Select New Primary Replica — SQL02, No data loss](/assets/images/26-07-08-failover/07-select-primary.png)
*그림 2-4. 새 주 복제본으로 SQL02 선택 — Failover Readiness: No data loss(초록)*

![Connect to Replica — Trust server certificate 체크](/assets/images/26-07-08-failover/08-connect-replica.png)
*그림 2-5. 보조(SQL02)에 연결 — Trust Server Certificate 체크 후 Connect*

![Connect to Replica — 연결 완료](/assets/images/26-07-08-failover/09-connect-replica-done.png)
*그림 2-6. SQL02 연결 완료(Connected As: AZLAB\adm-jmpark)*

![수동 장애조치 Summary — No data loss](/assets/images/26-07-08-failover/10-manual-failover-summary.png)
*그림 2-7. Summary — Current Primary: SQL01 → New Primary: SQL02, Failover Actions: No data loss*

Summary에서 **"Failover Actions: No data loss"** 가 뜨는 게 핵심임. 동기 커밋이라 두 노드 데이터가 완전히 일치하므로 손실 없이 넘어갈 수 있음. (비동기였다면 "Data loss possible" 경고가 떴을 것)

![수동 장애조치 Results — 전부 Success](/assets/images/26-07-08-failover/11-manual-failover-results.png)
*그림 2-8. The wizard completed successfully — 역할 변경·WSFC 쿼럼 검증까지 전부 Success*

### 검증

**① 역할 뒤바뀜** (아무 창에서나 — AG 전체 구성 정보라 어느 노드에 물어도 같은 답)

```sql
SELECT ar.replica_server_name AS 복제본, ars.role_desc AS 역할
FROM sys.availability_groups ag
JOIN sys.availability_replicas ar ON ag.group_id = ar.group_id
JOIN sys.dm_hadr_availability_replica_states ars ON ar.replica_id = ars.replica_id;
```
결과: **SQL02 = PRIMARY**, SQL01 = SECONDARY. 역할이 뒤바뀜.

![SQL01 창에서 역할 조회 — SQL01 SECONDARY](/assets/images/26-07-08-failover/12-role-check-sql01.png)
*그림 2-9. SQL01 창에서 조회 — 자기 자신이 SECONDARY로 바뀐 게 보임*

![SQL02 창에서 역할 조회 — SQL02 PRIMARY, SQL01 SECONDARY](/assets/images/26-07-08-failover/13-role-check-sql02.png)
*그림 2-10. SQL02 창에서 같은 쿼리 — 어느 창에서 물어도 같은 답(SQL02=PRIMARY)*

**② 데이터 보존** (이제 주가 된 SQL02에서)

```sql
-- SQL02(현재 주)에서
USE TestAG;
SELECT * FROM dbo.FailoverTest;
```
SQL01에서 넣었던 두 행("AG 구성 전 초기 데이터", "수동 장애조치 직전")이 SQL02에 그대로 보임. **데이터 손실 0.**

![SQL02에서 데이터 확인 — @@SERVERNAME=SQL02, 2건 모두 보존](/assets/images/26-07-08-failover/14-data-preserved-sql02.png)
*그림 2-11. 새 주 SQL02에서 조회 — SQL01에서 넣은 2건이 그대로 보임(데이터 손실 0)*

**③ Listener 이동** (어느 서버에서 실행해도 무방 — Listener로 접속하는 것이므로)

```powershell
Invoke-Sqlcmd -ServerInstance "AGLISTENER" -Query "SELECT @@SERVERNAME AS ConnectedNode"
```
결과: **SQL02** 반환. Listener가 새 주 복제본을 자동으로 추적함.

![Listener 접속 — ConnectedNode: SQL02](/assets/images/26-07-08-failover/15-listener-sql02.png)
*그림 2-12. AGLISTENER 접속 → SQL02 반환 — Listener가 새 주를 자동 추적*

> **이것이 Listener의 존재 이유**: 앱은 물리 서버명(SQL01/SQL02)을 몰라도 Listener 이름 하나만 알면 항상 현재 주 복제본에 연결됨. 뒤에서 주 노드가 바뀌어도 앱은 여전히 `AGLISTENER`만 바라보면 됨. 그래서 이 명령을 어느 서버에서 실행하든 결과가 같은 게 오히려 정상임.

---

## 3. Failover 2 — 자동 장애조치

이 글의 핵심. **주 노드를 강제로 죽여서 사람 개입 없이 자동으로 넘어가는지** 확인함. 현재 주가 SQL02이므로, 이번엔 SQL02를 죽여서 SQL01이 자동 승격되는지 봄.

### 자동 장애조치용 데이터 추가

현재 주(SQL02)에서 한 줄 더 추가. 이 데이터가 SQL02가 죽은 후 SQL01에서도 보이면 = 죽기 직전 데이터까지 동기화됐다는 증거.

```sql
-- SQL02(현재 주)에서
USE TestAG;
INSERT INTO dbo.FailoverTest (note) VALUES (N'자동 장애조치 직전 - SQL02에서 작성');
GO
SELECT * FROM dbo.FailoverTest;
```

![자동 장애조치용 데이터 추가 — SQL02에서 3번째 행(id 1002)](/assets/images/26-07-08-failover/16-auto-baseline-data.png)
*그림 3-1. SQL02에서 "자동 장애조치 직전" 행 추가 — id가 2→1002로 점프(IDENTITY 캐시 갭)*

> **참고**: 이때 새 행의 id가 연속되지 않고 점프하는 경우가 있음(예: 2 다음이 1002). 이건 SQL Server의 IDENTITY 캐시 동작으로, 재시작·장애조치 시 캐시 갭이 생기는 정상 현상임. 데이터 자체엔 문제없음.

### 주 노드 강제 종료

SQL01(또는 어느 서버든)에서 원격으로 SQL02의 SQL 서비스를 중지함.

```powershell
Invoke-Command -ComputerName SQL02 -ScriptBlock { Stop-Service MSSQLSERVER -Force }
```

![원격으로 SQL02 SQL 서비스 강제 중지](/assets/images/26-07-08-failover/17-stop-sql02.png)
*그림 3-2. Invoke-Command로 SQL02의 MSSQLSERVER 서비스 강제 중지 — 주 노드를 죽임*

> **명령 위치 주의**: 이 명령은 `-ComputerName SQL02`로 대상이 고정돼 있어 **어느 서버에서 실행해도 죽는 건 SQL02**임. 곧 주가 될 SQL01에서 실행하면 이어서 바로 확인 쿼리를 돌릴 수 있어 편함. 단, SQL02에 직접 접속(RDP)한 상태에서 자기 자신을 대상으로 실행하는 건 피할 것. VM 자체를 죽이려면 호스트에서 `Stop-VM -Name "SQL02" -TurnOff -Force`도 가능(더 현실적인 장애 시뮬레이션).

### 자동 승격 확인

서비스 중지 후 WSFC가 장애를 감지하고 SQL01을 승격하는 데 몇 초~수십 초 걸림. **약 30초 대기 후** SQL01에서 확인.

```sql
-- SQL01에서
SELECT ar.replica_server_name, ars.role_desc, ars.connected_state_desc
FROM sys.availability_groups ag
JOIN sys.availability_replicas ar ON ag.group_id = ar.group_id
JOIN sys.dm_hadr_availability_replica_states ars ON ar.replica_id = ars.replica_id;

USE TestAG;
SELECT * FROM dbo.FailoverTest;
```

결과:

```
replica_server_name   role_desc    connected_state_desc
SQL01                 PRIMARY      CONNECTED       ← 자동 승격!
SQL02                 SECONDARY    DISCONNECTED    ← 죽은 상태
```

![자동 장애조치 후 — SQL01 자동 승격 + 데이터 3건 보존](/assets/images/26-07-08-failover/18-auto-failover-result.png)
*그림 3-3. SQL02를 죽인 것 외에 아무것도 안 했는데 SQL01이 PRIMARY(CONNECTED)로 자동 승격, SQL02는 DISCONNECTED, 데이터 3건 전부 보존*

**핵심 두 가지가 증명됨:**

1. **SQL01이 저절로 주가 됨** — SQL02 서비스를 죽인 것 말고 사람이 한 일이 없음. WSFC가 감지하고 자동 승격시킴.
2. **데이터 손실 0** — SQL02가 죽기 직전에 SQL02에서 넣은 "자동 장애조치 직전" 행이 SQL01에 그대로 살아있음. 동기 커밋 덕분에 이미 SQL01에 복제돼 있었기 때문.

Listener도 즉시 새 주(SQL01)를 따라감. 앱은 여전히 `AGLISTENER`만 바라보면 됨.

![Listener 접속 — 이제 ConnectedNode: SQL01](/assets/images/26-07-08-failover/19-listener-sql01.png)
*그림 3-4. 자동 장애조치 후 AGLISTENER 접속 → SQL01 반환 — Listener가 새 주를 자동 추적*

이게 고가용성의 존재 이유임. 정리하면 이런 시나리오가 자동으로 처리된 것.

```
새벽, 주 서버가 갑자기 다운
  ↓ (사람 없음)
WSFC 자동 감지 → 다른 노드를 주로 자동 승격
  ↓
서비스 유지, 데이터 손실 0
  ↓
아침에 보니 이미 넘어가 있음
```

---

## 4. Failover 3 — 죽은 노드 복구·재동기화

자동 장애조치 후 SQL02는 죽은 채로 남아있음. 이걸 되살려서 **보조로 복귀하며 그동안의 변경을 자동으로 따라잡는지** 확인함. (이 단계를 해야 랩이 양 노드 HEALTHY 정상 상태로 돌아감)

```powershell
-- SQL01에서 원격으로 SQL02 서비스 재시작
Invoke-Command -ComputerName SQL02 -ScriptBlock { Start-Service MSSQLSERVER }
```

![원격으로 SQL02 SQL 서비스 재시작](/assets/images/26-07-08-failover/20-restart-sql02.png)
*그림 4-1. Invoke-Command로 SQL02의 MSSQLSERVER 서비스 재시작 — 죽은 노드를 되살림*

약 30초 후 상태 확인.

```sql
SELECT ar.replica_server_name, ars.role_desc, ars.connected_state_desc,
       ars.synchronization_health_desc
FROM sys.availability_groups ag
JOIN sys.availability_replicas ar ON ag.group_id = ar.group_id
JOIN sys.dm_hadr_availability_replica_states ars ON ar.replica_id = ars.replica_id;
```

결과:

```
replica_server_name   role_desc    connected_state_desc   synchronization_health_desc
SQL01                 PRIMARY      CONNECTED              HEALTHY
SQL02                 SECONDARY    CONNECTED              HEALTHY   ← 복귀 완료
```

![노드 복구 — SQL02 재연결 + HEALTHY](/assets/images/26-07-08-failover/21-node-recovery.png)
*그림 4-2. SQL02가 SECONDARY로 복귀 — CONNECTED + HEALTHY로 자동 재동기화 완료(주는 SQL01 유지)*

SQL02가 되살아나면서:
- **CONNECTED** — 죽었을 때 DISCONNECTED였다가 재연결
- **SECONDARY** — 주는 SQL01이 유지, SQL02는 보조로 복귀 (자동으로 주를 뺏지 않음)
- **HEALTHY** — 죽어있는 동안 SQL01에서 바뀐 내용을 자동으로 따라잡아 재동기화 완료

여기서 주목할 점은 **SQL02가 살아났다고 다시 주 자리를 뺏지 않는다**는 것. AG는 불필요한 재장애조치를 하지 않고, 살아난 노드는 조용히 보조로 합류해서 따라잡음. 이 동작 덕분에 노드가 오르내려도 서비스가 요동치지 않음.

---

## 5. 핵심 정리 — 쿼리를 어느 서버에서 실행하는가

AG를 다루면서 가장 헷갈렸던 게 "이 명령을 어느 서버에서 실행해야 하는가"였음. 정리하면 이렇게 나뉨.

| 작업 | 실행 위치 | 이유 |
|---|---|---|
| **역할/상태 조회** (`sys.availability_*`) | 아무 노드나 | AG 전체 구성 정보라 어디서 물어도 같은 답 |
| **데이터 읽기/쓰기** (`SELECT/INSERT`) | 현재 **주** 복제본 | 쓰기는 주에서만. 보조는 읽기전용(Readable Secondary 설정 시) |
| **Listener 접속** (`-ServerInstance AGLISTENER`) | 아무 데서나 | Listener가 현재 주로 자동 연결 |
| **원격 서비스 제어** (`Invoke-Command -ComputerName`) | 아무 데서나 | 대상이 `-ComputerName`으로 고정됨 |

가장 실수하기 쉬운 건 **데이터 확인**임. 장애조치로 주가 바뀌면, 데이터를 읽고 쓰는 대상도 새 주 복제본으로 바뀜. 그래서 쿼리 실행 전에 습관적으로 `SELECT @@SERVERNAME;`으로 현재 창의 서버를 확인하는 게 안전함. (SSMS에서 원하는 서버 노드를 클릭하고 New Query를 열면 그 서버에 연결된 창이 생김)

### 검증 결과 요약

| 검증 | 결과 |
|---|---|
| 수동 장애조치 | 역할 전환·데이터 보존·Listener 이동 전부 정상 |
| 자동 장애조치 | 주 노드 강제 종료 → 다른 노드 자동 승격, 데이터 손실 0 |
| 노드 복구 | 죽은 노드 재시작 → 보조 복귀 + 자동 재동기화 (HEALTHY) |

---

## 마치며

1편에서 구축한 AG가 실제로 **장애 상황에서 자동으로 서비스를 지켜낸다**는 걸 눈으로 확인했음. 특히 자동 장애조치에서 "서비스를 죽인 것 외에 아무것도 안 했는데 다른 노드가 주로 올라오고 데이터도 그대로"인 순간이, 왜 고가용성 구성을 하는지를 가장 직관적으로 보여줬음.

문서로 "AG는 자동 장애조치를 지원한다"고 읽는 것과, 직접 주 노드를 죽여보고 다른 노드가 올라오는 걸 확인하는 것은 완전히 다른 경험이었음. 이제 AG의 전체 생명주기 — 구성 → 정상 운영 → 장애 → 자동 복구 → 노드 복귀 — 를 한 바퀴 돌려봤으니, 실제 운영에서 관련 이슈를 만나도 어디를 봐야 할지 감이 생겼음.

다음은 ADFS 랩의 선행 조건인 **2-Tier PKI/CA 구축**으로 넘어갈 예정임.
