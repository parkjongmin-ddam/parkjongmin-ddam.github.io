---
layout: single
title: "Prompt Engineering 완전 가이드 (Google · 2025) — 한국어 번역본"
categories: ["AI", "프롬프트·컨텍스트"]
permalink: "/llm/prompt-enginnering/"
tags: [Prompt Engineering, Google, Gemini, LLM, AI]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# Prompt Engineering 완전 가이드  
### Google · 2025  
### 한국어 전체 번역본  
**역자: parkjongmin-ddam — DDAMNOTE 블로그**

---

> ⚡ **이 문서는 Google이 2025년에 공개한 공식 Prompt Engineering Guide(68p)의 전체 한국어 번역본입니다.**  


---

# 📚 Table of Contents
{: .no_toc }

- TOC  
{:toc}

---

# 🧩 1. Introduction

대규모 언어 모델(LLM)은 텍스트·이미지를 입력받아 다음 토큰을 예측하는 방식으로 작동합니다.  
프롬프트 엔지니어링은 단순한 기능이 아니라, **모델의 출력을 원하는 방향으로 유도하는 설계 기술**입니다.

좋은 프롬프트는 다음의 영향을 받습니다:

- 모델 및 학습 데이터  
- 단어 선택  
- 구조/포맷  
- temperature/top-k 등 샘플링 설정  
- 제공되는 맥락(Context)

이 문서는 Vertex AI·Gemini 모델을 중심으로 설명합니다.

---

# 🧠 2. Prompt Engineering 개론

프롬프트 엔지니어링의 목적:

- 모델이 원하는 형식으로 안정적으로 답변하도록 유도  
- 환각(hallucination) 최소화  
- API/RAG 시스템과 결합되는 구조화 출력(JSON 등) 안정 확보  

프롬프트 엔지니어링은 **반복 실험 기반의 엔지니어링 작업**입니다.

---

# ⚙️ 3. LLM Output Configuration

프롬프트만큼 중요한 것이 **모델의 출력 설정(Output Config)**입니다.

### 주요 파라미터
- **max_tokens** — 출력 길이  
- **temperature** — 무작위성(창의성)  
- **top-k** — 상위 k개 토큰만 후보  
- **top-p** — 확률 누적 기반 후보 제한  
- **sampling 전략** — 무작위/결정적 선택 조정  

---

# 🔥 4. Temperature

| Temperature | 특징 |
|------------|-------|
| 0.0~0.3 | 안정적, 결정적 |
| 0.4~0.7 | 적당한 창의성 |
| 0.8~1.0+ | 더 창의적, 불안정성 증가 |

Temperature를 0으로 두면 **Top-K/Top-P는 거의 무의미**해집니다.

---

# 🎯 5. Top-K & Top-P

### ✔ Top-K  
확률 상위 K개만 후보로 사용.

### ✔ Top-P (Nucleus Sampling)  
확률 누적이 P 이하인 후보만 사용.

### ✔ 추천값  
- 일반 작업: `T=0.2, P=0.95, K=30`  
- 창의적 생성: `T=0.9, P=0.99, K=40`  
- 정확성 필수 작업(수학 등): `T=0`

---

# 🚨 6. Repetition Loop 오류

Sampling 설정이 잘못되면 다음과 같은 오류가 발생할 수 있습니다:

- “and and and…”  
- “this means that this means that…”  

Temperature·Top-K·Top-P 조합을 조절해 방지합니다.

---

# 🛠️ 7. Prompting Techniques (프롬프트 기법)

- Zero-shot  
- One-shot / Few-shot  
- System Prompting  
- Role Prompting  
- Contextual Prompting  
- Step-back  
- Chain-of-Thought (CoT)  
- Self-consistency  
- Tree of Thoughts (ToT)  
- ReAct  
- Automatic Prompt Engineering  

이들은 서로 조합될 수 있습니다.

---

# 🎯 8. Zero-shot Prompting

예시 없이 지시만으로 수행하는 기본 기법입니다.

문제가 복잡할수록 Zero-shot은 부정확해질 수 있습니다.

---

# 🎯 9. One-shot & Few-shot Prompting

예시를 1개 제공하면 One-shot,  
여러 개 제공하면 Few-shot입니다.

✔ 예시는 모델의 패턴 학습 능력을 비약적으로 끌어올립니다.

Few-shot 사용 시 권장:

- 3~5개의 다양성 높은 예시  
- 실수 없는 고품질 예시  
- 클래스 균형 유지  

