"""Base module interface for TREGO Developer Environment Managers."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModuleStatus:
    is_installed: bool
    version: str | None = None
    path: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    healthy: bool = False


@dataclass
class PlanStep:
    id: str
    title: str
    description: str
    command: str | None = None
    gui_action: dict[str, Any] | None = None
    requires_permission: bool = False
    what: str | None = None
    why: str | None = None
    impact: str | None = None


@dataclass
class VerificationOutcome:
    verified: bool
    module_name: str
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    evidence: str = ""
    error_message: str | None = None


class BaseDevModule(abc.ABC):
    """Abstract base class for all TREGO developer environment modules."""

    name: str = "base"
    display_name: str = "Base Environment"

    @abc.abstractmethod
    def detect(self, computer: Any) -> ModuleStatus:
        """Inspect the system to determine whether this environment is installed,
        which version is active, and if any configuration issues exist."""
        raise NotImplementedError

    @abc.abstractmethod
    def requirements(self) -> list[str]:
        """Return the list of prerequisite components and configuration targets."""
        raise NotImplementedError

    @abc.abstractmethod
    def plan(self, status: ModuleStatus, target_config: dict[str, Any] | None = None) -> list[PlanStep]:
        """Generate a structured sequence of steps required to reach healthy state."""
        raise NotImplementedError

    @abc.abstractmethod
    def verify(self, computer: Any) -> VerificationOutcome:
        """Run real, concrete compilation/execution/analysis tests to prove
        that the environment is in a functioning state. Never assumes completion."""
        raise NotImplementedError
