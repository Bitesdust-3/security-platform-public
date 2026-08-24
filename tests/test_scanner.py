from pathlib import Path

import pytest

from app.services.scanner import ScanTargetError, build_nmap_command, nmap_available, parse_nmap_xml, validate_target_scope


def test_target_scope_is_limited_to_lab_networks():
    assert validate_target_scope("192.0.2.0/24") == "192.0.2.0/24"
    with pytest.raises(ScanTargetError):
        validate_target_scope("8.8.8.8")
    with pytest.raises(ScanTargetError):
        validate_target_scope("192.0.2.0/16")


def test_nmap_command_does_not_use_shell():
    command = build_nmap_command("192.0.2.10", Path("/tmp/result.xml"))

    assert command[0] == "nmap"
    assert "192.0.2.10" in command
    assert "&&" not in command


def test_nmap_availability_check_returns_boolean():
    assert isinstance(nmap_available(), bool)
