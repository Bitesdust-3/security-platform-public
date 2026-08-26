import ipaddress
import subprocess
import shutil
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from app.core.logger import logger


class ScanTargetError(ValueError):
    """Raised when a scan target is outside the allowed lab boundary."""


class NmapExecutionError(RuntimeError):
    """Raised when Nmap cannot produce a complete, parseable scan result."""


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
    state: str
    service_name: str | None
    product_name: str | None
    service_version: str | None
    raw_nmap: dict[str, str]


def build_nmap_command(target_scope: str, output_path: Path) -> list[str]:
    validated = validate_target_scope(target_scope)
    # Docker bridge networking can have a higher RTT than host networking.
    # 60 seconds previously produced timed-out XML that looked like an empty scan.
    return ["nmap", "-sV", "-T3", "--host-timeout", "5m", "-oX", str(output_path), validated]


def nmap_available() -> bool:
    return shutil.which("nmap") is not None


def run_nmap(target_scope: str, timeout_seconds: int = 360) -> list[DiscoveredService]:
    with tempfile.NamedTemporaryFile(prefix="security-platform-nmap-", suffix=".xml", delete=False) as output:
        output_path = Path(output.name)
    try:
        command = build_nmap_command(target_scope, output_path)
        logger.info("scan stage=nmap_execute target=%s command=%s", target_scope, " ".join(command))
        try:
            completed = subprocess.run(command, check=True, shell=False, timeout=timeout_seconds, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            logger.error("scan stage=nmap_execute failed target=%s returncode=%s stderr=%s", target_scope, exc.returncode, detail[:800])
            raise NmapExecutionError(f"Nmap 执行失败（返回码 {exc.returncode}）: {detail[:800]}") from exc
        except subprocess.TimeoutExpired as exc:
            logger.error("scan stage=nmap_execute timeout target=%s seconds=%s", target_scope, timeout_seconds)
            raise NmapExecutionError(f"Nmap 执行超时（{timeout_seconds} 秒）") from exc
        logger.info("scan stage=nmap_execute completed target=%s returncode=%s stdout=%s stderr=%s", target_scope, completed.returncode, (completed.stdout or "").strip()[-500:], (completed.stderr or "").strip()[-500:])
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise NmapExecutionError("Nmap 未生成 XML 扫描结果")
        try:
            discovered = parse_nmap_xml(output_path)
            logger.info("scan stage=result_parse completed target=%s open_services=%s", target_scope, len(discovered))
            return discovered
        except ET.ParseError as exc:
            raise NmapExecutionError(f"Nmap XML 解析失败: {exc}") from exc
    finally:
        output_path.unlink(missing_ok=True)


def parse_nmap_xml(path: Path) -> list[DiscoveredService]:
    root = ET.parse(path).getroot()
    if root.findall("host[@timedout='true']"):
        raise NmapExecutionError("Nmap 主机扫描超时，未获得完整端口结果")
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
            if service is not None:
                name = service.attrib.get("name")
                product = service.attrib.get("product")
                version = " ".join(part for part in (service.attrib.get("version"), service.attrib.get("extrainfo")) if part) or None
                raw_nmap = dict(service.attrib)
            else:
                name, product, version, raw_nmap = None, None, None, {}
            raw_nmap.update({"port_state": state.attrib.get("state", "unknown"), "port": port.attrib["portid"], "protocol": port.attrib.get("protocol", "tcp")})
            discovered.append(DiscoveredService(
                ip_address, hostname, int(port.attrib["portid"]), port.attrib.get("protocol", "tcp"),
                state.attrib.get("state", "unknown"), name, product, version, raw_nmap,
            ))
    return discovered
