---
layout: single
title:  "Claude Skill 정리 (Antigravity Agent)"
date:   2026-02-11
categories: [AI, Tool]
tags: [Claude, Antigravity, Agent, Skill]
author_profile: false
---

## 개요
이 문서는 YouTube 영상 **[Claude Skills.. 앤트로픽에 $200를 내야하는 이유](https://www.youtube.com/watch?v=jxzpitU9YBg)**를 참고하여 작성함. 해당 영상에서는 Antigravity Agent가 사용하는 강력한 기능인 **Claude Skill** 시스템에 대해 설명하고 있음.

![Claude Skill Concept](/assets/images/26-02-11/claude_skill_concept.png)

## Claude Skill이란?
Claude Skill은 AI 에이전트(Antigravity)가 복잡한 작업을 수행할 수 있도록 돕는 **전문적인 지침(Instruction)** 과 **리소스(Resource)** 의 모음임. 단순한 프롬프트를 넘어, 특정 작업을 수행하기 위한 단계별 가이드, 스크립트, 예제 코드 등을 하나의 'Skill'로 패키징하여 에이전트가 필요할 때 불러와 사용할 수 있게 함.

### 핵심 개념
1.  **확장성 (Extensibility)**: 기본 AI 모델의 능력을 넘어 특정 도메인이나 작업에 특화된 기능을 추가할 수 있음.
2.  **표준화 (Standardization)**: 복잡한 작업 절차를 문서화하여 AI가 항상 일관된 방식으로 작업을 수행하도록 보장함.
3.  **재사용성 (Reusability)**: 자주 사용하는 워크플로우를 스킬로 정의해두면 언제든 재사용이 가능함.

## Skill의 구조
Antigravity 시스템에서 Skill은 특정 폴더 구조를 따름. 가장 핵심이 되는 파일은 `SKILL.md`임.

![Skill Folder Structure](/assets/images/26-02-11/skill_folder_structure.png)

### 1. `SKILL.md` (필수)
스킬의 메인 설명서 역할을 하는 파일임. YAML Frontmatter와 Markdown 본문으로 구성됨.

![SKILL.md File Structure Diagram](/assets/images/26-02-11/skill_file_diagram.png)

*   **YAML Frontmatter**: 스킬의 이름(name)과 설명(description)을 정의함. 에이전트는 이 정보를 통해 어떤 스킬을 언제 사용해야 할지 판단함.
*   **Markdown Instructions**: 스킬을 사용하는 구체적인 방법, 절차, 주의사항 등이 상세히 기술됨.

```markdown
---
name: deploy_to_production
description: 프로덕션 배포를 위한 워크플로우. 테스트, 빌드, 안전 점검 단계를 포함함.
---

# 에이전트 배포 지침 (Instructions)

## 1. 사전 점검 (Pre-deployment Checks)
- [ ] `npm run test`를 실행하여 모든 테스트가 통과하는지 확인할 것.
- [ ] `git status`를 확인하여 커밋되지 않은 변경 사항이 없는지 확인할 것.
- [ ] 현재 브랜치가 `main`인지 확인할 것.

## 2. 빌드 프로세스 (Build Process)
- `npm run build` 명령어를 실행할 것.
- 만약 빌드가 실패하면, 에러 로그를 분석하고 작업을 중단할 것.

## 3. 배포 (Deployment)
- 배포 스크립트 실행: `./scripts/deploy.sh`
- 출력 로그에서 "Success" 메시지가 나오는지 모니터링할 것.

## 4. 배포 후 검증 (Post-deployment Verification)
- 프로덕션 URL에 접속하여 정상 작동 여부를 확인할 것.
- 주요 기능(로그인, 대시보드 등)을 테스트할 것.
```

### 2. 추가 리소스 (선택)
복잡한 스킬의 경우 다음과 같은 하위 디렉토리를 포함할 수 있음.
*   `scripts/`: 작업을 자동화하는 헬퍼 스크립트
*   `examples/`: 참고할 수 있는 예제 코드나 구현 패턴
*   `resources/`: 템플릿 파일이나 기타 필요한 에셋

## 사용 방법
에이전트는 사용자의 요청을 분석하여 적절한 Skill이 있는지 판단함. 만약 관련 스킬이 있다면:

![Skill Execution Flowchart](/assets/images/26-02-11/skill_execution_flowchart.png)

1.  `view_file` 도구를 사용하여 해당 스킬의 **SKILL.md** 파일을 읽음.
2.  파일에 정의된 지침을 완벽하게 숙지함.
3.  지침에 따라 단계별로 작업을 수행하거나, 포함된 스크립트를 실행함.

## 왜 중요한가?
Claude Skill 시스템은 AI를 단순한 코딩 어시스턴트에서 **자율적인 전문가(Autonomous Expert)** 로 진화시킴.
*   **복잡도 관리**: 수십 단계에 이르는 복잡한 배포 과정이나 리팩토링 작업을 하나의 스킬로 정의하여 실수를 줄임.
*   **컨텍스트 유지**: 긴 프롬프트를 매번 입력할 필요 없이 스킬 파일 하나로 방대한 컨텍스트를 제공함.
*   **Custom Agent**: 사용자가 직접 스킬을 정의함으로써 자신만의 맞춤형 AI 에이전트를 구축할 수 있음.

## 결론
영상에서 강조하는 것처럼, 이러한 Skill 시스템은 Claude와 같은 고성능 LLM의 잠재력을 극대화하는 핵심 기능임. Antigravity Agent는 이러한 Skill 구조를 채택하여 사용자와의 페어 프로그래밍 효율을 획기적으로 높여줌.
