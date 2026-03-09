import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

x = np.linspace(-5, 10, 400)
# 2x + 3y = 8 -> y = (8 - 2x) / 3
y1 = (8 - 2*x) / 3
# x - y = 1 -> y = x - 1
y2 = x - 1

plt.figure(figsize=(8, 6))
plt.plot(x, y1, '-r', label='2x + 3y = 8')
plt.plot(x, y2, '-b', label='x - y = 1')

# The solution is x=2.2, y=1.2
# Wait, let's solve exactly:
# 2x + 3(x - 1) = 8 => 2x + 3x - 3 = 8 => 5x = 11 => x = 11/5 = 2.2
# y = 2.2 - 1 = 1.2
plt.plot(11/5, 6/5, 'ko', markersize=8, label='Solution (2.2, 1.2)')

plt.title('2D 연립방정식의 교점 (가우스 소거법 원리)')
plt.xlabel('x')
plt.ylabel('y')
plt.axhline(0, color='black',linewidth=0.5)
plt.axvline(0, color='black',linewidth=0.5)
plt.grid(color = 'gray', linestyle = '--', linewidth = 0.5)
plt.legend(loc='upper left')

os.makedirs('assets/images', exist_ok=True)
plt.savefig('assets/images/linear_eq_2d.png', dpi=300, bbox_inches='tight')
print('2D image saved')
