---
layout: single
title: "Streamlit 기본 문법 및 핵심 개념 - Data Flow, Session State, Callbacks"
categories: python
tag: [python, streamlit, session-state, callbacks, forms, caching, data-flow]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# Streamlit 기본 문법 및 핵심 개념

## 📌 소개

Streamlit의 핵심 개념과 기본 문법을 정리한 문서임. Streamlit 공식 문서를 참고하여 작성함.

---

## 1. Data Flow (데이터 흐름)

Streamlit의 가장 중요한 특징은 **위에서 아래로 스크립트를 실행**한다는 것임.

**재실행 조건:**
- 소스 코드를 수정했을 때
- 사용자가 위젯(슬라이더, 버튼 등)과 상호작용했을 때

```python
import streamlit as st

# 스크립트는 항상 위에서 아래로 실행됨
st.write('1. 첫 번째 실행')
st.write('2. 두 번째 실행')
st.write('3. 세 번째 실행')

# 위젯과 상호작용하면 전체 스크립트가 다시 실행됨
number = st.slider('숫자 선택', 0, 10)
st.write(f'선택한 숫자: {number}')
```

**중요:** 슬라이더를 움직일 때마다 **전체 스크립트가 처음부터 다시 실행됨**!

---

## 2. Magic Commands (마법 명령어)

Streamlit은 변수나 값을 그냥 쓰기만 해도 자동으로 화면에 표시하는 "Magic Commands"를 지원함.

```python
import streamlit as st
import pandas as pd

# Magic Commands - st.write() 없이도 자동 표시됨!
"""
# 제목입니다
이것은 마법 명령어 예제입니다.
"""

# 변수를 그냥 쓰면 자동으로 표시됨
x = 10
x  # st.write(x)와 동일

# DataFrame도 자동 표시
df = pd.DataFrame({
    'A': [1, 2, 3],
    'B': [4, 5, 6]
})
df  # st.dataframe(df)와 동일

# 계산 결과도 자동 표시
2 + 2  # 4가 표시됨
```

**특징:**
- 변수나 리터럴 값이 **단독으로 한 줄**에 있으면 자동으로 `st.write()`가 호출됨
- 코드가 더 간결해지고 읽기 쉬워짐

---

## 3. st.write() - 만능 출력 함수

`st.write()`는 거의 모든 것을 표시할 수 있는 만능 함수임.

```python
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. 텍스트
st.write('Hello World!')

# 2. 마크다운
st.write('**굵은 글씨**, *기울임*, `코드`')

# 3. 숫자
st.write(1234)

# 4. 여러 인자
st.write('숫자:', 42, '문자열:', 'Hello')

# 5. DataFrame
df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
st.write(df)

# 6. 딕셔너리
st.write({'name': '홍길동', 'age': 30})

# 7. Matplotlib Figure
fig, ax = plt.subplots()
ax.plot([1, 2, 3])
st.write(fig)
```

**장점:** 데이터 타입을 자동으로 인식하여 적절한 형태로 표시함!

---

## 4. 위젯을 변수처럼 사용하기

Streamlit의 위젯은 **변수처럼** 사용할 수 있음.

```python
import streamlit as st

# 위젯의 반환값을 변수에 저장
name = st.text_input('이름을 입력하세요')
age = st.slider('나이를 선택하세요', 0, 100, 25)
agree = st.checkbox('동의합니다')

# 변수를 바로 사용
if agree:
    st.write(f'{name}님은 {age}살입니다.')
else:
    st.write('동의가 필요합니다.')
```

**작동 원리:**
1. 첫 실행: 위젯이 기본값으로 초기화됨
2. 사용자가 위젯 조작: 스크립트가 처음부터 다시 실행됨
3. 위젯의 현재 값이 변수에 할당됨

---

## 5. Session State (세션 상태)

`st.session_state`를 사용하면 재실행 간에도 데이터를 유지할 수 있음.

### 5.1 기본 사용법

```python
import streamlit as st

# Session State 초기화
if 'count' not in st.session_state:
    st.session_state.count = 0

# 버튼 클릭 시 카운트 증가
if st.button('클릭'):
    st.session_state.count += 1

st.write(f'버튼 클릭 횟수: {st.session_state.count}')
```

### 5.2 위젯에 key 지정하기

```python
import streamlit as st

# key를 지정하면 자동으로 session_state에 저장됨
st.text_input('이름', key='user_name')

# 어디서든 접근 가능
if st.session_state.user_name:
    st.write(f'안녕하세요, {st.session_state.user_name}님!')
```

### 5.3 Session State 활용 예제

```python
import streamlit as st

# 장바구니 예제
if 'cart' not in st.session_state:
    st.session_state.cart = []

item = st.text_input('상품 이름')
if st.button('장바구니에 추가'):
    if item:
        st.session_state.cart.append(item)

st.write('### 장바구니')
for i, product in enumerate(st.session_state.cart):
    st.write(f'{i+1}. {product}')
```

