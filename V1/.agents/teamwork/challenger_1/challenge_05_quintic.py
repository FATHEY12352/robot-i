import numpy as np
from scipy.integrate import quad

def test_quintic_polynomial_and_minimum_jerk():
    print("Testing Quintic Polynomial Trajectory and Minimum Jerk Formulation:")

    # Test parameters
    np.random.seed(42)
    for _ in range(100):
        q0 = np.random.uniform(-np.pi, np.pi)
        qf = np.random.uniform(-np.pi, np.pi)
        tf = np.random.uniform(0.5, 5.0)

        # 1. Analytical coefficients reported in monograph
        a0 = q0
        a1 = 0.0
        a2 = 0.0
        a3 = 10.0 * (qf - q0) / (tf**3)
        a4 = -15.0 * (qf - q0) / (tf**4)
        a5 = 6.0 * (qf - q0) / (tf**5)
        coeffs_reported = np.array([a0, a1, a2, a3, a4, a5])

        # 2. Linear system matrix for boundary conditions:
        # [ 1   0    0     0      0       0    ] [a0]   [q0]
        # [ 1  tf  tf^2  tf^3   tf^4    tf^5   ] [a1]   [qf]
        # [ 0   1    0     0      0       0    ] [a2] = [ 0]
        # [ 0   1  2tf   3tf^2  4tf^3   5tf^4  ] [a3]   [ 0]
        # [ 0   0    2     0      0       0    ] [a4]   [ 0]
        # [ 0   0    2   6tf    12tf^2  20tf^3 ] [a5]   [ 0]
        M_bc = np.array([
            [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [1.0, tf, tf**2, tf**3, tf**4, tf**5],
            [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 2*tf, 3*tf**2, 4*tf**3, 5*tf**4],
            [0.0, 0.0, 2.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 2.0, 6*tf, 12*tf**2, 20*tf**3]
        ])
        b_bc = np.array([q0, qf, 0.0, 0.0, 0.0, 0.0])
        coeffs_solved = np.linalg.solve(M_bc, b_bc)

        diff = np.max(np.abs(coeffs_reported - coeffs_solved))
        assert diff < 1e-11, f"Analytical quintic coefficients mismatch! diff={diff}"

        # 3. Check boundary conditions directly
        t = np.array([0.0, tf])
        q_eval = a0 + a1*t + a2*t**2 + a3*t**3 + a4*t**4 + a5*t**5
        q_dot_eval = a1 + 2*a2*t + 3*a3*t**2 + 4*a4*t**3 + 5*a5*t**4
        q_ddot_eval = 2*a2 + 6*a3*t + 12*a4*t**2 + 20*a5*t**3

        assert np.isclose(q_eval[0], q0, atol=1e-12)
        assert np.isclose(q_eval[1], qf, atol=1e-12)
        assert np.isclose(q_dot_eval[0], 0.0, atol=1e-12)
        assert np.isclose(q_dot_eval[1], 0.0, atol=1e-12)
        assert np.isclose(q_ddot_eval[0], 0.0, atol=1e-12)
        assert np.isclose(q_ddot_eval[1], 0.0, atol=1e-12)

    print("[PASS] Analytical coefficients a0..a5 satisfy all 6 boundary conditions to machine precision.")

    # 4. Variational test of Minimum Jerk property:
    # J(q) = 0.5 * int_0^tf (q_dddot(t))^2 dt
    # Test that any perturbation delta_q(t) with delta_q=0, delta_q_dot=0, delta_q_ddot=0 at 0 and tf INCREASES jerk cost
    q0 = 0.0
    qf = 1.0
    tf = 2.0
    a3 = 10.0 * (qf - q0) / (tf**3)
    a4 = -15.0 * (qf - q0) / (tf**4)
    a5 = 6.0 * (qf - q0) / (tf**5)

    def jerk_quintic(t):
        return 6*a3 + 24*a4*t + 60*a5*t**2

    cost_optimal, _ = quad(lambda t: 0.5 * jerk_quintic(t)**2, 0.0, tf)

    # Add perturbations of the form: delta_q(t) = eps * t^3 * (tf - t)^3
    # This automatically satisfies delta_q = delta_q_dot = delta_q_ddot = 0 at t=0 and t=tf
    for eps in [-0.5, -0.1, 0.1, 0.5, 1.0]:
        def delta_q_dddot(t):
            # delta_q = eps * (tf*t - t^2)^3
            # Third derivative of t^3 * (tf - t)^3
            # Let's use finite diff or analytical
            # delta = eps * (tf^3 t^3 - 3 tf^2 t^4 + 3 tf t^5 - t^6)
            # d/dt = eps * (3 tf^3 t^2 - 12 tf^2 t^3 + 15 tf t^4 - 6 t^5)
            # d2/dt2 = eps * (6 tf^3 t - 36 tf^2 t^2 + 60 tf t^3 - 30 t^4)
            # d3/dt3 = eps * (6 tf^3 - 72 tf^2 t + 180 tf t^2 - 120 t^3)
            return eps * (6*tf**3 - 72*tf**2*t + 180*tf*t**2 - 120*t**3)

        cost_perturbed, _ = quad(lambda t: 0.5 * (jerk_quintic(t) + delta_q_dddot(t))**2, 0.0, tf)
        delta_cost = cost_perturbed - cost_optimal
        assert delta_cost > 0, f"Perturbation did not increase jerk cost! delta={delta_cost}"

    print(f"Optimal jerk cost J* = {cost_optimal:.4f}, all perturbations strictly increase cost.")
    print("[PASS] Cartesian minimum jerk variational principle empirically verified!")

if __name__ == "__main__":
    test_quintic_polynomial_and_minimum_jerk()
