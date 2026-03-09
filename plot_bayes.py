import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# Proportions based on 1000 people
# 10 have cancer, 9 diagnosed correctly(0.9%), 1 incorrectly(0.1%)
# 990 healthy, 99 misdiagnosed(9.9%), 891 correctly diagnosed(89.1%)

labels = ['진짜 암환자\n(정확한 진단)', '진짜 암환자\n(오진으로 놓침)', '건강한 사람\n(오진으로 진짜 암이라 착각)', '건강한 사람\n(정상 판정)']
sizes = [0.9, 0.1, 9.9, 89.1]
colors = ['#ff9999', '#ffcccc', '#ffcc99', '#99ff99']
explode = (0.2, 0, 0.2, 0) # explode the "Diagnosed as cancer" slices

fig, ax = plt.subplots(figsize=(10, 7))
ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
ax.set_title('베이즈 정리의 함정: 병원에서 "암 통보"를 받은 사람들의 실제 비율 분포\n(착각: 9.9% vs 진짜: 0.9%)')

os.makedirs('assets/images', exist_ok=True)
plt.savefig('assets/images/bayes_theorem.png', dpi=300, bbox_inches='tight')
print('Bayes image saved')
