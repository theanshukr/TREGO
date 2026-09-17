"""Goal Interpreter for TREGO converting natural language requests into structured objectives."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GoalObjective:
    raw_text: str
    target_stack: str  # "cpp" | "python" | "flutter" | "git" | "github" | "general"
    category: str      # "setup" | "fix" | "run" | "troubleshoot" | "gui_action"
    target_state: list[str] = field(default_factory=list)
    verification_criteria: list[str] = field(default_factory=list)
    project_path: str | None = None
    repo_url: str | None = None


class GoalInterpreter:
    """Interprets voice or text user requests into structured, actionable goals."""

    def interpret(self, text: str) -> GoalObjective:
        cleaned = text.strip().lower()

        # 1. GitHub Project Onboarding (Check for URL or explicit clone request first)
        github_match = re.search(r"https?://github\.com/[^\s]+", text)
        if github_match or ("github" in cleaned and ("clone" in cleaned or "repo" in cleaned or "project" in cleaned)):
            repo_url = github_match.group(0) if github_match else None
            return GoalObjective(
                raw_text=text,
                target_stack="github",
                category="run",
                target_state=[
                    "Repository cloned",
                    "Project stack auto-detected",
                    "Dependencies installed",
                    "Project configured and built",
                ],
                verification_criteria=[
                    "Project build / test command executed with exit code 0",
                ],
                repo_url=repo_url,
            )

        # 2. C++ Development Setup
        if re.search(r"(c\+\+|cpp|\bgcc\b|\bg\+\+|\bmingw\b|\bclang\b)", cleaned):
            return GoalObjective(
                raw_text=text,
                target_stack="cpp",
                category="setup",
                target_state=[
                    "C++ compiler installed (g++, clang++, or MSVC)",
                    "Compiler binary accessible from system PATH",
                    "C++ standard libraries and headers configured",
                ],
                verification_criteria=[
                    "Compile minimal C++ test program",
                    "Execute binary and assert standard output",
                ],
            )

        # 3. Flutter / Dart Setup & Diagnostics
        if re.search(r"\b(flutter|dart|android sdk)\b", cleaned):
            is_fix = bool(re.search(r"\b(fix|error|why|broken|not running|build fail)\b", cleaned))
            return GoalObjective(
                raw_text=text,
                target_stack="flutter",
                category="fix" if is_fix else "setup",
                target_state=[
                    "Flutter SDK installed and in PATH",
                    "Android SDK and cmdline-tools configured",
                    "Android licenses accepted",
                ],
                verification_criteria=[
                    "flutter doctor validation with no blocking errors",
                    "flutter analyze / flutter test verification",
                ],
            )

        # 4. Python Setup
        if re.search(r"\b(python|py|pip|venv|virtualenv|conda)\b", cleaned):
            return GoalObjective(
                raw_text=text,
                target_stack="python",
                category="setup",
                target_state=[
                    "Python 3.x interpreter in PATH",
                    "pip package manager operational",
                    "venv module available",
                ],
                verification_criteria=[
                    "Execute Python verification script and import standard modules",
                ],
            )

        # 5. Git Setup
        if re.search(r"\b(git|version control)\b", cleaned):
            return GoalObjective(
                raw_text=text,
                target_stack="git",
                category="setup",
                target_state=["Git installed and in PATH"],
                verification_criteria=["git --version check"],
            )

        # 6. General Computer Use / GUI issue
        return GoalObjective(
            raw_text=text,
            target_stack="general",
            category="gui_action",
            target_state=["User goal visually or programmatically achieved"],
            verification_criteria=["Visual confirmation in screen perception"],
        )
