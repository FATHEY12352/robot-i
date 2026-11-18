#!/usr/bin/env python3
"""
E2E Test Runner for ESP32-S3 Compact 2-Layer Robotic Controller PCB (V4)
Discovers and executes Tiers 1-4 tests, provides progressive milestone reporting,
and prints a formatted summary table.
"""

import sys
import os
import argparse
import unittest
import time
from typing import Dict, List, Tuple, Any

# Ensure tests directory is on path
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

import test_tier1_features
import test_tier2_boundary
import test_tier3_cross
import test_tier4_workload

BANNER = """
================================================================================
     ESP32-S3 ROBOTIC CONTROLLER PCB (V4) - E2E VERIFICATION TEST RUNNER       
================================================================================
"""

class CustomTestResult(unittest.TestResult):
    def __init__(self, verbose=False):
        super().__init__()
        self.verbose = verbose
        self.passed_tests = []
        self.deferred_tests = []
        self.failed_tests = []
        self.error_tests = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed_tests.append(test)
        if self.verbose:
            print(f"  [PASS]     {test.id()}")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.deferred_tests.append((test, reason))
        if self.verbose:
            print(f"  [DEFERRED] {test.id()} -> {reason}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.failed_tests.append((test, err))
        if self.verbose:
            print(f"  [FAIL]     {test.id()}")

    def addError(self, test, err):
        super().addError(test, err)
        self.error_tests.append((test, err))
        if self.verbose:
            print(f"  [ERROR]    {test.id()}")

def run_suite(suite: unittest.TestSuite, verbose: bool = False) -> CustomTestResult:
    result = CustomTestResult(verbose=verbose)
    suite.run(result)
    return result

def print_summary_table(results_by_tier: Dict[str, CustomTestResult], elapsed_time: float, strict: bool, milestone: str):
    print("\n" + "=" * 80)
    print(f"                     E2E TEST EXECUTION SUMMARY (Mode: {milestone.upper() if milestone else 'PROGRESSIVE'})")
    print("=" * 80)
    print(f"{'Tier / Module':<30} | {'Total':<6} | {'Passed':<7} | {'Deferred':<9} | {'Failed':<7} | {'Status':<8}")
    print("-" * 80)
    
    total_all = 0
    passed_all = 0
    deferred_all = 0
    failed_all = 0
    
    for tier_name, res in results_by_tier.items():
        total = len(res.passed_tests) + len(res.deferred_tests) + len(res.failed_tests) + len(res.error_tests)
        passed = len(res.passed_tests)
        deferred = len(res.deferred_tests)
        failed = len(res.failed_tests) + len(res.error_tests)
        
        total_all += total
        passed_all += passed
        deferred_all += deferred
        failed_all += failed
        
        status = "FAIL" if failed > 0 else ("DEFERRED" if deferred > 0 and passed == 0 else "PASS")
        print(f"{tier_name:<30} | {total:<6} | {passed:<7} | {deferred:<9} | {failed:<7} | {status:<8}")

    print("-" * 80)
    overall_status = "FAIL" if failed_all > 0 else "SUCCESS"
    print(f"{'TOTALS':<30} | {total_all:<6} | {passed_all:<7} | {deferred_all:<9} | {failed_all:<7} | {overall_status:<8}")
    print("=" * 80)
    print(f"Execution Time: {elapsed_time:.3f}s | KiCad 10.0.6 Environment | 31-Feature Coverage")
    
    if failed_all > 0:
        print("\n[!] DETAILED FAILURE BREAKDOWN:")
        for tier_name, res in results_by_tier.items():
            for test, err in res.failed_tests:
                print(f"  * {test.id()}:")
                for line in str(err[1]).strip().split('\n')[-3:]:
                    print(f"      {line}")
            for test, err in res.error_tests:
                print(f"  * {test.id()} (ERROR):")
                for line in str(err[1]).strip().split('\n')[-3:]:
                    print(f"      {line}")
        print("=" * 80)

def main():
    parser = argparse.ArgumentParser(description="ESP32-S3 PCB (V4) E2E Test Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run only specified tier")
    parser.add_argument("--milestone", type=str, choices=["M1", "M2", "M3", "M4"], default="", help="Enforce milestone gate")
    parser.add_argument("--strict", action="store_true", help="Fail if any milestone artifact is missing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print verbose test results")
    args = parser.parse_args()

    if args.strict or args.milestone == "M4":
        os.environ["STRICT_E2E"] = "1"
    else:
        os.environ["STRICT_E2E"] = "0"

    print(BANNER)
    start_time = time.time()
    loader = unittest.TestLoader()
    
    tier_modules = {
        "Tier 1 (31 Features)": test_tier1_features,
        "Tier 2 (Boundary & Limits)": test_tier2_boundary,
        "Tier 3 (Cross & Strapping)": test_tier3_cross,
        "Tier 4 (Workload & Output)": test_tier4_workload
    }

    if args.tier:
        tier_key = list(tier_modules.keys())[args.tier - 1]
        tier_modules = {tier_key: tier_modules[tier_key]}

    results = {}
    for tier_name, mod in tier_modules.items():
        if args.verbose:
            print(f"\n--> Executing {tier_name}...")
        suite = loader.loadTestsFromModule(mod)
        res = run_suite(suite, verbose=args.verbose)
        results[tier_name] = res

    elapsed = time.time() - start_time
    print_summary_table(results, elapsed, args.strict, args.milestone)

    # Calculate exit code
    total_failures = sum(len(r.failed_tests) + len(r.error_tests) for r in results.values())
    sys.exit(1 if total_failures > 0 else 0)

if __name__ == "__main__":
    main()
