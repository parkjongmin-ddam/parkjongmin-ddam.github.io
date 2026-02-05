# Plotly 통계용 차트 실습

**공식 문서**: [https://plotly.com/python/statistical-charts/](https://plotly.com/python/statistical-charts/)

## 📊 개요

Plotly 공식 문서를 기반으로 다양한 통계용 차트를 실습하는 프로젝트임. 데이터 분석에 필수적인 7가지 통계 차트 유형을 포함함.

## 📁 파일

- [plotly_statistical_charts.py](file:///d:/python/Plotly/plotly_statistical_charts.py) - 메인 실습 파일임

## 📈 포함된 차트 유형

### 1. Box Plot (박스 플롯)
- **목적**: 데이터 분포와 이상치 확인
- **특징**: 
  - 중앙값, 사분위수, 이상치를 한눈에 파악함
  - 여러 그룹 간의 분포를 비교함
  - 평균과 표준편차를 표시함 (`boxmean='sd'`)

![Box Plot Visualization](C:/Users/jongm/.gemini/antigravity/brain/be2e5611-0cde-4f49-acf0-ea6af78b9266/box_plot_diagram_1770289330435.png)

### 2. Histogram (히스토그램)
- **목적**: 빈도 분포 분석
- **특징**:
  - 데이터의 분포 형태를 시각화함
  - 여러 데이터셋을 오버레이하여 비교함
  - 투명도 조절로 겹치는 부분을 확인함

### 3. Violin Plot (바이올린 플롯)
- **목적**: 상세한 분포 시각화
- **특징**:
  - Box Plot과 확률 밀도 함수를 결합함
  - 데이터의 전체 분포 형태를 파악함
  - 박스 플롯과 평균선을 함께 표시함

![Violin Plot Visualization](C:/Users/jongm/.gemini/antigravity/brain/be2e5611-0cde-4f49-acf0-ea6af78b9266/violin_plot_diagram_1770289345026.png)

### 4. Error Bars (오차 막대)
- **목적**: 불확실성 표현
- **특징**:
  - 평균값과 표준편차를 시각화함
  - 그룹 간 변동성을 비교함
  - 막대 그래프와 결합하여 표현함

### 5. 2D Histogram (2차원 히스토그램)
- **목적**: 이변량 데이터 분포
- **특징**:
  - 두 변수 간의 관계를 시각화함
  - 밀도 분포를 색상으로 표현함
  - 상관관계 패턴을 파악함

### 6. Marginal Distribution Plot (주변 분포 플롯)
- **목적**: 산점도와 주변 분포 동시 표시
- **특징**:
  - 중앙에 두 변수의 산점도를 배치함
  - X축 주변에 히스토그램을 배치함
  - Y축 주변에 박스 플롯을 배치함
  - Plotly Express를 활용함

![Marginal Distribution Plot](C:/Users/jongm/.gemini/antigravity/brain/be2e5611-0cde-4f49-acf0-ea6af78b9266/marginal_plot_example_1770289371253.png)

### 7. 종합 대시보드
- **목적**: 여러 통계 차트 통합
- **특징**:
  - 2x2 서브플롯으로 구성함
  - Box Plot, Histogram, Violin Plot, Error Bars를 한 화면에 표시함
  - 데이터 분석 결과를 종합적으로 비교함

![Statistical Dashboard Preview](C:/Users/jongm/.gemini/antigravity/brain/be2e5611-0cde-4f49-acf0-ea6af78b9266/statistical_dashboard_preview_1770289389492.png)

## 🔧 주요 기술 요소

### 사용된 라이브러리
```python
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
```

### 데이터 생성
- 정규분포 데이터를 생성함 (`np.random.normal`)
- 그룹별 데이터를 구성함
- 상관관계가 있는 2차원 데이터를 생성함

### 스타일링
- `template='plotly_white'`로 깔끔한 흰색 배경을 적용함
- 그룹별로 다른 색상을 적용하여 구분함
- 오버레이 차트에서 투명도를 조절하여 겹치는 부분을 확인함

## 💡 학습 포인트

### 1. Graph Objects vs Express
- **Graph Objects (`go`)**: 세밀한 제어가 가능하며, 복잡한 커스터마이징에 적합함
- **Plotly Express (`px`)**: 간단한 코드로 빠른 시각화가 가능함

### 2. 마커 속성 설정
```python
# 올바른 방법
marker=dict(color='lightblue')

# 주의: update_traces 사용 시 selector 지정해야 함
fig.update_traces(marker=dict(size=5), selector=dict(type='scatter'))
```

### 3. 서브플롯 구성
```python
make_subplots(
    rows=2, cols=2,
    specs=[[{"type": "box"}, {"type": "bar"}],
           [{"type": "violin"}, {"type": "bar"}]]
)
```

## 🚀 실행 방법

```bash
cd d:\python\Plotly
python plotly_statistical_charts.py
```

각 차트가 순차적으로 브라우저에서 열림.

## 📚 참고 자료

- [Plotly Statistical Charts 공식 문서](https://plotly.com/python/statistical-charts/)
- [Box Plots](https://plotly.com/python/box-plots/)
- [Histograms](https://plotly.com/python/histograms/)
- [Violin Plots](https://plotly.com/python/violin/)
- [Error Bars](https://plotly.com/python/error-bars/)
- [2D Histograms](https://plotly.com/python/2D-Histogram/)
- [Marginal Plots](https://plotly.com/python/marginal-plots/)

## 🎯 활용 분야

- **데이터 탐색**: 데이터의 분포와 특성을 파악함
- **이상치 탐지**: Box Plot으로 이상치를 식별함
- **그룹 비교**: 여러 그룹의 통계적 차이를 시각화함
- **불확실성 표현**: Error Bars로 측정 오차를 표시함
- **상관관계 분석**: 2D Histogram과 Marginal Plot을 활용함

## ✅ 완료 사항

- [x] Box Plot 구현함
- [x] Histogram 구현함
- [x] Violin Plot 구현함
- [x] Error Bars 구현함
- [x] 2D Histogram 구현함
- [x] Marginal Distribution Plot 구현함
- [x] 종합 대시보드 구현함
- [x] 모든 차트 테스트 완료함
