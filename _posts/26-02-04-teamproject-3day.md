---
layout: single
title: "팀 프로젝트 3일차 - Plotly를 활용한 시각화"
categories: python
tag: [python, plotly, visualization, stock-analysis]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# 📊 3일차: Plotly를 활용한 시각화

오늘은 Python의 강력한 시각화 라이브러리인 Plotly를 사용하여 주식 데이터를 시각화하는 방법을 학습하고 구현해봄. 캔들스틱 차트를 기본으로 하여 이동평균선과 거래량을 함께 표시하는 대시보드 형태의 차트를 만듦.

![Plotly Candlestick Chart](/assets/images/plotly_candlestick_chart.png)

### 📊 캔들스틱 차트 구현

주식 데이터의 시가, 고가, 저가, 종가를 한눈에 파악할 수 있는 캔들스틱 차트를 기본으로 구성함.

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

주가 흐름을 파악하기 위해 5일, 20일, 60일 이동평균선을 차트에 추가함.

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

가격 차트 하단에 거래량(Volume)을 함께 표시하기 위해 `make_subplots`를 사용하여 영역을 나눔. `shared_xaxes=True` 설정을 통해 두 차트의 X축을 동기화함.

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
