---
layout: single
title: "Streamlit 주요 기능 완벽 정리 - 데이터 애플리케이션 개발 가이드"
categories: ["Dev", "Streamlit"]
permalink: "/python/streamlit개념/"
tag: [python, streamlit, plotly, dashboard, data-visualization, web-app, interactive]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# Streamlit 주요 기능 완벽 정리

## 📌 소개

Streamlit은 Python으로 데이터 분석 및 머신러닝 웹 애플리케이션을 빠르게 구축할 수 있는 오픈소스 프레임워크임. 이 글에서는 실제 프로젝트에서 사용한 Streamlit의 주요 기능들을 정리함.

---

## 🚀 Streamlit 설치 및 실행

### 설치 방법

```bash
# pip를 이용한 설치
pip install streamlit

# 특정 버전 설치
pip install streamlit==1.30.0

# 필요한 라이브러리와 함께 설치
pip install streamlit pandas plotly
```

### Streamlit 앱 실행 방법

Streamlit은 일반적인 Python 스크립트와 달리 `python` 명령어가 아닌 **`streamlit run`** 명령어로 실행함.

```bash
# 기본 실행 방법
streamlit run app.py

# 특정 포트로 실행
streamlit run app.py --server.port 8080

# 브라우저 자동 실행 비활성화
streamlit run app.py --server.headless true
```

**❌ 잘못된 실행 방법:**
```bash
python app.py  # 이렇게 실행하면 안 됨!
```

**✅ 올바른 실행 방법:**
```bash
streamlit run app.py  # 이렇게 실행해야 함!
```

### 간단한 예제로 실행해보기

**hello.py 파일 생성:**
```python
import streamlit as st

st.title('Hello Streamlit! 🎉')
st.write('첫 번째 Streamlit 앱입니다.')

name = st.text_input('이름을 입력하세요')
if name:
    st.write(f'안녕하세요, {name}님!')
```

**실행:**
```bash
streamlit run hello.py
```

실행하면 자동으로 브라우저가 열리고 `http://localhost:8501`에서 앱을 확인할 수 있음.

### 주요 실행 옵션

```bash
# 포트 변경
streamlit run app.py --server.port 8080

# 외부 접속 허용
streamlit run app.py --server.address 0.0.0.0

# 파일 변경 감지 비활성화
streamlit run app.py --server.fileWatcherType none

# 테마 설정
streamlit run app.py --theme.base dark
```

### 개발 시 유용한 팁

**1. 자동 새로고침:**
- 코드를 수정하고 저장하면 Streamlit이 자동으로 변경사항을 감지함
- 브라우저 우측 상단에 "Rerun" 버튼이 나타남
- "Always rerun" 옵션을 선택하면 자동으로 재실행됨

**2. 캐시 초기화:**
```bash
# 캐시 삭제
streamlit cache clear
```

**3. 설정 파일:**
프로젝트 폴더에 `.streamlit/config.toml` 파일을 만들어 기본 설정 가능함
```toml
[server]
port = 8501
headless = false

[theme]
primaryColor = "#F63366"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

### 디버깅 방법

Streamlit에서는 `print()` 대신 다음 방법들을 사용함:

```python
import streamlit as st

# 1. st.write() - 가장 범용적
st.write('디버깅 메시지:', variable)

# 2. st.text() - 단순 텍스트
st.text(f'값: {variable}')

# 3. st.code() - 코드 형식으로 표시
st.code(f'variable = {variable}')

# 4. st.json() - JSON 형식으로 표시
st.json({'key': 'value', 'number': 123})

# 5. st.dataframe() - 데이터프레임 표시
st.dataframe(df)

# 6. st.expander() - 접을 수 있는 디버그 정보
with st.expander('디버그 정보'):
    st.write('변수 값:', variable)
    st.write('데이터프레임:', df)
```

**터미널에서 확인하고 싶을 때:**
```python
import streamlit as st

# 터미널에 출력 (개발 중 디버깅용)
print('터미널에 출력됨')  # streamlit run 실행한 터미널에 표시됨

