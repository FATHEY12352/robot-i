import numpy as np

d1 = 125.0
a2 = 210.0
a3 = 45.0
d4 = 195.0
d6 = 85.0

def fk_wrist(q1, q2, q3):
    xw = np.cos(q1) * (a2 * np.cos(q2) + a3 * np.cos(q2 + q3) - d4 * np.sin(q2 + q3))
    yw = np.sin(q1) * (a2 * np.cos(q2) + a3 * np.cos(q2 + q3) - d4 * np.sin(q2 + q3))
    zw = d1 + a2 * np.sin(q2) + a3 * np.sin(q2 + q3) + d4 * np.cos(q2 + q3)
    return np.array([xw, yw, zw])

def ik_wrist_analytical(pw, elbow_up=True):
    xw, yw, zw = pw
    # 1. q1
    q1 = np.arctan2(yw, xw)

    # 2. r and s
    r = np.sqrt(xw**2 + yw**2)
    s = zw - d1

    # Effective forearm length
    L_forearm = np.sqrt(a3**2 + d4**2)
    phi = np.arctan2(a3, d4) # Wait, is phi atan2(a3, d4) or atan2(d4, a3)?

    # Law of cosines for D
    D = (r**2 + s**2 - a2**2 - L_forearm**2) / (2.0 * a2 * L_forearm)
    if np.abs(D) > 1.0:
        return None, "Out of reach"

    sign = 1.0 if elbow_up else -1.0
    # Equation in text: q3 = atan2(±sqrt(1-D^2), D) - atan2(a3, d4)
    # Let's test this:
    q3_candidate = np.arctan2(sign * np.sqrt(max(0.0, 1.0 - D**2)), D) - phi

    # Equation in text: q2 = atan2(s, r) - atan2(L_forearm * sin(q3 + phi), a2 + L_forearm * cos(q3 + phi))
    q2_candidate = np.arctan2(s, r) - np.arctan2(L_forearm * np.sin(q3_candidate + phi), a2 + L_forearm * np.cos(q3_candidate + phi))

    return (q1, q2_candidate, q3_candidate), D

# Let's test IK against FK on 1000 random configurations
np.random.seed(123)
max_ik_err = 0.0
failed_count = 0

for i in range(1000):
    q1_orig = np.random.uniform(-1.5, 1.5)
    q2_orig = np.random.uniform(-0.5, 1.0)
    q3_orig = np.random.uniform(-1.5, 0.5)

    pw = fk_wrist(q1_orig, q2_orig, q3_orig)
    (q_sol, D) = ik_wrist_analytical(pw, elbow_up=True)
    
    # Check if this solution reconstructs pw
    pw_reconstructed = fk_wrist(*q_sol)
    err = np.linalg.norm(pw - pw_reconstructed)
    if err > max_ik_err:
        max_ik_err = err

print(f"Inverse Kinematics analytical test: max FK-IK position error = {max_ik_err:.6e} mm")
