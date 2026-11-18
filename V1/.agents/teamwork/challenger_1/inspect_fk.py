import numpy as np
from challenge_01_kinematics import dh_matrix

# Let's inspect at q = [0, 0, 0, 0, 0, 0]
q = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
d1 = 125.0
a2 = 210.0
a3 = 45.0
d4 = 195.0
d6 = 85.0

# Case A: exactly as written in table:
# 1: a1=0, alpha1=pi/2, d1=125.0, theta1=q1
# 2: a2=210.0, alpha2=0, d2=0, theta2=q2
# 3: a3=45.0, alpha3=pi/2, d3=0, theta3=q3 + pi/2
# 4: a4=0, alpha4=-pi/2, d4=195.0, theta4=q4
# 5: a5=0, alpha5=pi/2, d5=0, theta5=q5
# 6: a6=0, alpha6=0, d6=85.0, theta6=q6

A1 = dh_matrix(q[0], d1, 0, np.pi/2)
A2 = dh_matrix(q[1], 0, a2, 0)
A3 = dh_matrix(q[2] + np.pi/2, 0, a3, np.pi/2)
A4 = dh_matrix(q[3], d4, 0, -np.pi/2)
A5 = dh_matrix(q[4], 0, 0, np.pi/2)
A6 = dh_matrix(q[5], d6, 0, 0)

T01 = A1
T02 = T01 @ A2
T03 = T02 @ A3
T04 = T03 @ A4
T05 = T04 @ A5
T06 = T05 @ A6

print("At q = 0:")
print("T01 origin:", T01[:3, 3])
print("T02 origin:", T02[:3, 3])
print("T03 origin:", T03[:3, 3])
print("T04 origin:", T04[:3, 3])
print("T05 origin:", T05[:3, 3])
print("T06 origin:", T06[:3, 3])

# What did the formula in Section 2.3 give at q=0?
# xw = cos(q1) * [ a2 cos(q2) + a3 cos(q2 + q3) - d4 sin(q2 + q3) ]
# yw = sin(q1) * [ a2 cos(q2) + a3 cos(q2 + q3) - d4 sin(q2 + q3) ]
# zw = d1 + a2 sin(q2) + a3 sin(q2 + q3) + d4 cos(q2 + q3)
xw_eq = np.cos(q[0]) * (a2 * np.cos(q[1]) + a3 * np.cos(q[1] + q[2]) - d4 * np.sin(q[1] + q[2]))
yw_eq = np.sin(q[0]) * (a2 * np.cos(q[1]) + a3 * np.cos(q[1] + q[2]) - d4 * np.sin(q[1] + q[2]))
zw_eq = d1 + a2 * np.sin(q[1]) + a3 * np.sin(q[1] + q[2]) + d4 * np.cos(q[1] + q[2])
print("\nFormula in Section 2.3 at q=0:")
print("pw_eq:", [xw_eq, yw_eq, zw_eq])
