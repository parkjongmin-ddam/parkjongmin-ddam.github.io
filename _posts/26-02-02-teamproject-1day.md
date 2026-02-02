---
layout: single
title: "Generative AI 10기 팀 프로젝트 - 1일차"
categories: python
tag: [python, finance, project-planning, environment-setup]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# 📈 주식 정보 대시보드 팀 프로젝트

## 프로젝트 개요

**주제**: 주식 정보 대시보드 개발  
**기간**: 2025.01.01 ~ 2025.12.31 (데이터 분석 기간)  
**팀원**: Generative AI 10기  
**기술 스택**: Python, Plotly, Streamlit, FinanceDataReader, Pandas

---

## 1일차: 프로젝트 기획 및 환경 설정

### 📋 프로젝트 목표 설정

팀원별로 분석할 종목을 선정하고, 주식 데이터를 시각화하는 대시보드를 개발하는 것을 목표로 함.

**선정 종목**:

*   SK하이닉스 (000660)
*   삼성전자 (005930)
*   카카오 (035720)
*   마음AI (377480)
*   솔트록스 (304100)
*   한글과컴퓨터 (030520)

### 🛠️ 개발 환경 구축

**필요 라이브러리 설치**:

```bash
pip install finance-datareader
pip install plotly
pip install streamlit
pip install pandas
```

**requirements.txt 작성**:

```text
finance-datareader
plotly
streamlit
pandas
```

### 📊 데이터 수집 계획

*   **데이터 소스**: `FinanceDataReader` 라이브러리 활용
*   **분석 기간**: 2025년 1월 1일 ~ 2025년 12월 31일
*   **수집 데이터**: 시가(Open), 고가(High), 저가(Low), 종가(Close), 거래량(Volume)

### 💡 주요 학습 내용

1.  **FinanceDataReader 사용법**
    *   한국/미국 주식 데이터를 쉽게 수집할 수 있는 라이브러리임.
    *   별도의 API 키 없이 종목 코드로 즉시 호출 가능함.

2.  **프로젝트 구조 설계**
    *   `데이터 수집` → `데이터 전처리(MA 계산 등)` → `Plotly 시각화` → `Streamlit 배포` 순으로 진행함.

---

### 📝 오늘의 회고
*   가상환경을 구축하여 팀원 간의 개발 환경을 통일함.
*   종목별 특성에 따른 분석 포인트(반도체, AI 섹터 등)를 사전 논의함.
*   FinanceDataReader의 `StockListing` 기능을 통해 종목 코드를 정확히 확보함.

**다음 포스트**: [2일차 - 데이터 수집 및 전처리](./26-02-03-teamproject-2day.md)
