---
layout: single
title: "Streamlit Session State 완벽 가이드"
categories: ["Dev", "Streamlit"]
permalink: "/streamlit/Streamlit_Session/"
tag: [Python, Streamlit, Session-State, Web-Development]
toc: true
toc_sticky: true
author_profile: false
sidebar:
  nav: "docs"
header:
  teaser: /assets/images/session_state_dashboard.png
---

# 📦 Streamlit Session State 완벽 가이드

## 🎯 개요

Streamlit Session State는 웹 애플리케이션에서 사용자별 세션 데이터를 저장하고 관리하는 핵심 메커니즘임. 페이지가 다시 실행되어도 데이터를 유지할 수 있게 해주어 인터랙티브한 애플리케이션 개발을 가능하게 함.

이 프로젝트는 Session State의 개념부터 실전 활용까지 6가지 인터랙티브 예제로 학습할 수 있도록 설계된 교육용 대시보드임.

![Session State Dashboard](/assets/images/session_state_dashboard.png)

---

## 🔄 Streamlit 실행 모델 이해하기

### 기본 동작 방식

Streamlit은 사용자가 위젯과 상호작용할 때마다 **전체 스크립트를 처음부터 다시 실행**함. 이는 Streamlit의 핵심 철학이지만, 동시에 데이터 유지의 문제를 야기함.

```python
# 매번 재실행됨
count = 0  # 항상 0으로 초기화됨
if st.button("증가"):
    count += 1  # 버튼을 눌러도 다음 실행 시 다시 0이 됨
st.write(count)  # 항상 0 출력
```

### 문제점

- 변수가 매번 초기화됨
- 이전 상태를 기억할 수 없음
- 사용자 입력이 유지되지 않음

### Session State의 해결책

Session State를 사용하면 **재실행 간에 데이터를 유지**할 수 있음.

```python
# Session State 사용
if 'count' not in st.session_state:
    st.session_state.count = 0

if st.button("증가"):
    st.session_state.count += 1

st.write(st.session_state.count)  # 증가된 값이 유지됨
```

![Session State Concept](/assets/images/session_state_concept.png)

---

## 💡 Session State 핵심 개념

### 1. 딕셔너리 형태

`st.session_state`는 Python 딕셔너리처럼 동작함.

```python
# 딕셔너리 스타일
st.session_state['key'] = 'value'
value = st.session_state['key']

# 속성 스타일 (권장)
st.session_state.key = 'value'
value = st.session_state.key
```

### 2. 초기화 패턴

Session State를 사용하기 전에 반드시 초기화가 필요함.

![Initialization Patterns](/assets/images/initialization_patterns.png)

#### 패턴 1: if 문 사용

```python
if 'counter' not in st.session_state:
    st.session_state.counter = 0
```

**장점**: 명시적이고 이해하기 쉬움  
**사용 사례**: 단순한 조건부 초기화

#### 패턴 2: setdefault 사용

```python
st.session_state.setdefault('counter', 0)
```

**장점**: 간결하고 Pythonic함  
**사용 사례**: 한 줄로 기본값 설정

#### 패턴 3: 초기화 함수

```python
def initialize_session_state():
    """Session State 초기화"""
    defaults = {
        'count': 0,
        'logged_in': False,
        'data': []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# 스크립트 시작 시 호출
initialize_session_state()
```

**장점**: 재사용 가능하고 관리가 용이함  
**사용 사례**: 복잡한 애플리케이션에서 여러 상태를 한 번에 초기화

### 3. 데이터 타입

모든 Python 객체를 저장할 수 있음.

```python
# 기본 타입
st.session_state.number = 42
st.session_state.text = "Hello"
st.session_state.flag = True

# 컬렉션
st.session_state.items = [1, 2, 3]
st.session_state.data = {'key': 'value'}

# 객체
st.session_state.df = pd.DataFrame()
st.session_state.model = trained_model
```

---

## 🎨 6가지 실습 예제

### 1. 🔢 카운터 (난이도: ⭐)

**학습 목표**: 기본적인 Session State 사용법

#### 기능
- ➕ 증가: 카운터 값을 1 증가시킴
- ➖ 감소: 카운터 값을 1 감소시킴
- 🔄 초기화: 카운터를 0으로 리셋함
- 📊 히스토리: 모든 클릭 기록을 확인함

#### 핵심 코드

```python
if 'counter' not in st.session_state:
    st.session_state.counter = 0
    st.session_state.click_history = []

def increment():
    st.session_state.counter += 1
    st.session_state.click_history.append({
        'time': datetime.now().timestamp(),
        'action': 'increment',
        'value': st.session_state.counter
    })

st.button("증가", on_click=increment)
st.metric("현재 카운트", st.session_state.counter)
```

