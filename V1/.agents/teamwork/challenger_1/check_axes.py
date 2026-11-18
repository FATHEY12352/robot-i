import numpy as np
from challenge_01_kinematics import dh_matrix

q = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
d1 = 125.0
a2 = 210.0
a3 = 45.0
d4 = 195.0
d6 = 85.0

A1 = dh_matrix(q[0], d1, 0, np.pi/2)
A2 = dh_matrix(q[1], 0, a2, 0)
A3 = dh_matrix(q[2] + np.pi/2, 0, a3, np.pi/2)
A4 = dh_matrix(q[3], d4, 0, -np.pi/2)

T01 = A1
T02 = T01 @ A2
T03 = T02 @ A3
T04 = T03 @ A4

print("Frame 0: z0 = [0, 0, 1]")
print("Frame 1 R:\n", T01[:3, :3])
print("Frame 2 R:\n", T02[:3, :3])
print("Frame 3 R:\n", T03[:3, :3])
print("z3 axis (in base frame):", T03[:3, 2])
print("x3 axis (in base frame):", T03[:3, 0])
print("y3 axis (in base frame):", T03[:3, 1])
