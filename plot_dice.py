import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

dice = np.array([1, 2, 3, 4, 5, 6])
prob = np.array([1/6]*6)

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(dice, prob, color='skyblue', edgecolor='black', zorder=2)
ax.set_ylim(0, 0.3)

# Add Expected Value line
mean = 3.5
std_dev = np.sqrt(35/12) # ~1.707

ax.axvline(mean, color='red', linestyle='dashed', linewidth=2, label=f'기댓값(중심) = {mean}')
ax.axvspan(mean - std_dev, mean + std_dev, color='red', alpha=0.2, label=f'표준편차 범위 (흩어진 정도 ±{std_dev:.2f})')

ax.set_title('주사위 확률 분포 및 기댓값/표준편차 시각화')
ax.set_xlabel('주사위 눈금')
ax.set_ylabel('확률 (모두 1/6 = 약 0.166)')
ax.set_xticks(dice)
ax.grid(axis='y', linestyle='--', alpha=0.7, zorder=1)
ax.legend()

os.makedirs('assets/images', exist_ok=True)
plt.savefig('assets/images/dice_stats.png', dpi=300, bbox_inches='tight')
print('Dice image saved')
