---
layout: single
title:  "[Kaggle] 첫 번째 머신러닝 모델 구축 (Your First ML Model) 번역 및 정리"
date:   2026-02-23
categories: [Machine Learning, Data Science, Kaggle]
tags: [Kaggle, 머신러닝, Scikit-learn, 의사결정나무, 데이터분석, 튜토리얼]
author_profile: false
---

![Your First ML Model](/assets/images/26-02-23/your_first_ml_model.png)

## 📌 첫 번째 머신러닝 모델 구축 (Your First Machine Learning Model)

이전 단계에서 Pandas를 이용해 데이터를 탐색하는 방법을 배웠음. 이제 그 데이터를 사용하여 본격적인 첫 번째 머신러닝 모델을 만들어 볼 단계임.

---

### 1️⃣ 모델링을 위한 데이터 선택 (Selecting Data for Modeling)

보유한 데이터셋에 변수가 너무 많아 한눈에 파악하기 힘든 경우, 직관을 사용하여 분석에 필요한 변수만 우선적으로 선택함. 추후에는 통계적 기법을 통해 자동으로 변수를 우선순위화하는 방법을 배우게 됨. Pandas의 `columns` 속성을 사용하여 데이터셋의 모든 열 목록을 먼저 확인함.

```python
import pandas as pd

melbourne_file_path = '../input/melbourne-housing-snapshot/melb_data.csv'
melbourne_data = pd.read_csv(melbourne_file_path)

# 데이터셋의 모든 열(컬럼) 이름 확인
melbourne_data.columns
```

일반적으로 결측치(Missing Values)를 처리하는 다양한 방법이 있지만, 이번 기초 튜토리얼에서는 편의상 결측치가 포함된 행을 모두 삭제(Drop)하는 방식을 취함.

```python
# 결측치(na)가 있는 행(axis=0)을 삭제
melbourne_data = melbourne_data.dropna(axis=0)
```

---

### 2️⃣ 예측 대상 선택 (Selecting The Prediction Target)

데이터셋 내에서 우리가 예측하고자 하는 변수(타겟)를 추출해야 함. 이를 위해 점 표기법(dot-notation)을 사용할 수 있음. 

이 단일 열은 Series 형태로 저장되며, 데이터를 분리할 때 **예측 대상을 담는 변수는 관례적으로 소문자 `y`를 사용함.** 멜버른 주택 데이터에서는 'Price'(가격) 열이 타겟이 됨.

```python
# 예측 타겟을 y로 설정
y = melbourne_data.Price
```

---

### 3️⃣ "특성" 선택 (Choosing "Features")

모델에 입력값으로 사용되어 예측을 돕는 변수들을 **"특성(Features)"**이라고 부름. 주택 가격 데이터의 경우 방의 개수, 욕실 개수, 대지 크기 등이 특성에 해당함.

대괄호 안에 원하는 열 이름들의 리스트를 넣어 여러 개의 특성을 한 번에 선택할 수 있음. 이 특성 데이터는 **관례적으로 대문자 `X`라고 부름.**

```python
# 모델 학습에 사용할 특성 리스트 정의
melbourne_features = ['Rooms', 'Bathroom', 'Landsize', 'Lattitude', 'Longtitude']

# 해당 특성들만 추출하여 X 변수에 저장
X = melbourne_data[melbourne_features]

# 데이터 확인을 위해 통계 요약과 첫 5개 행 출력
X.describe()
X.head()
```

---

### 4️⃣ 모델 구축 (Building Your Model)

모델을 구축하기 위해 파이썬 생태계에서 가장 대중적인 머신러닝 라이브러리인 **scikit-learn(sklearn)**을 사용함. 일반적으로 데이터프레임 구조를 다룰 때 pandas(`pd`)를 쓰는 것처럼 널리 쓰이는 표준 도구임.

모델을 구축하고 사용하는 일반적인 단계는 다음과 같음:
1.  **정의(Define):** 사용할 모델의 유형(예: 의사결정나무)과 내부 파라미터를 설정함.
2.  **피팅(Fit):** 제공된 데이터(X, y)에서 유의미한 패턴을 학습함. 모델 훈련의 핵심 부분임.
3.  **예측(Predict):** 학습된 모델에 새로운 데이터(혹은 다시 훈련 데이터)를 넣어 결과를 추론함.
4.  **평가(Evaluate):** 모델의 예측값이 아까 얼마나 정확한지 그 성능을 수치로 측정함.

다음은 scikit-learn을 이용해 의사결정나무 모델을 정의하고 훈련시키는 예제 코드임.

```python
from sklearn.tree import DecisionTreeRegressor

# 1. 모델 정의 (매번 동일한 결과를 얻기 위해 random_state를 1로 지정)
melbourne_model = DecisionTreeRegressor(random_state=1)

# 2. 모델 피팅 (X 데이터의 패턴을 학습하여 y를 예측하도록 훈련)
melbourne_model.fit(X, y)
```
*   `random_state`: 머신러닝 프로세스 중에는 난수 생성 과정이 포함되는 경우가 많음. 이 숫자를 고정해두면 코드를 실행할 때마다 결과가 달라지는 것을 막을 수 있음.

이제 모델 학습이 완료되었으니, 훈련 속성에 포함되었던 상위 5개 주택 데이터로 직접 예측을 실행하여 결과값을 눈으로 확인해 봄.

```python
print("다음 5개 주택 데이터에 대한 예측을 수행함:")
print(X.head())

print("예측 결과:")
# 3. 예측 수행
print(melbourne_model.predict(X.head()))
```

---

### 📋 요약 및 핵심
이 단원에서는 모델 구축의 기초 뼈대에 대해 배웠음. 
`scikit-learn`을 활용하여 예측 타겟(`y`)과 특성(`X`)을 나누고, 4단계 워크플로우(Define 👉 Fit 👉 Predict 👉 Evaluate)를 기반으로 **DecisionTreeRegressor**를 직접 훈련시키고 검증해 보았음. 

다음 모듈에서는 마지막 단계인 평가(Evaluate) 기법을 상세히 다루며 예측 정확도를 수학적으로 계산하는 방법을 익힐 예정임.
