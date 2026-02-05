---
layout: single
title: "Generative AI 10기 팀 프로젝트 2일차 - 데이터 수집 및 전처리"
categories: python
tag: [python, pandas, finance-datareader, data-preprocessing, stock-analysis, moving-average]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# 📥 2일차: 데이터 수집 및 전처리

## 🎯 학습 목표

2일차에는 FinanceDataReader를 활용하여 실제 주식 데이터를 수집하고, Pandas를 이용해 데이터를 전처리하는 과정을 학습함. 특히 이동평균선 계산과 거래량 색상 구분을 통해 데이터 분석의 기초를 다짐.

---

## 📊 데이터 수집 워크플로우

![데이터 수집 워크플로우](../images/2026-02-03/data_collection_workflow.png)

데이터 수집부터 전처리까지의 전체 과정을 시각화한 워크플로우임. FinanceDataReader API를 통해 원시 데이터를 수집하고, 이를 정제하여 이동평균선을 계산한 후 분석 가능한 형태로 출력함.

---

## 📥 데이터 수집 구현

### 기본 데이터 수집 코드

```python
import FinanceDataReader as fdr
import pandas as pd

# SK 하이닉스 데이터 수집
ticker = "000660"
start_date = "2025-01-01"
end_date = "2025-12-31"

df = fdr.DataReader(ticker, start_date, end_date)
print(f"데이터 수집 완료: {len(df)}건")
```

### 📋 수집된 데이터 구조

FinanceDataReader를 통해 수집한 데이터는 다음과 같은 컬럼으로 구성됨:

| 컬럼명 | 설명 | 데이터 타입 |
|--------|------|-------------|
| **Date** | 거래일 (인덱스) | datetime64 |
| **Open** | 시가 (장 시작 가격) | float64 |
| **High** | 고가 (당일 최고가) | float64 |
| **Low** | 저가 (당일 최저가) | float64 |
| **Close** | 종가 (장 마감 가격) | float64 |
| **Volume** | 거래량 | int64 |
| **Change** | 전일 대비 변동률 | float64 |

### 💡 데이터 확인

```python
# 데이터 기본 정보 확인
print(df.info())
print("\n" + "="*50 + "\n")

# 처음 5개 행 확인
print(df.head())
print("\n" + "="*50 + "\n")

# 기본 통계량 확인
print(df.describe())
```

**출력 예시**:
```
<class 'pandas.core.frame.DataFrame'>
DatetimeIndex: 245 entries, 2025-01-02 to 2025-12-30
Data columns (total 6 columns):
 #   Column  Non-Null Count  Dtype  
---  ------  --------------  -----  
 0   Open    245 non-null    float64
 1   High    245 non-null    float64
 2   Low     245 non-null    float64
 3   Close   245 non-null    float64
 4   Volume  245 non-null    int64  
 5   Change  245 non-null    float64
```

---

## 🔧 데이터 전처리

### 이동평균선(Moving Average) 계산

이동평균선은 주가의 평균값을 일정 기간 동안 계산하여 추세를 파악하는 기술적 지표임.

```python
# 이동평균선 계산
df['MA5'] = df['Close'].rolling(window=5).mean()   # 5일 이동평균
df['MA20'] = df['Close'].rolling(window=20).mean() # 20일 이동평균
df['MA60'] = df['Close'].rolling(window=60).mean() # 60일 이동평균

# 결과 확인
print(df[['Close', 'MA5', 'MA20', 'MA60']].tail(10))
```

### 📈 이동평균선의 의미

![이동평균선 설명](../images/2026-02-03/moving_averages_explanation.png)

각 이동평균선은 서로 다른 기간의 추세를 나타냄:

#### **MA 5 (5일 이동평균)**
- **별칭**: 심리선
- **의미**: 단기 추세 파악
- **특징**: 주가 변동에 민감하게 반응하며, 단기 매매 타이밍 포착에 활용
- **활용**: 5일선이 상승하면 단기 상승 추세, 하락하면 단기 하락 추세