**주요 특징:**
- 재실행 간에도 데이터 유지됨
- 딕셔너리처럼 사용 가능함
- 위젯의 `key` 파라미터로 자동 저장 가능함

---

## 6. Callbacks (콜백 함수)

위젯의 값이 변경될 때 특정 함수를 실행할 수 있음.

```python
import streamlit as st

# 콜백 함수 정의
def update_name():
    st.session_state.full_name = f"{st.session_state.first_name} {st.session_state.last_name}"

# 위젯에 콜백 연결
st.text_input('이름', key='first_name', on_change=update_name)
st.text_input('성', key='last_name', on_change=update_name)

# 결과 표시
if 'full_name' in st.session_state:
    st.write(f'전체 이름: {st.session_state.full_name}')
```

**콜백 실행 순서:**
1. 위젯 값 변경
2. 콜백 함수 실행 (스크립트보다 먼저!)
3. 스크립트 재실행

**사용 가능한 콜백 파라미터:**
- `on_change`: 값이 변경될 때 실행
- `on_click`: 버튼 클릭 시 실행

---

## 7. 조건부 렌더링

조건문을 사용하여 동적으로 UI를 구성할 수 있음.

```python
import streamlit as st

# 로그인 상태 관리
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    st.write('환영합니다!')
    if st.button('로그아웃'):
        st.session_state.logged_in = False
        st.rerun()  # 즉시 재실행
else:
    st.write('로그인이 필요합니다.')
    username = st.text_input('사용자명')
    password = st.text_input('비밀번호', type='password')
    
    if st.button('로그인'):
        if username == 'admin' and password == '1234':
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error('로그인 실패!')
```

**활용 예시:**
- 로그인/로그아웃 화면 전환
- 단계별 폼 (Step 1, Step 2, ...)
- 권한에 따른 UI 표시/숨김

---

## 8. st.rerun() - 강제 재실행

특정 시점에 스크립트를 강제로 재실행할 수 있음.

```python
import streamlit as st
import time

if st.button('3초 후 재실행'):
    with st.spinner('대기 중...'):
        time.sleep(3)
    st.rerun()  # 스크립트 재실행
```

**사용 시나리오:**
- 상태 변경 후 즉시 UI 업데이트
- 데이터 새로고침
- 페이지 전환

---

## 9. 폼(Form) 사용하기

여러 입력을 모아서 한 번에 제출할 수 있음.

```python
import streamlit as st

# 폼 생성
with st.form('my_form'):
    st.write('회원가입')
    name = st.text_input('이름')
    email = st.text_input('이메일')
    age = st.number_input('나이', min_value=0, max_value=120)
    
    # 폼 제출 버튼 (필수!)
    submitted = st.form_submit_button('제출')
    
    if submitted:
        st.write(f'이름: {name}')
        st.write(f'이메일: {email}')
        st.write(f'나이: {age}')
```

**특징:**
- 폼 안의 위젯을 변경해도 스크립트가 재실행되지 않음
- `form_submit_button`을 클릭해야만 재실행됨
- 여러 입력을 받을 때 성능이 좋아짐

**폼 사용 규칙:**
- 폼 안에는 반드시 `st.form_submit_button`이 있어야 함
- 폼은 중첩될 수 없음
- 폼 안에서는 일부 위젯 사용 불가 (예: `st.button`)

---

## 10. 캐싱 (@st.cache_data)

데이터 로딩이나 계산이 오래 걸리는 함수는 캐싱하여 성능을 향상시킬 수 있음.

```python
import streamlit as st
import pandas as pd
import time

@st.cache_data
def load_data():
    # 시간이 오래 걸리는 작업
    time.sleep(3)
    df = pd.DataFrame({
        'A': range(1000),
        'B': range(1000, 2000)
    })
    return df

# 첫 실행: 3초 소요
# 이후 실행: 즉시 반환 (캐시된 결과 사용)
data = load_data()
st.write(data)
```

**캐싱 종류:**
- `@st.cache_data`: 데이터를 캐싱함 (DataFrame, 리스트 등)
- `@st.cache_resource`: 리소스를 캐싱함 (DB 연결, ML 모델 등)

**캐시 초기화:**
```python
# 특정 함수의 캐시 초기화
load_data.clear()

# 모든 캐시 초기화
st.cache_data.clear()
```

---

## 11. 주요 문법 정리표

