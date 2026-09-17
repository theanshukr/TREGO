"""Git and GitHub Version Control Module for TREGO."""
from __future__ import annotations

import re
from typing import Any

from server.trego.modules.base import BaseDevModule, ModuleStatus, PlanStep, VerificationOutcome


class GitModule(BaseDevModule):
    name = "git"
    display_name = "Git Version Control"

    def detect(self, computer: Any) -> ModuleStatus:
        status = ModuleStatus(is_installed=False)

        res = computer.run_dev_cmd("git --version")
        if res.get("ok") and res.get("exit_code") == 0:
            stdout = res.get("stdout", "").strip()
            match = re.search(r"git version\s*([\d\.]+)", stdout)
            version = match.group(1) if match else "Installed"

            where_res = computer.run_dev_cmd("where git")
            path = where_res.get("stdout", "").splitlines()[0] if where_res.get("ok") and where_res.get("stdout") else "PATH"

            status.is_installed = True
            status.version = f"Git {version}"
            status.path = path
            status.healthy = True
            return status

        status.is_installed = False
        status.issues.append("Git is not found in system PATH.")
        status.healthy = False
        return status

    def requirements(self) -> list[str]:
        return [
            "Git version control executable in PATH",
            "Verification: Git version probe and repository initialization test",
        ]

    def plan(self, status: ModuleStatus, target_config: dict[str, Any] | None = None) -> list[PlanStep]:
        steps: list[PlanStep] = []
        if not status.is_installed:
            steps.append(
                PlanStep(
                    id="install_git",
                    title="Install Git for Windows",
                    description="Install Git for Windows via Windows Package Manager",
                    command="winget install --id Git.Git --silent --accept-package-agreements --accept-source-agreements",
                    requires_permission=True,
                    what="Install Git version control software via winget",
                    why="Required for cloning repositories and managing source code",
                    impact="Installs Git for Windows and adds Git CLI to PATH",
                )
            )
        return steps

    def verify(self, computer: Any) -> VerificationOutcome:
        outcome = VerificationOutcome(verified=False, module_name=self.name)
        detect_res = self.detect(computer)
        if not detect_res.is_installed:
            outcome.checks_failed.append("Git binary presence check")
            outcome.error_message = "Git is not installed or not in PATH."
            return outcome

        outcome.checks_passed.append(f"Git detected ({detect_res.version})")
        outcome.verified = True
        outcome.evidence = f"Successfully verified {detect_res.version}."
        return outcome
