---
layout: single
title:  "[Kaggle] 랜덤 포레스트 (Random Forests) 번역 및 정리"
date:   2026-02-23
categories: [Machine Learning, Data Science, Kaggle]
tags: [Kaggle, 머신러닝, 랜덤포레스트, Random Forest, 데이터분석, 튜토리얼]
author_profile: false
---

## 📌 랜덤 포레스트 (Random Forests)

이전 튜토리얼에서 의사 결정 나무(Decision Tree)의 깊이를 조절하며 과소적합과 과대적합 문제를 다루었음. 하지만 의사 결정 나무 자체는 본질적으로 어려운 선택의 문제를 남김. 

*   잎(leaf)이 많은 깊은 나무는 각 예측이 아주 적은 수의 주택 데이터에서 나오기 때문에 **과대적합(Overfitting)**될 가능성이 높음. 
*   반대로 잎이 적은 얕은 나무는 데이터의 특징을 충분히 잡아내지 못해 성능이 떨어지는 **과소적합(Underfitting)**이 발생함.

오늘날 가장 정교한 모델링 기술들도 과소적합과 과대적합 사이의 이러한 긴장 관계에 직면해 있음. 하지만 수많은 모델 중 더 나은 성능을 낼 수 있는 영리한 아이디어를 가진 모델이 있으며, 그 대표적인 예가 바로 **랜덤 포레스트(Random Forest)**임.

---

### 1️⃣ 랜덤 포레스트란?

랜덤 포레스트는 말 그대로 **"수많은 의사 결정 나무들이 모인 숲(Forest)"**임. 

하나의 나무 결과값에만 의존하는 것이 아니라, 무수히 많은 의사 결정 나무를 동시에 생성하여 각각 예측을 수행하게 함. 그리고 각 나무에서 나온 예측값들의 **평균**을 내어 최종 예측 결과를 도출함.

*   **장점:** 일반적으로 단일 의사 결정 나무보다 예측 정확도가 훨씬 뛰어남.
*   **특징:** 복잡한 튜닝 없이 기본 파라미터(default parameters)만으로도 상당히 좋은 성능을 냄. 머신러닝을 깊게 파고들면 성능이 더 뛰어난 복잡한 모델(XGBoost, LightGBM 등)을 배우게 되지만, 그런 모델들은 파라미터를 미세하게 조정하는 데 매우 민감함. 반면 랜덤 포레스트는 초보자가 다루기에도 매우 다루기 쉽고 강력함.

---

### 2️⃣ 예시 코드 및 구현 (Example)

이전 실습을 통해 데이터를 불러오고 타겟(`y`)과 특성(`X`)을 나눈 뒤 훈련용/검증용 데이터로 분할하는 코드는 이미 구성되어 있다고 가정함. (`train_X`, `val_X`, `train_y`, `val_y` 준비 완료)

`scikit-learn`에서 의사 결정 나무 모델을 만들었던 것과 거의 동일한 방식으로 랜덤 포레스트 모델을 구축할 수 있음. `DecisionTreeRegressor` 클래스 대신 `RandomForestRegressor` 클래스를 불러오기만 하면 됨.

```python
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from sklearn.ensemble import RandomForestRegressor

# 데이터 전처리 생략 (이전 예제와 동일)
# train_X, val_X, train_y, val_y 가 준비된 상태라고 가정함

# 1. 랜덤 포레스트 모델 정의 (결과 재현성을 위해 random_state 고정)
forest_model = RandomForestRegressor(random_state=1)

# 2. 훈련 데이터에 모델 피팅(학습)
forest_model.fit(train_X, train_y)

# 3. 검증 데이터로 주택 가격 예측 수행
melb_preds = forest_model.predict(val_X)

# 4. 검증 오차(MAE) 계산 및 출력
print(mean_absolute_error(val_y, melb_preds))
```

**출력 결과 (예상):**
`191669.7536453626`

---

### 📋 결론 (Conclusion)

최종 MAE 값이 약 19만 달러로 출력되었음. 이는 이전에 단일 의사 결정 나무 하나만 사용했을 때의 최고 성능(오차 약 25만 달러)에 비해 **정확도가 엄청나게 크게 향상된 수치임.**

물론 데이터를 더 정교하게 다듬거나 파라미터를 조정하여 개선할 여지는 남아있음. 단일 의사 결정 나무의 최대 깊이를 조절했던 것처럼, 랜덤 포레스트의 성능 역시 파라미터를 변경해 최적화할 수 있음. 

하지만 앞서 언급했듯이 랜덤 포레스트의 가장 큰 장점 중 하나는 별도의 복잡한 튜닝 노력 없이도 기본 상태에서 이미 꽤 훌륭한 성능을 보여준다는 점임. 실무에서도 빠르게 베이스라인(Baseline) 성능을 잡을 때 가장 즐겨 쓰는 모델이기도 함.
