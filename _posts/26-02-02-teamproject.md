---
layout: post
title: "Generative AI 10기 팀 프로젝트 - 주식 정보 대시보드"
date: 2026-02-02
categories: [Project, Team]
tags: [python, plotly, streamlit, finance, dashboard, stock-analysis]
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

## 2일차: 데이터 수집 및 전처리

### 📥 데이터 수집 구현

**기본 데이터 수집 코드**:
```python
import FinanceDataReader as fdr
import pandas as pd

# SK 하이닉스 데이터 수집
ticker = "000660"
start_date = "2025-01-01"
end_date = "2025-12-31"

df = fdr.DataReader(ticker, start_date, end_date)
print(f"데이터 수집 완료: {len(df)}건")
```

### 🔧 데이터 전처리

**이동평균선(Moving Average) 계산**:
```python
# 이동평균선 계산
df['MA5'] = df['Close'].rolling(window=5).mean()   # 5일 이동평균
df['MA20'] = df['Close'].rolling(window=20).mean() # 20일 이동평균
df['MA60'] = df['Close'].rolling(window=60).mean() # 60일 이동평균
```

**이동평균선의 의미**:
- **MA 5 (5일)**: 단기 추세 파악, 심리선
- **MA 20 (20일)**: 약 1개월 평균, 세력선/생명선
- **MA 60 (60일)**: 약 3개월 평균, 수급선

### 🎨 거래량 색상 구분

```python
# 거래량 색상 구분 (상승: 빨강, 하락: 파랑)
colors = []
for i, row in df.iterrows():
    if row['Close'] >= row['Open']:
        colors.append('#ff5252')  # Red (상승)
    else:
        colors.append('#448aff')  # Blue (하락)
```

### 💡 주요 학습 내용

1. **Pandas 데이터 처리**
   - `rolling()` 함수를 활용한 이동평균 계산
   - DataFrame 순회 및 조건부 처리

2. **주식 데이터 분석 기초**
   - 캔들스틱의 의미 (시가, 고가, 저가, 종가)
   - 이동평균선을 통한 추세 분석

---

## 3일차: Plotly를 활용한 시각화

### 📊 캔들스틱 차트 구현

**기본 캔들스틱 차트**:
```python
import plotly.graph_objects as go

fig = go.Figure(data=[go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    name='Price',
    increasing_line_color='#ff5252',  # 양봉 (상승)
    decreasing_line_color='#448aff'   # 음봉 (하락)
)])

fig.show()
```

### 📈 이동평균선 추가

```python
# 이동평균선 추가
fig.add_trace(go.Scatter(
    x=df.index, 
    y=df['MA5'], 
    line=dict(color='#ffeb3b', width=1.5), 
    name='MA 5'
))

fig.add_trace(go.Scatter(
    x=df.index, 
    y=df['MA20'], 
    line=dict(color='#00e676', width=1.5), 
    name='MA 20'
))

fig.add_trace(go.Scatter(
    x=df.index, 
    y=df['MA60'], 
    line=dict(color='#e040fb', width=1.5), 
    name='MA 60'
))
```

### 📊 서브플롯 구성 (가격 + 거래량)

```python
from plotly.subplots import make_subplots

# 2행 1열 서브플롯 생성
fig = make_subplots(
    rows=2, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.03,
    subplot_titles=('SK Hynix Stock Price', 'Volume'),
    row_heights=[0.7, 0.3]
)

# 캔들스틱 차트 (상단)
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'], high=df['High'],
    low=df['Low'], close=df['Close'],
    name='Price',
    increasing_line_color='#ff5252',
    decreasing_line_color='#448aff'
), row=1, col=1)

# 거래량 차트 (하단)
fig.add_trace(go.Bar(
    x=df.index, 
    y=df['Volume'],
    marker_color=colors,
    name='Volume',
    opacity=0.8
), row=2, col=1)
```

### 💡 주요 학습 내용

1. **Plotly 기본 사용법**
   - `go.Candlestick()`: 캔들스틱 차트 생성
   - `go.Scatter()`: 선 그래프 (이동평균선)
   - `go.Bar()`: 막대 그래프 (거래량)

2. **서브플롯 활용**
   - `make_subplots()`: 여러 차트를 하나의 화면에 배치
   - `shared_xaxes`: X축 공유로 연동된 차트 구현

---

## 4일차: 대시보드 스타일링 및 완성

### 🎨 다크 모드 테마 적용

