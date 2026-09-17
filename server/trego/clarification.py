"""Clarification Manager for TREGO handling user decisions during ambiguity."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from server.trego.goal import GoalObjective
from server.trego.modules import ModuleStatus


@dataclass
class ClarificationRequest:
    id: str
    question: str
    options: list[str]
    default_option: str
    context: str = ""


class ClarificationManager:
    """Detects meaningful ambiguity and generates concise user clarification prompts."""

    def evaluate_ambiguity(
        self,
        goal: GoalObjective,
        module_status: ModuleStatus | None,
        context: dict[str, Any] | None = None,
    ) -> ClarificationRequest | None:
        if not module_status:
            return None

        # Scenario: Python already installed and user asks to "Install/Setup Python"
        if goal.target_stack == "python" and module_status.is_installed:
            return ClarificationRequest(
                id="python_existing_version",
                question=(
                    f"Python is already installed ({module_status.version}). "
                    "How would you like to proceed?"
                ),
                options=[
                    f"Use existing {module_status.version} and verify",
                    "Create a new virtual environment (.venv)",
                    "Upgrade to Python 3.12 via winget",
                ],
                default_option=f"Use existing {module_status.version} and verify",
                context="Existing Python installation detected.",
            )

        # Scenario: Package installation scope ambiguity
        if "install" in goal.raw_text.lower() and "package" in goal.raw_text.lower():
            return ClarificationRequest(
                id="package_scope",
                question="Should I install this package globally or only inside a project virtual environment?",
                options=[
                    "Install inside current project virtual environment (Recommended)",
                    "Install globally across the system",
                ],
                default_option="Install inside current project virtual environment (Recommended)",
            )

        return None
