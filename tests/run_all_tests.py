"""Standalone Test Runner for TREGO."""
import sys
import os

# Ensure repo root is on sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import tests.test_command_policy as t_policy
import tests.test_goal_interpreter as t_goal
import tests.test_troubleshooter as t_trouble
import tests.test_modules as t_mod
import tests.test_real_input as t_input

tests_to_run = [
    ("Command Policy: Read-Only", t_policy.test_read_only_commands_allowed),
    ("Command Policy: High Risk / Permission Gate", t_policy.test_high_risk_commands_require_permission),
    ("Command Policy: Blocked Destructive", t_policy.test_blocked_destructive_commands),
    ("Goal Interpreter: C++ Goals", t_goal.test_interpret_cpp_goals),
    ("Goal Interpreter: Flutter Goals", t_goal.test_interpret_flutter_goals),
    ("Goal Interpreter: Python Goals", t_goal.test_interpret_python_goals),
    ("Goal Interpreter: GitHub Onboarding", t_goal.test_interpret_github_repo),
    ("Diagnostics: Command Not Found / PATH", t_trouble.test_diagnose_command_not_found),
    ("Diagnostics: Flutter Android SDK", t_trouble.test_diagnose_flutter_android_sdk),
    ("Diagnostics: Python Module Missing", t_trouble.test_diagnose_python_module_missing),
    ("Troubleshooter: Diagnostic Loop", t_trouble.test_troubleshooter_diagnostic_loop),
    ("Modules: C++ Detect & Requirements", t_mod.test_cpp_module_detect_and_requirements),
    ("Modules: Python Real Verification", t_mod.test_python_module_real_verify),
    ("Modules: Flutter Doctor & Diagnostics", t_mod.test_flutter_module_parse_doctor),
    ("Real Input: Protocol & Tool Schemas", t_input.test_real_input_protocol_and_schemas),
    ("Real Input: Mouse & Keyboard Validation", t_input.test_real_input_arg_validation),
    ("Real Input: Client & Executor Proxies", t_input.test_real_input_proxies),
]

passed = 0
failed = 0

print("=" * 60)
print("RUNNING TREGO TEST SUITE")
print("=" * 60)

for name, fn in tests_to_run:
    try:
        fn()
        print(f"[PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        failed += 1

print("=" * 60)
print(f"Results: {passed} passed, {failed} failed out of {len(tests_to_run)} tests.")
print("=" * 60)

if failed > 0:
    sys.exit(1)
else:
    print("ALL TREGO TESTS PASSED SUCCESSFULLY! [OK]")