```python
fig.update_layout(
    title=dict(
        text='<b>SK Hynix Final Dashboard (2025)</b>',
        x=0.5, y=0.95,
        font=dict(size=24, color='white')
    ),
    template='plotly_dark',
    plot_bgcolor='rgba(17, 17, 17, 1)',
    paper_bgcolor='rgba(10, 10, 10, 1)',
    height=900,
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="right", x=1,
        font=dict(color='white')
    ),
    xaxis_rangeslider_visible=False,
    hovermode='x unified'
)
```

### 🎯 축 스타일링

```python
# 공통 축 스타일
common_axis_style = dict(
    gridcolor='rgba(128, 128, 128, 0.2)',
    showspikes=True,
    spikethickness=1,
    spikedash='dot',
    spikecolor='#999999'
)

fig.update_xaxes(**common_axis_style)
fig.update_yaxes(**common_axis_style, tickformat=',')
```

### 💾 HTML 파일로 저장

```python
import os

output_file = "hynix_dashboard_final.html"
fig.write_html(output_file)
print(f"최종 대시보드가 '{output_file}'로 저장되었습니다.")

# 윈도우 환경에서 자동으로 브라우저 열기
if os.name == 'nt':
    os.startfile(output_file)
```

### 💡 주요 학습 내용

1. **Plotly 레이아웃 커스터마이징**
   - 다크 모드 테마 적용
   - 그리드, 스파이크 라인 등 세부 스타일링
   - 범례 위치 및 스타일 조정

2. **파일 저장 및 실행**
   - `write_html()`: 인터랙티브 HTML 파일 생성
   - OS별 파일 실행 방법

---

## 5일차: Streamlit 웹 대시보드 구현

### 🌐 Streamlit 앱 구조

**페이지 설정**:
```python
import streamlit as st

st.set_page_config(
    page_title="Team Project Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)
```

### 🎨 커스텀 CSS 스타일

```python
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    .main-header {
        font-size: 2.5rem;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #1f2937;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #374151;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)
```

### 📊 데이터 캐싱

```python
@st.cache_data
def load_data(ticker, start, end):
    try:
        df = fdr.DataReader(ticker, start, end)
        if df.empty:
            return None
        
        # 이동평균선 계산
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        return df
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return None
```

### 🎯 메트릭 표시

```python
# 최근 데이터 기준 정보 표시
last_row = df.iloc[-1]
prev_row = df.iloc[-2] if len(df) > 1 else last_row

change = last_row['Close'] - prev_row['Close']
pct_change = (change / prev_row['Close']) * 100

# 4개의 컬럼으로 메트릭 표시
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("종가 (Close)", f"{last_row['Close']:,} KRW", 
              f"{change:+,} ({pct_change:+.2f}%)")
with col2:
    st.metric("시가 (Open)", f"{last_row['Open']:,} KRW")
with col3:
    st.metric("고가 (High)", f"{last_row['High']:,} KRW")
with col4:
    st.metric("거래량 (Volume)", f"{last_row['Volume']:,}")
```

### 🔄 사이드바 종목 선택

```python
COMPANIES = {
    "SK하이닉스": "000660",
    "삼성전자": "005930",
    "카카오": "035720",
    "마음AI": "377480",
    "솔트록스": "304100",
    "한글과컴퓨터": "030520"
}

st.sidebar.title("📈 주가 대시보드")
st.sidebar.markdown("팀 프로젝트 종목 분석")

selected_company = st.sidebar.radio(
    "분석할 종목을 선택하세요:",
    list(COMPANIES.keys()),
    index=0
)
```

### 🚀 앱 실행

```bash
streamlit run app.py
```

### 💡 주요 학습 내용

1. **Streamlit 기본 구조**
   - `st.set_page_config()`: 페이지 설정
   - `st.sidebar`: 사이드바 구성
   - `st.columns()`: 레이아웃 분할

2. **성능 최적화**
   - `@st.cache_data`: 데이터 캐싱으로 성능 향상
   - 불필요한 재계산 방지

3. **인터랙티브 요소**
   - `st.radio()`: 라디오 버튼으로 종목 선택
   - `st.metric()`: 주요 지표 표시
   - `st.expander()`: 접을 수 있는 데이터 테이블

---

## 프로젝트 결과물

### 📁 프로젝트 구조

```
team_project/
├── hynix_final_dashboard.py    # Plotly HTML 대시보드 생성
├── hynix_dashboard_final.html  # 생성된 HTML 파일
├── Front-end/
│   └── app.py                  # Streamlit 웹 대시보드
├── requirements.txt            # 필요 라이브러리 목록
└── .venv/                      # 가상환경
```