# 브라우저에 출력 (사용자에게 보여줄 때)
st.write('브라우저에 출력됨')  # 웹 페이지에 표시됨
```

### 프로젝트 구조 예시

```
my-streamlit-app/
│
├── app.py                 # 메인 앱 파일
├── requirements.txt       # 필요한 패키지 목록
├── .streamlit/
│   └── config.toml       # Streamlit 설정
├── data/                 # 데이터 파일
│   └── sample.csv
├── utils/                # 유틸리티 함수
│   └── helpers.py
└── README.md
```

**requirements.txt 예시:**
```
streamlit==1.30.0
pandas==2.0.0
plotly==5.18.0
numpy==1.24.0
```

**설치:**
```bash
pip install -r requirements.txt
```

---

## 1️⃣ 텍스트 및 마크다운 표시 기능

### 1.1 제목 및 헤더

Streamlit은 다양한 레벨의 제목을 지원함.

```python
import streamlit as st

# 타이틀 (가장 큰 제목)
st.title('이것은 타이틀 입니다')

# 이모티콘 삽입 가능
st.title('스마일 :sunglasses:')

# 헤더
st.header('헤더를 입력할 수 있어요! :sparkles:')

# 서브헤더
st.subheader('이것은 subheader 입니다')

# 캡션 (작은 텍스트)
st.caption('캡션을 한 번 넣어 봤습니다')
```

**특징:**
- 이모티콘 shortcode를 사용하여 다양한 이모티콘 삽입 가능함
- 이모티콘 참고: https://streamlit-emoji-shortcodes-streamlit-app-gwckff.streamlit.app/

### 1.2 코드 표시

```python
# 코드 블록 표시
sample_code = '''
def function():
    print('hello, world')
'''
st.code(sample_code, language="python")
```

코드를 syntax highlighting과 함께 깔끔하게 표시할 수 있음.

### 1.3 일반 텍스트 및 마크다운

```python
# 일반 텍스트
st.text('일반적인 텍스트를 입력해 보았습니다.')

# 마크다운 문법 지원
st.markdown('streamlit은 **마크다운 문법을 지원**합니다.')

# 컬러 텍스트 (blue, green, orange, red, violet)
st.markdown("텍스트의 색상을 :green[초록색]으로, 그리고 **:blue[파란색]** 볼트체로 설정할 수 있습니다.")

# LaTeX 수식 표현
st.markdown(":green[$\\sqrt{x^2+y^2}=1$] 와 같이 latex 문법의 수식 표현도 가능합니다 :pencil:")
```

### 1.4 LaTeX 수식

```python
# LaTeX 수식 전용 표시
st.latex(r'\sqrt{x^2+y^2}=1')
```

수학 공식을 아름답게 표현할 수 있음.

---

## 2️⃣ 데이터 표시 기능

### 2.1 DataFrame 표시

```python
import pandas as pd

# DataFrame 생성
dataframe = pd.DataFrame({
    'first column': [1, 2, 3, 4],
    'second column': [10, 20, 30, 40],
})

# Interactive DataFrame (정렬, 필터링 가능)
st.dataframe(dataframe, use_container_width=False)
```

**특징:**
- `use_container_width`: 데이터프레임을 컨테이너 크기에 맞춰 확장할지 여부 설정함 (True/False)
- 사용자가 직접 정렬하고 탐색할 수 있는 인터랙티브 UI 제공함

### 2.2 정적 테이블

```python
# 정적 테이블 (인터랙션 없음)
st.table(dataframe)
```

DataFrame과 달리 인터랙티브 UI를 제공하지 않는 정적 테이블임.

### 2.3 메트릭 표시

```python
# 단일 메트릭
st.metric(label="온도", value="10°C", delta="1.2°C")
st.metric(label="삼성전자", value="61,000 원", delta="-1,200 원")

# 컬럼으로 나누어 표시
col1, col2, col3 = st.columns(3)
col1.metric(label="달러USD", value="1,228 원", delta="-12.00 원")
col2.metric(label="일본JPY(100엔)", value="958.63 원", delta="-7.44 원")
col3.metric(label="유럽연합EUR", value="1,335.82 원", delta="11.44 원")
```

**특징:**
- `delta` 값이 양수면 녹색 화살표, 음수면 빨간색 화살표로 표시됨
- 대시보드의 KPI 표시에 매우 유용함

---

## 3️⃣ 사용자 입력 위젯

### 3.1 버튼

```python
# 일반 버튼
button = st.button('버튼을 눌러보세요')

if button:
    st.write(':blue[버튼]이 눌렸습니다 :sparkles:')
```

### 3.2 다운로드 버튼

```python
# 파일 다운로드 버튼
dataframe = pd.DataFrame({
    'first column': [1, 2, 3, 4],
    'second column': [10, 20, 30, 40],
})

