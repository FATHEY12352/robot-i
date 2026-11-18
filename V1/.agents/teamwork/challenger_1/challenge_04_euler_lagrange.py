import numpy as np

def test_euler_lagrange_and_skew_symmetry():
    print("Testing Euler-Lagrange Dynamics and Skew-Symmetry Property (M_dot - 2C):")

    # Consider a 2-link planar manipulator:
    # m1, m2 = link masses; l1, l2 = link lengths; lc1, lc2 = COM distances; I1, I2 = moments of inertia
    m1, m2 = 1.5, 0.8 # kg
    l1, l2 = 0.25, 0.20 # m
    lc1, lc2 = 0.125, 0.10 # m
    I1, I2 = (1/12)*m1*l1**2, (1/12)*m2*l2**2
    g = 9.81

    def M_mat(q):
        q1, q2 = q
        m11 = I1 + I2 + m1*lc1**2 + m2*(l1**2 + lc2**2 + 2*l1*lc2*np.cos(q2))
        m12 = I2 + m2*(lc2**2 + l1*lc2*np.cos(q2))
        m21 = m12
        m22 = I2 + m2*lc2**2
        return np.array([[m11, m12], [m21, m22]])

    def C_mat_christoffel(q, q_dot):
        # Numerical partial derivatives dM_jk / dq_i
        eps = 1e-7
        n = 2
        dM = np.zeros((n, n, n)) # dM[k, j, i] = d M_kj / dq_i
        for i in range(n):
            q_plus = q.copy()
            q_minus = q.copy()
            q_plus[i] += eps
            q_minus[i] -= eps
            M_plus = M_mat(q_plus)
            M_minus = M_mat(q_minus)
            dM[:, :, i] = (M_plus - M_minus) / (2 * eps)

        # C_kj = 0.5 * sum_i ( dM_kj/dq_i + dM_ki/dq_j - dM_ij/dq_k ) * q_dot_i
        # Matches equation in Chapter 2, line 407
        C = np.zeros((n, n))
        for k in range(n):
            for j in range(n):
                c_kj = 0.0
                for i in range(n):
                    gamma = 0.5 * (dM[k, j, i] + dM[k, i, j] - dM[i, j, k])
                    c_kj += gamma * q_dot[i]
                C[k, j] = c_kj
        return C

    # Stress-test over 500 random states (q, q_dot)
    np.random.seed(42)
    max_skew_viol = 0.0
    max_quad_viol = 0.0
    min_eigenval = 1e9

    for _ in range(500):
        q = np.random.uniform(-np.pi, np.pi, 2)
        q_dot = np.random.uniform(-5.0, 5.0, 2)

        M = M_mat(q)
        # Check symmetry and positive definiteness
        symm_err = np.max(np.abs(M - M.T))
        assert symm_err < 1e-12, "M matrix is not symmetric!"
        eigvals = np.linalg.eigvalsh(M)
        assert np.all(eigvals > 0), "M matrix is not positive definite!"
        min_eigenval = min(min_eigenval, np.min(eigvals))

        # Compute M_dot numerically: dM/dt = sum_i (dM/dq_i * q_dot_i)
        eps = 1e-7
        M_dot = np.zeros((2, 2))
        for i in range(2):
            q_plus = q.copy()
            q_minus = q.copy()
            q_plus[i] += eps
            q_minus[i] -= eps
            M_dot += ((M_mat(q_plus) - M_mat(q_minus)) / (2 * eps)) * q_dot[i]

        C = C_mat_christoffel(q, q_dot)
        S = M_dot - 2.0 * C

        # Test skew-symmetry: S + S^T = 0
        skew_err = np.max(np.abs(S + S.T))
        max_skew_viol = max(max_skew_viol, skew_err)

        # Test x^T S x = 0 for 10 random vectors
        for _ in range(10):
            x = np.random.uniform(-10.0, 10.0, 2)
            quad = x.T @ S @ x
            max_quad_viol = max(max_quad_viol, abs(quad))

    print(f"Minimum eigenvalue of M(q): {min_eigenval:.6f} > 0 (strictly positive definite)")
    print(f"Max skew-symmetry violation |(M_dot - 2C) + (M_dot - 2C)^T|: {max_skew_viol:.6e}")
    print(f"Max quadratic form violation |x^T (M_dot - 2C) x|: {max_quad_viol:.6e}")
    assert max_skew_viol < 1e-6, "Skew-symmetry property failed!"
    assert max_quad_viol < 1e-5, "Quadratic zero energy conservation property failed!"
    print("[PASS] Euler-Lagrange dynamics and skew-symmetry formulation empirically confirmed!")

if __name__ == "__main__":
    test_euler_lagrange_and_skew_symmetry()
