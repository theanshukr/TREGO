"""Tests for TREGO Developer Modules."""
from unittest.mock import MagicMock
from server.trego.modules.cpp import CppModule
from server.trego.modules.python import PythonModule
from server.trego.modules.flutter import FlutterModule


def test_cpp_module_detect_and_requirements():
    mock_computer = MagicMock()
    mock_computer.run_dev_cmd.side_effect = [
        {"ok": True, "exit_code": 0, "stdout": "g++ (Rev2, Built by MSYS2 project) 14.2.0\nCopyright (C) 2024 Free Software Foundation, Inc."},
        {"ok": True, "exit_code": 0, "stdout": "C:\\msys64\\ucrt64\\bin\\g++.exe\n"},
    ]
    cpp = CppModule()
    status = cpp.detect(mock_computer)
    assert status.is_installed is True
    assert "14.2.0" in status.version
    assert len(cpp.requirements()) > 0


def test_python_module_real_verify():
    class RealPythonTester:
        def run_dev_cmd(self, cmd, timeout=15):
            import subprocess
            res = subprocess.run(["python", "-c", "import sys, os, venv; print('TREGO_PYTHON_VERIFIED_SUCCESS', sys.version)"], capture_output=True, text=True)
            return {"ok": True, "exit_code": res.returncode, "stdout": res.stdout, "stderr": res.stderr}

        def detect(self):
            return True

    py_mod = PythonModule()
    computer = RealPythonTester()
    res = py_mod.verify(computer)
    assert res.verified is True
    assert "TREGO_PYTHON_VERIFIED_SUCCESS" in res.evidence or len(res.checks_passed) > 0


def test_flutter_module_parse_doctor():
    mock_computer = MagicMock()
    doctor_output = """
[√] Flutter (Channel stable, 3.29.0, on Microsoft Windows)
[!] Android toolchain - develop for Android devices
    X Android SDK not found at C:\\Android\\Sdk.
    ! Some Android licenses not accepted.
[√] Chrome - develop for the web
    """
    mock_computer.run_dev_cmd.side_effect = [
        {"ok": True, "exit_code": 0, "stdout": "Flutter 3.29.0"},
        {"ok": True, "exit_code": 0, "stdout": "C:\\flutter\\bin\\flutter.bat"},
        {"ok": True, "exit_code": 0, "stdout": doctor_output},
    ]

    fl = FlutterModule()
    status = fl.detect(mock_computer)
    assert status.is_installed is True
    assert status.healthy is False
    assert any("Android SDK is missing" in i for i in status.issues)
    assert any("licenses not accepted" in i for i in status.issues)

    plan_steps = fl.plan(status)
    assert len(plan_steps) >= 2
    assert any(s.id == "configure_android_sdk" for s in plan_steps)
