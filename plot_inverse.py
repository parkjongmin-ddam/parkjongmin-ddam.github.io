import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# Define a simple grid
x = np.linspace(-2, 2, 5)
y = np.linspace(-2, 2, 5)
X, Y = np.meshgrid(x, y)
points = np.vstack([X.ravel(), Y.ravel()])

# Transformation matrix A
A = np.array([[1, 2], 
              [2, 3]])

# Apply transformation
transformed_points = A.dot(points)

# Apply inverse transformation to show it goes back
A_inv = np.linalg.inv(A)
restored_points = A_inv.dot(transformed_points)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# Original Grid
axes[0].scatter(points[0], points[1], c='b', s=50)
axes[0].set_title('1. 원본 데이터 (단위행렬 상태)')
axes[0].grid(True)
axes[0].set_xlim(-15, 15)
axes[0].set_ylim(-15, 15)
axes[0].axhline(0, color='black', linewidth=1)
axes[0].axvline(0, color='black', linewidth=1)

# Transformed Grid
axes[1].scatter(transformed_points[0], transformed_points[1], c='r', s=50)
axes[1].set_title('2. 행렬 A를 곱해서 공간을 찌그러뜨림 (변환)')
axes[1].grid(True)
axes[1].set_xlim(-15, 15)
axes[1].set_ylim(-15, 15)
axes[1].axhline(0, color='black', linewidth=1)
axes[1].axvline(0, color='black', linewidth=1)

# Restored Grid
axes[2].scatter(restored_points[0], restored_points[1], c='g', s=50)
axes[2].set_title('3. 역행렬 A⁻¹을 직빵으로 곱해 원래대로 복구!')
axes[2].grid(True)
axes[2].set_xlim(-15, 15)
axes[2].set_ylim(-15, 15)
axes[2].axhline(0, color='black', linewidth=1)
axes[2].axvline(0, color='black', linewidth=1)

os.makedirs('assets/images', exist_ok=True)
plt.savefig('assets/images/inverse_matrix.png', dpi=300, bbox_inches='tight')
print('Inverse matrix image saved')