st.download_button(
    label='CSV로 다운로드',
    data=dataframe.to_csv(), 
    file_name='sample.csv', 
    mime='text/csv'
)
```

사용자가 데이터를 CSV 파일로 다운로드할 수 있게 함.

### 3.3 체크박스

```python
# 체크박스
agree = st.checkbox('동의 하십니까?')

if agree:
    st.write('동의 해주셔서 감사합니다 :100:')
```

### 3.4 라디오 버튼

```python
# 라디오 선택 버튼 (단일 선택)
mbti = st.radio(
    '당신의 MBTI는 무엇입니까?',
    ('ISTJ', 'ENFP', '선택지 없음'))

if mbti == 'ISTJ':
    st.write('당신은 :blue[현실주의자] 이시네요')
elif mbti == 'ENFP':
    st.write('당신은 :green[활동가] 이시네요')
else:
    st.write("당신에 대해 :red[알고 싶어요]:grey_exclamation:")
```

### 3.5 선택박스 (Selectbox)

```python
# 드롭다운 선택박스
mbti = st.selectbox(
    '당신의 MBTI는 무엇입니까?',
    ('ISTJ', 'ENFP', '선택지 없음'), 
    index=2  # 기본 선택 인덱스
)
```

**특징:**
- `index` 파라미터로 기본 선택값 지정 가능함

### 3.6 다중 선택박스 (Multiselect)

```python
# 다중 선택박스
options = st.multiselect(
    '당신이 좋아하는 과일은 뭔가요?',
    ['망고', '오렌지', '사과', '바나나'],
    ['망고', '오렌지']  # 기본 선택값
)

st.write(f'당신의 선택은: :red[{options}] 입니다.')
```

여러 개의 옵션을 동시에 선택할 수 있음.

### 3.7 슬라이더

```python
from datetime import datetime as dt
import datetime

# 범위 슬라이더
values = st.slider(
    '범위의 값을 다음과 같이 지정할 수 있어요:sparkles:',
    0.0, 100.0, (25.0, 75.0))
st.write('선택 범위:', values)

# 날짜/시간 슬라이더
start_time = st.slider(
    "언제 약속을 잡는 것이 좋을까요?",
    min_value=dt(2020, 1, 1, 0, 0), 
    max_value=dt(2020, 1, 7, 23, 0),
    value=dt(2020, 1, 3, 12, 0),
    step=datetime.timedelta(hours=1),
    format="MM/DD/YY - HH:mm")
st.write("선택한 약속 시간:", start_time)
```

**특징:**
- 숫자 범위뿐만 아니라 날짜/시간 선택도 가능함
- `step` 파라미터로 증감 단위 조절 가능함

### 3.8 텍스트 입력

```python
# 텍스트 입력
title = st.text_input(
    label='가고 싶은 여행지가 있나요?', 
    placeholder='여행지를 입력해 주세요'
)
st.write(f'당신이 선택한 여행지: :violet[{title}]')

# 텍스트 영역 (여러 줄)
question = st.text_area(
    '질문', 
    placeholder='질문을 입력해 주세요'
)
```

### 3.9 숫자 입력

```python
# 숫자 입력
number = st.number_input(
    label='나이를 입력해 주세요.', 
    min_value=10, 
    max_value=100, 
    value=30,  # 기본값
    step=5     # 증감 단위
)
st.write('당신이 입력하신 나이는: ', number)
```

### 3.10 날짜 입력

```python
import datetime

# 날짜 선택
date = st.date_input(
    "조회 시작일을 선택해 주세요",
    datetime.datetime(2022, 1, 1)
)
```

---

## 4️⃣ 파일 업로드 기능

```python
import time

# 파일 업로드
file = st.file_uploader("파일 선택(csv or excel)", type=['csv', 'xls', 'xlsx'])

# 파일 확장자에 따라 다르게 처리
if file is not None:
    ext = file.name.split('.')[-1]
    if ext == 'csv':
        df = pd.read_csv(file)
        st.dataframe(df)
    elif 'xls' in ext:
        df = pd.read_excel(file, engine='openpyxl')
        st.dataframe(df)
```

**특징:**
- `type` 파라미터로 허용할 파일 형식 지정 가능함
- 업로드된 파일은 즉시 처리 가능함

---

## 5️⃣ 차트 및 시각화

### 5.1 Matplotlib/Seaborn 차트

```python
import matplotlib.pyplot as plt
import seaborn as sns

# 한글 폰트 설정
plt.rcParams['font.family'] = "AppleGothic"  # Mac
# plt.rcParams['font.family'] = "NanumGothic"  # Windows, Linux
plt.rcParams['axes.unicode_minus'] = False

