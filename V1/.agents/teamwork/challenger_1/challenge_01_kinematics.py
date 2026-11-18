import numpy as np

def dh_matrix(theta, d, a, alpha):
    ct = np.cos(theta)
    st = np.sin(theta)
    ca = np.cos(alpha)
    sa = np.sin(alpha)
    return np.array([
        [ct, -st * ca,  st * sa, a * ct],
        [st,  ct * ca, -ct * sa, a * st],
        [0.0,      sa,       ca,      d],
        [0.0,     0.0,      0.0,    1.0]
    ])

def test_dh_matrix_derivation():
    # Verify A_i = Rot_z(theta) * Trans_z(d) * Trans_x(a) * Rot_x(alpha)
    for _ in range(10):
        th = np.random.uniform(-np.pi, np.pi)
        d = np.random.uniform(-100, 100)
        a = np.random.uniform(-100, 100)
        al = np.random.uniform(-np.pi, np.pi)

        Rz = np.array([
            [np.cos(th), -np.sin(th), 0, 0],
            [np.sin(th),  np.cos(th), 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        Tz = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, d],
            [0, 0, 0, 1]
        ])
        Tx = np.array([
            [1, 0, 0, a],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        Rx = np.array([
            [1, 0, 0, 0],
            [0, np.cos(al), -np.sin(al), 0],
            [0, np.sin(al),  np.cos(al), 0],
            [0, 0, 0, 1]
        ])
        prod = Rz @ Tz @ Tx @ Rx
        formula = dh_matrix(th, d, a, al)
        diff = np.max(np.abs(prod - formula))
        assert diff < 1e-12, f"DH Matrix product mismatch! diff={diff}"
    print("[PASS] DH matrix formulation exactly matches standard product definition.")

def test_fk_and_wrist_center():
    # Parameters from table in Section 2.3:
    # 1: a1=0, alpha1=pi/2, d1=125.0, theta1=q1
    # 2: a2=210.0, alpha2=0, d2=0, theta2=q2
    # 3: a3=45.0, alpha3=pi/2, d3=0, theta3=q3 + pi/2 (or q3?)
    # 4: a4=0, alpha4=-pi/2, d4=195.0, theta4=q4
    # 5: a5=0, alpha5=pi/2, d5=0, theta5=q5
    # 6: a6=0, alpha6=0, d6=85.0, theta6=q6
    d1 = 125.0
    a2 = 210.0
    a3 = 45.0
    d4 = 195.0
    d6 = 85.0

    print("Checking wrist center equation with theta3 = q3 + pi/2 vs theta3 = q3:")
    np.random.seed(42)
    for option in ["with_offset", "without_offset"]:
        errors = []
        for _ in range(50):
            q = np.random.uniform(-1.0, 1.0, size=6)
            q1, q2, q3, q4, q5, q6 = q

            A1 = dh_matrix(q1, d1, 0, np.pi/2)
            A2 = dh_matrix(q2, 0, a2, 0)
            th3 = q3 + np.pi/2 if option == "with_offset" else q3
            A3 = dh_matrix(th3, 0, a3, np.pi/2)
            A4 = dh_matrix(q4, d4, 0, -np.pi/2)
            A5 = dh_matrix(q5, 0, 0, np.pi/2)
            A6 = dh_matrix(q6, d6, 0, 0)

            # T0_4 origin gives wrist center:
            T0_4 = A1 @ A2 @ A3 @ A4
            pw_actual = T0_4[:3, 3]

            # Compare with equation in section 2.3:
            # xw = cos(q1) * [ a2 cos(q2) + a3 cos(q2 + q3) - d4 sin(q2 + q3) ]
            # yw = sin(q1) * [ a2 cos(q2) + a3 cos(q2 + q3) - d4 sin(q2 + q3) ]
            # zw = d1 + a2 sin(q2) + a3 sin(q2 + q3) + d4 cos(q2 + q3)
            xw_eq = np.cos(q1) * (a2 * np.cos(q2) + a3 * np.cos(q2 + q3) - d4 * np.sin(q2 + q3))
            yw_eq = np.sin(q1) * (a2 * np.cos(q2) + a3 * np.cos(q2 + q3) - d4 * np.sin(q2 + q3))
            zw_eq = d1 + a2 * np.sin(q2) + a3 * np.sin(q2 + q3) + d4 * np.cos(q2 + q3)
            pw_eq = np.array([xw_eq, yw_eq, zw_eq])

            err = np.linalg.norm(pw_actual - pw_eq)
            errors.append(err)
        max_err = np.max(errors)
        print(f"Option {option}: max error = {max_err:.4f} mm")

if __name__ == "__main__":
    test_dh_matrix_derivation()
    test_fk_and_wrist_center()
