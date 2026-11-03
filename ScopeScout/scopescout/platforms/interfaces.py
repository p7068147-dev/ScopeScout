
import platform
import re
import socket
import subprocess
from dataclasses import dataclass


@dataclass
class NetworkInterface:
    name: str
    description: str
    wireless: bool


def discover_interfaces():
    """Discover wireless interfaces on macOS and Linux."""

    system = platform.system()
    available = {
        name for _, name in socket.if_nameindex()
    }

    results = []

    if system == "Linux":
        try:
            output = subprocess.run(
                ["iw", "dev"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            ).stdout

            wireless_names = re.findall(
                r"^\s*Interface\s+(\S+)",
                output,
                re.MULTILINE,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            wireless_names = []

        # Linux sysfs fallback
        if not wireless_names:
            for name in available:
                if name == "lo":
                    continue

                from pathlib import Path

                if (Path("/sys/class/net") / name / "wireless").exists():
                    wireless_names.append(name)

        for name in sorted(set(wireless_names)):
            if name in available:
                results.append(
                    NetworkInterface(
                        name=name,
                        description="Linux wireless interface",
                        wireless=True,
                    )
                )

    elif system == "Darwin":
        try:
            output = subprocess.run(
                ["networksetup", "-listallhardwareports"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            ).stdout

            blocks = re.split(r"\n\s*\n", output)

            for block in blocks:
                if "Hardware Port: Wi-Fi" not in block:
                    continue

                match = re.search(
                    r"Device:\s*(\S+)",
                    block,
                )

                if match:
                    name = match.group(1)

                    if name in available:
                        results.append(
                            NetworkInterface(
                                name=name,
                                description="macOS Wi-Fi interface",
                                wireless=True,
                            )
                        )

        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    else:
        raise RuntimeError(
            f"Unsupported operating system: {system}"
        )

    return results


def validate_interface(name):
    """Check that an interface still exists and is wireless."""

    return any(
        interface.name == name
        for interface in discover_interfaces()
    )