| 기능 | 문법 | 설명 |
|------|------|------|
| **텍스트 출력** | `st.write()` | 만능 출력 함수 |
| **제목** | `st.title()` | 큰 제목 |
| **헤더** | `st.header()` | 중간 제목 |
| **서브헤더** | `st.subheader()` | 작은 제목 |
| **마크다운** | `st.markdown()` | 마크다운 형식 |
| **코드** | `st.code()` | 코드 블록 표시 |
| **구분선** | `st.divider()` | 수평선 |
| **버튼** | `st.button()` | 클릭 버튼 |
| **체크박스** | `st.checkbox()` | 체크박스 |
| **라디오** | `st.radio()` | 라디오 버튼 |
| **선택박스** | `st.selectbox()` | 드롭다운 |
| **다중선택** | `st.multiselect()` | 다중 선택 |
| **슬라이더** | `st.slider()` | 슬라이더 |
| **텍스트 입력** | `st.text_input()` | 한 줄 입력 |
| **텍스트 영역** | `st.text_area()` | 여러 줄 입력 |
| **숫자 입력** | `st.number_input()` | 숫자 입력 |
| **날짜 입력** | `st.date_input()` | 날짜 선택 |
| **파일 업로드** | `st.file_uploader()` | 파일 업로드 |
| **DataFrame** | `st.dataframe()` | 인터랙티브 테이블 |
| **차트** | `st.line_chart()` | 라인 차트 |
| **Plotly** | `st.plotly_chart()` | Plotly 차트 |
| **컬럼** | `st.columns()` | 컬럼 레이아웃 |
| **사이드바** | `st.sidebar` | 사이드바 |
| **탭** | `st.tabs()` | 탭 |
| **확장** | `st.expander()` | 접을 수 있는 영역 |
| **폼** | `st.form()` | 폼 |
| **세션 상태** | `st.session_state` | 상태 저장 |
| **재실행** | `st.rerun()` | 강제 재실행 |
| **캐싱** | `@st.cache_data` | 데이터 캐싱 |

---

## 12. 개발 워크플로우

**권장 작업 방식:**
1. 코드 에디터와 브라우저를 나란히 배치함
2. 코드를 수정하고 저장함
3. Streamlit이 변경을 감지하고 "Rerun" 버튼 표시함
4. "Always rerun" 선택하면 자동으로 재실행됨
5. 결과를 즉시 확인하고 다시 수정함

**빠른 개발 사이클:**
```
코드 작성 → 저장 → 자동 재실행 → 결과 확인 → 코드 수정 → ...
```

이러한 빠른 피드백 루프가 Streamlit의 가장 큰 장점임!

---

## 13. 실전 예제: 간단한 계산기

모든 개념을 활용한 종합 예제:

```python
import streamlit as st

st.title('🧮 간단한 계산기')

# Session State 초기화
if 'history' not in st.session_state:
    st.session_state.history = []

# 폼으로 입력 받기
with st.form('calculator_form'):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        num1 = st.number_input('첫 번째 숫자', value=0.0)
    
    with col2:
        operation = st.selectbox('연산', ['+', '-', '×', '÷'])
    
    with col3:
        num2 = st.number_input('두 번째 숫자', value=0.0)
    
    submitted = st.form_submit_button('계산')
    
    if submitted:
        # 계산 수행
        if operation == '+':
            result = num1 + num2
        elif operation == '-':
            result = num1 - num2
        elif operation == '×':
            result = num1 * num2
        elif operation == '÷':
            if num2 != 0:
                result = num1 / num2
            else:
                st.error('0으로 나눌 수 없습니다!')
                result = None
        
        # 결과 표시 및 히스토리 저장
        if result is not None:
            st.success(f'결과: {num1} {operation} {num2} = {result}')
            st.session_state.history.append(f'{num1} {operation} {num2} = {result}')

# 계산 히스토리 표시
if st.session_state.history:
    with st.expander('계산 히스토리'):
        for i, calc in enumerate(reversed(st.session_state.history), 1):
            st.write(f'{i}. {calc}')
    
    if st.button('히스토리 초기화'):
        st.session_state.history = []
        st.rerun()
```

---

## 📚 핵심 개념 요약

1. **Data Flow**: 위에서 아래로 실행, 위젯 변경 시 전체 재실행
2. **Magic Commands**: 변수만 써도 자동 표시
3. **st.write()**: 만능 출력 함수
4. **위젯**: 변수처럼 사용 가능
5. **Session State**: 재실행 간 데이터 유지
6. **Callbacks**: 위젯 변경 시 함수 실행
7. **조건부 렌더링**: 동적 UI 구성
8. **st.rerun()**: 강제 재실행
9. **Form**: 여러 입력 한 번에 제출
10. **Caching**: 성능 최적화

---

## 🔗 참고 자료

- Streamlit 공식 문서: https://docs.streamlit.io/
- API Reference: https://docs.streamlit.io/develop/api-reference
- Main Concepts: https://docs.streamlit.io/get-started/fundamentals/main-concepts
