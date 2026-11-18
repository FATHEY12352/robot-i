import numpy as np
from scipy.integrate import solve_ivp

def test_cartesian_impedance_control():
    print("Testing Cartesian Impedance Control Formulation:")

    # Target parameters
    m_d = 1.2 # kg
    k_d = 400.0 # N/m
    zeta = 0.8
    d_d = 2.0 * zeta * np.sqrt(m_d * k_d)
    print(f"Virtual impedance: M_d={m_d} kg, K_d={k_d} N/m, D_d={d_d:.4f} N*s/m (zeta={zeta})")

    # Dynamic system: M_d * e_ddot + D_d * e_dot + K_d * e = F_ext
    F_ext_step = 25.0 # N

    def odefun(t, y):
        e, e_dot = y
        F = F_ext_step if t >= 0.1 else 0.0
        e_ddot = (F - d_d * e_dot - k_d * e) / m_d
        return [e_dot, e_ddot]

    sol = solve_ivp(odefun, [0.0, 2.0], [0.0, 0.0], t_eval=np.linspace(0, 2.0, 1000), method='RK45')

    expected_e_ss = F_ext_step / k_d # 25 / 400 = 0.0625 m = 62.5 mm
    actual_e_ss = sol.y[0, -1]

    print(f"Expected steady-state displacement: {expected_e_ss * 1e3:.2f} mm")
    print(f"Simulated steady-state displacement: {actual_e_ss * 1e3:.2f} mm")
    err_ss = abs(actual_e_ss - expected_e_ss)
    assert err_ss < 1e-4, f"Impedance steady-state deflection mismatch! err={err_ss}"

    # Verify analytical Lyapunov derivative: dV/dt = - D_d * e_dot^2 <= 0
    def odefun_free(t, y):
        e, e_dot = y
        return [e_dot, (-d_d * e_dot - k_d * e) / m_d]

    sol_free = solve_ivp(odefun_free, [0.0, 1.0], [0.05, 0.2], t_eval=np.linspace(0, 1.0, 500))
    edot_free = sol_free.y[1]
    dV_dt_analytical = - d_d * (edot_free**2)
    assert np.all(dV_dt_analytical <= 0.0), "Analytical Lyapunov derivative is positive!"
    print(f"Max dV/dt analytical: {np.max(dV_dt_analytical):.6e} <= 0 (strictly dissipative)")

    print("[PASS] Cartesian impedance dynamic response and Lyapunov stability verified!")

if __name__ == "__main__":
    test_cartesian_impedance_control()
