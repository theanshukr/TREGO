"""Python Developer Environment Module for TREGO."""
from __future__ import annotations

import re
from typing import Any

from server.trego.modules.base import BaseDevModule, ModuleStatus, PlanStep, VerificationOutcome


class PythonModule(BaseDevModule):
    name = "python"
    display_name = "Python Development Environment"

    def detect(self, computer: Any) -> ModuleStatus:
        status = ModuleStatus(is_installed=False)

        # 1. Probe 'python --version'
        res = computer.run_dev_cmd("python --version")
        if res.get("ok") and res.get("exit_code") == 0:
            stdout = res.get("stdout", "").strip() or res.get("stderr", "").strip()
            match = re.search(r"Python\s+([\d\.]+)", stdout)
            version = match.group(1) if match else "Installed"

            where_res = computer.run_dev_cmd("where python")
            path = where_res.get("stdout", "").splitlines()[0] if where_res.get("ok") and where_res.get("stdout") else "PATH"

            status.is_installed = True
            status.version = f"Python {version}"
            status.path = path
            status.healthy = True
            status.details["pip"] = self._check_pip(computer)
            return status

        # 2. Probe Windows Python launcher 'py --version'
        py_res = computer.run_dev_cmd("py --version")
        if py_res.get("ok") and py_res.get("exit_code") == 0:
            stdout = py_res.get("stdout", "").strip() or py_res.get("stderr", "").strip()
            match = re.search(r"Python\s+([\d\.]+)", stdout)
            version = match.group(1) if match else "Installed via py launcher"
            status.is_installed = True
            status.version = f"Python {version} (py launcher)"
            status.healthy = True
            status.details["pip"] = self._check_pip(computer)
            return status

        status.is_installed = False
        status.issues.append("Python runtime not detected in system PATH or py launcher.")
        status.healthy = False
        return status

    def _check_pip(self, computer: Any) -> bool:
        res = computer.run_dev_cmd("pip --version")
        return bool(res.get("ok") and res.get("exit_code") == 0)

    def requirements(self) -> list[str]:
        return [
            "Python 3.8+ interpreter runtime",
            "Pip package manager",
            "Venv (Virtual Environment) module support",
            "Verification: Execution of Python script and module imports",
        ]

    def plan(self, status: ModuleStatus, target_config: dict[str, Any] | None = None) -> list[PlanStep]:
        steps: list[PlanStep] = []
        if not status.is_installed or not status.healthy:
            steps.append(
                PlanStep(
                    id="install_python",
                    title="Install Python 3 Runtime",
                    description="Install the latest stable Python 3 release via winget",
                    command="winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements",
                    requires_permission=True,
                    what="Install Python 3.12 runtime and standard tools via winget",
                    why="Required for Python development and running Python applications",
                    impact="Installs Python 3.12 and adds python/pip to PATH",
                )
            )
        return steps

    def verify(self, computer: Any) -> VerificationOutcome:
        outcome = VerificationOutcome(verified=False, module_name=self.name)

        # Test 1: Check detection
        detect_res = self.detect(computer)
        if not detect_res.is_installed:
            outcome.checks_failed.append("Python interpreter check")
            outcome.error_message = "Python interpreter is not available."
            return outcome
        outcome.checks_passed.append(f"Detected runtime: {detect_res.version}")

        # Test 2: Execute inline Python script to test standard library & venv capability
        verify_cmd = 'python -c "import sys, os, venv; print(\'TREGO_PYTHON_VERIFIED_SUCCESS\', sys.version)"'
        exec_res = computer.run_dev_cmd(verify_cmd, timeout=15)

        if not exec_res.get("ok") or exec_res.get("exit_code") != 0:
            # Fallback to py launcher
            verify_cmd = 'py -c "import sys, os, venv; print(\'TREGO_PYTHON_VERIFIED_SUCCESS\', sys.version)"'
            exec_res = computer.run_dev_cmd(verify_cmd, timeout=15)

        stdout = exec_res.get("stdout", "")
        if "TREGO_PYTHON_VERIFIED_SUCCESS" not in stdout:
            outcome.checks_failed.append("Python script execution and module imports")
            outcome.error_message = f"Python execution failed: {exec_res.get('stderr') or exec_res.get('stdout')}"
            return outcome

        outcome.checks_passed.append("Executed verification script; verified standard library and venv module")
        outcome.verified = True
        outcome.evidence = f"Successfully verified Python runtime ({detect_res.version}) with full venv support."
        return outcome
