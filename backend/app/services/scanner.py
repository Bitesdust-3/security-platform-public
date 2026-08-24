import ipaddress
import subprocess
import shutil
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


class ScanTargetError(ValueError):
    """Raised when a scan target is outside the allowed lab boundary."""


def validate_target_scope(value: str) -> str:
    try:
        if "/" in value:
            network = ipaddress.ip_network(value, strict=False)
            if network.version != 4 or network.prefixlen < 24:
                raise ScanTargetError("仅允许不大于 /24 的 IPv4 实验网段")
            target = str(network)
        else:
            address = ipaddress.ip_address(value)
            target = str(address)
        if not (ipaddress.ip_address(target.split("/")[0]).is_private or ipaddress.ip_address(target.split("/")[0]).is_loopback):
            raise ScanTargetError("仅允许私有、回环或文档测试地址")
        return target
    except ValueError as exc:
        raise ScanTargetError("目标必须是合法 IP 或 CIDR") from exc


@dataclass(frozen=True)
class DiscoveredService:
    ip_address: str
    hostname: str | None
    port: int
    protocol: str
    service_name: str | None
    service_version: str | None


def build_nmap_command(target_scope: str, output_path: Path) -> list[str]:
    validated = validate_target_scope(target_scope)
    return ["nmap", "-sV", "-T3", "--host-timeout", "60s", "-oX", str(output_path), validated]


def nmap_available() -> bool:
    return shutil.which("nmap") is not None


def run_nmap(target_scope: str, timeout_seconds: int = 120) -> list[DiscoveredService]:
    with tempfile.NamedTemporaryFile(prefix="security-platform-nmap-", suffix=".xml", delete=False) as output:
        output_path = Path(output.name)
    try:
        command = build_nmap_command(target_scope, output_path)
        subprocess.run(command, check=True, shell=False, timeout=timeout_seconds, capture_output=True, text=True)
        return parse_nmap_xml(output_path)
    finally:
        output_path.unlink(missing_ok=True)


def parse_nmap_xml(path: Path) -> list[DiscoveredService]:
    root = ET.parse(path).getroot()
    discovered: list[DiscoveredService] = []
    for host in root.findall("host"):
        status = host.find("status")
        if status is not None and status.attrib.get("state") != "up":
            continue
        address = host.find("address")
        if address is None or address.attrib.get("addrtype") != "ipv4":
            continue
        ip_address = address.attrib["addr"]
        hostname_node = host.find("hostnames/hostname")
        hostname = hostname_node.attrib.get("name") if hostname_node is not None else None
        for port in host.findall("ports/port"):
            state = port.find("state")
            if state is None or state.attrib.get("state") != "open":
                continue
            service = port.find("service")
            discovered.append(DiscoveredService(ip_address, hostname, int(port.attrib["portid"]), port.attrib.get("protocol", "tcp"), service.attrib.get("name") if service is not None else None, service.attrib.get("product") if service is not None else None))
    return discovered
