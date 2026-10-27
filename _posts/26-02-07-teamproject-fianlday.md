---
layout: single
title: "Generative AI 10기 팀 프로젝트 - 5일차: Streamlit 웹 대시보드 구현 및 배포"
categories: ["Project", "주식 대시보드(팀)"]
permalink: "/python/teamproject-fianlday/"
tag: [python, streamlit, dashboard, deployment, streamlit-cloud, web-app]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# 📊 5일차: Streamlit 웹 대시보드 구현 및 배포

## 학습 목표

5일차에는 Plotly로 만든 정적 HTML 대시보드를 Streamlit을 활용한 인터랙티브 웹 애플리케이션으로 전환하고, Streamlit Cloud에 배포하는 전 과정을 학습함.

### 📊 완성된 대시보드 미리보기

![Streamlit Dashboard Mockup](/assets/images/26-02-07/streamlit_dashboard_mockup_1770453107257.png)

---

## 🌐 Streamlit 앱 구조

### 페이지 설정

Streamlit 앱의 기본 설정을 구성함. 페이지 제목, 아이콘, 레이아웃 등을 설정할 수 있음.

```python
import streamlit as st

st.set_page_config(
    page_title="Team Project Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)
```

**주요 설정 항목:**
- `page_title`: 브라우저 탭에 표시될 제목
- `page_icon`: 파비콘 (이모티콘 또는 이미지 URL)
- `layout`: "centered" 또는 "wide" 선택
- `initial_sidebar_state`: "expanded" 또는 "collapsed"

---

## 🎨 커스텀 CSS 스타일

Streamlit의 기본 스타일을 커스터마이징하여 더 세련된 UI를 구현함.

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

**스타일링 포인트:**
- `.stApp`: 전체 앱 배경색
- `.main-header`: 메인 헤더 스타일
- `.metric-card`: 메트릭 카드 스타일

---

## 📊 데이터 캐싱

Streamlit의 `@st.cache_data` 데코레이터를 사용하여 데이터 로딩 성능을 최적화함.

```python
import FinanceDataReader as fdr

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

**캐싱의 장점:**
- 동일한 데이터 요청 시 재계산하지 않음
- 앱 성능 대폭 향상
- 사용자 경험 개선

### 캐싱 개념 시각화

![Streamlit Caching Concept](/assets/images/26-02-07/streamlit_caching_concept_1770453157867.png)

---

## 🎯 메트릭 표시

주요 지표를 시각적으로 표시하여 한눈에 정보를 파악할 수 있게 함.

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

**메트릭 카드 특징:**
- 주요 값과 변화량을 함께 표시
- 증가/감소에 따라 자동으로 색상 변경
- 깔끔한 레이아웃

---

## 🔄 사이드바 종목 선택

사이드바에 라디오 버튼을 배치하여 종목을 선택할 수 있게 함.

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

ticker = COMPANIES[selected_company]
```

**사이드바 활용:**
- 입력 위젯을 깔끔하게 정리
- 메인 화면은 데이터 표시에 집중
- 사용자 경험 향상

---

## 📈 Plotly 차트 통합

Streamlit에서 Plotly 차트를 표시하는 방법:

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 데이터 로드
df = load_data(ticker, "2025-01-01", "2025-12-31")