# DataFrame 생성
data = pd.DataFrame({
    '이름': ['영식', '철수', '영희'],
    '나이': [22, 31, 25],
    '몸무게': [75.5, 80.2, 55.1]
})

# Matplotlib 차트
fig, ax = plt.subplots()
ax.bar(data['이름'], data['나이'])
st.pyplot(fig)

# Seaborn 차트
barplot = sns.barplot(x='이름', y='나이', data=data, ax=ax, palette='Set2')
fig = barplot.get_figure()
st.pyplot(fig)
```

### 5.2 Streamlit 내장 차트

```python
import FinanceDataReader as fdr

# 주식 데이터 가져오기
df = fdr.DataReader('005930', '2022-01-01')  # 삼성전자
data = df.sort_index(ascending=True).loc[:, 'Close']

# 라인 차트
st.line_chart(data)
```

**특징:**
- `st.line_chart()`, `st.bar_chart()`, `st.area_chart()` 등 간단한 차트 제공함
- 별도의 figure 생성 없이 바로 데이터를 시각화할 수 있음

### 5.3 Plotly 인터랙티브 차트

Plotly는 강력한 인터랙티브 차트 라이브러리로, Streamlit과 완벽하게 통합됨. 사용자가 차트를 확대/축소하고, 데이터 포인트를 탐색할 수 있는 동적 시각화를 제공함.

#### 5.3.1 기본 Plotly 차트

```python
import plotly.express as px
import plotly.graph_objects as go

# 샘플 데이터
df = pd.DataFrame({
    '과일': ['사과', '바나나', '오렌지', '포도', '딸기'],
    '판매량': [100, 150, 80, 120, 90]
})

# Plotly Express로 간단한 막대 차트
fig = px.bar(df, x='과일', y='판매량', 
             title='과일별 판매량',
             color='판매량',
             color_continuous_scale='Blues')

# Streamlit에 표시
st.plotly_chart(fig, use_container_width=True)
```

**특징:**
- `st.plotly_chart()` 함수로 Plotly 차트를 표시함
- `use_container_width=True`로 컨테이너 너비에 맞춰 차트 크기 조절 가능함
- 자동으로 줌, 팬, 호버 등의 인터랙티브 기능 제공함

#### 5.3.2 주식 캔들스틱 차트

```python
import plotly.graph_objects as go
import FinanceDataReader as fdr

# 주식 데이터 가져오기
df = fdr.DataReader('005930', '2025-01-01', '2025-12-31')  # 삼성전자

# 캔들스틱 차트 생성
fig = go.Figure(data=[go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    name='주가'
)])

# 레이아웃 설정
fig.update_layout(
    title='삼성전자 주가 차트',
    yaxis_title='주가 (원)',
    xaxis_title='날짜',
    template='plotly_dark',  # 다크 테마
    height=600
)

st.plotly_chart(fig, use_container_width=True)
```

**특징:**
- 캔들스틱 차트로 주식의 시가, 고가, 저가, 종가를 한눈에 볼 수 있음
- `template` 파라미터로 다양한 테마 적용 가능함 (plotly, plotly_white, plotly_dark 등)

#### 5.3.3 이동평균선 추가

```python
# 이동평균 계산
df['MA5'] = df['Close'].rolling(window=5).mean()
df['MA20'] = df['Close'].rolling(window=20).mean()
df['MA60'] = df['Close'].rolling(window=60).mean()

# 캔들스틱 차트 생성
fig = go.Figure()

# 캔들스틱 추가
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    name='주가'
))

# 이동평균선 추가
fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], 
                         mode='lines', name='MA5',
                         line=dict(color='orange', width=1)))
fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], 
                         mode='lines', name='MA20',
                         line=dict(color='blue', width=1)))
fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], 
                         mode='lines', name='MA60',
                         line=dict(color='purple', width=1)))

# 레이아웃 설정
fig.update_layout(
    title='주가 차트 with 이동평균선',
    yaxis_title='주가 (원)',
    xaxis_title='날짜',
    template='plotly_white',
    height=600,
    xaxis_rangeslider_visible=False  # 하단 범위 슬라이더 숨김
)

st.plotly_chart(fig, use_container_width=True)
```

#### 5.3.4 서브플롯 (가격 + 거래량)

```python
from plotly.subplots import make_subplots

# 서브플롯 생성 (2행 1열)
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.7, 0.3],
    subplot_titles=('주가', '거래량')
)

