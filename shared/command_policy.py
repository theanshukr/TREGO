"""TREGO Command Policy and Security Layer.

Enforces risk classification, binary allowlists, argument sanitization,
and permission gating for terminal and developer execution commands.
"""
from __future__ import annotations

import enum
import os
import re
import shlex
from dataclasses import dataclass, field
from typing import Any


class CommandRisk(str, enum.Enum):
    READ_ONLY = "READ_ONLY"          # Safe inspection (e.g. g++ --version, git status, flutter doctor)
    SAFE_MUTATION = "SAFE_MUTATION"  # Project-local / isolated actions (e.g. git clone, python -m venv)
    HIGH_RISK = "HIGH_RISK"          # System changes / installs / global configs (requires explicit permission)
    BLOCKED = "BLOCKED"              # Strictly forbidden commands / destructive operations


# Allowed executables for developer commands and diagnostics
_ALLOWED_COMMAND_BINARIES: dict[str, dict[str, Any]] = {
    # Compilers and build tools
    "g++": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "gcc": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "clang": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "clang++": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "cmake": {"risk": CommandRisk.SAFE_MUTATION, "allow_flags": True},
    "make": {"risk": CommandRisk.SAFE_MUTATION, "allow_flags": True},
    "ninja": {"risk": CommandRisk.SAFE_MUTATION, "allow_flags": True},
    
    # Python & package tools
    "python": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "py": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "python3": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "pip": {"risk": CommandRisk.SAFE_MUTATION, "allow_flags": True},
    
    # Flutter & Dart
    "flutter": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "dart": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    
    # Git & GitHub
    "git": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "gh": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    
    # Node / JS tools
    "node": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "npm": {"risk": CommandRisk.SAFE_MUTATION, "allow_flags": True},
    "npx": {"risk": CommandRisk.SAFE_MUTATION, "allow_flags": True},
    "yarn": {"risk": CommandRisk.SAFE_MUTATION, "allow_flags": True},
    "pnpm": {"risk": CommandRisk.SAFE_MUTATION, "allow_flags": True},
    
    # Package Managers (High-Risk -> Must have permission)
    "winget": {"risk": CommandRisk.HIGH_RISK, "allow_flags": True},
    "choco": {"risk": CommandRisk.HIGH_RISK, "allow_flags": True},
    
    # System inspection & Windows diagnostics
    "where": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "where.exe": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "cmd.exe": {"risk": CommandRisk.READ_ONLY, "allow_subcommands": ["/c", "ver", "echo", "set", "dir"]},
    "ipconfig": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "systeminfo": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "hostname": {"risk": CommandRisk.READ_ONLY, "allow_flags": True},
    "setx": {"risk": CommandRisk.HIGH_RISK, "allow_flags": True},
}

# Subcommand-level risk elevation rules
_RISK_OVERRIDE_RULES = [
    # pip install -> high risk if global, safe if in venv
    (re.compile(r"^pip\s+install", re.IGNORECASE), CommandRisk.HIGH_RISK),
    (re.compile(r"^npm\s+install\s+(-g|--global)", re.IGNORECASE), CommandRisk.HIGH_RISK),
    (re.compile(r"^winget\s+(install|upgrade|uninstall)", re.IGNORECASE), CommandRisk.HIGH_RISK),
    (re.compile(r"^choco\s+(install|upgrade|uninstall)", re.IGNORECASE), CommandRisk.HIGH_RISK),
    (re.compile(r"^git\s+(clone|pull|fetch)", re.IGNORECASE), CommandRisk.SAFE_MUTATION),
    (re.compile(r"^flutter\s+doctor", re.IGNORECASE), CommandRisk.READ_ONLY),
    (re.compile(r"^flutter\s+(analyze|test|build)", re.IGNORECASE), CommandRisk.READ_ONLY),
    (re.compile(r"^flutter\s+create", re.IGNORECASE), CommandRisk.SAFE_MUTATION),
    (re.compile(r"^setx", re.IGNORECASE), CommandRisk.HIGH_RISK),
]