#### 학습 포인트
- Session State 초기화 패턴
- 콜백 함수 활용
- 히스토리 데이터 저장

---

### 2. 🔐 로그인 시스템 (난이도: ⭐⭐)

**학습 목표**: 인증 상태 관리

#### 기능
- 🔓 로그인: 사용자 인증 (테스트 비밀번호: 1234)
- 🔒 로그아웃: 세션 종료
- ⏱️ 로그인 시간 추적: 세션 지속 시간 표시

#### 핵심 코드

```python
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ''
    st.session_state.login_time = None

if not st.session_state.logged_in:
    # 로그인 폼
    username = st.text_input("사용자 이름")
    password = st.text_input("비밀번호", type="password")
    
    if st.button("로그인"):
        if password == "1234":
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.login_time = datetime.now()
            st.rerun()
else:
    # 로그인 후 화면
    st.success(f"환영합니다, {st.session_state.username}님!")
    
    if st.button("로그아웃"):
        st.session_state.logged_in = False
        st.session_state.username = ''
        st.session_state.login_time = None
        st.rerun()
```

#### 학습 포인트
- 조건부 UI 렌더링
- `st.rerun()` 활용
- 시간 데이터 저장

---

### 3. 🛒 쇼핑 카트 (난이도: ⭐⭐)

**학습 목표**: 리스트 데이터 관리

#### 기능
- ➕ 상품 추가: 장바구니에 상품 추가
- ❌ 상품 제거: 개별 상품 삭제
- 🗑️ 장바구니 비우기: 전체 삭제
- 💳 결제: 결제 처리 및 초기화

#### 핵심 코드

```python
if 'cart' not in st.session_state:
    st.session_state.cart = []
    st.session_state.total_price = 0

# 상품 추가
if st.button(f"추가 - {product}"):
    st.session_state.cart.append({
        'product': product,
        'price': price,
        'time': datetime.now().strftime("%H:%M:%S")
    })
    st.session_state.total_price += price
    st.rerun()

# 총 금액 계산
total = sum(item['price'] for item in st.session_state.cart)
st.metric("총 금액", f"{total:,}원")
```

#### 학습 포인트
- 리스트 데이터 추가/삭제
- 동적 UI 생성
- 실시간 계산

---

### 4. 📝 다단계 설문조사 (난이도: ⭐⭐⭐)

**학습 목표**: 다단계 프로세스 관리

#### 기능
- **1단계**: 기본 정보 입력 (이름, 나이)
- **2단계**: 선호도 조사 (색상, 음식)
- **3단계**: 의견 수집 (피드백, 만족도)
- **4단계**: 결과 확인 및 JSON 출력

#### 핵심 코드

```python
if 'survey_step' not in st.session_state:
    st.session_state.survey_step = 1
    st.session_state.survey_data = {}

# 진행 상황 표시
progress = (st.session_state.survey_step - 1) / 3
st.progress(progress)

if st.session_state.survey_step == 1:
    # 1단계 UI
    name = st.text_input("이름")
    age = st.number_input("나이", min_value=0)
    
    if st.button("다음"):
        st.session_state.survey_data['name'] = name
        st.session_state.survey_data['age'] = age
        st.session_state.survey_step = 2
        st.rerun()

elif st.session_state.survey_step == 2:
    # 2단계 UI
    favorite_color = st.selectbox("좋아하는 색상", ["빨강", "파랑", "초록"])
    
    if st.button("다음"):
        st.session_state.survey_data['favorite_color'] = favorite_color
        st.session_state.survey_step = 3
        st.rerun()
```

#### 학습 포인트
- 단계별 UI 전환
- 데이터 누적 저장
- 진행 상황 표시

---

### 5. ✅ To-Do 리스트 (난이도: ⭐⭐⭐)

**학습 목표**: CRUD 작업 구현

#### 기능
- ➕ 할 일 추가: 새 항목 생성
- ✅ 완료 체크: 상태 토글
- 🗑️ 삭제: 개별/완료/전체 삭제
- 📊 통계: 전체/완료/대기 개수

#### 핵심 코드

```python
if 'todos' not in st.session_state:
    st.session_state.todos = []
    st.session_state.todo_id_counter = 0

# 추가
if st.button("추가"):
    st.session_state.todos.append({
        'id': st.session_state.todo_id_counter,
        'text': new_todo,
        'completed': False,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    st.session_state.todo_id_counter += 1
    st.rerun()

# 완료 토글
completed = st.checkbox("완료", value=todo['completed'], key=f"todo_{todo['id']}")
if completed != todo['completed']:
    st.session_state.todos[idx]['completed'] = completed
    st.rerun()

# 삭제
if st.button("삭제", key=f"delete_{todo['id']}"):
    st.session_state.todos.pop(idx)
    st.rerun()
```

