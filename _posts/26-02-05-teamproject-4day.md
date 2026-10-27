---
layout: single
title: "Generative AI 10기 팀 프로젝트 - 4일차: 대시보드 스타일링 및 완성"
categories: ["Project", "주식 대시보드(팀)"]
permalink: "/python/teamproject-4day/"
tag: [python, plotly, dashboard, visualization, dark-mode, styling]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# 📊 4일차: 대시보드 스타일링 및 완성

## 학습 목표

4일차에는 Plotly를 활용하여 대시보드의 시각적 완성도를 높이는 작업을 진행함. 다크 모드 테마 적용, 축 스타일링, 그리고 최종 결과물을 HTML 파일로 저장하는 방법을 학습함.

### 📊 완성된 대시보드 미리보기

![Dark Mode Dashboard](/assets/images/26-02-05/dark_mode_dashboard_1770288574903.png)

---

## 🎨 다크 모드 테마 적용

### 레이아웃 설정

Plotly의 `update_layout()` 메서드를 사용하여 대시보드 전체의 스타일을 설정함.

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

### 주요 설정 항목

| 속성 | 설명 | 값 |
|------|------|-----|
| `template` | Plotly 기본 테마 | `'plotly_dark'` |
| `plot_bgcolor` | 차트 영역 배경색 | `'rgba(17, 17, 17, 1)'` |
| `paper_bgcolor` | 전체 배경색 | `'rgba(10, 10, 10, 1)'` |
| `height` | 차트 높이 | `900` (픽셀) |
| `hovermode` | 호버 모드 | `'x unified'` |

### 타이틀 스타일링

- **위치**: `x=0.5, y=0.95` (중앙 상단)
- **폰트**: 크기 24, 흰색
- **HTML 태그**: `<b>` 태그로 굵게 표시

### 범례(Legend) 설정

- **방향**: 수평 (`orientation="h"`)
- **위치**: 차트 상단 우측
- **색상**: 흰색 텍스트

### 📐 레이아웃 커스터마이징 가이드

![Layout Customization Guide](/assets/images/26-02-05/layout_customization_guide_1770288601886.png)

---

## 🎯 축 스타일링

### 공통 축 스타일 정의

차트의 X축과 Y축에 공통으로 적용할 스타일을 딕셔너리로 정의함.

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

### 축 스타일 상세 설명

#### 그리드 라인
- **색상**: `rgba(128, 128, 128, 0.2)` (반투명 회색)
- **목적**: 데이터 읽기 쉽게 하면서도 시각적 방해 최소화

#### 스파이크 라인
- **표시 여부**: `showspikes=True`
- **두께**: `1` 픽셀
- **스타일**: `'dot'` (점선)
- **색상**: `#999999` (회색)

> **스파이크 라인이란?**  
> 마우스를 차트 위에 올렸을 때 X축과 Y축에 표시되는 보조선으로, 정확한 값을 읽는 데 도움을 줌.

#### Y축 추가 설정
- **숫자 포맷**: `tickformat=','` (천 단위 구분 기호)
- **예시**: `50000` → `50,000`

### 🎯 축 스타일링 시각화

![Axis Styling Features](/assets/images/26-02-05/axis_styling_features_1770288621929.png)

---

## 💾 HTML 파일로 저장

### 저장 및 실행 코드

```python
import os

output_file = "hynix_dashboard_final.html"
fig.write_html(output_file)
print(f"최종 대시보드가 '{output_file}'로 저장되었습니다.")

# 윈도우 환경에서 자동으로 브라우저 열기
if os.name == 'nt':
    os.startfile(output_file)
```

### 📤 HTML 내보내기 프로세스

![HTML Export Process](/assets/images/26-02-05/html_export_process_1770288682005.png)

### 코드 설명

1. **파일 저장**: `fig.write_html(output_file)`
   - Plotly 차트를 인터랙티브 HTML 파일로 저장
   - JavaScript가 포함되어 있어 브라우저에서 바로 실행 가능

2. **OS 확인**: `os.name == 'nt'`
   - `'nt'`: Windows 운영체제
   - `'posix'`: Linux/Mac 운영체제

3. **자동 실행**: `os.startfile(output_file)`
   - Windows에서 기본 브라우저로 HTML 파일 자동 실행
   - Mac/Linux에서는 `subprocess` 모듈 사용 필요

### HTML 파일의 장점

