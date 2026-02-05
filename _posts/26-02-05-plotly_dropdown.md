---
layout: single
title: "Plotly 인터렉티브 드롭다운 실습 - 동적 데이터 시각화"
categories: python
tag: [python, plotly, interactivity, dropdown, updatemenus, dynamic-charts, visualization]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# Plotly 인터렉티브 드롭다운 실습

**공식 문서**: [https://plotly.com/python/dropdowns/](https://plotly.com/python/dropdowns/)

## 📊 개요

Plotly의 `updatemenus` 기능을 활용하여 사용자와 상호작용하는 인터렉티브 차트를 구현하는 방법을 다룸. 

## 📁 파일

- [plotly_dropdown_practice.py](file:///d:/python/Plotly/plotly_dropdown_practice.py) - 드롭다운 실습 코드

## 🔑 핵심 메서드

Plotly 드롭다운은 다음 세 가지 메서드를 통해 차트를 업데이트함.

![Plotly Update Methods Comparison](C:/Users/jongm/.gemini/antigravity/brain/be2e5611-0cde-4f49-acf0-ea6af78b9266/plotly_update_methods_comparison_1770289942752.png)

### 1. Restyle (`method="restyle"`)
- **기능**: 데이터 속성 또는 Trace 속성을 변경함.
- **예시**: 
  - 특정 데이터 계열만 표시/숨김 (`visible` 속성 제어)
  - 차트 타입 변경 (Scatter ↔ Bar)
  - 마커 색상, 라인 스타일 변경

### 2. Relayout (`method="relayout"`)
- **기능**: 차트의 레이아웃 속성을 변경함.
- **예시**:
  - 축 스케일 변경 (Linear ↔ Log)
  - 차트 제목, 배경색, 테마 변경
  - 주석(Annotation) 표시/숨김

### 3. Update (`method="update"`)
- **기능**: `restyle`과 `relayout`을 동시에 실행함.
- **예시**:
  - 년도별 데이터 변경 시, 차트 데이터(x, y)와 차트 제목(title)을 동시에 업데이트
  - 복잡한 대시보드 인터랙션 구현

## 💻 구현 예제

### 기본 구조
```python
updatemenus = [
    dict(
        type="dropdown",
        buttons=list([
            dict(label="Option 1",
                 method="restyle",
                 args=[{"visible": [True, False]}]),
            dict(label="Option 2",
                 method="restyle",
                 args=[{"visible": [False, True]}]),
        ]),
    )
]

fig.update_layout(updatemenus=updatemenus)
```

### 🧬 드롭다운 구조 시각화

![Plotly Dropdown Structure Diagram](C:/Users/jongm/.gemini/antigravity/brain/be2e5611-0cde-4f49-acf0-ea6af78b9266/plotly_dropdown_structure_1770289972559.png)

### 스타일링 옵션 (`pad`, `x`, `y`)
드롭다운의 위치와 여백을 세밀하게 조정할 수 있음.
```python
dict(
    direction="down",
    pad={"r": 10, "t": 10},  # 패딩
    x=0.1,                   # x 위치 (0~1)
    xanchor="left",
    y=1.1,                   # y 위치 (1.0 이상이면 차트 상단)
    yanchor="top"
)
```

## 🚀 실행 결과

![Interactive Dashboard Preview](C:/Users/jongm/.gemini/antigravity/brain/be2e5611-0cde-4f49-acf0-ea6af78b9266/interactive_dashboard_preview_1770289988380.png)

스크립트를 실행하면 세 가지 예제가 순차적으로 표시됨:
1. **데이터 선택**: 주식 데이터를 `visible` 속성으로 제어하여 선택적으로 표시함.
2. **레이아웃 변경**: Y축 스케일을 Linear와 Log로 전환함.
3. **복합 기능**: Gapminder 데이터를 사용하여 년도별 데이터 변화와 차트 타입 변경을 동시에 수행하는 고급 인터랙션을 보여줌.

## 💡 팁

- `args` 리스트는 Trace의 인덱스와 매핑됨. `{"visible": [True, False]}`는 첫 번째 Trace는 보이고, 두 번째는 숨기라는 의미임.
- 여러 개의 드롭다운을 배치할 때는 `x`, `y` 좌표를 사용하여 겹치지 않게 정렬하는 것이 중요함.
- `update` 메서드는 가장 강력하지만, 인자 구조가 복잡할 수 있으므로 주의가 필요함.
