import numpy as np
import plotly.graph_objects as go
import os

study_hours = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
pass_fail = np.array([0, 0, 0, 0, 1, 0, 1, 1, 1, 1]) 

coef_linear = np.polyfit(study_hours, pass_fail, 1) 
linear_y = np.polyval(coef_linear, study_hours)

def sigmoid(x):
    return 1 / (1 + np.exp(-(x - 5.5))) 

logistic_y = sigmoid(study_hours)

fig = go.Figure()

fig.add_trace(go.Scatter(x=study_hours, y=pass_fail, mode='markers', 
                         name='실제 데이터 (1=합격, 0=불합격)', marker=dict(size=12, color='black')))

fig.add_trace(go.Scatter(x=study_hours, y=linear_y, mode='lines', 
                         name='선형 회귀 (끝없이 올라가는 100% 모순 직선)', line=dict(color='red', dash='dash', width=3)))

# Make plotting smoother for logistic
smooth_x = np.linspace(0, 11, 100)
smooth_logistic_y = sigmoid(smooth_x)

fig.add_trace(go.Scatter(x=smooth_x, y=smooth_logistic_y, mode='lines', 
                         name='로지스틱 회귀 (우아한 S자 시그모이드 곡선)', line=dict(color='blue', width=4)))

fig.update_layout(title="선형 회귀 vs 로지스틱 회귀 시각적 비교",
                  xaxis_title="공부 시간 (시간)", yaxis_title="합격 확률 (0~1 범위 내)",
                  template="plotly_white",
                  legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))

os.makedirs('assets/images', exist_ok=True)
try:
    fig.write_image('assets/images/plotly_logistic.png', scale=2)
    print("Plotly image saved successfully.")
except Exception as e:
    print(f"Failed to save image: {e}")
    # Fallback to HTML if kaleido is missing
    fig.write_html('assets/images/plotly_logistic.html')
    print("Saved as HTML fallback.")