# 첫 번째 서브플롯: 캔들스틱
fig.add_trace(
    go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='주가'
    ),
    row=1, col=1
)

# 이동평균선 추가
fig.add_trace(
    go.Scatter(x=df.index, y=df['MA20'], 
               mode='lines', name='MA20',
               line=dict(color='blue', width=1)),
    row=1, col=1
)

# 두 번째 서브플롯: 거래량
fig.add_trace(
    go.Bar(x=df.index, y=df['Volume'], name='거래량',
           marker_color='lightblue'),
    row=2, col=1
)

# 레이아웃 설정
fig.update_layout(
    title='주가 및 거래량 차트',
    height=800,
    template='plotly_white',
    showlegend=True,
    xaxis_rangeslider_visible=False
)

fig.update_xaxes(title_text="날짜", row=2, col=1)
fig.update_yaxes(title_text="주가 (원)", row=1, col=1)
fig.update_yaxes(title_text="거래량", row=2, col=1)

st.plotly_chart(fig, use_container_width=True)
```

**특징:**
- `make_subplots()`로 여러 차트를 하나의 figure에 배치할 수 있음
- `shared_xaxes=True`로 x축을 공유하여 동기화된 줌/팬 가능함
- `row_heights`로 각 서브플롯의 높이 비율 조절 가능함

#### 5.3.5 인터랙티브 드롭다운 메뉴

```python
# 여러 종목 데이터 준비
stocks = {
    '삼성전자': '005930',
    'SK하이닉스': '000660',
    'NAVER': '035420'
}

# 첫 번째 종목으로 초기 차트 생성
first_stock = list(stocks.keys())[0]
df = fdr.DataReader(stocks[first_stock], '2025-01-01', '2025-12-31')

# 모든 종목에 대한 trace 생성
fig = go.Figure()

for stock_name, stock_code in stocks.items():
    df_temp = fdr.DataReader(stock_code, '2025-01-01', '2025-12-31')
    
    fig.add_trace(go.Scatter(
        x=df_temp.index,
        y=df_temp['Close'],
        name=stock_name,
        visible=(stock_name == first_stock)  # 첫 번째만 보이게
    ))

# 드롭다운 버튼 생성
buttons = []
for i, stock_name in enumerate(stocks.keys()):
    # 각 버튼마다 어떤 trace를 보일지 설정
    visible = [False] * len(stocks)
    visible[i] = True
    
    buttons.append(
        dict(
            label=stock_name,
            method="update",
            args=[{"visible": visible},
                  {"title": f"{stock_name} 주가 차트"}]
        )
    )

# 레이아웃에 드롭다운 추가
fig.update_layout(
    updatemenus=[
        dict(
            active=0,
            buttons=buttons,
            direction="down",
            pad={"r": 10, "t": 10},
            showactive=True,
            x=0.1,
            xanchor="left",
            y=1.15,
            yanchor="top"
        )
    ],
    title=f"{first_stock} 주가 차트",
    xaxis_title="날짜",
    yaxis_title="주가 (원)",
    template='plotly_white',
    height=600
)

st.plotly_chart(fig, use_container_width=True)
```

**특징:**
- `updatemenus`로 드롭다운, 버튼 등의 인터랙티브 컨트롤 추가 가능함
- `method="update"`로 차트 데이터와 레이아웃을 동적으로 변경할 수 있음
- 사용자가 직접 차트를 조작하여 다양한 데이터를 탐색할 수 있음

#### 5.3.6 Plotly Express로 빠른 시각화

```python
import plotly.express as px

# 라인 차트
fig = px.line(df, x=df.index, y='Close', 
              title='종가 추이',
              labels={'Close': '종가 (원)', 'index': '날짜'})
st.plotly_chart(fig, use_container_width=True)

# 영역 차트
fig = px.area(df, x=df.index, y='Volume',
              title='거래량 추이',
              labels={'Volume': '거래량', 'index': '날짜'})
st.plotly_chart(fig, use_container_width=True)

# 산점도
fig = px.scatter(df, x='Volume', y='Close',
                 title='거래량 vs 종가',
                 labels={'Volume': '거래량', 'Close': '종가 (원)'},
                 trendline="ols")  # 추세선 추가
st.plotly_chart(fig, use_container_width=True)

# 히스토그램
fig = px.histogram(df, x='Close', nbins=50,
                   title='종가 분포',
                   labels={'Close': '종가 (원)'})
