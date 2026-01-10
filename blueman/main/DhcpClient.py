from typing import List

from gi.repository import GObject
from gi.repository import GLib
import socket
import subprocess
import logging
import shutil  # Added for safe executable lookup
from blueman.bluemantyping import GSignals


class DhcpClient(GObject.GObject):
    __gsignals__: GSignals = {
        # arg: interface name eg. ppp0
        'connected': (GObject.SignalFlags.NO_HOOKS, None, (str,)),
        'error-occurred': (GObject.SignalFlags.NO_HOOKS, None, (int,)),
    }

    # Fixed/safe paths for common DHCP clients (priority order)
    DHCP_CLIENTS = [
        "/usr/sbin/dhclient",
        "/usr/sbin/dhcpcd",
        "/usr/sbin/udhcpc",
    ]

    querying: List[str] = []

    def __init__(self, interface: str, timeout: int = 30) -> None:
        """The interface name has to be trusted / sanitized!"""
        super().__init__()

        self._interface = interface
        self._timeout = timeout

        self._command = None
        for client_path in self.DHCP_CLIENTS:
            # Use shutil.which for safe, realpath-resolved lookup
            resolved_path = shutil.which(client_path)
            if resolved_path:
                # Build command with resolved safe path
                if resolved_path.endswith("dhclient"):
                    self._command = [resolved_path, "-e", "IF_METRIC=100", "-1", self._interface]
                elif resolved_path.endswith("dhcpcd"):
                    self._command = [resolved_path, "-m", "100", self._interface]
                elif resolved_path.endswith("udhcpc"):
                    self._command = [
                        resolved_path,
                        "-t", "20",
                        "-x", "hostname", socket.gethostname(),
                        "-n", "-i", self._interface
                    ]
                break

    def run(self) -> None:
        if not self._command:
            raise Exception("No DHCP client found, please install dhclient, dhcpcd, or udhcpc")

        if self._interface in DhcpClient.querying:
            raise Exception("DHCP already running on this interface")
        else:
            DhcpClient.querying.append(self._interface)

        self._client = subprocess.Popen(self._command)
        GLib.timeout_add(1000, self._check_client)
        GLib.timeout_add(self._timeout * 1000, self._on_timeout)

    def _on_timeout(self) -> bool:
        if not self._client.poll():
            logging.warning("Timeout reached, terminating DHCP client")
            self._client.terminate()
        return False

    def _check_client(self) -> bool:
        netifs = get_local_interfaces()
        status = self._client.poll()
        if status == 0:
            def complete() -> bool:
                ip = netifs[self._interface][0]
                logging.info(f"bound to {ip}")
                self.emit("connected", ip)
                return False

            GLib.timeout_add(1000, complete)
            DhcpClient.querying.remove(self._interface)
            return False
        elif status:
            logging.error(f"dhcp client failed with status code {status}")
            self.emit("error-occurred", status)
            DhcpClient.querying.remove(self._interface)
            return False
        else:
            return True
