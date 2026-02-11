---
layout: single
title:  "Claude Code Teams 사용 가이드"
date:   2026-02-11
categories: [AI, Tool]
tags: [Claude, Code Teams, Agent, Collaboration]
author_profile: false
---

**Claude Code Teams**는 여러 Claude Code 인스턴스가 하나의 팀처럼 협업하여 복잡한 작업을 수행할 수 있도록 지원하는 기능임. 서로 다른 역할을 가진 에이전트들이 메시지를 주고받으며 중앙 집중식 관리 하에 자율적으로 작업을 조정함.

![Claude Code Teams Concept](/assets/images/26-02-11/claude_code_teams_concept.png)

## 핵심 기능 (Key Features)

### 1. 병렬 처리 및 조율 (Parallel Execution & Orchestration)
단일 에이전트가 순차적으로 처리해야 했던 작업을 여러 에이전트가 동시에 수행할 수 있음.
-   예: 한 에이전트는 UX를 검토하고, 다른 에이전트는 기술 아키텍처를 분석하며, 세 번째 에이전트는 '악마의 변호인(Devil's Advocate)' 역할을 수행하여 비판적인 시각을 제공함.

### 2. 컨텍스트 공유 및 통신 (Context Sharing & Communication)
*   **자동 메시지 전달**: 팀원 간의 메시지가 자동으로 전달되므로 리더가 일일이 업데이트를 확인할 필요가 없음.
*   **공유 작업 목록 (Shared Task List)**: 모든 에이전트가 작업 상태를 실시간으로 확인하고, 할당된 작업을 스스로 가져가서 처리함.

### 3. Sub-agents vs Agent Teams
| 구분 | Sub-agents | Agent Teams |
| :--- | :--- | :--- |
| **보고 체계** | 메인 에이전트에게만 보고 | 팀원 간 직접 소통 및 협업 가능 |
| **작업 방식** | 지시받은 특정 작업만 수행 | 공유된 목표를 위해 자율적으로 조율 |
| **적합한 사례** | 단일 작업 위임 | 복잡한 문제 해결, 다각도 분석 |

## 사용 방법 (How to Use)

### 1. 기능 활성화
현재 실험적 기능이므로 환경 변수를 설정해야 함.
```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```
또는 `settings.json` 설정:
```json
{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
```

### 2. 팀 시작하기 (Starting a Team)
Claude에게 자연어로 팀 구성을 요청할 수 있음.
> "I'm designing a CLI tool. Create an agent team to explore this from different angles: one on UX, one on technical architecture, one playing devil's advocate."

### 팀 구성 파일 및 아키텍처
*   **팀 설정 파일**: `~/.claude/teams/{team-name}/config.json`
*   **작업 목록 폴더**: `~/.claude/tasks/{team-name}/`

## 주의사항 및 팁 (Limitations & Best Practices)
*   **토큰 비용 증가**: 여러 에이전트가 병렬로 실행되므로 토큰 사용량이 급격히 증가할 수 있음. 복잡도가 높은 작업에만 신중하게 사용할 것.
*   **역할 분담**: 각 에이전트에게 명확한 역할과 컨텍스트를 부여해야 충돌 없이 효율적으로 협업할 수 있음.
*   **모니터링**: `broadcast` 기능(모두에게 메시지 보내기)은 비용이 많이 들므로 꼭 필요한 경우에만 사용하고, 주로 `message`로 특정 팀원과 소통하는 것이 좋음.

## 결론
Claude Code Teams는 AI 에이전트를 단순한 '도구'에서 '동료'로 격상시키는 기능임. 복잡한 프로젝트나 다각도의 검토가 필요한 연구 작업에서 특히 강력한 성능을 발휘할 것으로 기대됨.