st.plotly_chart(fig, use_container_width=True)
```

**Plotly Express vs Graph Objects:**
- **Plotly Express (px)**: 간단하고 빠른 차트 생성, 한 줄로 복잡한 차트 생성 가능함
- **Graph Objects (go)**: 세밀한 커스터마이징 가능, 복잡한 차트 구성에 적합함

#### 5.3.7 Streamlit과 Plotly 연동 팁

```python
# 1. Streamlit 위젯으로 Plotly 차트 제어
chart_type = st.selectbox(
    '차트 유형 선택',
    ['라인 차트', '영역 차트', '막대 차트']
)

if chart_type == '라인 차트':
    fig = px.line(df, x=df.index, y='Close')
elif chart_type == '영역 차트':
    fig = px.area(df, x=df.index, y='Close')
else:
    fig = px.bar(df, x=df.index, y='Close')

st.plotly_chart(fig, use_container_width=True)

# 2. 컬러 스케일 선택
color_scale = st.selectbox(
    '컬러 스케일',
    ['Blues', 'Reds', 'Greens', 'Viridis', 'Plasma']
)

fig = px.bar(df.head(10), x=df.head(10).index, y='Close',
             color='Close',
             color_continuous_scale=color_scale)
st.plotly_chart(fig, use_container_width=True)

# 3. 날짜 범위 필터링
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input('시작일', df.index.min())
with col2:
    end_date = st.date_input('종료일', df.index.max())

# 필터링된 데이터로 차트 생성
filtered_df = df.loc[start_date:end_date]
fig = px.line(filtered_df, x=filtered_df.index, y='Close',
              title=f'{start_date} ~ {end_date} 주가 추이')
st.plotly_chart(fig, use_container_width=True)
```

**Plotly 주요 장점:**
- ✅ 완전한 인터랙티브 차트 (줌, 팬, 호버, 선택 등)
- ✅ 전문적인 금융 차트 (캔들스틱, OHLC 등) 지원함
- ✅ 다양한 차트 타입과 커스터마이징 옵션 제공함
- ✅ 서브플롯으로 복잡한 대시보드 구성 가능함
- ✅ 드롭다운, 슬라이더 등 내장 인터랙티브 컨트롤 제공함
- ✅ 반응형 디자인으로 모바일에서도 잘 작동함

---

## 6️⃣ 레이아웃 기능

### 6.1 컬럼 (Columns)

```python
# 3개의 컬럼으로 나누기
col1, col2, col3 = st.columns(3)

col1.metric(label="달러USD", value="1,228 원", delta="-12.00 원")
col2.metric(label="일본JPY(100엔)", value="958.63 원", delta="-7.44 원")
col3.metric(label="유럽연합EUR", value="1,335.82 원", delta="11.44 원")
```

화면을 여러 컬럼으로 나누어 콘텐츠를 배치할 수 있음.

### 6.2 사이드바 (Sidebar)

```python
# 사이드바에 위젯 배치
with st.sidebar:
    date = st.date_input(
        "조회 시작일을 선택해 주세요",
        datetime.datetime(2022, 1, 1)
    )
    
    code = st.text_input(
        '종목코드', 
        value='',
        placeholder='종목코드를 입력해 주세요'
    )
```

사이드바를 활용하여 입력 위젯을 깔끔하게 정리할 수 있음.

### 6.3 탭 (Tabs)

```python
# 탭 생성
tab1, tab2 = st.tabs(['차트', '데이터'])

with tab1:    
    st.line_chart(data)

with tab2:
    st.dataframe(df.sort_index(ascending=False))
```

콘텐츠를 탭으로 구분하여 표시할 수 있음.

### 6.4 확장 가능한 영역 (Expander)

```python
# 접었다 펼 수 있는 영역
with st.expander('컬럼 설명'):
    st.markdown('''
    - Open: 시가
    - High: 고가
    - Low: 저가
    - Close: 종가
    - Adj Close: 수정 종가
    - Volume: 거래량
    ''')
```

추가 정보를 접어두고 필요할 때만 펼쳐볼 수 있음.

---

## 7️⃣ 캐싱 기능

```python
@st.cache
def read_pensiondata():
    data = PensionData('https://www.dropbox.com/s/nxeo1tziv05ejz7/national-pension.csv?dl=1')
    return data

# 함수 호출 시 캐싱됨
data = read_pensiondata()
```

**특징:**
- `@st.cache` 데코레이터를 사용하면 함수 결과를 캐싱함
- 동일한 입력에 대해 함수를 다시 실행하지 않아 성능이 크게 향상됨
- 데이터 로딩, API 호출 등 시간이 오래 걸리는 작업에 필수적임

---

## 8️⃣ 외부 API 연동 예제

### 8.1 Naver Clova API 연동

```python
import json
import configparser
import http.client

