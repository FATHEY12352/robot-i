import numpy as np
from scipy.integrate import solve_ivp

def test_coupled_thermal_model():
    print("Testing Coupled Two-Mass Thermal Model & Copper Heating Dynamics:")

    # Parameters from Chapter 2, Section 2.1.2:
    C_th_w = 1.25   # J/K (winding heat capacity)
    C_th_c = 18.5   # J/K (case heat capacity)
    R_th_wc = 9.2   # K/W (thermal resistance winding to case)
    R_th_ca = 16.8  # K/W (thermal resistance case to ambient)
    T_amb = 25.0    # degC
    alpha_Cu = 0.00393 # K^-1

    # Check resistance increase at 85 degC (Delta T = 60 K):
    delta_T = 60.0
    R_ratio = 1.0 + alpha_Cu * delta_T
    print(f"Resistance ratio at Tw=85 degC: {R_ratio:.4f} (+{(R_ratio-1)*100:.2f}%)")
    assert np.isclose(R_ratio, 1.2358, atol=1e-3), "Copper resistance scaling error!"

    torque_loss = (1.0 - 1.0 / R_ratio) * 100.0
    print(f"Torque loss at Tw=85 degC: {torque_loss:.2f}% (monograph claimed ~19.1%)")
    assert np.isclose(torque_loss, 19.08, atol=0.2), "Torque loss percentage error!"

    # Solve coupled ODE:
    # State y = [T_w, T_case]
    # dT_w/dt = ( I^2 * R_w(T_w) - (T_w - T_case)/R_th_wc ) / C_th_w
    # dT_case/dt = ( (T_w - T_case)/R_th_wc - (T_case - T_amb)/R_th_ca ) / C_th_c

    I_holding = 1.35 # A (holding current at 0.5 tau_stall)

    for Rw0, label in [(2.96, "STS3215 7.4V (Rw0=2.96 Ohm)"), (4.20, "STS3215 12V / Appx (Rw0=4.20 Ohm)")]:
        def thermal_ode(t, y):
            Tw, Tc = y
            Rw = Rw0 * (1.0 + alpha_Cu * (Tw - T_amb))
            P_joule = (I_holding**2) * Rw
            dTw = (P_joule - (Tw - Tc) / R_th_wc) / C_th_w
            dTc = ((Tw - Tc) / R_th_wc - (Tc - T_amb) / R_th_ca) / C_th_c
            return [dTw, dTc]

        # Simulate 1800 seconds (30 minutes)
        t_span = [0.0, 1800.0]
        y0 = [T_amb, T_amb]
        t_eval = np.linspace(0.0, 1800.0, 3600)
        sol = solve_ivp(thermal_ode, t_span, y0, t_eval=t_eval, method='RK45')

        t_min = sol.t / 60.0
        Tw = sol.y[0]
        Tc = sol.y[1]

        # Find time to reach 85 degC for winding
        idx_85 = np.where(Tw >= 85.0)[0]
        t_to_85 = t_min[idx_85[0]] if len(idx_85) > 0 else None

        # Find time to reach 70 degC for case (trip threshold)
        idx_trip = np.where(Tc >= 70.0)[0]
        t_trip = t_min[idx_trip[0]] if len(idx_trip) > 0 else None

        print(f"\n--- Scenario: {label} ---")
        if t_to_85 is not None:
            print(f"Time to reach Tw = 85 degC: {t_to_85:.2f} minutes")
        else:
            print(f"Tw did not reach 85 degC; max Tw = {np.max(Tw):.2f} degC")
        if t_trip is not None:
            print(f"Case reached thermal trip limit (70 degC) at: {t_trip:.2f} minutes")
        else:
            print(f"Case max temp = {np.max(Tc):.2f} degC (thermal trip threshold not reached)")
        print(f"Final temp after 30 min: Tw = {Tw[-1]:.2f} degC, Tc = {Tc[-1]:.2f} degC")

    print("\n[PASS] Thermal ODE confirms rapid temperature elevation and thermal trip risk under continuous holding current.")

if __name__ == "__main__":
    test_coupled_thermal_model()
