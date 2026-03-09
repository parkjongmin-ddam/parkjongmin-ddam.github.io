import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# N = 50000, P = 0.0001 -> lam = 5
N = 50000
P = 0.0001
lam = N * P 

# Both distributions
binom = np.random.binomial(N, P, size=1000)
poisson = np.random.poisson(lam, size=1000)

fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

# Binomial
axes[0].hist(binom, bins=np.arange(0, 15)-0.5, color='skyblue', edgecolor='black', alpha=0.8, density=True)
axes[0].set_title('1. 진짜 이항 분포 (무식하게 5만 번 돌림)')
axes[0].set_xlabel('당첨 횟수')
axes[0].set_ylabel('확률 비율')
axes[0].grid(axis='y', linestyle='--', alpha=0.7)

# Poisson
axes[1].hist(poisson, bins=np.arange(0, 15)-0.5, color='lightgreen', edgecolor='black', alpha=0.8, density=True)
axes[1].set_title('2. 포아송 근사치 (가벼운 수학 공식으로 때움)')
axes[1].set_xlabel('당첨 횟수')
axes[1].grid(axis='y', linestyle='--', alpha=0.7)

plt.suptitle('포아송 근사의 마법: 두 그래프의 비율 분포가 거의 똑같음!', fontsize=14, fontweight='bold')

os.makedirs('assets/images', exist_ok=True)
plt.savefig('assets/images/poisson_approx.png', dpi=300, bbox_inches='tight')
print('Poisson image saved')
