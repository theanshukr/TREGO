"""Verification Engine for TREGO ensuring mandatory, concrete proof of success."""
from __future__ import annotations

from typing import Any

from server.trego.modules import BaseDevModule, VerificationOutcome, get_module


class VerificationEngine:
    """Mandatory verification engine: NEVER declares success based solely on command exit codes."""

    def verify_environment(
        self,
        target_stack: str,
        computer: Any,
        project_dir: str | None = None,
    ) -> VerificationOutcome:
        """Run verified test procedures on the target stack/environment."""
        mod = get_module(target_stack)
        if not mod:
            return VerificationOutcome(
                verified=False,
                module_name=target_stack,
                error_message=f"No verification module found for stack '{target_stack}'",
            )

        if target_stack in ("flutter", "dart") and project_dir:
            return mod.verify(computer, project_dir=project_dir)  # type: ignore[call-arg]
        elif target_stack in ("github", "github_project") and project_dir:
            return mod.verify(computer, project_dir=project_dir)  # type: ignore[call-arg]

        return mod.verify(computer)
