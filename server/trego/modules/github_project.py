"""GitHub Project Setup & Onboarding Module for TREGO."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from server.trego.modules.base import BaseDevModule, ModuleStatus, PlanStep, VerificationOutcome


class GitHubProjectModule(BaseDevModule):
    name = "github_project"
    display_name = "GitHub Project Onboarding"

    def detect_stack(self, computer: Any, project_dir: str) -> dict[str, Any]:
        """Inspect project directory to detect framework and language dependencies."""
        stack_info = {"stack": "unknown", "files": [], "dependencies_cmd": None, "build_cmd": None}

        res = computer.run_dev_cmd(f'Get-ChildItem -Name "{project_dir}"')
        files = res.get("stdout", "").splitlines()
        stack_info["files"] = files

        if "pubspec.yaml" in files:
            stack_info["stack"] = "flutter"
            stack_info["dependencies_cmd"] = "flutter pub get"
            stack_info["build_cmd"] = "flutter analyze"
        elif "package.json" in files:
            stack_info["stack"] = "node"
            stack_info["dependencies_cmd"] = "npm install"
            stack_info["build_cmd"] = "npm test --if-present"
        elif "requirements.txt" in files or "pyproject.toml" in files:
            stack_info["stack"] = "python"
            stack_info["dependencies_cmd"] = (
                "pip install -r requirements.txt"
                if "requirements.txt" in files
                else "pip install ."
            )
            stack_info["build_cmd"] = "python -m unittest discover"
        elif "CMakeLists.txt" in files:
            stack_info["stack"] = "cpp_cmake"
            stack_info["dependencies_cmd"] = "cmake -B build"
            stack_info["build_cmd"] = "cmake --build build"

        return stack_info

    def detect(self, computer: Any) -> ModuleStatus:
        git_res = computer.run_dev_cmd("git --version")
        is_git_ok = bool(git_res.get("ok") and git_res.get("exit_code") == 0)
        return ModuleStatus(
            is_installed=is_git_ok,
            healthy=is_git_ok,
            details={"git_available": is_git_ok},
        )

    def requirements(self) -> list[str]:
        return [
            "Git version control",
            "Project stack detection (Node/Python/Flutter/C++)",
            "Dependency installation",
            "Build & test verification",
        ]

    def plan(self, status: ModuleStatus, target_config: dict[str, Any] | None = None) -> list[PlanStep]:
        steps: list[PlanStep] = []
        target_config = target_config or {}
        repo_url = target_config.get("repo_url", "")
        target_dir = target_config.get("target_dir", "")

        if repo_url:
            steps.append(
                PlanStep(
                    id="clone_repo",
                    title=f"Clone Repository {repo_url}",
                    description=f"Clone {repo_url} into local directory",
                    command=f'git clone "{repo_url}" "{target_dir}"' if target_dir else f'git clone "{repo_url}"',
                    requires_permission=False,
                    what=f"Clone repository from {repo_url}",
                    why="Required to download project source code",
                    impact="Creates project files on local disk",
                )
            )

        return steps

    def verify(self, computer: Any, project_dir: str | None = None) -> VerificationOutcome:
        outcome = VerificationOutcome(verified=False, module_name=self.name)
        if not project_dir:
            outcome.error_message = "No project directory specified for verification."
            return outcome

        stack = self.detect_stack(computer, project_dir)
        outcome.checks_passed.append(f"Detected project stack: {stack['stack']}")

        if stack.get("build_cmd"):
            res = computer.run_dev_cmd(stack["build_cmd"], cwd=project_dir, timeout=60)
            if not res.get("ok") or res.get("exit_code") != 0:
                outcome.checks_failed.append(f"Execution of {stack['build_cmd']}")
                outcome.error_message = f"Build verification failed: {res.get('stderr') or res.get('stdout')}"
                return outcome
            outcome.checks_passed.append(f"Build verification ({stack['build_cmd']}) passed successfully")

        outcome.verified = True
        outcome.evidence = f"Verified {stack['stack']} project setup in {project_dir}."
        return outcome
