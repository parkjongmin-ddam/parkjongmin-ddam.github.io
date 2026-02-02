---
layout: post
title: "팀 프로젝트 1일차 - 주식 대시보드 기획 및 환경 설정"
date: 2026-02-02
categories: [Project, Team, Day1]
tags: [python, stock-analysis, finance, project-planning, environment-setup]
---

# 📈 주식 정보 대시보드 팀 프로젝트 - 1일차

**날짜**: 2026년 2월 2일  
**목표**: 프로젝트 계획 수립 및 개발 환경 구축  
**소요 시간**: 약 4시간

---

## 📋 프로젝트 개요

### 프로젝트 목표

팀원별로 분석할 종목을 선정하고, 주식 데이터를 시각화하는 **인터랙티브 대시보드**를 개발하는 것을 목표로 함.

### 기본 정보

| 항목 | 내용 |
|------|------|
| **프로젝트명** | 주식 정보 대시보드 |
| **팀** | Generative AI 10기 |
| **데이터 분석 기간** | 2025.01.01 ~ 2025.12.31 |
| **기술 스택** | Python, Plotly, Streamlit, FinanceDataReader, Pandas |
| **개발 기간** | 5일 |

![프로젝트 개요](../assets/img/project/project_overview.png)

---

## 🎯 선정 종목

팀원별로 관심 있는 종목을 선정하여 분석하기로 결정함.

### 종목 리스트

| 종목명 | 종목 코드 | 섹터 | 선정 이유 |
|--------|-----------|------|-----------|
| **SK하이닉스** | 000660 | 반도체 | AI 반도체 수요 증가, 메모리 시장 선도 |
| **삼성전자** | 005930 | 전자/반도체 | 국내 대표 기업, 안정적 성장 |
| **카카오** | 035720 | IT/플랫폼 | 디지털 플랫폼 생태계 확장 |
| **마음AI** | 377480 | AI/소프트웨어 | 생성형 AI 기술 기업 |
| **솔트록스** | 304100 | AI/빅데이터 | AI 솔루션 전문 기업 |
| **한글과컴퓨터** | 030520 | 소프트웨어 | 국산 소프트웨어 대표 기업 |

### 종목 선정 기준

1. **성장성**: AI 및 기술 섹터 중심
2. **다양성**: 반도체, IT, 소프트웨어 등 다양한 분야
3. **관심도**: 팀원들의 관심사 반영
4. **데이터 접근성**: FinanceDataReader에서 쉽게 데이터 수집 가능

---

## 🛠️ 개발 환경 구축

### 1. Python 가상환경 생성

프로젝트별로 독립적인 환경을 구축하기 위해 가상환경을 생성함.

```bash
# 프로젝트 디렉토리 생성
mkdir team_project
cd team_project

# 가상환경 생성
python -m venv .venv

# 가상환경 활성화 (Windows)
.venv\Scripts\activate
```

**가상환경 사용 이유**:
- 프로젝트별 패키지 버전 관리
- 시스템 Python 환경과 분리
- 협업 시 동일한 환경 구축 가능

### 2. 필수 라이브러리 설치

```bash
# 필수 라이브러리 설치
pip install finance-datareader
pip install plotly
pip install streamlit
pip install pandas
```

### 3. requirements.txt 작성

협업 및 배포를 위해 사용한 패키지 목록을 기록함.

```text
finance-datareader==0.9.50
plotly==5.18.0
streamlit==1.31.0
pandas==2.1.4
```

**requirements.txt 생성 명령어**:
```bash
# 현재 설치된 패키지 목록 저장
pip freeze > requirements.txt
```

### 4. 프로젝트 폴더 구조

```
team_project/
├── .venv/                      # 가상환경 (Git 제외)
├── data/                       # 데이터 저장 폴더
│   └── raw/                    # 원본 데이터
├── src/                        # 소스 코드
│   ├── data_collection.py     # 데이터 수집 스크립트
│   ├── preprocessing.py       # 데이터 전처리
│   └── visualization.py       # 시각화 함수
├── Front-end/                  # Streamlit 앱
│   └── app.py                 # 메인 앱
├── requirements.txt           # 패키지 목록
├── .gitignore                 # Git 제외 파일
└── README.md                  # 프로젝트 설명
```

![폴더 구조](../assets/img/project/folder_structure.png)

---

## 📊 데이터 수집 계획

### 데이터 소스

**FinanceDataReader** 라이브러리를 활용하여 한국 주식 데이터를 수집함.

#### FinanceDataReader란?

- 한국, 미국 등 다양한 금융 데이터를 제공하는 Python 라이브러리
- 무료로 사용 가능
- 간단한 API로 데이터 수집 가능

#### 기본 사용법

```python
import FinanceDataReader as fdr

# 종목 데이터 수집
df = fdr.DataReader('000660', '2025-01-01', '2025-12-31')

# 데이터 확인
print(df.head())
```

### 수집 데이터 항목

| 컬럼명 | 설명 | 활용 방안 |
|--------|------|-----------|
| **Open** | 시가 | 장 시작 가격, 캔들스틱 차트 |
| **High** | 고가 | 당일 최고 가격, 변동성 분석 |
| **Low** | 저가 | 당일 최저 가격, 변동성 분석 |
| **Close** | 종가 | 장 마감 가격, 추세 분석 |
| **Volume** | 거래량 | 거래 활발도, 매매 신호 |
| **Change** | 변화율 | 전일 대비 변동률 |