### 🎯 주요 기능

1. **캔들스틱 차트**
   - 주가의 시가, 고가, 저가, 종가를 시각적으로 표현
   - 양봉(빨강), 음봉(파랑)으로 상승/하락 구분

2. **이동평균선**
   - MA 5, MA 20, MA 60을 통한 추세 분석
   - 단기/중기/장기 흐름 파악

3. **거래량 차트**
   - 거래량을 막대 그래프로 표시
   - 주가 상승/하락에 따른 색상 구분

4. **인터랙티브 대시보드**
   - Streamlit을 통한 웹 기반 대시보드
   - 종목 선택 및 실시간 차트 업데이트
   - 주요 지표 메트릭 표시

### 📊 시각화 특징

- **다크 모드 테마**: 눈의 피로를 줄이는 어두운 배경
- **반응형 레이아웃**: 화면 크기에 맞춰 자동 조정
- **호버 인터랙션**: 마우스를 올리면 상세 정보 표시
- **통합 X축**: 가격과 거래량 차트가 연동되어 움직임

---

## 배운 점 및 느낀 점

### 📚 기술적 학습

1. **데이터 수집 및 처리**
   - FinanceDataReader를 활용한 금융 데이터 수집
   - Pandas를 통한 데이터 전처리 및 분석

2. **데이터 시각화**
   - Plotly를 활용한 인터랙티브 차트 구현
   - 캔들스틱, 이동평균선, 거래량 차트 구성

3. **웹 대시보드 개발**
   - Streamlit을 활용한 빠른 웹 앱 개발
   - 사용자 인터랙션 구현 (종목 선택, 메트릭 표시)

### 💡 인사이트

1. **주식 데이터 분석의 중요성**
   - 이동평균선을 통한 추세 파악
   - 거래량과 주가의 상관관계 이해

2. **시각화의 힘**
   - 복잡한 데이터를 직관적으로 표현
   - 인터랙티브 요소로 사용자 경험 향상

3. **협업의 가치**
   - 팀원별 종목 분석을 통한 다양한 관점
   - 코드 공유 및 피드백을 통한 성장

---

## 향후 개선 방향

### 🚀 추가 기능 아이디어

1. **기술적 지표 추가**
   - RSI (Relative Strength Index)
   - MACD (Moving Average Convergence Divergence)
   - 볼린저 밴드 (Bollinger Bands)

2. **비교 분석 기능**
   - 여러 종목 동시 비교
   - 섹터별 성과 분석

3. **알림 기능**
   - 특정 가격 도달 시 알림
   - 이동평균선 골든크로스/데드크로스 알림

4. **데이터 확장**
   - 실시간 데이터 연동
   - 해외 주식 데이터 추가
   - 뉴스 및 공시 정보 통합

### 🔧 기술적 개선

1. **성능 최적화**
   - 데이터 캐싱 전략 개선
   - 차트 렌더링 최적화

2. **UI/UX 개선**
   - 반응형 디자인 강화
   - 모바일 최적화

3. **배포**
   - Streamlit Cloud 배포
   - Docker 컨테이너화

---

## 참고 자료

