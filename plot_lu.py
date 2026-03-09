import matplotlib.pyplot as plt
import numpy as np
import scipy.linalg as la
import os

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# Base square face
square = np.array([[0, 1, 1, 0, 0],
                   [0, 0, 1, 1, 0]])

# Transformation matrix A
A = np.array([[2, 1], 
              [3, 2]])

# Get LU decomp of A
P, L, U = la.lu(A)

# Transformations
step1_U = U.dot(square)
step2_LU = L.dot(U.dot(square)) # Should equal A.dot(square)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# Original
axes[0].plot(square[0], square[1], 'b-', linewidth=2)
axes[0].fill(square[0], square[1], 'b', alpha=0.3)
axes[0].set_title('1. 원본 데이터 (정사각형)')
axes[0].grid(True)
axes[0].set_xlim(-1, 5)
axes[0].set_ylim(-1, 5)
axes[0].axhline(0, color='black', linewidth=1)
axes[0].axvline(0, color='black', linewidth=1)

# Apply U (Upper triangular)
axes[1].plot(step1_U[0], step1_U[1], 'orange', linestyle='-', linewidth=2)
axes[1].fill(step1_U[0], step1_U[1], 'orange', alpha=0.3)
axes[1].set_title('2. 모래 1 (U 행렬): 가로축 변형')
axes[1].grid(True)
axes[1].set_xlim(-1, 5)
axes[1].set_ylim(-1, 5)
axes[1].axhline(0, color='black', linewidth=1)
axes[1].axvline(0, color='black', linewidth=1)

# Apply L on top of U (Equals A)
axes[2].plot(step2_LU[0], step2_LU[1], 'g-', linewidth=2)
axes[2].fill(step2_LU[0], step2_LU[1], 'g', alpha=0.3)
axes[2].set_title('3. 모래 2 (L 행렬): 원본 A를 곱한 것과 완벽히 일치!')
axes[2].grid(True)
axes[2].set_xlim(-1, 5)
axes[2].set_ylim(-1, 5)
axes[2].axhline(0, color='black', linewidth=1)
axes[2].axvline(0, color='black', linewidth=1)

os.makedirs('assets/images', exist_ok=True)
plt.savefig('assets/images/lu_decomposition.png', dpi=300, bbox_inches='tight')
print('LU decomp image saved')
