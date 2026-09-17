"""Environment and System Inspector for TREGO."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from server.trego.modules import MODULE_REGISTRY, BaseDevModule, ModuleStatus


@dataclass
class SystemReport:
    os: str = "Windows"
    os_version: str = ""
    modules: dict[str, ModuleStatus] = field(default_factory=dict)
    system_info: dict[str, Any] = field(default_factory=dict)
    disk_space: dict[str, Any] = field(default_factory=dict)
    network_status: dict[str, Any] = field(default_factory=dict)
    path_entries: list[str] = field(default_factory=list)


class EnvironmentInspector:
    """Performs deep, non-destructive inspection of system and developer environments."""

    def inspect_system(self, computer: Any) -> SystemReport:
        report = SystemReport()

        # 1. System info & OS
        sys_res = computer.get_system_info()
        if sys_res.get("ok"):
            report.system_info = sys_res.get("result", {})
            report.os_version = str(report.system_info.get("os", "Windows"))

        # 2. Disk space
        disk_res = computer.check_disk_space()
        if disk_res.get("ok"):
            report.disk_space = disk_res.get("result", {})

        # 3. Network status
        net_res = computer.check_network_status()
        if net_res.get("ok"):
            report.network_status = net_res.get("result", {})

        # 4. PATH entries
        path_res = computer.run_dev_cmd("$env:PATH")
        if path_res.get("ok"):
            raw_path = path_res.get("stdout", "")
            report.path_entries = [p.strip() for p in raw_path.split(";") if p.strip()]

        return report

    def inspect_module(self, module_name: str, computer: Any) -> ModuleStatus:
        mod = MODULE_REGISTRY.get(module_name.lower().strip())
        if not mod:
            return ModuleStatus(
                is_installed=False,
                healthy=False,
                issues=[f"Unknown module '{module_name}'"],
            )
        return mod.detect(computer)

    def inspect_all_modules(self, computer: Any) -> dict[str, ModuleStatus]:
        results: dict[str, ModuleStatus] = {}
        # Distinct modules
        seen_mods: set[str] = set()
        for key, mod in MODULE_REGISTRY.items():
            if mod.name in seen_mods:
                continue
            seen_mods.add(mod.name)
            results[mod.name] = mod.detect(computer)
        return results
