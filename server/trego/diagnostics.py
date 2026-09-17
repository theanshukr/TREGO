"""Diagnostic pattern matcher and root cause analyzer for TREGO."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiagnosticResult:
    error_type: str
    probable_cause: str
    suggested_fix: str
    command_to_fix: str | None = None
    requires_permission: bool = False
    confidence: float = 0.9


class DiagnosticEngine:
    """Analyzes terminal error output and system state to identify actionable root causes."""

    def diagnose_error(self, error_text: str, context: dict[str, Any] | None = None) -> DiagnosticResult | None:
        text = error_text.strip()
        if not text:
            return None

        # 1. 'is not recognized as an internal or external command' / PATH error
        if re.search(r"is not recognized as an internal or external command|The term .* is not recognized", text, re.IGNORECASE):
            binary_match = re.search(r"'([^']+)' is not recognized|The term '([^']+)'", text)
            binary = binary_match.group(1) if binary_match and binary_match.group(1) else (binary_match.group(2) if binary_match else "command")
            return DiagnosticResult(
                error_type="CommandNotFoundOrPathMissing",
                probable_cause=f"'{binary}' is either not installed or its directory is not included in the system PATH.",
                suggested_fix=f"Install {binary} or add its binary directory to PATH environment variable.",
                confidence=0.95,
            )

        # 2. C++ Missing Header
        if "fatal error:" in text and "No such file or directory" in text:
            header_match = re.search(r"fatal error:\s*([^:]+):\s*No such file or directory", text)
            header = header_match.group(1) if header_match else "header file"
            return DiagnosticResult(
                error_type="CppMissingHeader",
                probable_cause=f"The C++ source requires '{header}', which is missing from include paths or requires an external library.",
                suggested_fix=f"Check include search path or install required development package containing {header}.",
                confidence=0.92,
            )

        # 3. Flutter Android SDK / licenses
        if "Android SDK not found" in text or "Unable to locate Android SDK" in text:
            return DiagnosticResult(
                error_type="FlutterAndroidSdkMissing",
                probable_cause="Flutter cannot find the Android SDK path.",
                suggested_fix="Set ANDROID_HOME environment variable to %LOCALAPPDATA%\\Android\\Sdk.",
                command_to_fix='setx ANDROID_HOME "%LOCALAPPDATA%\\Android\\Sdk"',
                requires_permission=True,
                confidence=0.95,
            )

        if "Some Android licenses not accepted" in text:
            return DiagnosticResult(
                error_type="FlutterAndroidLicensesUnaccepted",
                probable_cause="Android SDK licenses have not been accepted.",
                suggested_fix="Run 'flutter doctor --android-licenses' to accept terms.",
                command_to_fix="flutter doctor --android-licenses",
                requires_permission=True,
                confidence=0.98,
            )

        # 4. Python ModuleNotFoundError
        if "ModuleNotFoundError:" in text:
            mod_match = re.search(r"No module named '([^']+)'", text)
            module = mod_match.group(1) if mod_match else "package"
            return DiagnosticResult(
                error_type="PythonModuleMissing",
                probable_cause=f"Required Python module '{module}' is not installed in the active environment.",
                suggested_fix=f"Install the missing dependency using: pip install {module}",
                command_to_fix=f"pip install {module}",
                requires_permission=False,
                confidence=0.95,
            )

        # 5. Permission / Access Denied
        if "Access is denied" in text or "Permission denied" in text:
            return DiagnosticResult(
                error_type="AccessDenied",
                probable_cause="The operation requires elevated administrator permissions or file is locked.",
                suggested_fix="Run the terminal or action with Administrator privileges.",
                requires_permission=True,
                confidence=0.90,
            )

        return None
