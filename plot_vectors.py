import matplotlib.pyplot as plt
import numpy as np
import os

# Set up matplotlib for Korean font if possible, else standard
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Define vectors
A = np.array([1, -1, 1])
B = np.array([1, -1, 0])
C = np.array([-1, 1, 0])

# Plot origin
origin = [0, 0, 0]

# Plot vectors
ax.quiver(*origin, *A, color='b', arrow_length_ratio=0.1, label='A (1, -1, 1)')
ax.quiver(*origin, *B, color='g', arrow_length_ratio=0.1, label='B (1, -1, 0)')
ax.quiver(*origin, *C, color='r', arrow_length_ratio=0.1, label='C (-1, 1, 0)')

# Set limits and labels
ax.set_xlim([-1.5, 1.5])
ax.set_ylim([-1.5, 1.5])
ax.set_zlim([-0.5, 1.5])
ax.set_xlabel('Action')
ax.set_ylabel('Romance')
ax.set_zlabel('Comedy')

ax.view_init(elev=20, azim=45)
plt.legend()
plt.title('Movie Preference Vectors (A vs B vs C)')

# Make sure directory exists
os.makedirs('assets/images', exist_ok=True)
plt.savefig('assets/images/vector_dot_product.png')
print("Image saved to assets/images/vector_dot_product.png")
