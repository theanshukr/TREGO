"""TREGO Developer Environment Modules Registry."""
from __future__ import annotations

from server.trego.modules.base import BaseDevModule, ModuleStatus, PlanStep, VerificationOutcome
from server.trego.modules.cpp import CppModule
from server.trego.modules.flutter import FlutterModule
from server.trego.modules.git import GitModule
from server.trego.modules.github_project import GitHubProjectModule
from server.trego.modules.python import PythonModule

MODULE_REGISTRY: dict[str, BaseDevModule] = {
    "cpp": CppModule(),
    "c++": CppModule(),
    "python": PythonModule(),
    "py": PythonModule(),
    "flutter": FlutterModule(),
    "dart": FlutterModule(),
    "git": GitModule(),
    "github": GitHubProjectModule(),
    "github_project": GitHubProjectModule(),
}


def get_module(name: str) -> BaseDevModule | None:
    return MODULE_REGISTRY.get(name.lower().strip())