### 데이터 분석 기간

- **시작일**: 2025년 1월 1일
- **종료일**: 2025년 12월 31일
- **기간**: 1년 (약 250 거래일)

**기간 선정 이유**:
- 충분한 데이터 양 확보
- 단기/중기/장기 추세 분석 가능
- 이동평균선 계산에 적합

---

## 💡 주요 학습 내용

### 1. FinanceDataReader 사용법

#### 설치 및 임포트

```python
# 설치
pip install finance-datareader

# 임포트
import FinanceDataReader as fdr
```

#### 주요 기능

**1) 종목 데이터 수집**
```python
# 특정 기간의 주식 데이터
df = fdr.DataReader('000660', '2025-01-01', '2025-12-31')
```

**2) 종목 리스트 조회**
```python
# 한국 거래소 상장 종목 리스트
krx = fdr.StockListing('KRX')
print(krx.head())
```

**3) 지수 데이터 수집**
```python
# KOSPI 지수
kospi = fdr.DataReader('KS11', '2025-01-01', '2025-12-31')
```

### 2. 프로젝트 구조 설계

프로젝트를 효율적으로 진행하기 위한 단계별 계획을 수립함.

#### 개발 프로세스

```
1. 데이터 수집 (Day 2)
   ↓
2. 데이터 전처리 (Day 2)
   ↓
3. 데이터 시각화 (Day 3)
   ↓
4. 대시보드 스타일링 (Day 4)
   ↓
5. 웹 대시보드 구현 (Day 5)
```

![개발 프로세스](../assets/img/project/development_process.png)

#### 각 단계별 목표

| 단계 | 목표 | 산출물 |
|------|------|--------|
| **데이터 수집** | 6개 종목의 2025년 데이터 수집 | CSV 파일 |
| **데이터 전처리** | 이동평균선, 거래량 색상 계산 | 전처리된 DataFrame |
| **데이터 시각화** | Plotly로 캔들스틱 차트 구현 | HTML 차트 |
| **스타일링** | 다크 모드, 인터랙티브 요소 추가 | 완성된 HTML |
| **웹 대시보드** | Streamlit으로 웹 앱 구현 | 배포 가능한 앱 |

---

## 📝 오늘의 체크리스트

- [x] 프로젝트 목표 설정
- [x] 분석 종목 선정 (6개)
- [x] Python 가상환경 생성
- [x] 필수 라이브러리 설치
- [x] requirements.txt 작성
- [x] 프로젝트 폴더 구조 설계
- [x] .gitignore 설정
- [x] 데이터 수집 계획 수립
- [x] FinanceDataReader 사용법 학습
- [x] Git 저장소 초기화

---

## 🎓 배운 점

### 기술적 학습

1. **가상환경의 중요성**
   - 프로젝트별 독립적인 패키지 관리
   - 버전 충돌 방지
   - 배포 시 일관성 보장

2. **FinanceDataReader의 강점**
   - 간단한 API로 금융 데이터 수집
   - 별도의 API 키 불필요
   - 한국 주식 데이터에 최적화

3. **프로젝트 구조화**
   - 체계적인 폴더 구조로 유지보수 용이
   - 역할별 파일 분리로 협업 효율 향상

### 협업 인사이트

1. **명확한 목표 설정**
   - 팀원 간 공통 목표 공유
   - 각자의 역할 분담

2. **기술 스택 선정**
   - 학습 곡선과 생산성 고려
   - 무료 도구 우선 활용

---

## 🚀 다음 단계 (2일차 예고)

### 계획

1. **데이터 수집 구현**
   - 6개 종목의 2025년 데이터 수집
   - CSV 파일로 저장

2. **데이터 전처리**
   - 이동평균선(MA 5, 20, 60) 계산
   - 거래량 색상 구분 로직 구현

3. **데이터 탐색**
   - 기본 통계 분석
   - 결측치 확인 및 처리

---

## 💬 회고

### 잘한 점

- ✅ 명확한 프로젝트 목표 설정
- ✅ 체계적인 환경 구축
- ✅ 팀원 간 원활한 소통

### 개선할 점

- 🔄 더 구체적인 일정 계획 필요
- 🔄 각 종목별 분석 방향 세분화
- 🔄 중간 점검 시간 마련

### 느낀 점

프로젝트의 시작이 중요하다는 것을 다시 한번 느낌. 명확한 목표와 체계적인 환경 설정이 향후 개발 속도와 품질에 큰 영향을 미칠 것으로 예상됨.

---

## 📚 참고 자료

- [FinanceDataReader GitHub](https://github.com/FinanceData/FinanceDataReader)
- [Pandas 공식 문서](https://pandas.pydata.org/docs/)
- [Python 가상환경 가이드](https://docs.python.org/ko/3/tutorial/venv.html)

---

**작성일**: 2026-02-02  
**다음 포스트**: [2일차 - 데이터 수집 및 전처리](./26-02-03-teamproject-2day.md)
