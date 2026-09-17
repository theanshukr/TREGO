"""Tests for TREGO Diagnostic Engine and Troubleshooter."""
from server.trego.diagnostics import DiagnosticEngine
from server.trego.troubleshooter import Troubleshooter


def test_diagnose_command_not_found():
    engine = DiagnosticEngine()
    err = "'g++' is not recognized as an internal or external command, operable program or batch file."
    diag = engine.diagnose_error(err)
    assert diag is not None
    assert diag.error_type == "CommandNotFoundOrPathMissing"
    assert "g++" in diag.probable_cause


def test_diagnose_flutter_android_sdk():
    engine = DiagnosticEngine()
    err = "[!] Android toolchain - develop for Android devices\n    X Unable to locate Android SDK."
    diag = engine.diagnose_error(err)
    assert diag is not None
    assert diag.error_type == "FlutterAndroidSdkMissing"
    assert "ANDROID_HOME" in diag.suggested_fix


def test_diagnose_python_module_missing():
    engine = DiagnosticEngine()
    err = "ModuleNotFoundError: No module named 'torch'"
    diag = engine.diagnose_error(err)
    assert diag is not None
    assert diag.error_type == "PythonModuleMissing"
    assert "pip install torch" in diag.command_to_fix


def test_troubleshooter_diagnostic_loop():
    troubleshooter = Troubleshooter()
    plan = troubleshooter.troubleshoot(
        error_output="ModuleNotFoundError: No module named 'requests'",
        goal_context="python setup",
    )
    assert plan is not None
    assert "requests" in plan.cause or "requests" in plan.proposed_action
    assert plan.command == "pip install requests"