#### **MA 20 (20일 이동평균)**
- **별칭**: 세력선, 생명선
- **의미**: 약 1개월(20 거래일) 평균
- **특징**: 중기 추세를 나타내며, 주가 지지선/저항선 역할
- **활용**: 주가가 20일선 위에 있으면 강세, 아래에 있으면 약세

#### **MA 60 (60일 이동평균)**
- **별칭**: 수급선
- **의미**: 약 3개월(60 거래일) 평균
- **특징**: 장기 추세를 나타내며, 주요 지지선/저항선
- **활용**: 60일선 돌파 시 장기 상승 전환 신호

### 🔍 Rolling 함수 이해하기

```python
# rolling() 함수의 동작 원리
# window=5: 최근 5개 데이터의 평균

# 예시 데이터
prices = [100, 102, 101, 103, 105, 107, 106]

# MA5 계산 과정
# 1일차: NaN (데이터 부족)
# 2일차: NaN (데이터 부족)
# 3일차: NaN (데이터 부족)
# 4일차: NaN (데이터 부족)
# 5일차: (100+102+101+103+105)/5 = 102.2
# 6일차: (102+101+103+105+107)/5 = 103.6
# 7일차: (101+103+105+107+106)/5 = 104.4
```

### ⚠️ NaN 값 처리

이동평균선 계산 시 초기 데이터는 NaN(결측치)이 발생함:

```python
# NaN 값 확인
print(f"MA5 NaN 개수: {df['MA5'].isna().sum()}")
print(f"MA20 NaN 개수: {df['MA20'].isna().sum()}")
print(f"MA60 NaN 개수: {df['MA60'].isna().sum()}")

# NaN 값 제거 (필요시)
df_clean = df.dropna()

# 또는 0으로 채우기
df_filled = df.fillna(0)

# 또는 앞의 값으로 채우기 (forward fill)
df_ffill = df.fillna(method='ffill')
```

---

## 🎨 거래량 색상 구분

### 색상 구분 로직

거래량을 시각화할 때 주가의 상승/하락에 따라 색상을 다르게 표시하면 직관적인 분석이 가능함.

![거래량 색상 코딩](../images/2026-02-03/volume_color_coding.png)

```python
# 거래량 색상 구분 (상승: 빨강, 하락: 파랑)
colors = []
for i, row in df.iterrows():
    if row['Close'] >= row['Open']:
        colors.append('#ff5252')  # Red (상승/양봉)
    else:
        colors.append('#448aff')  # Blue (하락/음봉)

# 색상 리스트를 DataFrame에 추가
df['Color'] = colors

# 결과 확인
print(df[['Open', 'Close', 'Color']].head(10))
```

### 🎯 조건부 처리 방법

위의 for 루프 방식 외에도 Pandas의 벡터화 연산을 활용할 수 있음:

```python
# 방법 1: numpy.where 사용 (더 빠름)
import numpy as np
df['Color'] = np.where(df['Close'] >= df['Open'], '#ff5252', '#448aff')

# 방법 2: apply 사용
df['Color'] = df.apply(lambda row: '#ff5252' if row['Close'] >= row['Open'] else '#448aff', axis=1)

# 방법 3: map 사용
df['Color'] = (df['Close'] >= df['Open']).map({True: '#ff5252', False: '#448aff'})
```

**성능 비교**:
- `numpy.where`: 가장 빠름 (벡터화 연산)
- `for loop`: 가장 느림 (Python 레벨 반복)
- `apply`: 중간 속도

### 📊 거래량 분석

