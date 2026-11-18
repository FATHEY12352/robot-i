#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
ROBOI Mathematical & Physical Formulation Empirical Adversarial Suite
Challenger 1 (teamwork_challenger)
Working Directory: d:\projekt\ARM\.agents\teamwork\challenger_1
"""

import sys
import os
import numpy as np

# Ensure working directory is on path
workdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(workdir)

from challenge_01_kinematics import test_dh_matrix_derivation
from challenge_03_jacobian import test_singularities_and_yoshikawa
from challenge_04_euler_lagrange import test_euler_lagrange_and_skew_symmetry
from challenge_05_quintic import test_quintic_polynomial_and_minimum_jerk
from challenge_06_impedance import test_cartesian_impedance_control
from challenge_07_thermal import test_coupled_thermal_model
from challenge_08_structural import test_cantilever_deflection_and_flutter

def run_suite():
    print("=" * 80)
    print("RUNNING EMPIRICAL ADVERSARIAL CHALLENGE SUITE (CHALLENGER 1)")
    print("=" * 80)

    # 1. DH Transformation Matrix Derivation
    print("\n>>> SUITE 1: DH Transformation Matrix")
    test_dh_matrix_derivation()

    # 2. Jacobian, Singularities, and Yoshikawa Manipulability
    print("\n>>> SUITE 2: Jacobian Matrix, Singularities & Yoshikawa Manipulability")
    test_singularities_and_yoshikawa()

    # 3. Euler-Lagrange Dynamics & Skew-Symmetry (M_dot - 2C)
    print("\n>>> SUITE 3: Euler-Lagrange Dynamics & Skew-Symmetry")
    test_euler_lagrange_and_skew_symmetry()

    # 4. Quintic Polynomials & Minimum Jerk
    print("\n>>> SUITE 4: Quintic Polynomials & Minimum Jerk Trajectory")
    test_quintic_polynomial_and_minimum_jerk()

    # 5. Cartesian Impedance Control
    print("\n>>> SUITE 5: Cartesian Impedance Control & Lyapunov Stability")
    test_cartesian_impedance_control()

    # 6. Coupled Thermal Model & I^2 R Copper Heating
    print("\n>>> SUITE 6: Coupled Thermal Model & I^2 R Heating")
    test_coupled_thermal_model()

    # 7. Cantilever Deflection & Structural Flutter
    print("\n>>> SUITE 7: Cantilever Deflection & Structural Flutter")
    test_cantilever_deflection_and_flutter()

    print("\n" + "=" * 80)
    print("ALL NUMERICAL SIMULATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_suite()