---

# ⚙️ 10. System / Role / Context Prompting

### 🧩 SYSTEM  
출력 규칙·포맷·지침을 정의  
예: “항상 JSON으로 출력하라”

### 🧩 ROLE  
모델에게 역할 부여  
예: “너는 사이버 보안 전문가다”

### 🧩 CONTEXT  
배경·상황 정보 제공  
예: “이 문서는 금융기관 내부 정책이다”

---

# 🧠 11. Step-back Prompting

문제를 해결하기 전에  
“한 단계 추상적으로 생각하도록” 지시하는 방식입니다.

효과:

- 더 넓은 관점에서 reasoning  
- 개념 이해 개선  
- CoT와 결합 시 강력해짐

---

# 🔗 12. Chain-of-Thought(CoT)


중간 reasoning 과정을 명시적으로 작성하도록 유도합니다.

✔ 복잡한 문제 해결 능력 향상  
✔ 논리적 일관성 증가  

주의: 너무 긴 CoT는 오히려 오류를 증가시킬 수 있습니다.

---

# 🧩 13. Self-consistency

여러 개의 CoT를 생성하고  
가장 자주 등장하는 결론을 선택하는 방식입니다.

효과:

- 안정성 증가  
- 오답/환각 감소  
- 복잡한 논리 문제에 특히 강력

---

# 🌲 14. Tree of Thoughts (ToT)

여러 reasoning 경로(branch)를  
트리 형태로 확장하여 최적의 흐름을 선택하는 방식입니다.

적합한 작업:

- 전략 설계  
- 최적화 문제  
- 복잡한 추론  

---

# 🤖 15. ReAct (Reason + Act)

Reasoning + Action(도구 사용)을 결합한 방식.

작동 흐름:

1. Reason  
2. Action(검색, API, 계산 등)  
3. Observation  
4. Answer

RAG·에이전트 기반 시스템의 핵심.

---

# ♻️ 16. Automatic Prompt Engineering (APE)

LLM이 스스로 프롬프트를 생성·평가·선택하는 방식입니다.

과정:

1. 프롬프트 후보 생성  
2. 모델/평가기로 테스트  
3. 최고 성능 프롬프트 선택  

---

# 🧑‍💻 17. Code Prompting

LLM을 이용한 코드 관련 작업:

- 코드 생성  
- 코드 설명  
- 코드 번역  
- 코드 디버깅/리뷰  

각 작업은 형식, 언어, 제약 조건을 명확히 지정해야 품질이 높아집니다.

---

# 🖼️ 18. Multimodal Prompting

텍스트 + 이미지 + 오디오 등  
여러 형태의 입력을 결합한 prompting.

적용 예:

- UI 스크린샷 → 코드 생성  
- 그래프/표 해석  
- 이미지 요약  
- OCR 기반 분석  

---

# ⭐ 19. Best Practices (모범 사례)

### ✔ 예시 제공  
### ✔ 간결한 설계  
### ✔ 출력 구조 명확히  
### ✔ 제약보다 지시 사용  
### ✔ 최대 토큰 길이 지정  
### ✔ 변수 기반 프롬프트  
### ✔ 입력 형식 다양화  
### ✔ 클래스 분포 다양화  
### ✔ 모델 업데이트 대응  

---

# 🔧 20. JSON Repair

Google 모델은 JSON 출력 시  
경미한 오류가 있어도 자동으로 복구할 수 있습니다.

---

# 📐 21. Working with Schemas

스키마를 프롬프트에 포함하면:

- 구조화 출력 안정
- 파싱 오류 감소
- hallucination 감소

예:

```json
{
  "title": "string",
  "summary": "string",
  "score": "number"
}
```

---

# 📚 22. 참고 논문 (Reference Papers)

이 문서에서 소개된 프롬프트 엔지니어링 기법들은 다음의 주요 연구 논문들을 기반으로 합니다.

## 🔗 Chain-of-Thought (CoT) Prompting

**논문:** "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"
**저자:** Jason Wei, Xuezhi Wang, Dale Schuurmans, Maarten Bosma, Brian Ichter, Fei Xia, Ed Chi, Quoc Le, Denny Zhou (Google Research)
**출판:** NeurIPS 2022 / arXiv:2201.11903
**발표일:** 2022년 1월

