from pathlib import Path

import pytest

import subprocess

from app.services.scanner import NmapExecutionError, ScanTargetError, build_nmap_command, nmap_available, parse_nmap_xml, run_nmap, validate_target_scope


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


def test_parse_nmap_xml_preserves_structured_service_fields(tmp_path: Path):
    report = tmp_path / "result.xml"
    report.write_text("""<?xml version='1.0'?><nmaprun><host><status state='up'/><address addr='192.0.2.10' addrtype='ipv4'/><ports><port protocol='tcp' portid='80'><state state='open'/><service name='http' product='Apache httpd' version='2.4.58' extrainfo='Ubuntu'/></port></ports></host></nmaprun>""")

    results = parse_nmap_xml(report)

    assert len(results) == 1
    assert results[0].state == "open"
    assert results[0].service_name == "http"
    assert results[0].product_name == "Apache httpd"
    assert results[0].service_version == "2.4.58 Ubuntu"
    assert results[0].raw_nmap["port"] == "80"


def test_timed_out_nmap_xml_is_not_treated_as_a_completed_empty_scan(tmp_path: Path):
    report = tmp_path / "timeout.xml"
    report.write_text("""<?xml version='1.0'?><nmaprun><host timedout='true'><status state='up'/></host></nmaprun>""")

    with pytest.raises(NmapExecutionError, match="超时"):
        parse_nmap_xml(report)


def test_nmap_execution_failure_raises_clear_error(monkeypatch):
    def failed_run(*_args, **_kwargs):
        raise subprocess.CalledProcessError(2, "nmap", stderr="network unavailable")

    monkeypatch.setattr("app.services.scanner.subprocess.run", failed_run)
    with pytest.raises(NmapExecutionError, match="返回码 2"):
        run_nmap("192.0.2.10")
