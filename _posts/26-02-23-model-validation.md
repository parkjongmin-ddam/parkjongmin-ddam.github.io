---
layout: single
title:  "[Kaggle] 모델 검증 (Model Validation) 번역 및 정리"
date:   2026-02-23
categories: [Machine Learning, Data Science, Kaggle]
tags: [Kaggle, 머신러닝, MAE, 모델검증, 데이터분석, 튜토리얼]
author_profile: false
---

## 📌 모델 검증 (Model Validation)

첫 번째 인공지능 모델을 성공적으로 구축했음. 하지만 만든 모델의 성능이 얼마나 좋은지 어떻게 평가할 수 있을까? 

이 단원에서는 모델의 품질을 객관적으로 측정하는 데 필수적인 **모델 검증(Model Validation)**에 대해 다룸. 모델의 성능을 정확히 측정하는 것은 모델을 지속적으로 개선해 나가는 과정의 핵심임.

---

### 1️⃣ 모델 검증이란 무엇인가?

대부분의 경우 모델 품질을 나타내는 지표로 **평균 절대 오차(Mean Absolute Error, 줄여서 MAE)**를 사용함. 먼저 MAE의 마지막 단어인 '오차(Error)'부터 이해해 보도록 함.

각 주택에 대한 오차는 다음과 같이 계산됨:
> **오차(Error)** = 실제 가격(Actual Price) - 예측 가격(Predicted Price)

예를 들어, 어떤 집의 실제 가격이 $150,000인데 모델이 $100,000으로 예측했다면 오차는 $50,000이 됨.

MAE는 각 예측 오차의 절대값(음수를 양수로 바꾼 값)을 모두 취한 뒤, 그 절대값들의 평균을 구해 계산함. 즉, **"이 모델의 예측은 평균적으로 약 X 달러 정도 빗나간다"**라는 직관적인 의미를 가짐.

pandas와 scikit-learn을 이용해 MAE를 계산하는 방법은 다음과 같음.

```python
import pandas as pd

# 데이터 로드
melbourne_file_path = '../input/melbourne-housing-snapshot/melb_data.csv'
melbourne_data = pd.read_csv(melbourne_file_path) 
# 결측치 제거
filtered_melbourne_data = melbourne_data.dropna(axis=0)

# 타겟(y)과 특성(X) 분리
y = filtered_melbourne_data.Price
melbourne_features = ['Rooms', 'Bathroom', 'Landsize', 'BuildingArea', 'YearBuilt', 'Lattitude', 'Longtitude']
X = filtered_melbourne_data[melbourne_features]

from sklearn.tree import DecisionTreeRegressor
# 모델 정의 및 학습(Fitting)
melbourne_model = DecisionTreeRegressor()
melbourne_model.fit(X, y)
```

이제 `mean_absolute_error` 함수를 사용해 오차를 계산함.

```python
from sklearn.metrics import mean_absolute_error

# 기존 학습 데이터(X)에 대한 예측값 생성
predicted_home_prices = melbourne_model.predict(X)
# 실제 가격(y)과 예측값 간의 MAE 계산
print(mean_absolute_error(y, predicted_home_prices))
```

---

### 2️⃣ '인샘플(In-Sample)' 점수의 심각한 문제점

방금 계산한 방식(모델을 훈련시킬 때 쓴 데이터로 다시 예측을 수행해 오차를 구하는 방식)을 **'인샘플(In-Sample)'** 점수라고 함. 이는 모델 평가에 있어 매우 큰 오류를 범하는 것임.

*   **문제 예시:** 부동산 데이터셋에 우연히도 '문 색깔이 초록색'인 집들이 유독 최고가에 팔린 기록만 있었다고 가정해 봄. 모델은 이 패턴을 학습하여 "초록색 문 = 무조건 비싼 집"이라는 공식을 만들어냄.
*   학습 데이터(=인샘플) 안에서는 이 규칙이 완벽하게 들어맞기 때문에, 모델의 정확도는 엄청나게 높게 나옴. 
*   하지만 실제 부동산 시장에서 문 색깔은 가격과 무관함. 이 모델에 한 번도 본 적 없는 새로운 데이터(다른 지역의 초록색 문 집)를 입력하면 터무니없는 가격을 예측하게 됨.

모델의 실질적인 가치는 **'새로운 데이터에 대한 예측 능력'**에 있음. 따라서 모델 훈련에 사용되지 않은 별도의 데이터를 통해 성과를 측정해야 함. 이를 **검증 데이터(Validation Data)**라고 부름.

---

### 3️⃣ 데이터 분할: 훈련용(Train)과 검증용(Validation)

위 문제를 해결하기 위한 가장 간단한 방법은 무작위로 데이터를 두 그룹으로 나누는 것임. 
*   일부 데이터로만 모델을 구축(**훈련 데이터**)
*   나머지 제외해둔 데이터로 모델의 성능을 테스트(**검증 데이터**)

`scikit-learn` 라이브러리는 `train_test_split`이라는 아주 유용한 함수를 제공하여 이 데이터 분할 작업을 쉽게 처리해 줌.

```python
from sklearn.model_selection import train_test_split

# 특징(X)과 타겟(y) 데이터를 훈련용(train)과 검증용(val)으로 무작위 분할함
# random_state 값을 지정하면 코드를 실행할 때마다 항상 같은 데이터가 동일하게 분할됨 (재현성 확보)
train_X, val_X, train_y, val_y = train_test_split(X, y, random_state = 0)

# 1. 훈련 데이터(train_X, train_y)로만 모델을 훈련시킴
melbourne_model = DecisionTreeRegressor()
melbourne_model.fit(train_X, train_y)

# 2. 훈련에 사용하지 않은 검증 데이터(val_X)로 예측 생성
val_predictions = melbourne_model.predict(val_X)

# 3. 실제 검증 데이터(val_y)와 예측값 간의 진짜 MAE 계산
print(mean_absolute_error(val_y, val_predictions))
```

### 🔬 결과 비교의 충격 (Wow!)
*   **인샘플(In-Sample) MAE:** 약 500달러 (거의 오차가 없음!)
*   **아웃오브샘플(Out-of-Sample) MAE (검증 분할 후):** 약 250,000달러 이상

인샘플 데이터를 사용할 땐 모델이 가격을 완벽히 맞추는 줄 알았지만, 실제 한 번도 못 본 데이터(검증 데이터)를 주자 평균 예측치가 25만 달러(약 3억 원 이상)나 빗나갔음. 실무 환경에선 전혀 쓸모없는 모델이었다는 뜻임.

이러한 현상이 발생하는 원인과 이를 모델 개선에 어떻게 활용할 수 있는지(Underfitting과 Overfitting)에 대해 다음 튜토리얼에서 다룰 것임.
