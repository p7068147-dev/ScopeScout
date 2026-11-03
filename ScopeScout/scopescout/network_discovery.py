
import ipaddress
import platform
import re
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtCore import QThread, Signal


def get_interface_network(interface):
    """Find the IPv4 network assigned to the selected interface."""

    system = platform.system()

    if system == "Linux":
        result = subprocess.run(
            ["ip", "-o", "-4", "addr", "show", "dev", interface],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        match = re.search(r"\binet\s+(\d+\.\d+\.\d+\.\d+/\d+)", result.stdout)

        if not match:
            raise RuntimeError(
                f"No IPv4 address found on {interface}"
            )

        return ipaddress.ip_interface(match.group(1)).network

    if system == "Darwin":
        result = subprocess.run(
            ["ifconfig", interface],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        ip_match = re.search(
            r"\binet\s+(\d+\.\d+\.\d+\.\d+)",
            result.stdout,
        )
        mask_match = re.search(
            r"\bnetmask\s+(0x[0-9a-fA-F]+)",
            result.stdout,
        )

        if not ip_match or not mask_match:
            raise RuntimeError(
                f"No IPv4 address or netmask found on {interface}"
            )

        netmask = socket.inet_ntoa(
            int(mask_match.group(1), 16).to_bytes(4, "big")
        )

        return ipaddress.IPv4Network(
            (ip_match.group(1), netmask),
            strict=False,
        )

    raise RuntimeError(f"Unsupported operating system: {system}")


def ping_host(address):
    """Check whether a local IPv4 address responds to ping."""

    system = platform.system()

    if system == "Darwin":
        command = ["ping", "-n", "-c", "1", "-W", "1000", str(address)]
    else:
        command = ["ping", "-n", "-c", "1", "-W", "1", str(address)]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def read_arp_table():
    """Read the operating system's current IPv4 ARP neighbor table."""

    try:
        result = subprocess.run(
            ["arp", "-an"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}

    devices = {}

    for line in result.stdout.splitlines():
        ip_match = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)", line)
        mac_match = re.search(
            r"\bat\s+(([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})",
            line,
        )

        if ip_match:
            address = ip_match.group(1)
            mac = mac_match.group(1).lower() if mac_match else "Unknown"
            devices[address] = mac

    return devices


def resolve_hostname(address):
    try:
        return socket.gethostbyaddr(address)[0]
    except (socket.herror, socket.gaierror, OSError):
        return "Unknown"


def scan_network(interface):
    """Discover responsive hosts on the selected interface's local subnet."""

    network = get_interface_network(interface)

    if network.num_addresses > 1024:
        raise RuntimeError(
            f"Network {network} is too large for this discovery scan. "
            "A maximum of 1024 addresses is supported."
        )

    addresses = [
        str(address)
        for address in network.hosts()
    ]

    responsive = []

    with ThreadPoolExecutor(max_workers=64) as executor:
        futures = {
            executor.submit(ping_host, address): address
            for address in addresses
        }

        for future in as_completed(futures):
            address = futures[future]

            try:
                if future.result():
                    responsive.append(address)
            except Exception:
                pass

    arp_entries = read_arp_table()
    devices = []

    for address in sorted(responsive, key=ipaddress.ip_address):
        devices.append({
            "ip": address,
            "mac": arp_entries.get(address, "Unknown"),
            "hostname": resolve_hostname(address),
            "vendor": "Unknown",
            "status": "Responding to ping",
        })

    # Include other local ARP entries, even if they did not respond to ping.
    known_addresses = {device["ip"] for device in devices}

    for address, mac in arp_entries.items():
        if address in known_addresses:
            continue

        try:
            if ipaddress.ip_address(address) not in network:
                continue
        except ValueError:
            continue

        devices.append({
            "ip": address,
            "mac": mac,
            "hostname": resolve_hostname(address),
            "vendor": "Unknown",
            "status": "Present in ARP table",
        })

    return sorted(
        devices,
        key=lambda device: ipaddress.ip_address(device["ip"]),
    )


class NetworkScanWorker(QThread):
    completed = Signal(list)
    failed = Signal(str)

    def __init__(self, interface):
        super().__init__()
        self.interface = interface

    def run(self):
        try:
            devices = scan_network(self.interface)
            self.completed.emit(devices)
        except Exception as error:
            self.failed.emit(str(error))
