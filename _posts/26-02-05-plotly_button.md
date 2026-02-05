---
layout: single
title: "Plotly 인터렉티브 버튼 실습 - 사용자 제어 차트"
categories: python
tag: [python, plotly, interactivity, buttons, updatemenus, animation, custom-buttons, visualization]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# Plotly 인터렉티브 버튼 실습

**공식 문서**: [https://plotly.com/python/custom-buttons/](https://plotly.com/python/custom-buttons/)

## 📊 개요

Plotly의 버튼(`updatemenus` with `type="buttons"`)을 활용하여 사용자 인터랙션을 구현하는 방법을 다룸. 드롭다운과 달리 버튼은 여러 개를 나란히 배치할 수 있으며, 즉각적인 시각적 피드백을 제공함.

## 📁 파일

- [plotly_button_practice.py](file:///d:/python/Plotly/plotly_button_practice.py) - 버튼 실습 코드

## 🔑 버튼 vs 드롭다운

| 특징 | 버튼 (`type="buttons"`) | 드롭다운 (`type="dropdown"`) |
|------|------------------------|----------------------------|
| **배치** | 가로/세로로 나열 | 접혀있다가 펼쳐짐 |
| **시각성** | 모든 옵션이 항상 보임 | 선택 시에만 옵션 표시 |
| **용도** | 2~5개 정도의 주요 옵션 | 많은 옵션 (5개 이상) |
| **공간** | 더 많은 공간 필요 | 공간 절약 |

## 💻 구현 예제

### 1. 기본 버튼 구조
```python
updatemenus = [
    dict(
        type="buttons",  # 버튼 타입
        direction="left",  # 버튼 배치 방향
        buttons=list([
            dict(label="Option 1", method="restyle", args=[...]),
            dict(label="Option 2", method="restyle", args=[...]),
        ]),
        x=0.5,
        y=1.15,
        bgcolor="lightgray",
        active=0,  # 초기 활성 버튼
        showactive=True
    )
]
```

### 2. 버튼 배치 방향
- `direction="left"`: 왼쪽에서 오른쪽으로 배치
- `direction="right"`: 오른쪽에서 왼쪽으로 배치
- `direction="up"`: 아래에서 위로 배치
- `direction="down"`: 위에서 아래로 배치

### 3. 버튼 스타일링
```python
dict(
    bgcolor="#f0f0f0",      # 배경색
    bordercolor="#333",     # 테두리 색
    borderwidth=1,          # 테두리 두께
    font=dict(size=14),     # 폰트 크기
    active=0,               # 초기 활성 버튼 인덱스
    showactive=True,        # 활성 버튼 강조 표시
    pad=dict(r=10, t=10)    # 패딩
)
```

## 🚀 실행 결과

스크립트를 실행하면 네 가지 예제가 순차적으로 표시됨:

1. **차트 타입 전환**: Bar, Line, Area 차트 간 전환
2. **데이터 필터링**: 제품별 데이터 표시/숨김 제어
3. **복합 버튼 그룹**: 축 스케일과 테마를 동시에 제어하는 두 개의 버튼 그룹
4. **애니메이션 버튼**: Play/Pause 버튼으로 년도별 데이터 변화를 애니메이션으로 표시

## 💡 주요 메서드

### 1. Restyle
데이터 속성 변경 (차트 타입, 가시성, 색상 등)
```python
dict(label="Bar", method="restyle", args=[{"type": "bar"}])
```

### 2. Relayout
레이아웃 속성 변경 (축 스케일, 테마, 제목 등)
```python
dict(label="Log", method="relayout", args=[{"xaxis.type": "log"}])
```

### 3. Update
데이터와 레이아웃 동시 변경
```python
dict(label="Update", method="update", args=[{data}, {layout}])
```

### 4. Animate
애니메이션 제어 (Play/Pause)
```python
dict(
    label="Play",
    method="animate",
    args=[None, {"frame": {"duration": 500}}]
)
```

## 🎨 고급 활용

### 여러 버튼 그룹 배치
```python
updatemenus = [
    # 첫 번째 버튼 그룹
    dict(type="buttons", x=0.0, y=1.15, buttons=[...]),
    # 두 번째 버튼 그룹
    dict(type="buttons", x=0.5, y=1.15, buttons=[...])
]
```

### 애니메이션과 슬라이더 결합
Play/Pause 버튼과 함께 슬라이더를 추가하여 사용자가 직접 프레임을 선택할 수 있도록 함.

## 📚 참고 자료

- [Custom Buttons 공식 문서](https://plotly.com/python/custom-buttons/)
- [Animations 공식 문서](https://plotly.com/python/animations/)
- [Update Menus 공식 문서](https://plotly.com/python/dropdowns/)

## ✅ 완료 사항

- [x] 차트 타입 전환 버튼 구현함
- [x] 데이터 필터링 버튼 구현함
- [x] 복합 버튼 그룹 구현함
- [x] 애니메이션 버튼 구현함
- [x] 모든 버튼 테스트 완료함