```python
# 상승일/하락일 통계
rising_days = (df['Close'] >= df['Open']).sum()
falling_days = (df['Close'] < df['Open']).sum()

print(f"상승일: {rising_days}일 ({rising_days/len(df)*100:.1f}%)")
print(f"하락일: {falling_days}일 ({falling_days/len(df)*100:.1f}%)")

# 상승일/하락일 평균 거래량
rising_volume = df[df['Close'] >= df['Open']]['Volume'].mean()
falling_volume = df[df['Close'] < df['Open']]['Volume'].mean()

print(f"\n상승일 평균 거래량: {rising_volume:,.0f}")
print(f"하락일 평균 거래량: {falling_volume:,.0f}")
```

---

## 💡 주요 학습 내용

### 1. Pandas 데이터 처리

#### `rolling()` 함수 활용

```python
# 기본 사용법
df['MA5'] = df['Close'].rolling(window=5).mean()

# 다양한 집계 함수
df['MA5_std'] = df['Close'].rolling(window=5).std()    # 표준편차
df['MA5_min'] = df['Close'].rolling(window=5).min()    # 최소값
df['MA5_max'] = df['Close'].rolling(window=5).max()    # 최대값
df['MA5_sum'] = df['Close'].rolling(window=5).sum()    # 합계

# 중심 이동평균 (center=True)
df['MA5_center'] = df['Close'].rolling(window=5, center=True).mean()
```

#### DataFrame 순회 및 조건부 처리

```python
# iterrows() - 각 행을 순회
for index, row in df.iterrows():
    print(f"날짜: {index}, 종가: {row['Close']}")

# itertuples() - 더 빠른 순회 방법
for row in df.itertuples():
    print(f"날짜: {row.Index}, 종가: {row.Close}")

# 조건부 필터링
high_volume = df[df['Volume'] > df['Volume'].mean()]
print(f"평균 이상 거래량 일수: {len(high_volume)}일")
```

### 2. 주식 데이터 분석 기초

#### 캔들스틱의 의미

```python
# 캔들스틱 패턴 분석을 위한 기본 정보
df['Body'] = abs(df['Close'] - df['Open'])        # 몸통 크기
df['Upper_Shadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)  # 위꼬리
df['Lower_Shadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']   # 아래꼬리

# 양봉/음봉 구분
df['Candle_Type'] = df.apply(
    lambda row: '양봉' if row['Close'] >= row['Open'] else '음봉', 
    axis=1
)

# 결과 확인
print(df[['Open', 'High', 'Low', 'Close', 'Body', 'Upper_Shadow', 'Lower_Shadow', 'Candle_Type']].head())
```

**캔들스틱 구성 요소**:
- **시가(Open)**: 장 시작 가격
- **고가(High)**: 당일 최고 가격
- **저가(Low)**: 당일 최저 가격
- **종가(Close)**: 장 마감 가격
- **몸통(Body)**: 시가와 종가 사이의 영역
- **위꼬리(Upper Shadow)**: 고가와 몸통 상단 사이
- **아래꼬리(Lower Shadow)**: 저가와 몸통 하단 사이

#### 이동평균선을 통한 추세 분석

```python
# 골든크로스 / 데드크로스 탐지
df['Golden_Cross'] = (df['MA5'] > df['MA20']) & (df['MA5'].shift(1) <= df['MA20'].shift(1))
df['Dead_Cross'] = (df['MA5'] < df['MA20']) & (df['MA5'].shift(1) >= df['MA20'].shift(1))

# 골든크로스 발생일 확인
golden_cross_dates = df[df['Golden_Cross'] == True].index
print(f"골든크로스 발생일: {len(golden_cross_dates)}회")
for date in golden_cross_dates:
    print(f"  - {date.strftime('%Y-%m-%d')}")

# 데드크로스 발생일 확인
dead_cross_dates = df[df['Dead_Cross'] == True].index
print(f"\n데드크로스 발생일: {len(dead_cross_dates)}회")
for date in dead_cross_dates:
    print(f"  - {date.strftime('%Y-%m-%d')}")
```