- ✅ **독립 실행**: Python 환경 없이도 브라우저에서 실행
- ✅ **인터랙티브**: 줌, 팬, 호버 등 모든 기능 유지
- ✅ **공유 용이**: 파일 하나로 결과물 공유 가능
- ✅ **오프라인 사용**: 인터넷 연결 없이도 확인 가능

---

## 💡 주요 학습 내용

### 1. Plotly 레이아웃 커스터마이징

#### 테마 시스템
- **기본 제공 테마**: `plotly`, `plotly_white`, `plotly_dark`, `ggplot2`, `seaborn` 등
- **커스텀 색상**: RGBA 형식으로 투명도 조절 가능
- **일관성**: 전체 차트에 통일된 스타일 적용

#### 다크 모드의 장점
- 👁️ **눈의 피로 감소**: 어두운 환경에서 편안한 시청
- 🎨 **데이터 강조**: 밝은 색상의 데이터가 더욱 돋보임
- 💻 **전문적인 느낌**: 현대적이고 세련된 UI

### 2. 축 스타일링 기법

#### 그리드 최적화
```python
gridcolor='rgba(128, 128, 128, 0.2)'  # 투명도 0.2로 설정
```
- 너무 진하면 데이터를 가림
- 너무 연하면 가독성 저하
- 적절한 투명도로 균형 유지

#### 인터랙티브 요소
```python
hovermode='x unified'  # 모든 데이터 시리즈를 한 번에 표시
```
- `'x'`: X축 값이 같은 모든 데이터 표시
- `'y'`: Y축 값이 같은 모든 데이터 표시
- `'closest'`: 가장 가까운 데이터 포인트만 표시
- `'x unified'`: X축 기준으로 통합된 툴팁 표시

### 3. 파일 저장 및 실행

#### write_html() 메서드
```python
fig.write_html(
    file='output.html',
    auto_open=True,           # 저장 후 자동으로 브라우저 열기
    include_plotlyjs='cdn',   # Plotly.js CDN 사용 (파일 크기 감소)
    config={'displayModeBar': False}  # 툴바 숨기기
)
```

#### OS별 파일 실행 방법

| OS | 방법 | 코드 |
|-----|------|------|
| Windows | `os.startfile()` | `os.startfile('file.html')` |
| Mac | `open` 명령어 | `subprocess.run(['open', 'file.html'])` |
| Linux | `xdg-open` 명령어 | `subprocess.run(['xdg-open', 'file.html'])` |

---

## 🎨 스타일링 Best Practices

### 색상 선택 가이드

#### 다크 모드 색상 팔레트

![Color Palette Reference](/assets/images/26-02-05/color_palette_reference_1770288658821.png)

```python
# 배경색
DARK_BG = 'rgba(10, 10, 10, 1)'      # 전체 배경
PLOT_BG = 'rgba(17, 17, 17, 1)'      # 차트 영역

# 강조색
RED = '#ff5252'      # 상승 (양봉)
BLUE = '#448aff'     # 하락 (음봉)
YELLOW = '#ffeb3b'   # MA 5
GREEN = '#00e676'    # MA 20
PURPLE = '#e040fb'   # MA 60

# 보조색
GRID = 'rgba(128, 128, 128, 0.2)'    # 그리드
SPIKE = '#999999'                     # 스파이크 라인
```

### 가독성 향상 팁

1. **대비 확보**: 배경과 텍스트 색상의 충분한 대비
2. **일관성 유지**: 같은 의미의 요소는 같은 색상 사용
3. **색맹 고려**: 색상만으로 정보 전달하지 않기
4. **적절한 간격**: 요소 간 충분한 여백 확보

---

## 🔍 완성된 대시보드 기능

### 인터랙티브 기능

- **줌**: 드래그하여 특정 영역 확대
- **팬**: 확대된 상태에서 차트 이동
- **호버**: 마우스를 올리면 상세 정보 표시
- **범례 클릭**: 특정 데이터 시리즈 숨기기/보이기
- **리셋**: 더블 클릭으로 원래 뷰로 복귀

### 데이터 시각화 요소

1. **캔들스틱 차트**: 주가의 시가, 고가, 저가, 종가
2. **이동평균선**: MA 5, MA 20, MA 60
3. **거래량 차트**: 상승/하락에 따른 색상 구분
4. **스파이크 라인**: 정확한 값 읽기 지원

---