#### 학습 포인트
- 고유 ID 관리
- 체크박스 상태 동기화
- 필터링 및 통계

---

### 6. 📄 폼 데이터 관리 (난이도: ⭐⭐)

**학습 목표**: 복잡한 폼 데이터 저장

#### 기능
- 💾 저장: 폼 데이터를 Session State에 저장
- 🔄 초기화: 폼 데이터 삭제
- 📋 미리보기: 저장된 데이터 확인
- 🔁 복원: 저장된 데이터로 폼 채우기

#### 핵심 코드

```python
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}

# 저장된 값으로 초기화
name = st.text_input(
    "이름",
    value=st.session_state.form_data.get('name', '')
)

email = st.text_input(
    "이메일",
    value=st.session_state.form_data.get('email', '')
)

# 저장
if st.button("저장"):
    st.session_state.form_data = {
        'name': name,
        'email': email,
        'saved_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    st.success("저장되었습니다!")
```

#### 학습 포인트
- 딕셔너리 데이터 관리
- 폼 값 복원
- 날짜/시간 데이터 처리

---

## 🎨 콜백 함수와 Session State

### 콜백 함수

위젯이 변경될 때 자동으로 실행되는 함수를 지정할 수 있음.

```python
def increment():
    st.session_state.count += 1

if 'count' not in st.session_state:
    st.session_state.count = 0

# on_click 콜백
st.button("증가", on_click=increment)
st.write(st.session_state.count)
```

### 위젯 키와 자동 동기화

위젯에 `key`를 지정하면 자동으로 session_state와 동기화됨.

```python
# 위젯 값이 자동으로 session_state에 저장됨
name = st.text_input("이름", key="user_name")

# 다른 곳에서 접근 가능
st.write(f"저장된 이름: {st.session_state.user_name}")
```

---

## ⚠️ 주의사항

### 1. 키 충돌 방지

위젯의 `key`와 수동으로 설정한 session_state 키가 충돌하지 않도록 주의함.

```python
# ❌ 잘못된 예
st.session_state.name = "John"
st.text_input("이름", key="name")  # 충돌!

# ✅ 올바른 예
st.session_state.user_name = "John"
st.text_input("이름", key="input_name")
```

### 2. st.rerun() 사용

Session State를 변경한 후 즉시 UI를 업데이트하려면 `st.rerun()`을 호출함.

```python
if st.button("초기화"):
    st.session_state.count = 0
    st.rerun()  # 즉시 화면 갱신
```

### 3. 초기화 타이밍

Session State 초기화는 스크립트 상단에서 수행하는 것이 좋음.

```python
# ✅ 권장: 스크립트 상단
def initialize_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.count = 0
        st.session_state.data = []
        st.session_state.initialized = True

initialize_session_state()

# 나머지 코드...
```

---

## 🔍 디버깅

### Session State 내용 확인

```python
# 전체 session_state 출력
st.write("Session State:", st.session_state)

# 특정 키 존재 확인
if 'key' in st.session_state:
    st.write("키가 존재함")

# 모든 키 출력
st.write("모든 키:", list(st.session_state.keys()))
```

### 개발자 도구

```python
with st.expander("🔧 Session State 디버그"):
    st.json(dict(st.session_state))
```

---

## 📊 Session State vs 캐싱

| 특징 | Session State | Caching (@st.cache_data) |
|------|--------------|--------------------------|
| **목적** | 사용자별 상태 저장 | 계산 결과 재사용 |
| **범위** | 단일 세션 | 모든 사용자 공유 |
| **수명** | 세션 종료 시 삭제 | 캐시 만료 시까지 |
| **용도** | UI 상태, 사용자 입력 | 데이터 로딩, 모델 학습 |

---

## 💡 베스트 프랙티스

### 1. 초기화 함수 사용

```python
def initialize_session_state():
    """Session State 초기화"""
    defaults = {
        'count': 0,
        'logged_in': False,
        'page': 'home',
        'data': []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# 스크립트 시작 시 호출
initialize_session_state()
```

### 2. 네임스페이스 사용

```python
# 관련 데이터를 그룹화
if 'user' not in st.session_state:
    st.session_state.user = {
        'name': '',
        'email': '',
        'logged_in': False
    }

# 접근
st.session_state.user['name'] = "John"
```

### 3. 상태 초기화 함수

```python
def reset_state():
    """상태 초기화"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]

if st.button("전체 초기화"):
    reset_state()
    st.rerun()
```

---

## 🚀 프로젝트 구조

```
Session/
├── session_manager.py           # 🎯 메인 대시보드 (700+ 줄)
├── session_state_개념.md        # 📚 Session State 개념 설명
├── 실습가이드.md                # 🚀 실습 가이드
└── README.md                    # 📖 프로젝트 개요
```

