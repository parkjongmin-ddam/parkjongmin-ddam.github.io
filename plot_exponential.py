import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

mean_arrival_time = 4
intervals = np.random.exponential(scale=mean_arrival_time, size=500)

fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(intervals, bins=40, color='mediumpurple', edgecolor='black', alpha=0.7)

ax.axvline(mean_arrival_time, color='red', linestyle='dashed', linewidth=2, label=f'평균 간격 = {mean_arrival_time}분')

ax.set_title('지수 분포 시뮬레이션: 손님 500명의 카페 도착 대기시간')
ax.set_xlabel('다음 손님이 올 때까지 걸린 시간 (분)')
ax.set_ylabel('발생 빈도(명)')
ax.legend()
ax.grid(axis='y', linestyle='--', alpha=0.7)

os.makedirs('assets/images', exist_ok=True)
plt.savefig('assets/images/exponential_dist.png', dpi=300, bbox_inches='tight')
print('Exponential image saved')