## 📝 전체 코드 예시

```python
import FinanceDataReader as fdr
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# 1. 데이터 수집
ticker = "000660"  # SK하이닉스
start_date = "2025-01-01"
end_date = "2025-12-31"
df = fdr.DataReader(ticker, start_date, end_date)

# 2. 이동평균선 계산
df['MA5'] = df['Close'].rolling(window=5).mean()
df['MA20'] = df['Close'].rolling(window=20).mean()
df['MA60'] = df['Close'].rolling(window=60).mean()

# 3. 거래량 색상 구분
colors = []
for i, row in df.iterrows():
    if row['Close'] >= row['Open']:
        colors.append('#ff5252')  # Red (상승)
    else:
        colors.append('#448aff')  # Blue (하락)

# 4. 서브플롯 생성
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    subplot_titles=('SK Hynix Stock Price', 'Volume'),
    row_heights=[0.7, 0.3]
)

# 5. 캔들스틱 차트
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'], high=df['High'],
    low=df['Low'], close=df['Close'],
    name='Price',
    increasing_line_color='#ff5252',
    decreasing_line_color='#448aff'
), row=1, col=1)

# 6. 이동평균선
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

# 7. 거래량 차트
fig.add_trace(go.Bar(
    x=df.index, y=df['Volume'],
    marker_color=colors,
    name='Volume',
    opacity=0.8
), row=2, col=1)

# 8. 레이아웃 스타일링
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

# 9. 축 스타일링
common_axis_style = dict(
    gridcolor='rgba(128, 128, 128, 0.2)',
    showspikes=True,
    spikethickness=1,
    spikedash='dot',
    spikecolor='#999999'
)

fig.update_xaxes(**common_axis_style)
fig.update_yaxes(**common_axis_style, tickformat=',')

# 10. HTML 파일로 저장
output_file = "hynix_dashboard_final.html"
fig.write_html(output_file)
print(f"최종 대시보드가 '{output_file}'로 저장되었습니다.")

# 윈도우 환경에서 자동으로 브라우저 열기
if os.name == 'nt':
    os.startfile(output_file)
```

---

## 🚀 다음 단계

### 5일차 예고: Streamlit 웹 대시보드

4일차에서는 정적 HTML 파일을 생성했다면, 5일차에는 Streamlit을 활용하여 동적인 웹 애플리케이션을 만들 예정임.

**주요 기능**:
- 종목 선택 기능
- 실시간 데이터 업데이트
- 인터랙티브 UI
- 웹 배포

---

## 📚 참고 자료

- [Plotly Layout 공식 문서](https://plotly.com/python/reference/layout/)
- [Plotly Themes 가이드](https://plotly.com/python/templates/)
- [Plotly 색상 가이드](https://plotly.com/python/colorscales/)
- [HTML Export 문서](https://plotly.com/python/interactive-html-export/)

---

## 💭 배운 점 및 느낀 점

### 기술적 성장

1. **시각화 디자인 감각**
   - 다크 모드 테마의 효과적인 활용법 학습
   - 색상 선택과 대비의 중요성 이해
   - 사용자 경험을 고려한 인터랙티브 요소 구현

2. **Plotly 고급 기능**
   - 레이아웃 커스터마이징의 다양한 옵션 탐구
   - 축 스타일링을 통한 가독성 향상
   - HTML 파일 생성으로 결과물 공유 방법 습득

3. **코드 최적화**
   - 공통 스타일을 딕셔너리로 관리하는 방법
   - OS별 분기 처리로 범용성 확보
   - 재사용 가능한 코드 구조 설계

### 프로젝트 인사이트

- **완성도의 중요성**: 기능뿐만 아니라 시각적 완성도가 사용자 경험에 큰 영향을 미침
- **디테일의 힘**: 작은 스타일링 요소들이 모여 전문적인 결과물을 만듦
- **공유와 협업**: HTML 파일로 저장하여 팀원들과 쉽게 공유할 수 있음

---

## ✨ 마무리

4일차에는 Plotly를 활용한 대시보드 스타일링 작업을 완료함. 다크 모드 테마 적용, 축 스타일링, HTML 파일 저장 등을 통해 전문적인 수준의 시각화 결과물을 만들 수 있었음. 다음 단계에서는 Streamlit을 활용하여 더욱 동적이고 인터랙티브한 웹 애플리케이션으로 발전시킬 예정임.