---

## 🎯 학습 체크리스트

### 기본 (필수)
- [x] Session State 초기화 방법 이해
- [x] 값 읽기/쓰기 방법 이해
- [x] 콜백 함수 사용법 이해
- [x] 카운터 예제 완료

### 중급 (권장)
- [x] 리스트/딕셔너리 데이터 관리
- [x] 다단계 프로세스 구현
- [x] 조건부 UI 렌더링
- [x] 로그인 & 쇼핑 카트 예제 완료

### 고급 (선택)
- [x] 복잡한 상태 관리
- [x] 최적화 기법 적용
- [x] 디버깅 및 문제 해결
- [x] 모든 예제 완료 및 커스텀 예제 구현

---

## 🌟 프로젝트 하이라이트

### 교육적 가치
- 📚 **체계적인 학습**: 개념 → 기본 → 고급 순서
- 🎯 **실전 중심**: 6가지 실용적인 예제
- 🔍 **디버깅 도구**: 실시간 상태 확인

### 기술적 완성도
- 💻 **700+ 줄의 코드**: 주석과 구조화
- 🎨 **프리미엄 디자인**: 현대적인 UI/UX
- 🔧 **디버그 기능**: 개발자 친화적

### 실용적 가치
- 🚀 **즉시 활용 가능**: 실제 프로젝트에 적용
- 📖 **완벽한 문서화**: 개념부터 실습까지
- 🎓 **학습 로드맵**: 단계별 가이드

---

## 📈 활용 사례

### 1. 교육
- Streamlit 워크샵 교재
- 대학 강의 자료
- 온라인 튜토리얼

### 2. 개발
- 프로젝트 템플릿
- 코드 참고 자료
- 디버깅 도구

### 3. 프로토타이핑
- 빠른 UI 프로토타입
- 사용자 테스트
- 개념 증명 (PoC)

---

## 🔮 향후 계획

- [ ] 더 많은 예제 추가 (게임, 채팅 등)
- [ ] 영어 버전 문서
- [ ] 비디오 튜토리얼
- [ ] 고급 패턴 가이드
- [ ] 성능 최적화 팁

---

## 📚 참고 자료

### 공식 문서
- [Streamlit Session State](https://docs.streamlit.io/library/api-reference/session-state)
- [Session State 고급 기능](https://docs.streamlit.io/library/advanced-features/session-state)
- [Streamlit API Reference](https://docs.streamlit.io/library/api-reference)

### 커뮤니티
- [Streamlit 포럼](https://discuss.streamlit.io/)
- [Streamlit GitHub](https://github.com/streamlit/streamlit)
- [Streamlit Gallery](https://streamlit.io/gallery)

---

## 💻 실행 방법

### 1. 설치

```bash
# Streamlit 설치
pip install streamlit pandas
```

### 2. 실행

```bash
streamlit run session_manager.py
```

### 3. 접속

브라우저에서 `http://localhost:8501` 접속

---

## 🎨 UI/UX 디자인

### 색상 팔레트
- **메인 그라디언트**: `#667eea` → `#764ba2` (보라색 계열)
- **사이드바**: `#2d3748` → `#1a202c` (다크 그레이)
- **강조색**: `#667eea` (보라색)

### 스타일링 요소
- ✨ **그라디언트 배경**: 프리미엄 느낌
- 🌙 **다크 사이드바**: 가독성 향상
- 🎯 **커스텀 탭**: 선택된 탭 강조
- 💫 **호버 효과**: 버튼에 애니메이션

---

## 🎓 학습 로드맵

### 1단계: 개념 이해 (30분)
1. Session State의 필요성 이해
2. 기본 사용 패턴 학습
3. 초기화 방법 익히기

### 2단계: 기본 실습 (1시간)
1. **카운터 예제** 실습
2. **로그인 시스템** 실습
3. **쇼핑 카트** 실습

### 3단계: 고급 실습 (1.5시간)
1. **다단계 설문조사** 실습
2. **To-Do 리스트** 실습
3. **폼 데이터 관리** 실습

### 4단계: 응용 (자유)
1. 커스텀 예제 만들기
2. 실제 프로젝트에 적용
3. 고급 패턴 탐구

---

## 🎯 핵심 요약

1. **Session State는 필수**: Streamlit에서 상태 관리의 핵심 메커니즘임
2. **초기화가 중요**: 사용 전 반드시 초기화 필요
3. **콜백 활용**: 효율적인 상태 업데이트
4. **디버깅 도구**: 실시간 상태 확인으로 개발 효율 향상
5. **베스트 프랙티스**: 초기화 함수, 네임스페이스, 키 충돌 방지

---

**Made with ❤️ using Streamlit**

**2026-02-09**
