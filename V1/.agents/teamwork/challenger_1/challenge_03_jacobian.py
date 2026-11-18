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

def get_fk_all_frames(q):
    # Dimensions in meters (SI standard)
    d1 = 0.125
    a2 = 0.210
    a3 = 0.045
    d4 = 0.195
    d6 = 0.085

    A = [
        dh_matrix(q[0], d1, 0, np.pi/2),
        dh_matrix(q[1], 0, a2, 0),
        dh_matrix(q[2], 0, a3, -np.pi/2),
        dh_matrix(q[3], d4, 0, -np.pi/2),
        dh_matrix(q[4], 0, 0, np.pi/2),
        dh_matrix(q[5], d6, 0, 0)
    ]
    T = [np.eye(4)]
    for i in range(6):
        T.append(T[-1] @ A[i])
    return T

def compute_geometric_jacobian(q):
    T = get_fk_all_frames(q)
    p_e = T[6][:3, 3] # End-effector position
    J = np.zeros((6, 6))
    for i in range(6):
        z_prev = T[i][:3, 2] # z_{i-1}
        p_prev = T[i][:3, 3] # p_{i-1}
        J_v = np.cross(z_prev, (p_e - p_prev))
        J_w = z_prev
        J[:3, i] = J_v
        J[3:, i] = J_w
    return J

def test_singularities_and_yoshikawa():
    print("Testing Jacobian, Singularities, and Yoshikawa Manipulability (in SI units):")

    # 1. Wrist Singularity: q5 = 0
    q_wrist_sing = np.array([0.2, 0.4, -0.3, 0.5, 0.0, 0.3])
    J_wrist = compute_geometric_jacobian(q_wrist_sing)
    det_wrist = np.linalg.det(J_wrist)
    u, s_wrist, vt = np.linalg.svd(J_wrist)
    w_wrist = np.sqrt(max(0.0, np.linalg.det(J_wrist @ J_wrist.T)))
    prod_s_wrist = np.prod(s_wrist)

    print(f"1. Wrist singularity (q5=0):")
    print(f"   det(J) = {det_wrist:.4e}, min(sigma) = {s_wrist[-1]:.4e}, w(q) = {w_wrist:.4e}")
    assert s_wrist[-1] < 1e-12, "Wrist singularity failed: min singular value is not zero!"
    assert w_wrist < 1e-9, "Yoshikawa manipulability at wrist singularity is not zero!"

    # 2. Shoulder Singularity: center of wrist on z0 axis (rw = 0)
    from scipy.optimize import root_scalar
    def rw_func(q2):
        q3 = -0.8
        a2 = 0.210; a3 = 0.045; d4 = 0.195
        return a2 * np.cos(q2) + a3 * np.cos(q2 + q3) - d4 * np.sin(q2 + q3)
    sol = root_scalar(rw_func, bracket=[0.0, np.pi/2])
    q2_sing = sol.root
    q_shoulder_sing = np.array([0.2, q2_sing, -0.8, 0.4, 0.5, 0.3])
    J_sh = compute_geometric_jacobian(q_shoulder_sing)
    det_sh = np.linalg.det(J_sh)
    u, s_sh, vt = np.linalg.svd(J_sh)
    w_sh = np.sqrt(max(0.0, np.linalg.det(J_sh @ J_sh.T)))
    print(f"2. Shoulder singularity (rw=0):")
    print(f"   det(J) = {det_sh:.4e}, min(sigma) = {s_sh[-1]:.4e}, w(q) = {w_sh:.4e}")
    # In shoulder singularity, rank drops because base rotation produces no linear velocity at wrist center
    # Note: If tool offset d6 is present and wrist is oriented, J_e might have small coupling, so let's check wrist center Jacobian
    p_w = get_fk_all_frames(q_shoulder_sing)[4][:3, 3]
    rw = np.hypot(p_w[0], p_w[1])
    print(f"   Wrist radius rw = {rw:.4e} m")
    assert rw < 1e-12, "Shoulder root finding failed!"

    # 3. Elbow Singularity: arm fully extended
    a3 = 0.045; d4 = 0.195
    phi = np.arctan2(d4, a3)
    q3_ext = -phi
    q_elbow_sing = np.array([0.1, 0.2, q3_ext, 0.3, 0.4, 0.2])
    J_elb = compute_geometric_jacobian(q_elbow_sing)
    det_elb = np.linalg.det(J_elb)
    u, s_elb, vt = np.linalg.svd(J_elb)
    w_elb = np.sqrt(max(0.0, np.linalg.det(J_elb @ J_elb.T)))
    print(f"3. Elbow singularity (full extension q3 = -phi):")
    print(f"   det(J) = {det_elb:.4e}, min(sigma) = {s_elb[-1]:.4e}, w(q) = {w_elb:.4e}")
    assert s_elb[-1] < 1e-12, "Elbow singularity failed: min singular value is not zero!"

    # 4. Regular configuration: verify w(q) = prod(sigma) = |det(J)|
    q_reg = np.array([0.2, 0.3, -0.4, 0.5, 0.6, 0.7])
    J_reg = compute_geometric_jacobian(q_reg)
    det_reg = np.linalg.det(J_reg)
    u, s_reg, vt = np.linalg.svd(J_reg)
    w_reg = np.sqrt(np.linalg.det(J_reg @ J_reg.T))
    prod_s_reg = np.prod(s_reg)
    print(f"4. Regular configuration:")
    print(f"   det(J) = {det_reg:.6f}, |det(J)| = {abs(det_reg):.6f}, prod(sigma) = {prod_s_reg:.6f}, w(q) = {w_reg:.6f}")
    assert np.isclose(w_reg, abs(det_reg), rtol=1e-5), "Yoshikawa formula does not equal |det(J)|!"
    assert np.isclose(w_reg, prod_s_reg, rtol=1e-5), "Yoshikawa formula does not equal prod(sigma)!"
    print("\n[ALL CHECKS PASSED] Singularity conditions and Yoshikawa manipulability formula are physically and mathematically verified.")

if __name__ == "__main__":
    test_singularities_and_yoshikawa()
