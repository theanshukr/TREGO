"""C++ Developer Environment Module for TREGO."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

from server.trego.modules.base import BaseDevModule, ModuleStatus, PlanStep, VerificationOutcome


class CppModule(BaseDevModule):
    name = "cpp"
    display_name = "C++ Development Environment"

    def detect(self, computer: Any) -> ModuleStatus:
        status = ModuleStatus(is_installed=False)
        
        # 1. Try checking g++
        res = computer.run_dev_cmd("g++ --version")
        if res.get("ok") and res.get("exit_code") == 0:
            stdout = res.get("stdout", "")
            match = re.search(r"g\+\+\s*\(.*?\)\s*([\d\.]+)", stdout)
            version = match.group(1) if match else "Installed"
            
            where_res = computer.run_dev_cmd("where g++")
            path = where_res.get("stdout", "").splitlines()[0] if where_res.get("ok") and where_res.get("stdout") else "PATH"
            
            status.is_installed = True
            status.version = f"GCC/g++ {version}"
            status.path = path
            status.healthy = True
            status.details["compiler"] = "g++"
            return status

        # 2. Try checking clang++
        res = computer.run_dev_cmd("clang++ --version")
        if res.get("ok") and res.get("exit_code") == 0:
            stdout = res.get("stdout", "")
            match = re.search(r"clang version\s*([\d\.]+)", stdout)
            version = match.group(1) if match else "Installed"
            status.is_installed = True
            status.version = f"Clang {version}"
            status.healthy = True
            status.details["compiler"] = "clang++"
            return status

        # 3. Try checking MSVC cl.exe
        res = computer.run_dev_cmd("cmd.exe /c cl")
        if res.get("ok") and "Microsoft" in res.get("stderr", ""):
            status.is_installed = True
            status.version = "Microsoft C/C++ Optimizing Compiler (MSVC)"
            status.healthy = True
            status.details["compiler"] = "cl"
            return status

        # If not detected in PATH, inspect common install locations (MinGW, MSYS2)
        status.is_installed = False
        status.issues.append("No working C++ compiler (g++, clang++, or MSVC) found in PATH.")
        status.healthy = False
        return status

    def requirements(self) -> list[str]:
        return [
            "C++ Compiler (g++, clang++, or cl.exe)",
            "System PATH configuration for compiler binaries",
            "C++ Standard Library headers & toolchain",
            "Verification: Minimal C++ program compile and execution test",
        ]

    def plan(self, status: ModuleStatus, target_config: dict[str, Any] | None = None) -> list[PlanStep]:
        steps: list[PlanStep] = []
        if not status.is_installed or not status.healthy:
            steps.append(
                PlanStep(
                    id="install_cpp_compiler",
                    title="Install MinGW-w64 C++ Compiler Toolchain",
                    description="Install GCC/MinGW-w64 via Windows Package Manager (winget)",
                    command="winget install --id MSYS2.MSYS2 --silent --accept-package-agreements --accept-source-agreements",
                    requires_permission=True,
                    what="Install MSYS2 / MinGW-w64 C++ Compiler toolchain via winget",
                    why="Required to compile and build C++ code on Windows",
                    impact="Installs the MSYS2/MinGW toolchain and configures build binaries",
                )
            )
            steps.append(
                PlanStep(
                    id="configure_cpp_path",
                    title="Configure C++ Compiler PATH",
                    description="Add compiler binary directory to user PATH environment variable",
                    command='setx PATH "%PATH%;C:\\msys64\\ucrt64\\bin;C:\\msys64\\mingw64\\bin"',
                    requires_permission=True,
                    what="Add C:\\msys64\\ucrt64\\bin to user environment PATH",
                    why="Allows terminal and build tools to invoke g++ directly",
                    impact="Modifies User PATH environment variable",
                )
            )
        return steps

    def verify(self, computer: Any) -> VerificationOutcome:
        outcome = VerificationOutcome(verified=False, module_name=self.name)
        
        # Test 1: Check compiler binary availability
        detect_res = self.detect(computer)
        if not detect_res.is_installed:
            outcome.checks_failed.append("C++ compiler binary check")
            outcome.error_message = "g++ or compatible C++ compiler not available in PATH"
            return outcome
        outcome.checks_passed.append(f"Compiler detected: {detect_res.version}")

        # Test 2: Compile a test C++ program
        test_cpp_content = (
            "#include <iostream>\n"
            "int main() {\n"
            '    std::cout << "TREGO_CPP_VERIFIED_SUCCESS" << std::endl;\n'
            "    return 0;\n"
            "}\n"
        )
        temp_dir = tempfile.gettempdir().replace("\\", "/")
        source_path = f"{temp_dir}/trego_verify.cpp"
        binary_path = f"{temp_dir}/trego_verify.exe"

        # Write test source file via powershell command
        write_cmd = f'Set-Content -Path "{source_path}" -Value \'{test_cpp_content}\''
        computer.run_dev_cmd(write_cmd)

        # Compile command
        compile_cmd = f'g++ -std=c++17 "{source_path}" -o "{binary_path}"'
        comp_res = computer.run_dev_cmd(compile_cmd, timeout=30)
        
        if not comp_res.get("ok") or comp_res.get("exit_code") != 0:
            outcome.checks_failed.append("Compilation of minimal C++ test program")
            outcome.error_message = f"Compilation failed: {comp_res.get('stderr') or comp_res.get('stdout')}"
            return outcome
        outcome.checks_passed.append("Compiled test C++ program successfully")

        # Test 3: Execute compiled binary and assert stdout
        run_res = computer.run_dev_cmd(f'"{binary_path}"', timeout=10)
        stdout = run_res.get("stdout", "")
        if "TREGO_CPP_VERIFIED_SUCCESS" not in stdout:
            outcome.checks_failed.append("Execution of compiled C++ binary")
            outcome.error_message = f"Binary output did not match expected verification string. Got: {stdout}"
            return outcome
        outcome.checks_passed.append("Executed compiled binary: output verified")

        # Cleanup
        computer.run_dev_cmd(f'Remove-Item -Force "{source_path}","{binary_path}" -ErrorAction SilentlyContinue')

        outcome.verified = True
        outcome.evidence = f"Successfully compiled and executed C++ test binary using {detect_res.version}."
        return outcome
