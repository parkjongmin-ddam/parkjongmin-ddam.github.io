import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

x = np.linspace(0, 1, 100)
y = 2 * x

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(x, y, 'b-', linewidth=2, label='확률밀도함수 f(x) = 2x')

# Fill area from 0.5 to 1.0
x_fill = np.linspace(0.5, 1.0, 50)
y_fill = 2 * x_fill
ax.fill_between(x_fill, y_fill, color='orange', alpha=0.5, label='확률 면적 (0.5 ≤ x ≤ 1.0) = 75%')

ax.set_title('확률밀도함수(PDF)의 면적이 곧 확률!')
ax.set_xlabel('X 값')
ax.set_ylabel('f(x)')
ax.grid(True, linestyle='--', alpha=0.7)
ax.legend(loc='upper left')
ax.set_xlim(0, 1.1)
ax.set_ylim(0, 2.2)

os.makedirs('assets/images', exist_ok=True)
plt.savefig('assets/images/pdf_area.png', dpi=300, bbox_inches='tight')
print('PDF image saved')