class CompletionExecutor:
    def __init__(self, host, api_key, api_key_primary_val, request_id):
        self._host = host
        self._api_key = api_key
        self._api_key_primary_val = api_key_primary_val
        self._request_id = request_id

    def _send_request(self, completion_request):
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'X-NCP-CLOVASTUDIO-API-KEY': self._api_key,
            'X-NCP-APIGW-API-KEY': self._api_key_primary_val,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id
        }
        
        conn = http.client.HTTPSConnection(self._host)
        conn.request('POST', '/testapp/v1/completions/LK-D', 
                    json.dumps(completion_request), headers)
        response = conn.getresponse()
        result = json.loads(response.read().decode(encoding='utf-8'))
        conn.close()
        return result

    def execute(self, completion_request):
        res = self._send_request(completion_request)
        if res['status']['code'] == '20000':
            return res['result']['text']
        else:
            return 'Error'

# API 키 설정
config = configparser.ConfigParser()
config.read('./your_apikey.ini')

completion_executor = CompletionExecutor(
    host=config['CLOVA']['host'],
    api_key=config['CLOVA']['api_key'],
    api_key_primary_val=config['CLOVA']['api_key_primary_val'],
    request_id=config['CLOVA']['request_id']
)

# Streamlit UI
st.title('나만의 챗봇')

preset_input = st.selectbox(
    '사전 문장',
    ('MBTI에 대한 지식을 기반으로, 아래의 질문에 답해보세요.', 
    '키워드를 포함하여 설날 인사말을 생성합니다.',
    '30대 남성으로 질문에 군인말투로 끝을 다,나,까로 대답한다.'),
    index=1
)

question = st.text_area('질문', placeholder='질문을 입력해 주세요')

if preset_input and question:
    preset_text = f'{preset_input}\n\n질문:{question}'
    
    request_data = {
        'text': preset_text,
        'maxTokens': 100,
        'temperature': 0.5,
        'topK': 0,
        'topP': 0.8,
        'repeatPenalty': 5.0,
        'start': '\n###답:',
        'stopBefore': ['###', '질문:', '답:', '###\n'],
        'includeTokens': True,
        'includeAiFilters': True,
        'includeProbs': True
    }
    
    response_text = completion_executor.execute(request_data)
    st.markdown(response_text.split('###')[1])
```

### 8.2 Bitly URL 단축 API

```python
import bitlyshortener
import configparser

# API 키 설정
config = configparser.ConfigParser()
config.read('./your_apikey.ini')

access_tokens = [config['bitly']['access_token']]
shortener = bitlyshortener.Shortener(tokens=access_tokens)

# Streamlit UI
url = st.text_input('URL을 입력해 주세요')

if url:
    shortened = shortener.shorten_urls([url])
    st.markdown(f'''
    ### URL이 생성되었습니다:sparkles:
    
    **긴 주소**
    ''')
    st.code(f'{url}')
    st.markdown(f'**짧은 주소**')
    st.code(f'{shortened[0]}')
```

---

## 9️⃣ 실전 프로젝트 예제

### 9.1 로또 번호 생성기

```python
import random
import datetime

st.title(':sparkles:로또 생성기:sparkles:')

def generate_lotto():
    lotto = set()
    
    while len(lotto) < 6:
        number = random.randint(1, 46)
        lotto.add(number)
    
    lotto = list(lotto)
    lotto.sort()
    return lotto

button = st.button('로또를 생성해 주세요!')

