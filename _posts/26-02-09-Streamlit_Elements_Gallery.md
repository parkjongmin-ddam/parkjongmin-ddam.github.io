---
layout: single
title: "Streamlit Elements 갤러리 완전 분석: 초보자를 위한 가이드"
categories: Streamlit
tag: [Python, Streamlit, Streamlit-Elements, Dashboard]
toc: true
toc_sticky: true
author_profile: false
sidebar:
  nav: "docs"
header:
  teaser: /assets/images/streamlit_elements_gallery.png
---

# 🎨 Streamlit Elements 갤러리 완전 분석

## 🎯 개요

Streamlit Elements는 Streamlit 애플리케이션에서 Material UI, Nivo 차트, Monaco 에디터 등 강력한 서드파티 라이브러리를 사용할 수 있게 해주는 확장 컴포넌트임.

이 글에서는 `streamlit-elements` 데모 갤러리에 포함된 주요 컴포넌트들을 분석하고, 초보자도 쉽게 이해할 수 있도록 그 구조와 활용법을 정리함.

![Streamlit Elements Gallery](/assets/images/streamlit_elements_gallery.png)

---

## 🏗️ 갤러리 구조 이해하기

갤러리 예제는 크게 **대시보드(Dashboard)** 와 **개별 아이템(Item)** 구조로 이루어져 있음. 마치 레고 판(Dashboard) 위에 레고 블록(Item)을 끼우는 것과 유사함.

### 1. Dashboard (`dashboard.py`)
- **역할**: 모든 컴포넌트를 담는 판(Plate) 역할을 함.
- **기능**:
  - 그리드 레이아웃을 제공하여 아이템들을 격자 모양으로 배치함.
  - 드래그 앤 드롭을 지원하여 사용자가 자유롭게 배치를 바꿀 수 있음.
  - 다크 모드/라이트 모드 전환 기능을 내장하고 있음.

### 2. 개별 아이템들
각 아이템은 `Dashboard.Item`을 상속받아 구현됨. 이는 모든 아이템이 공통적인 특징(이동 가능, 크기 조절 가능 등)을 가지면서, 자신만의 고유한 기능을 수행하도록 설계된 것임.

---

## 🧩 주요 컴포넌트 분석

### 1. 🗂️ Card (`card.py`)
- **무엇인가?**: 이미지, 텍스트, 버튼 등을 포함할 수 있는 다용도 카드임.
- **활용**: 사용자 프로필, 제품 소개, 뉴스 기사 등을 예쁘게 보여줄 때 사용함.
- **특징**:
  - Material UI의 `Card` 컴포넌트를 사용함.
  - '좋아요', '공유' 같은 액션 버튼을 추가할 수 있음.
  - `sync()` 함수를 통해 버튼 클릭 상태를 Streamlit과 동기화함.

### 2. 📊 DataGrid (`datagrid.py`)
- **무엇인가?**: 엑셀처럼 데이터를 표 형태로 보여주고 조작할 수 있는 컴포넌트임.
- **활용**: 많은 양의 데이터를 목록으로 보여주거나, 특정 값을 직접 수정해야 할 때 유용함.
- **특징**:
  - 정렬(Sorting), 필터링(Filtering), 페이지 넘기기(Paging) 기능이 기본 제공됨.
  - JSON 데이터를 입력받아 표를 그림.
  - 셀 내용을 더블 클릭하여 직접 수정할 수 있음 (`editable: True`).

### 3. 📝 Editor (`editor.py`)
- **무엇인가?**: VS Code와 같은 강력한 코드 에디터를 웹 화면에 띄워줌.
- **활용**: 사용자가 직접 코드를 입력하거나, 설정 파일을 수정하게 할 때 사용함.
- **특징**:
  - Monaco Editor를 기반으로 하여 문법 강조(Syntax Highlighting)를 지원함.
  - 여러 파일을 동시에 열 수 있는 탭(Tab) 기능을 구현해 둠.
  - `Ctrl+S`를 누르거나 'Apply' 버튼을 눌러 내용을 저장할 수 있음.

### 4. 🥧 Pie Chart (`pie.py`) & 🕸️ Radar Chart (`radar.py`)
- **무엇인가?**: 데이터를 시각적으로 보여주는 차트 컴포넌트임.
- **활용**: 데이터 분포나 비율, 여러 항목 간의 비교 분석 결과를 보여줄 때 사용함.
- **특징**:
  - **Pie Chart**: 원형 그래프로 전체 중 차지하는 비율을 보여줌. 섹션을 클릭하거나 마우스를 올리면 상세 정보가 나옴.
  - **Radar Chart**: 거미줄 모양 그래프로 여러 속성을 한눈에 비교함 (예: 맛 비교 - 단맛, 쓴맛, 신맛 등).
  - Nivo 라이브러리를 사용하여 디자인이 깔끔하고 애니메이션이 자연스러움.

### 5. 🎬 Player (`player.py`)
- **무엇인가?**: 동영상 재생기임.
- **활용**: 유튜브 영상이나 로컬 비디오 파일을 재생할 때 사용함.
- **특징**:
  - URL을 입력하면 해당 영상을 바로 재생함.
  - 재생, 일시정지, 볼륨 조절 등의 기본 컨트롤러를 포함함.

---

## 💡 어떻게 활용할까?

이 갤러리 예제는 단순한 데모가 아니라, **모듈형 대시보드**를 만드는 훌륭한 템플릿임.

1. **나만의 아이템 만들기**: `Dashboard.Item`을 상속받는 새로운 클래스를 만들어서 내가 원하는 기능(예: 지도, 채팅창)을 추가할 수 있음.
2. **레이아웃 커스터마이징**: `dashboard.Grid`의 설정을 변경하여 초기 배치나 아이템 크기를 조절할 수 있음.
3. **상태 관리**: `streamlit.session_state`와 연동하여, 대시보드에서 일어난 변경 사항(데이터 수정, 코드 입력 등)을 Streamlit 앱 전체에 반영할 수 있음.

## 🚀 결론

Streamlit Elements는 Streamlit의 한계를 넘어, 더욱 풍부하고 동적인 사용자 경험(UX)을 제공할 수 있게 해줌. 특히 이 갤러리 예제들은 각각의 기능이 모듈화되어 있어, 코드를 분석하고 재사용하기에 매우 좋음.

초보자라면 먼저 `card.py`나 `player.py` 같은 단순한 컴포넌트부터 코드를 수정해보며 익히는 것을 추천함!

**Made with ❤️ using Streamlit Elements**

**2026-02-09**