**골든크로스 (Golden Cross)**:
- 단기 이동평균선이 장기 이동평균선을 상향 돌파
- 상승 추세 전환 신호
- 매수 타이밍으로 활용

**데드크로스 (Dead Cross)**:
- 단기 이동평균선이 장기 이동평균선을 하향 돌파
- 하락 추세 전환 신호
- 매도 타이밍으로 활용

---

## 🔍 실전 예제: 완전한 데이터 전처리 파이프라인

```python
import FinanceDataReader as fdr
import pandas as pd
import numpy as np

def preprocess_stock_data(ticker, start_date, end_date):
    """
    주식 데이터를 수집하고 전처리하는 함수
    
    Parameters:
    - ticker: 종목 코드
    - start_date: 시작일
    - end_date: 종료일
    
    Returns:
    - 전처리된 DataFrame
    """
    # 1. 데이터 수집
    print(f"[1/5] 데이터 수집 중... (종목: {ticker})")
    df = fdr.DataReader(ticker, start_date, end_date)
    print(f"      수집 완료: {len(df)}건")
    
    # 2. 이동평균선 계산
    print("[2/5] 이동평균선 계산 중...")
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    print("      계산 완료: MA5, MA20, MA60")
    
    # 3. 거래량 색상 구분
    print("[3/5] 거래량 색상 구분 중...")
    df['Color'] = np.where(df['Close'] >= df['Open'], '#ff5252', '#448aff')
    print("      구분 완료")
    
    # 4. 추가 지표 계산
    print("[4/5] 추가 지표 계산 중...")
    df['Daily_Return'] = df['Close'].pct_change() * 100  # 일일 수익률 (%)
    df['Volatility'] = df['Close'].rolling(window=20).std()  # 변동성
    df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()  # 거래량 이동평균
    print("      계산 완료: 일일 수익률, 변동성, 거래량 MA")
    
    # 5. 골든크로스/데드크로스 탐지
    print("[5/5] 크로스 신호 탐지 중...")
    df['Golden_Cross'] = (df['MA5'] > df['MA20']) & (df['MA5'].shift(1) <= df['MA20'].shift(1))
    df['Dead_Cross'] = (df['MA5'] < df['MA20']) & (df['MA5'].shift(1) >= df['MA20'].shift(1))
    print("      탐지 완료")
    
    print("\n✅ 전처리 완료!")
    return df

# 사용 예시
ticker = "000660"  # SK하이닉스
start_date = "2025-01-01"
end_date = "2025-12-31"

df = preprocess_stock_data(ticker, start_date, end_date)

# 결과 확인
print("\n" + "="*70)
print("📊 전처리 결과 요약")
print("="*70)
print(f"데이터 기간: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")
print(f"총 거래일: {len(df)}일")
print(f"컬럼 수: {len(df.columns)}개")
print(f"\n컬럼 목록:")
for col in df.columns:
    print(f"  - {col}")
```

---

## 📈 데이터 품질 확인

### 결측치 확인

```python
# 결측치 개수 확인
print("결측치 개수:")
print(df.isna().sum())

# 결측치 비율 확인
print("\n결측치 비율 (%):")
print((df.isna().sum() / len(df) * 100).round(2))

# 결측치 시각화
import matplotlib.pyplot as plt
plt.figure(figsize=(10, 6))
df.isna().sum().plot(kind='bar')
plt.title('Missing Values by Column')
plt.ylabel('Count')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

### 이상치 탐지

```python
# IQR 방법으로 이상치 탐지
Q1 = df['Close'].quantile(0.25)
Q3 = df['Close'].quantile(0.75)
IQR = Q3 - Q1

lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

outliers = df[(df['Close'] < lower_bound) | (df['Close'] > upper_bound)]
print(f"이상치 개수: {len(outliers)}개")
print(f"이상치 비율: {len(outliers)/len(df)*100:.2f}%")