if button:
    for i in range(1, 6):
        st.subheader(f'{i}. 행운의 번호: :green[{generate_lotto()}]')
    st.write(f"생성된 시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
```

### 9.2 주식 차트 검색 앱

```python
import FinanceDataReader as fdr
import datetime

st.title('종목 차트 검색')

with st.sidebar:
    date = st.date_input(
        "조회 시작일을 선택해 주세요",
        datetime.datetime(2022, 1, 1)
    )
    
    code = st.text_input(
        '종목코드', 
        value='',
        placeholder='종목코드를 입력해 주세요'
    )

if code and date:
    df = fdr.DataReader(code, date)
    data = df.sort_index(ascending=True).loc[:, 'Close']
    
    tab1, tab2 = st.tabs(['차트', '데이터'])
    
    with tab1:    
        st.line_chart(data)
    
    with tab2:
        st.dataframe(df.sort_index(ascending=False))
    
    with st.expander('컬럼 설명'):
        st.markdown('''
        - Open: 시가
        - High: 고가
        - Low: 저가
        - Close: 종가
        - Adj Close: 수정 종가
        - Volume: 거래량
        ''')
```

### 9.3 국민연금 급여 조회 앱

이 앱은 국민연금 데이터를 기반으로 회사별 급여를 추정하는 복잡한 예제임.

**주요 기능:**
- 회사명으로 검색
- 해당 회사의 월급여 및 연봉 추정
- 동종 업계 평균과 비교
- 시각화를 통한 비교 분석

```python
# 회사 검색
company_name = st.text_input('회사명을 입력해 주세요', placeholder='검색할 회사명 입력')

if data and company_name:
    output = data.find_company(company_name=company_name)
    if len(output) > 0:
        st.subheader(output.iloc[0]['사업장명'])
        info = data.company_info(company_name=company_name)
        
        # 회사 정보 표시
        st.markdown(f"""
        - `{info['주소']}`
        - 업종코드명 `{info['업종코드명']}`
        - 총 근무자 `{int(info['가입자수']):,}` 명
        - 신규 입사자 `{info['신규']:,}` 명
        - 퇴사자 `{info['상실']:,}` 명
        """)
        
        # 메트릭 표시
        col1, col2, col3 = st.columns(3)
        col1.text('월급여 추정')
        col1.markdown(f"`{int(output.iloc[0]['월급여추정']):,}` 원")
        
        col2.text('연봉 추정')
        col2.markdown(f"`{int(output.iloc[0]['연간급여추정']):,}` 원")
        
        col3.text('가입자수 추정')
        col3.markdown(f"`{int(output.iloc[0]['가입자수']):,}` 명")
```

---

## 🔟 유용한 팁

### 1. 한글 폰트 설정

```python
# Matplotlib 한글 폰트 설정
plt.rcParams['font.family'] = "AppleGothic"  # Mac
# plt.rcParams['font.family'] = "NanumGothic"  # Windows, Linux
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
```

### 2. API 키 관리

```python
# .ini 파일로 API 키 관리
import configparser

config = configparser.ConfigParser()
config.read('./your_apikey.ini')

api_key = config['SECTION']['key_name']
```

**your_apikey.ini 예시:**
```ini
[CLOVA]
host = clovastudio.apigw.ntruss.com
api_key = your_api_key_here
api_key_primary_val = your_primary_key_here
request_id = your_request_id_here

[bitly]
access_token = your_bitly_token_here
```

### 3. 데이터 포맷팅

```python
# 숫자 천 단위 콤마
st.write(f"{1234567:,}")  # 1,234,567

# 소수점 자리수 제한
st.write(f"{3.141592:.2f}")  # 3.14
```

### 4. 조건부 렌더링

```python
# 입력값이 있을 때만 처리
if code and date:
    # 데이터 처리 및 표시
    pass
```

---

## 📚 결론

Streamlit은 Python 개발자가 빠르게 데이터 애플리케이션을 만들 수 있는 강력한 도구임. 

**주요 장점:**
- ✅ 간단한 문법으로 빠른 개발 가능함
- ✅ 다양한 위젯과 차트 지원함
- ✅ **Plotly를 통한 강력한 인터랙티브 시각화 가능함**
- ✅ 외부 API 연동이 쉬움
- ✅ 캐싱 기능으로 성능 최적화 가능함
- ✅ 레이아웃 기능으로 깔끔한 UI 구성 가능함

**활용 분야:**
- 📊 데이터 대시보드
- 🤖 머신러닝 모델 데모
- 📈 주식/금융 분석 도구 (Plotly 캔들스틱 차트 활용)
- 🔍 데이터 탐색 도구
- 💬 챗봇 인터페이스
- 📉 인터랙티브 비즈니스 리포트

Streamlit을 활용하면 복잡한 웹 개발 지식 없이도 전문적인 데이터 애플리케이션을 만들 수 있음!

---

## 🔗 참고 자료

- Streamlit 공식 문서: https://docs.streamlit.io/
- Streamlit 이모티콘: https://streamlit-emoji-shortcodes-streamlit-app-gwckff.streamlit.app/
- FinanceDataReader: https://github.com/financedata-org/FinanceDataReader
- Plotly 공식 문서: https://plotly.com/python/
- Plotly Graph Objects: https://plotly.com/python/graph-objects/
- Plotly Express: https://plotly.com/python/plotly-express/