- [FinanceDataReader 공식 문서](https://github.com/FinanceData/FinanceDataReader)
- [Plotly Python 문서](https://plotly.com/python/)
- [Streamlit 공식 문서](https://docs.streamlit.io/)
- [Pandas 공식 문서](https://pandas.pydata.org/docs/)

---

## 프로젝트 실행 방법

### 1. 환경 설정

```bash
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화 (Windows)
.venv\Scripts\activate

# 필요 라이브러리 설치
pip install -r requirements.txt
```

### 2. Plotly HTML 대시보드 실행

```bash
python hynix_final_dashboard.py
```

### 3. Streamlit 웹 대시보드 실행 (로컬)

```bash
cd Front-end
streamlit run app.py
```

---

## 🌐 Streamlit Cloud 웹 배포

### 배포 개요

Streamlit Cloud를 활용하면 무료로 웹 애플리케이션을 배포할 수 있습니다. GitHub 저장소와 연동하여 자동으로 배포되며, 코드 변경 시 자동으로 업데이트됩니다.

### 1단계: GitHub 저장소 준비

#### 1-1. 저장소 생성

```bash
# Git 초기화
git init

# .gitignore 파일 생성
echo ".venv/" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo ".env" >> .gitignore
echo "*.html" >> .gitignore

# GitHub에 저장소 생성 후
git remote add origin https://github.com/your-username/stock-dashboard.git
```

#### 1-2. 필수 파일 구조

```
stock-dashboard/
├── app.py                    # Streamlit 앱 메인 파일
├── requirements.txt          # 의존성 패키지 목록
├── .streamlit/
│   └── config.toml          # Streamlit 설정 파일 (선택)
├── README.md                # 프로젝트 설명
└── .gitignore               # Git 제외 파일 목록
```

#### 1-3. requirements.txt 작성

```text
streamlit==1.31.0
finance-datareader==0.9.50
plotly==5.18.0
pandas==2.1.4
```

**버전 고정 이유**:
- 배포 환경에서 일관된 동작 보장
- 라이브러리 업데이트로 인한 호환성 문제 방지

#### 1-4. .streamlit/config.toml 생성 (선택사항)

```toml
[theme]
primaryColor = "#ff5252"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#1f2937"
textColor = "#ffffff"
font = "sans serif"

[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = true
```

### 2단계: 코드 커밋 및 푸시

```bash
# 모든 파일 추가
git add .

# 커밋
git commit -m "Initial commit: Stock dashboard app"

# GitHub에 푸시
git push -u origin main
```

### 3단계: Streamlit Cloud 배포

#### 3-1. Streamlit Cloud 가입

1. [Streamlit Cloud](https://streamlit.io/cloud) 접속
2. **Sign up** 클릭
3. GitHub 계정으로 로그인
4. Streamlit Cloud 권한 승인

#### 3-2. 새 앱 배포

1. **New app** 버튼 클릭
2. 배포 정보 입력:
   - **Repository**: `your-username/stock-dashboard`
   - **Branch**: `main`
   - **Main file path**: `app.py` (또는 `Front-end/app.py`)
3. **Advanced settings** (선택사항):
   - **Python version**: 3.9 또는 3.10 선택
   - **Secrets**: API 키 등 민감 정보 입력 (필요시)
4. **Deploy!** 클릭

#### 3-3. 배포 완료

- 배포 과정은 약 2-5분 소요
- 배포 완료 후 고유 URL 생성: `https://your-app-name.streamlit.app`
- 로그를 통해 배포 상태 확인 가능

### 4단계: 배포 후 관리

#### 자동 업데이트

```bash
# 코드 수정 후
git add .
git commit -m "Update: Add new features"
git push

# Streamlit Cloud가 자동으로 감지하여 재배포
```

#### 수동 재시작

1. Streamlit Cloud 대시보드 접속
2. 앱 선택
3. **Reboot app** 클릭

#### 로그 확인

- **Manage app** → **Logs** 탭에서 실시간 로그 확인
- 에러 발생 시 디버깅에 활용

### 5단계: 환경 변수 및 Secrets 관리

API 키나 민감한 정보가 필요한 경우:

#### 5-1. Streamlit Cloud에서 Secrets 설정

1. **Manage app** → **Settings** → **Secrets**
2. TOML 형식으로 입력:

```toml
# .streamlit/secrets.toml 형식
[api_keys]
finance_api = "your-api-key-here"

[database]
host = "your-db-host"
password = "your-db-password"
```

#### 5-2. 코드에서 Secrets 사용

```python
import streamlit as st

# Secrets 접근
api_key = st.secrets["api_keys"]["finance_api"]
db_host = st.secrets["database"]["host"]
```

### 배포 시 주의사항

#### ⚠️ 메모리 제한

- Streamlit Cloud 무료 플랜: **1GB RAM**
- 대용량 데이터 처리 시 메모리 최적화 필요

**해결 방법**:
```python
# 데이터 캐싱 활용
@st.cache_data(ttl=3600)  # 1시간 캐시
def load_data(ticker, start, end):
    df = fdr.DataReader(ticker, start, end)
    return df

# 불필요한 데이터 제거
df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
```

#### ⚠️ 실행 시간 제한

- 앱 로딩 시간: **최대 90초**
- 긴 작업은 백그라운드 처리 또는 캐싱 활용

#### ⚠️ 데이터 수집 제한

```python
# 데이터 수집 실패 시 대비
try:
    df = fdr.DataReader(ticker, start, end)
    if df.empty:
        st.warning("데이터가 없습니다. 기간을 조정해주세요.")
        st.stop()
except Exception as e:
    st.error(f"데이터 수집 실패: {e}")
    st.info("잠시 후 다시 시도해주세요.")
    st.stop()
```

### 배포 최적화 팁

#### 1. 로딩 속도 개선

```python
# 세션 스테이트 활용
if 'data' not in st.session_state:
    st.session_state.data = load_data(ticker, start, end)

df = st.session_state.data
```

#### 2. 프로그레스 바 추가

```python
with st.spinner('데이터를 불러오는 중...'):
    df = load_data(ticker, start, end)
    
progress_bar = st.progress(0)
for i in range(100):
    # 처리 작업
    progress_bar.progress(i + 1)
```

#### 3. 에러 핸들링 강화

```python
def safe_load_data(ticker, start, end, max_retries=3):
    for attempt in range(max_retries):
        try:
            df = fdr.DataReader(ticker, start, end)
            return df
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"데이터 로드 실패: {e}")
                return None
            time.sleep(1)  # 재시도 전 대기
```

### 배포 체크리스트

- [ ] `requirements.txt` 파일 작성 및 버전 명시
- [ ] `.gitignore`에 민감 정보 및 불필요한 파일 추가
- [ ] GitHub 저장소에 코드 푸시
- [ ] Streamlit Cloud 계정 생성 및 GitHub 연동
- [ ] 앱 배포 및 URL 확인
- [ ] 배포된 앱 테스트 (모든 기능 동작 확인)
- [ ] README.md 작성 (프로젝트 설명, 사용법)
- [ ] 에러 로그 확인 및 디버깅
- [ ] 성능 최적화 (캐싱, 메모리 관리)
- [ ] 모바일 반응형 테스트

### 대안 배포 방법

#### 1. Heroku 배포

```bash
# Procfile 생성
echo "web: streamlit run app.py --server.port=$PORT" > Procfile

# runtime.txt 생성
echo "python-3.10.12" > runtime.txt

# Heroku CLI로 배포
heroku create your-app-name
git push heroku main
```

#### 2. Docker 컨테이너화

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
# Docker 빌드 및 실행
docker build -t stock-dashboard .
docker run -p 8501:8501 stock-dashboard
```

#### 3. AWS EC2 배포

```bash
# EC2 인스턴스 접속 후
sudo apt update
sudo apt install python3-pip
pip3 install -r requirements.txt

# 백그라운드 실행
nohup streamlit run app.py --server.port=8501 &
```

### 배포 후 모니터링

#### 1. 사용자 통계 확인

Streamlit Cloud 대시보드에서 확인 가능:
- 일일 방문자 수
- 앱 실행 시간
- 에러 발생 빈도

#### 2. Google Analytics 연동 (선택)

```python
# app.py에 추가
import streamlit.components.v1 as components

# Google Analytics 스크립트
ga_script = """
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
"""

components.html(ga_script, height=0)
```

### 문제 해결 (Troubleshooting)

#### 문제 1: 배포 실패 - ModuleNotFoundError

**원인**: `requirements.txt`에 패키지 누락

**해결**:
```bash
# 로컬에서 사용 중인 패키지 확인
pip freeze > requirements.txt

# 또는 필요한 패키지만 명시
echo "streamlit" >> requirements.txt
echo "finance-datareader" >> requirements.txt
```

#### 문제 2: 메모리 초과 에러

**원인**: 1GB RAM 제한 초과

**해결**:
```python
# 데이터 다운샘플링
df = df.iloc[::2]  # 2개 중 1개만 사용

# 불필요한 컬럼 제거
df = df[['Close', 'Volume']]

# 데이터 타입 최적화
df['Volume'] = df['Volume'].astype('int32')
```

#### 문제 3: 앱 로딩 시간 초과

**원인**: 초기 데이터 로딩이 90초 초과

**해결**:
```python
# 데이터 기간 축소
START_DATE = "2025-06-01"  # 6개월로 축소

# 또는 샘플 데이터 먼저 표시
with st.spinner('데이터 로딩 중...'):
    df = load_data_async(ticker, start, end)
```

---

## 🎉 배포 완료 예시

배포가 완료되면 다음과 같은 URL로 접속 가능합니다:

**배포 URL**: `https://stock-dashboard-team10.streamlit.app`

### 공유 방법

1. **직접 링크 공유**
   - URL을 복사하여 팀원, 포트폴리오에 공유

2. **QR 코드 생성**
   ```python
   import qrcode
   
   qr = qrcode.make("https://your-app.streamlit.app")
   qr.save("app_qr.png")
   ```

3. **README.md에 배지 추가**
   ```markdown
   [![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app.streamlit.app)
   ```

---

**프로젝트 기간**: 5일  
**팀**: Generative AI 10기  
**작성일**: 2026-02-02  
**배포 URL**: [Stock Dashboard](https://streamlit.io/cloud) (배포 후 업데이트)
