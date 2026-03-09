import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import os

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Define range
X, Y = np.meshgrid(np.linspace(-5, 5, 20), np.linspace(-5, 5, 20))

# x + 2y - z = 2 -> z = x + 2y - 2
Z1 = X + 2*Y - 2
# 2x + 5y + 2z = 9 -> z = (9 - 2x - 5y) / 2
Z2 = (9 - 2*X - 5*Y) / 2
# -x - 2y + 3z = 2 -> z = (2 + x + 2y) / 3
Z3 = (2 + X + 2*Y) / 3

ax.plot_surface(X, Y, Z1, alpha=0.5, color='r')
ax.plot_surface(X, Y, Z2, alpha=0.5, color='g')
ax.plot_surface(X, Y, Z3, alpha=0.5, color='b')

# The solution is x=1, y=1, z=1
ax.scatter([1], [1], [1], color='black', s=100, label='Solution (1, 1, 1)', depthshade=False)

ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.set_title('3D 연립방정식(세 평면)의 교차점')

# Create proxy artists for legend
from matplotlib.lines import Line2D
import matplotlib.patches as mpatches

red_patch = mpatches.Patch(color='r', alpha=0.5, label='x + 2y - z = 2')
green_patch = mpatches.Patch(color='g', alpha=0.5, label='2x + 5y + 2z = 9')
blue_patch = mpatches.Patch(color='b', alpha=0.5, label='-x - 2y + 3z = 2')
black_dot = Line2D([0], [0], marker='o', color='w', label='Solution (1, 1, 1)', markerfacecolor='black', markersize=10)

ax.legend(handles=[red_patch, green_patch, blue_patch, black_dot], loc='upper left')

os.makedirs('assets/images', exist_ok=True)
plt.savefig('assets/images/linear_eq_3d.png', dpi=300, bbox_inches='tight')
print('3D image saved')
