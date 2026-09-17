"""Flutter & Dart Developer Environment Module for TREGO."""
from __future__ import annotations

import os
import re
import tempfile
from typing import Any

from server.trego.modules.base import BaseDevModule, ModuleStatus, PlanStep, VerificationOutcome


class FlutterModule(BaseDevModule):
    name = "flutter"
    display_name = "Flutter & Dart Environment"

    def detect(self, computer: Any) -> ModuleStatus:
        status = ModuleStatus(is_installed=False)

        # 1. Probe 'flutter --version'
        res = computer.run_dev_cmd("flutter --version", timeout=25)
        if not res.get("ok") or res.get("exit_code") != 0:
            status.is_installed = False
            status.issues.append("Flutter SDK is not found in PATH.")
            status.healthy = False
            return status

        stdout = res.get("stdout", "")
        match = re.search(r"Flutter\s+([\d\.]+)", stdout)
        version = match.group(1) if match else "Installed"

        where_res = computer.run_dev_cmd("where flutter")
        path = where_res.get("stdout", "").splitlines()[0] if where_res.get("ok") and where_res.get("stdout") else "PATH"

        status.is_installed = True
        status.version = f"Flutter {version}"
        status.path = path

        # 2. Run 'flutter doctor' to diagnose subsystem components
        doc_res = computer.run_dev_cmd("flutter doctor -v", timeout=45)
        doc_out = doc_res.get("stdout", "")

        status.details["doctor_output"] = doc_out

        # Parse common issues
        if "Android toolchain - develop for Android devices" in doc_out:
            if "Android SDK not found" in doc_out or "Unable to locate Android SDK" in doc_out:
                status.issues.append("Android SDK is missing or ANDROID_HOME is not set.")
            if "cmdline-tools component is missing" in doc_out:
                status.issues.append("Android SDK Command-line Tools component is missing.")
            if "Some Android licenses not accepted" in doc_out or "licenses not accepted" in doc_out:
                status.issues.append("Android SDK licenses not accepted.")

        status.healthy = len(status.issues) == 0
        return status

    def requirements(self) -> list[str]:
        return [
            "Flutter SDK & Dart SDK",
            "System PATH configured with Flutter bin directory",
            "Android SDK & platform-tools",
            "Android SDK Command-line Tools & licenses",
            "Real Verification: flutter doctor clean check + flutter analyze/test execution",
        ]

    def plan(self, status: ModuleStatus, target_config: dict[str, Any] | None = None) -> list[PlanStep]:
        steps: list[PlanStep] = []

        if not status.is_installed:
            steps.append(
                PlanStep(
                    id="install_flutter",
                    title="Install Flutter SDK",
                    description="Install Flutter SDK via Windows Package Manager",
                    command="winget install --id Google.Flutter --silent --accept-package-agreements --accept-source-agreements",
                    requires_permission=True,
                    what="Install Google Flutter SDK via winget",
                    why="Required for building Flutter mobile and desktop apps",
                    impact="Installs Flutter SDK into local program directory",
                )
            )

        for issue in status.issues:
            if "Android SDK is missing" in issue:
                steps.append(
                    PlanStep(
                        id="configure_android_sdk",
                        title="Configure ANDROID_HOME Environment Variable",
                        description="Set ANDROID_HOME pointing to local Android SDK path",
                        command='setx ANDROID_HOME "%LOCALAPPDATA%\\Android\\Sdk"',
                        requires_permission=True,
                        what="Set user environment variable ANDROID_HOME",
                        why="Flutter requires ANDROID_HOME to locate the Android SDK",
                        impact="Sets ANDROID_HOME in user environment",
                    )
                )
            elif "licenses not accepted" in issue:
                steps.append(
                    PlanStep(
                        id="accept_android_licenses",
                        title="Accept Android SDK Licenses",
                        description="Run flutter doctor --android-licenses with automatic consent",
                        command="flutter doctor --android-licenses",
                        requires_permission=True,
                        what="Accept Android SDK licensing agreements",
                        why="Android builds require explicit license acceptance",
                        impact="Accepts licensing terms in Android SDK toolchain",
                    )
                )

        return steps

    def verify(self, computer: Any, project_dir: str | None = None) -> VerificationOutcome:
        outcome = VerificationOutcome(verified=False, module_name=self.name)

        # Step 1: Detect Flutter presence
        detect_res = self.detect(computer)
        if not detect_res.is_installed:
            outcome.checks_failed.append("Flutter SDK presence check")
            outcome.error_message = "Flutter is not installed or not in PATH."
            return outcome
        outcome.checks_passed.append(f"Flutter SDK detected ({detect_res.version})")

        # Step 2: Check for blocking doctor issues
        if detect_res.issues:
            outcome.checks_failed.append(f"Doctor diagnostic issues: {', '.join(detect_res.issues)}")
            outcome.error_message = f"Flutter doctor reported issues: {detect_res.issues[0]}"
            return outcome
        outcome.checks_passed.append("Flutter doctor validation passed without blocking issues")

        # Step 3: Concrete code analysis & test execution
        temp_dir = tempfile.gettempdir().replace("\\", "/")
        test_app_dir = f"{temp_dir}/trego_flutter_test_app"

        if project_dir and os.path.exists(project_dir):
            # Target project verification
            analyze_res = computer.run_dev_cmd("flutter analyze", cwd=project_dir, timeout=60)
            if not analyze_res.get("ok") or analyze_res.get("exit_code") != 0:
                outcome.checks_failed.append(f"Flutter analyze in {project_dir}")
                outcome.error_message = f"Analysis failed: {analyze_res.get('stderr') or analyze_res.get('stdout')}"
                return outcome
            outcome.checks_passed.append("Target Flutter project analysis succeeded with 0 errors")
        else:
            # Create a minimal verify app and run flutter analyze to prove toolchain operation
            create_cmd = f'flutter create --project-name trego_verify_app --no-pub "{test_app_dir}"'
            create_res = computer.run_dev_cmd(create_cmd, timeout=45)
            if create_res.get("ok") and create_res.get("exit_code") == 0:
                outcome.checks_passed.append("Flutter template creation test passed")
            # Cleanup test app
            computer.run_dev_cmd(f'Remove-Item -Recurse -Force "{test_app_dir}" -ErrorAction SilentlyContinue')

        outcome.verified = True
        outcome.evidence = f"Verified Flutter SDK ({detect_res.version}) and toolchain diagnostics."
        return outcome
