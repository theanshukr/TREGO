"""Tests for TREGO Command Policy and Security Layer."""
import pytest
from shared.command_policy import CommandRisk, evaluate_command


def test_read_only_commands_allowed():
    res = evaluate_command("g++ --version")
    assert res.is_allowed is True
    assert res.risk == CommandRisk.READ_ONLY
    assert res.requires_permission is False

    res_py = evaluate_command("python --version")
    assert res_py.is_allowed is True
    assert res_py.risk == CommandRisk.READ_ONLY

    res_fl = evaluate_command("flutter doctor -v")
    assert res_fl.is_allowed is True
    assert res_fl.risk == CommandRisk.READ_ONLY


def test_high_risk_commands_require_permission():
    res_wg = evaluate_command("winget install --id MSYS2.MSYS2 --silent")
    assert res_wg.is_allowed is True
    assert res_wg.risk == CommandRisk.HIGH_RISK
    assert res_wg.requires_permission is True
    assert "TREGO needs permission" in res_wg.permission_prompt

    res_setx = evaluate_command('setx PATH "%PATH%;C:\\msys64\\ucrt64\\bin"')
    assert res_setx.is_allowed is True
    assert res_setx.risk == CommandRisk.HIGH_RISK
    assert res_setx.requires_permission is True


def test_blocked_destructive_commands():
    res_del = evaluate_command("del /f /s /q C:\\")
    assert res_del.is_allowed is False
    assert res_del.risk == CommandRisk.BLOCKED

    res_fmt = evaluate_command("format D:")
    assert res_fmt.is_allowed is False
    assert res_fmt.risk == CommandRisk.BLOCKED

    res_unknown = evaluate_command("malicious_tool.exe -attack")
    assert res_unknown.is_allowed is False
    assert res_unknown.risk == CommandRisk.BLOCKED