### 핵심 내용
- 중간 추론 과정(intermediate reasoning steps)을 명시적으로 생성하도록 유도
- Few-shot 예시에 추론 단계를 포함시키는 간단한 방법으로 복잡한 추론 능력 향상
- 산술, 상식 추론, 기호 추론 등 다양한 작업에서 성능 개선 입증
- 충분히 큰 언어 모델에서 자연스럽게 추론 능력이 발현됨을 증명

**📄 논문 링크:** [arXiv:2201.11903](https://arxiv.org/abs/2201.11903)

---

## 🧩 Self-Consistency

**논문:** "Self-Consistency Improves Chain of Thought Reasoning in Language Models"
**저자:** Xuezhi Wang, Jason Wei, Dale Schuurmans, Quoc Le, Ed H. Chi, Sharan Narang, Aakanksha Chowdhery, Denny Zhou (Google Research, Brain Team)
**출판:** ICLR 2023 / arXiv:2203.11171
**발표일:** 2022년 3월 (최종 업데이트 2023년 3월)

### 핵심 내용
- CoT의 greedy decoding을 대체하는 새로운 디코딩 전략
- 다양한 추론 경로를 샘플링한 후 가장 일관된(consistent) 답변 선택
- Majority voting을 통한 최종 답변 결정

### 성능 향상
- GSM8K: +17.9%
- SVAMP: +11.0%
- AQuA: +12.2%
- StrategyQA: +6.4%
- ARC-challenge: +3.9%

**📄 논문 링크:** [arXiv:2203.11171](https://arxiv.org/abs/2203.11171)

---

## 🌲 Tree of Thoughts (ToT)

**논문:** "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"
**저자:** Shunyu Yao, Dian Yu, Jeffrey Zhao, Izhak Shafran, Tom Griffiths, Yuan Cao, Karthik Narasimhan (Princeton University, Google DeepMind)
**출판:** NeurIPS 2023 / arXiv:2305.10601
**발표일:** 2023년 5월

### 핵심 내용
- CoT를 일반화하여 여러 추론 경로를 트리 구조로 탐색
- 중간 단계마다 자기 평가(self-evaluation)를 통해 다음 행동 결정
- Look-ahead와 backtracking을 통한 전역적 선택 가능
- 체계적인 문제 해결을 위한 의도적 탐색(deliberate exploration)

### 실험 결과
- Game of 24 작업에서 GPT-4 + CoT는 4% 성공률
- GPT-4 + ToT는 74% 성공률 달성 (18.5배 향상)

**📄 논문 링크:** [arXiv:2305.10601](https://arxiv.org/abs/2305.10601)
**💻 코드:** [GitHub - Tree of Thoughts](https://github.com/princeton-nlp/tree-of-thought-llm)

---

## 🤖 ReAct (Reason + Act)

**논문:** "ReAct: Synergizing Reasoning and Acting in Language Models"
**저자:** Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, Yuan Cao (Princeton University, Google Research)
**출판:** ICLR 2023 / arXiv:2210.03629
**발표일:** 2022년 10월

### 핵심 내용
- Reasoning trace와 task-specific action을 교차(interleave) 생성
- 추론이 행동 계획을 유도하고, 행동이 외부 정보원과 상호작용
- Wikipedia API 등 외부 지식 베이스 활용으로 hallucination 감소
- 환각(hallucination)과 오류 전파 문제 해결

### 실험 결과
- **Question Answering (HotpotQA)**: CoT 대비 hallucination 대폭 감소
- **Fact Verification (Fever)**: 외부 지식 활용으로 정확도 향상
- **ALFWorld (Interactive Decision Making)**: 절대 성공률 +34%
- **WebShop**: 절대 성공률 +10%
- 단 1-2개의 in-context 예시만으로 모방 학습·강화 학습 방법 능가

**📄 논문 링크:** [arXiv:2210.03629](https://arxiv.org/abs/2210.03629)
**💻 코드:** [GitHub - ReAct](https://github.com/ysymyth/ReAct)
**🌐 프로젝트:** [ReAct Official Website](https://react-lm.github.io/)

---

## ♻️ Automatic Prompt Engineering (APE)

**논문:** "Large Language Models Are Human-Level Prompt Engineers"
**저자:** Yongchao Zhou, Andrei Ioan Muresanu, Ziwen Han, Keiran Paster, Silviu Pitis, Harris Chan, Jimmy Ba (University of Toronto, Vector Institute, University of Waterloo)
**출판:** ICLR 2023 / arXiv:2211.01910
**발표일:** 2022년 11월 (최종 업데이트 2023년 3월)

### 핵심 내용
- 프롬프트를 "프로그램"으로 취급하여 자동 생성 및 최적화
- LLM이 후보 instruction을 제안하고, 점수 함수로 최적 선택
- Human-in-the-loop 없이 고품질 프롬프트 자동 생성

### 실험 결과
- 24개 NLP 작업 중 19개에서 사람이 작성한 instruction과 동등하거나 더 우수한 성능
- **획기적 발견**: "Let's think step by step" 보다 더 나은 CoT 프롬프트 자동 발견
  - MultiArith: 78.7% → 82.0%
  - GSM8K: 40.7% → 43.0%

**📄 논문 링크:** [arXiv:2211.01910](https://arxiv.org/abs/2211.01910)
**💻 코드:** [GitHub - Automatic Prompt Engineer](https://github.com/keirp/automatic_prompt_engineer)
**🌐 프로젝트:** [APE Project Page](https://sites.google.com/view/automatic-prompt-engineer)

---

## 📖 추가 권장 자료

### 공식 가이드 및 문서
- [Prompt Engineering Guide](https://www.promptingguide.ai/) - 다양한 프롬프팅 기법의 종합 가이드
- [Google Research Blog - Chain of Thought](https://research.google/blog/language-models-perform-reasoning-via-chain-of-thought/)
- [Google Research Blog - ReAct](https://research.google/blog/react-synergizing-reasoning-and-acting-in-language-models/)

### 연구 리소스
- [Chain-of-Thought Papers Collection](https://github.com/Timothyxxx/Chain-of-ThoughtsPapers) - CoT 관련 논문 모음
- [Hugging Face Papers](https://huggingface.co/papers) - 최신 논문 큐레이션

---

## 📊 기법별 적용 시나리오 요약

| 기법 | 최적 사용 시나리오 | 성능 향상 폭 | 비용/복잡도 |
|------|------------------|-------------|-----------|
| **CoT** | 수학, 논리 추론, 복잡한 문제 | 중간~높음 | 낮음 |
| **Self-Consistency** | 정확도가 중요한 추론 작업 | 높음 (+10~18%) | 중간 (다중 샘플링) |
| **ToT** | 전략 게임, 최적화 문제 | 매우 높음 (18배) | 높음 (트리 탐색) |
| **ReAct** | 정보 검색, 사실 확인, 에이전트 | 높음 (+34%) | 중간 (외부 도구 필요) |
| **APE** | 프롬프트 최적화 자동화 | 중간~높음 | 높음 (초기 설정) |

---

## 🎓 인용 (Citations)

이 문서의 논문들을 인용하실 경우 아래 형식을 사용하시기 바랍니다:

```bibtex
@article{wei2022chain,
  title={Chain-of-thought prompting elicits reasoning in large language models},
  author={Wei, Jason and Wang, Xuezhi and Schuurmans, Dale and Bosma, Maarten and Ichter, Brian and Xia, Fei and Chi, Ed and Le, Quoc and Zhou, Denny},
  journal={Advances in Neural Information Processing Systems},
  volume={35},
  pages={24824--24837},
  year={2022}
}

@article{wang2023self,
  title={Self-consistency improves chain of thought reasoning in language models},
  author={Wang, Xuezhi and Wei, Jason and Schuurmans, Dale and Le, Quoc and Chi, Ed and Narang, Sharan and Chowdhery, Aakanksha and Zhou, Denny},
  journal={International Conference on Learning Representations (ICLR)},
  year={2023}
}

@article{yao2023tree,
  title={Tree of thoughts: Deliberate problem solving with large language models},
  author={Yao, Shunyu and Yu, Dian and Zhao, Jeffrey and Shafran, Izhak and Griffiths, Tom and Cao, Yuan and Narasimhan, Karthik},
  journal={Advances in Neural Information Processing Systems},
  volume={36},
  year={2023}
}

@article{yao2022react,
  title={React: Synergizing reasoning and acting in language models},
  author={Yao, Shunyu and Zhao, Jeffrey and Yu, Dian and Du, Nan and Shafran, Izhak and Narasimhan, Karthik and Cao, Yuan},
  journal={International Conference on Learning Representations (ICLR)},
  year={2023}
}

@article{zhou2022large,
  title={Large language models are human-level prompt engineers},
  author={Zhou, Yongchao and Muresanu, Andrei Ioan and Han, Ziwen and Paster, Keiran and Pitis, Silviu and Chan, Harris and Ba, Jimmy},
  journal={International Conference on Learning Representations (ICLR)},
  year={2023}
}
```