if df is not None:
    # 거래량 색상 구분
    colors = ['#ff5252' if row['Close'] >= row['Open'] else '#448aff' 
              for _, row in df.iterrows()]
    
    # 서브플롯 생성
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f'{selected_company} 주가', '거래량'),
        row_heights=[0.7, 0.3]
    )
    
    # 캔들스틱 차트
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name='Price',
        increasing_line_color='#ff5252',
        decreasing_line_color='#448aff'
    ), row=1, col=1)
    
    # 이동평균선
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA5'],
        line=dict(color='#ffeb3b', width=1.5),
        name='MA 5'
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA20'],
        line=dict(color='#00e676', width=1.5),
        name='MA 20'
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA60'],
        line=dict(color='#e040fb', width=1.5),
        name='MA 60'
    ), row=1, col=1)
    
    # 거래량 차트
    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'],
        marker_color=colors,
        name='Volume',
        opacity=0.8
    ), row=2, col=1)
    
    # 레이아웃 설정
    fig.update_layout(
        template='plotly_dark',
        plot_bgcolor='rgba(17, 17, 17, 1)',
        paper_bgcolor='rgba(10, 10, 10, 1)',
        height=800,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    
    # Streamlit에 차트 표시
    st.plotly_chart(fig, use_container_width=True)
```

---

## 🚀 앱 실행

로컬에서 Streamlit 앱을 실행하는 방법:

```bash
streamlit run app.py
```

브라우저가 자동으로 열리고 `http://localhost:8501`에서 앱을 확인할 수 있음.

---

## 🌐 Streamlit Cloud 웹 배포

### 배포 개요

Streamlit Cloud를 활용하면 무료로 웹 애플리케이션을 배포할 수 있음. GitHub 저장소와 연동하여 자동으로 배포되며, 코드 변경 시 자동으로 업데이트됨.

### 배포 워크플로우

![Streamlit Deployment Workflow](/assets/images/26-02-07/streamlit_deployment_workflow_1770453086938.png)

### 배포 단계 타임라인

![Deployment Steps Timeline](/assets/images/26-02-07/deployment_steps_timeline_1770453132372.png)

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

**버전 고정 이유:**
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
   - **Main file path**: `app.py`
3. **Advanced settings** (선택사항):
   - **Python version**: 3.9 또는 3.10 선택
   - **Secrets**: API 키 등 민감 정보 입력 (필요시)
4. **Deploy!** 클릭

#### 3-3. 배포 완료

- 배포 과정은 약 2-5분 소요
- 배포 완료 후 고유 URL 생성: `https://your-app-name.streamlit.app`
- 로그를 통해 배포 상태 확인 가능

---

## 🔧 배포 후 관리

### 자동 업데이트

```bash
# 코드 수정 후
git add .
git commit -m "Update: Add new features"
git push

# Streamlit Cloud가 자동으로 감지하여 재배포
```

### 수동 재시작

1. Streamlit Cloud 대시보드 접속
2. 앱 선택
3. **Reboot app** 클릭

### 로그 확인

- **Manage app** → **Logs** 탭에서 실시간 로그 확인
- 에러 발생 시 디버깅에 활용

---

## 🔐 환경 변수 및 Secrets 관리

API 키나 민감한 정보가 필요한 경우:

### Streamlit Cloud에서 Secrets 설정

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

### 코드에서 Secrets 사용

```python
import streamlit as st

# Secrets 접근
api_key = st.secrets["api_keys"]["finance_api"]
db_host = st.secrets["database"]["host"]
```

---

## ⚠️ 배포 시 주의사항

### 메모리 제한

- Streamlit Cloud 무료 플랜: **1GB RAM**
- 대용량 데이터 처리 시 메모리 최적화 필요

**해결 방법:**
```python
# 데이터 캐싱 활용
@st.cache_data(ttl=3600)  # 1시간 캐시
def load_data(ticker, start, end):
    df = fdr.DataReader(ticker, start, end)
    return df

# 불필요한 데이터 제거
df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
```

### 실행 시간 제한

- 앱 로딩 시간: **최대 90초**
- 긴 작업은 백그라운드 처리 또는 캐싱 활용

### 데이터 수집 제한

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

---

## 💡 배포 최적화 팁

### 1. 로딩 속도 개선

```python
# 세션 스테이트 활용
if 'data' not in st.session_state:
    st.session_state.data = load_data(ticker, start, end)

df = st.session_state.data
```

### 2. 프로그레스 바 추가

```python
with st.spinner('데이터를 불러오는 중...'):
    df = load_data(ticker, start, end)
    
progress_bar = st.progress(0)
for i in range(100):
    # 처리 작업
    progress_bar.progress(i + 1)
```

### 3. 에러 핸들링 강화

```python
import time

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

---

## ✅ 배포 체크리스트

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

---

## 🔍 문제 해결 (Troubleshooting)

### 주요 배포 문제 및 해결 방법

![Deployment Troubleshooting Guide](/assets/images/26-02-07/deployment_troubleshooting_guide_1770453181552.png)

### 문제 1: 배포 실패 - ModuleNotFoundError

**원인**: `requirements.txt`에 패키지 누락

**해결**:
```bash
# 로컬에서 사용 중인 패키지 확인
pip freeze > requirements.txt

# 또는 필요한 패키지만 명시
echo "streamlit" >> requirements.txt
echo "finance-datareader" >> requirements.txt
```

### 문제 2: 메모리 초과 에러

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

### 문제 3: 앱 로딩 시간 초과

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

## 🎉 배포 완료 및 공유

배포가 완료되면 다음과 같은 URL로 접속 가능함:

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

## 💭 배운 점 및 느낀 점

### 기술적 성장

1. **Streamlit 웹 개발**
   - Python만으로 완전한 웹 앱 구축
   - 인터랙티브 UI 구현
   - 사용자 경험 설계

2. **배포 프로세스**
   - GitHub 연동 자동 배포
   - 환경 변수 및 Secrets 관리
   - 성능 최적화 기법

3. **문제 해결 능력**
   - 메모리 제한 극복
   - 에러 핸들링 강화
   - 로딩 속도 최적화

### 프로젝트 인사이트

- **빠른 프로토타이핑**: Streamlit으로 아이디어를 빠르게 구현
- **배포의 중요성**: 실제 사용자가 접근할 수 있는 서비스 제공
- **최적화의 필요성**: 제한된 리소스 내에서 효율적인 코드 작성

---

## 📚 참고 자료

- [Streamlit 공식 문서](https://docs.streamlit.io/)
- [Streamlit Cloud 배포 가이드](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app)
- [FinanceDataReader 문서](https://github.com/FinanceData/FinanceDataReader)
- [Plotly Python 문서](https://plotly.com/python/)

---

## ✨ 마무리

5일차에는 Streamlit을 활용한 웹 대시보드 구현과 Streamlit Cloud 배포를 완료함. 로컬에서만 실행되던 대시보드를 인터넷에 공개하여 누구나 접근할 수 있는 서비스로 발전시킴. 배포 과정에서 발생하는 다양한 문제를 해결하며 실전 경험을 쌓을 수 있었음. 🚀
