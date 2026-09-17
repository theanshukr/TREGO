"""Permission Manager for TREGO ensuring human-in-the-loop control for sensitive operations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shared.command_policy import CommandRisk, evaluate_command


@dataclass
class PermissionPrompt:
    id: str
    what: str
    why: str
    impact: str
    command: str | None = None
    risk_level: str = "HIGH_RISK"
    context: dict[str, Any] = field(default_factory=dict)


class PermissionManager:
    """Evaluates proposed actions and constructs clear permission prompts."""

    def evaluate_step(
        self,
        command: str,
        purpose: str = "",
    ) -> PermissionPrompt | None:
        eval_res = evaluate_command(command, purpose=purpose)
        if eval_res.requires_permission:
            return PermissionPrompt(
                id=f"perm_{abs(hash(command))}",
                what=eval_res.what or f"Run `{command}`",
                why=eval_res.why or purpose or "Required for environment setup",
                impact=eval_res.impact or "System or environment modification",
                command=command,
                risk_level=eval_res.risk.value,
            )
        return None
