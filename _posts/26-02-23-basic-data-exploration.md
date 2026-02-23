---
layout: single
title:  "[Kaggle] 기초 데이터 탐색 (Basic Data Exploration) 번역 및 정리"
date:   2026-02-23
categories: [Machine Learning, Data Science, Kaggle]
tags: [Kaggle, 머신러닝, Pandas, 데이터분석, 튜토리얼]
author_profile: false
---

![Basic Data Exploration](/assets/images/26-02-23/basic_data_exploration_pandas.png)

## 📌 기초 데이터 탐색 (Basic Data Exploration)

머신러닝 프로젝트의 첫 번째 단계는 데이터에 익숙해지는 것임. 이를 위해 데이터 과학자들이 가장 많이 사용하는 도구인 **Pandas** 라이브러리를 사용하게 됨.

---

### 1️⃣ Pandas를 사용하여 데이터와 친숙해지기 (Using Pandas to Get Familiar With Your Data)

데이터 프로젝트의 시작은 데이터를 불러오고 구조를 파악하는 것임. Pandas는 데이터를 탐색하고 조작하는 데 핵심적인 역할을 함. 보통 코드에서는 `pd`라는 약칭으로 사용함.

```python
import pandas as pd
```

Pandas 라이브러리의 핵심은 **데이터프레임(DataFrame)**임. 데이터프레임은 통계적으로 표(Table) 형식의 데이터라고 생각하면 쉬움. 엑셀 시트나 SQL의 테이블과 유사한 구조임.

이 예제에서는 멜버른의 주택 가격 데이터를 사용함.

```python
# 파일 경로 설정 (데이터 접근을 용이하게 하기 위해 변수에 저장)
melbourne_file_path = '../input/melbourne-housing-snapshot/melb_data.csv'

# 데이터를 읽어와서 DataFrame에 저장
melbourne_data = pd.read_csv(melbourne_file_path) 

# 데이터 요약 정보 출력
melbourne_data.describe()
```

---

### 2️⃣ 데이터 설명 해석하기 (Interpreting Data Description)

`describe()` 함수를 실행하면 데이터셋의 각 수치형 열(Column)에 대해 8가지 통계 수치가 나타남. 각 항목이 의미하는 바는 다음과 같음.

*   **count (개수):** 결측치(Missing Values)를 제외하고 데이터가 존재하는 행의 개수를 의미함. 결측치는 여러 이유로 발생할 수 있음. 예를 들어, 방이 1개인 집을 조사할 때 '두 번째 침실의 크기'는 수집되지 않았을 수 있음.
*   **mean (평균):** 해당 열 값들의 산술 평균임.
*   **std (표준편차):** 값이 평균에서 얼마나 퍼져 있는지를 나타내는 수치임.
*   **min (최솟값):** 해당 열에서 가장 작은 값임.
*   **25%, 50%, 75% (백분위수):** 데이터를 크기 순으로 정렬했을 때 해당 위치에 있는 값임. 
    *   **25% (1사분위수):** 데이터의 25%가 이 값보다 작거나 같음.
    *   **50% (중앙값):** 데이터의 딱 중간에 위치한 값임. 평균과는 다를 수 있음.
    *   **75% (3사분위수):** 데이터의 75%가 이 값보다 작거나 같음.
*   **max (최댓값):** 해당 열에서 가장 큰 값임.

이러한 통계 요약 수치들을 통해 데이터의 전반적인 분포와 극단적인 이상치(Outlier) 여부를 빠르게 파악할 수 있음.

---

### 💪 직접 해보기 (Your Turn)

자세한 데이터 탐색 이론을 배웠으니 실제 데이터를 가지고 직접 코딩을 해 볼 차례임. 멜버른 데이터 대신 아이오와(Iowa)주의 주택 가격 데이터를 사용하여 직접 데이터를 로드하고 통계를 확인해 보길 바람.

---

### 📋 요약

1.  **데이터 로드:** `pd.read_csv()`를 사용하여 CSV 파일을 데이터프레임으로 불러옴.
2.  **데이터 요약:** `describe()` 명령어로 데이터의 전반적인 기술 통계량을 확인함.
3.  **결측치 인식:** 통계값 중 `count` 수치를 다른 열들과 비교해 보며 데이터가 비어있는 부분을 파악하는 것이 중요함.

이 다음 단계에서는 모델을 학습시키기 위해 수많은 데이터 중 특정한 데이터를 선택하고 필터링하는 방법을 배울 것임.
