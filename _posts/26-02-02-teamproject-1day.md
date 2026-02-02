---
layout: post
title: "팀 프로젝트 1일차 - 주식 대시보드 기획 및 환경 설정"
date: 2026-02-02
categories: [Project, Team, Day1]
tags: [python, plotly, streamlit, finance, dashboard, stock-analysis]
---

# 📈 주식 정보 대시보드 팀 프로젝트 - 1일차

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
- SK하이닉스 (000660)
- 삼성전자 (005930)
- 카카오 (035720)
- 마음AI (377480)
- 솔트록스 (304100)
- 한글과컴퓨터 (030520)

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
```

### 📊 데이터 수집 계획

- **데이터 소스**: FinanceDataReader 라이브러리 활용
- **분석 기간**: 2025년 1월 1일 ~ 2025년 12월 31일
- **수집 데이터**: 시가, 고가, 저가, 종가, 거래량

### 💡 주요 학습 내용

1. **FinanceDataReader 사용법**
   - 한국 주식 데이터를 쉽게 가져올 수 있는 라이브러리
   - 종목 코드를 통해 데이터 수집 가능

2. **프로젝트 구조 설계**
   - 데이터 수집 → 전처리 → 시각화 → 대시보드 구현 순서로 진행

---

**프로젝트 기간**: 5일  
**팀**: Generative AI 10기  
**작성일**: 2026-02-02
