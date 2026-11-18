import numpy as np
from challenge_01_kinematics import dh_matrix

d1 = 125.0
a2 = 210.0
a3 = 45.0
d4 = 195.0
d6 = 85.0

# Let's test combinations of theta3 offset and alpha3
# Formula in text:
# xw = cos(q1) * [ a2 cos(q2) + a3 cos(q2 + q3) - d4 sin(q2 + q3) ]
# yw = sin(q1) * [ a2 cos(q2) + a3 cos(q2 + q3) - d4 sin(q2 + q3) ]
# zw = d1 + a2 sin(q2) + a3 sin(q2 + q3) + d4 cos(q2 + q3)

def pw_formula(q):
    q1, q2, q3, q4, q5, q6 = q
    xw = np.cos(q1) * (a2 * np.cos(q2) + a3 * np.cos(q2 + q3) - d4 * np.sin(q2 + q3))
    yw = np.sin(q1) * (a2 * np.cos(q2) + a3 * np.cos(q2 + q3) - d4 * np.sin(q2 + q3))
    zw = d1 + a2 * np.sin(q2) + a3 * np.sin(q2 + q3) + d4 * np.cos(q2 + q3)
    return np.array([xw, yw, zw])

# Test different candidate DH tables
candidates = [
    ("Table in text", 0, np.pi/2, d1, "q1",   a2, 0, 0, "q2",   a3, np.pi/2, 0, "q3 + pi/2",   0, -np.pi/2, d4, "q4"),
    ("theta3 = q3",   0, np.pi/2, d1, "q1",   a2, 0, 0, "q2",   a3, np.pi/2, 0, "q3",          0, -np.pi/2, d4, "q4"),
    ("alpha3 = 0",    0, np.pi/2, d1, "q1",   a2, 0, 0, "q2",   a3, 0, 0, "q3",                0, -np.pi/2, d4, "q4"),
    ("puma standard", 0, np.pi/2, d1, "q1",   a2, 0, 0, "q2",   0, np.pi/2, 0, "q3 + pi/2",    0, -np.pi/2, d4, "q4"),
]

q_test = np.array([0.2, -0.3, 0.4, 0.1, -0.2, 0.5])
target_pw = pw_formula(q_test)
print("Target pw from formula:", target_pw)

# Let's search systematically for DH table that reproduces the formula
for th3_off in [0, np.pi/2, -np.pi/2, np.pi]:
    for al3 in [0, np.pi/2, -np.pi/2, np.pi]:
        for al2 in [0, np.pi/2, -np.pi/2]:
            for th2_off in [0, np.pi/2, -np.pi/2]:
                q1, q2, q3, q4 = q_test[:4]
                A1 = dh_matrix(q1, d1, 0, np.pi/2)
                A2 = dh_matrix(q2 + th2_off, 0, a2, al2)
                A3 = dh_matrix(q3 + th3_off, 0, a3, al3)
                A4 = dh_matrix(q4, d4, 0, -np.pi/2)
                T04 = A1 @ A2 @ A3 @ A4
                pw = T04[:3, 3]
                if np.linalg.norm(pw - target_pw) < 1e-4:
                    print(f"FOUND MATCHING DH! th2_off={th2_off}, al2={al2}, th3_off={th3_off}, al3={al3}")