# 이상치 날짜 출력
if len(outliers) > 0:
    print("\n이상치 발생일:")
    for date, row in outliers.iterrows():
        print(f"  - {date.strftime('%Y-%m-%d')}: {row['Close']:,.0f}원")
```

---

## 💾 데이터 저장

```python
# CSV 파일로 저장
output_file = f"{ticker}_preprocessed.csv"
df.to_csv(output_file, encoding='utf-8-sig')
print(f"데이터가 '{output_file}'로 저장되었습니다.")

# Excel 파일로 저장
excel_file = f"{ticker}_preprocessed.xlsx"
df.to_excel(excel_file, sheet_name='Stock Data')
print(f"데이터가 '{excel_file}'로 저장되었습니다.")

# Pickle 파일로 저장 (가장 빠름)
pickle_file = f"{ticker}_preprocessed.pkl"
df.to_pickle(pickle_file)
print(f"데이터가 '{pickle_file}'로 저장되었습니다.")
```

---

## 🎓 2일차 학습 정리

### ✅ 달성한 목표

1. ✔️ FinanceDataReader를 활용한 주식 데이터 수집
2. ✔️ Pandas를 이용한 데이터 전처리
3. ✔️ 이동평균선 계산 및 의미 이해
4. ✔️ 거래량 색상 구분 로직 구현
5. ✔️ 골든크로스/데드크로스 탐지

### 📚 핵심 개념

| 개념 | 설명 | 활용 |
|------|------|------|
| **이동평균선** | 일정 기간 주가의 평균 | 추세 파악, 지지/저항선 |
| **rolling()** | 이동 윈도우 집계 함수 | 이동평균, 이동 표준편차 등 |
| **골든크로스** | 단기선이 장기선 상향 돌파 | 매수 신호 |
| **데드크로스** | 단기선이 장기선 하향 돌파 | 매도 신호 |
| **캔들스틱** | OHLC 데이터 시각화 | 주가 흐름 파악 |

### 🔑 주요 코드 스니펫

```python
# 데이터 수집
df = fdr.DataReader(ticker, start_date, end_date)

# 이동평균선 계산
df['MA5'] = df['Close'].rolling(window=5).mean()
df['MA20'] = df['Close'].rolling(window=20).mean()
df['MA60'] = df['Close'].rolling(window=60).mean()

# 거래량 색상 구분
df['Color'] = np.where(df['Close'] >= df['Open'], '#ff5252', '#448aff')

# 골든크로스 탐지
df['Golden_Cross'] = (df['MA5'] > df['MA20']) & (df['MA5'].shift(1) <= df['MA20'].shift(1))
```

---

## 🚀 다음 단계 (3일차 예고)

3일차에는 Plotly를 활용하여 수집하고 전처리한 데이터를 시각화할 예정임:

1. **캔들스틱 차트 구현**
   - `go.Candlestick()`을 활용한 기본 차트
   - 양봉/음봉 색상 커스터마이징

2. **이동평균선 추가**
   - `go.Scatter()`로 MA5, MA20, MA60 표시
   - 각 선의 색상 및 스타일 지정

3. **서브플롯 구성**
   - 가격 차트 + 거래량 차트 결합
   - X축 공유로 연동된 차트 구현

4. **인터랙티브 기능**
   - 호버 정보 표시
   - 줌/팬 기능
   - 범례 및 레이아웃 커스터마이징

---

## 📌 참고 자료

- [FinanceDataReader GitHub](https://github.com/FinanceData/FinanceDataReader)
- [Pandas 공식 문서 - rolling()](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html)
- [Pandas 공식 문서 - 조건부 선택](https://pandas.pydata.org/docs/user_guide/indexing.html)
- [주식 기술적 분석 기초](https://www.investopedia.com/terms/t/technicalanalysis.asp)

---

**작성일**: 2026-02-03  
**작성자**: parkjongmin  
**다음 포스트**: 3일차 - Plotly를 활용한 시각화