# Hard-blocked command patterns (Destructive, dangerous system alterations, shell-escape chains)
_BLOCKED_PATTERNS = [
    re.compile(r"(\||;|&&|&)\s*(rmdir|del|format|diskpart|reg\s+delete)", re.IGNORECASE),
    re.compile(r"\bformat\s+[a-zA-Z]:", re.IGNORECASE),
    re.compile(r"\brmdir\s+/[sS]\s+/[qQ]\s+[cC]:\\", re.IGNORECASE),
    re.compile(r"\bdel\s+/[fF]\s+/[sS]\s+/[qQ]\s+[cC]:\\", re.IGNORECASE),
    re.compile(r"\bnet\s+user\s+", re.IGNORECASE),
    re.compile(r"\bnet\s+localgroup\s+administrators", re.IGNORECASE),
    re.compile(r"\b(shutdown|reboot)\b", re.IGNORECASE),
    re.compile(r"\b(powershell|pwsh)\s+-e(nc|ncodedcommand)?\b", re.IGNORECASE),
]


@dataclass
class PolicyEvaluation:
    is_allowed: bool
    risk: CommandRisk
    reason: str
    binary: str
    sanitized_args: list[str]
    requires_permission: bool = False
    permission_prompt: str | None = None
    what: str | None = None
    why: str | None = None
    impact: str | None = None


def evaluate_command(
    command_str: str,
    *,
    purpose: str = "",
) -> PolicyEvaluation:
    """Evaluate a proposed terminal or dev command against TREGO security policies.
    
    Returns a PolicyEvaluation describing whether it is allowed, its risk classification,
    and whether an explicit permission gate is mandatory.
    """
    raw_cmd = command_str.strip()
    if not raw_cmd:
        return PolicyEvaluation(
            is_allowed=False,
            risk=CommandRisk.BLOCKED,
            reason="Empty command",
            binary="",
            sanitized_args=[],
        )

    # Check hard blocked patterns
    for pattern in _BLOCKED_PATTERNS:
        if pattern.search(raw_cmd):
            return PolicyEvaluation(
                is_allowed=False,
                risk=CommandRisk.BLOCKED,
                reason="Command matches security blocked pattern",
                binary="",
                sanitized_args=[],
            )

    # Tokenize arguments safely
    try:
        tokens = shlex.split(raw_cmd, posix=False)
    except Exception as e:
        return PolicyEvaluation(
            is_allowed=False,
            risk=CommandRisk.BLOCKED,
            reason=f"Malformed command syntax: {e}",
            binary="",
            sanitized_args=[],
        )

    if not tokens:
        return PolicyEvaluation(
            is_allowed=False,
            risk=CommandRisk.BLOCKED,
            reason="No command tokens found",
            binary="",
            sanitized_args=[],
        )

    binary = tokens[0].lower().rstrip(".exe")
    args = tokens[1:]

    # Check if binary is allowed
    bin_config = _ALLOWED_COMMAND_BINARIES.get(binary)
    if not bin_config:
        # Check full binary with .exe
        bin_config = _ALLOWED_COMMAND_BINARIES.get(tokens[0].lower())
        if not bin_config:
            return PolicyEvaluation(
                is_allowed=False,
                risk=CommandRisk.BLOCKED,
                reason=f"Binary '{tokens[0]}' is not in the allowed developer toolchain",
                binary=tokens[0],
                sanitized_args=args,
            )

    # Determine risk level
    base_risk = bin_config.get("risk", CommandRisk.SAFE_MUTATION)
    risk = base_risk
    for pattern, elevated_risk in _RISK_OVERRIDE_RULES:
        if pattern.search(raw_cmd):
            risk = elevated_risk
            break

    # Permission requirement logic
    requires_permission = (risk == CommandRisk.HIGH_RISK)
    
    what = f"Execute `{raw_cmd}`"
    why = purpose or f"Required for {binary} environment setup/execution"
    impact = (
        "May install software or alter system/environment configurations"
        if risk == CommandRisk.HIGH_RISK
        else "Inspects or alters local project files"
    )

    permission_prompt = (
        f"TREGO needs permission to run: `{raw_cmd}`\n"
        f"Reason: {why}\n"
        f"Impact: {impact}\n"
        f"Should I proceed?"
    ) if requires_permission else None

    return PolicyEvaluation(
        is_allowed=True,
        risk=risk,
        reason="Command passed security policy evaluation",
        binary=binary,
        sanitized_args=args,
        requires_permission=requires_permission,
        permission_prompt=permission_prompt,
        what=what,
        why=why,
        impact=impact,
    )
