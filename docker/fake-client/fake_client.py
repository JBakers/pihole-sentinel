#!/usr/bin/env python3
"""
Fake DHCP/Network Client

Simulates a network device that:
- Stays alive on the Docker network (ARP presence)
- Periodically pings both Pi-holes (populates ARP tables)
- Optionally registers itself as a DHCP lease on the primary Pi-hole

Environment variables:
  CLIENT_NAME:    Hostname for this client (default: auto-generated)
  CLIENT_MAC:     MAC address override (default: container's real MAC)
  PRIMARY_IP:     Primary Pi-hole IP to ping (default: 10.99.0.10)
  SECONDARY_IP:   Secondary Pi-hole IP to ping (default: 10.99.0.11)
  VIP_IP:         VIP address to ping (default: 10.99.0.100)
  PING_INTERVAL:  Seconds between ping cycles (default: 5)
"""

import os
import socket
import time
import uuid
import logging
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s"
)
logger = logging.getLogger(os.getenv("CLIENT_NAME", "fake-client"))

CLIENT_NAME = os.getenv("CLIENT_NAME", f"device-{uuid.uuid4().hex[:6]}")
PRIMARY_IP = os.getenv("PRIMARY_IP", "10.99.0.10")
SECONDARY_IP = os.getenv("SECONDARY_IP", "10.99.0.11")
VIP_IP = os.getenv("VIP_IP", "10.99.0.100")
PING_INTERVAL = int(os.getenv("PING_INTERVAL", "5"))


def get_own_ip():
    """Get this container's IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((PRIMARY_IP, 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "unknown"


def get_own_mac():
    """Get this container's MAC address from the network interface."""
    try:
        result = subprocess.run(
            ["ip", "link", "show", "eth0"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            line = line.strip()
            if "link/ether" in line:
                return line.split()[1].upper()
    except Exception:
        pass
    return "00:00:00:00:00:00"


def tcp_ping(ip, port=80, timeout=2):
    """TCP connect to populate ARP tables on both sides."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            return result == 0
    except Exception:
        return False


def main():
    own_ip = get_own_ip()
    own_mac = get_own_mac()

    logger.info(f"Fake client started: {CLIENT_NAME}")
    logger.info(f"  IP:  {own_ip}")
    logger.info(f"  MAC: {own_mac}")
    logger.info(f"  Pinging: {PRIMARY_IP}, {SECONDARY_IP}, {VIP_IP}")
    logger.info(f"  Interval: {PING_INTERVAL}s")

    cycle = 0
    while True:
        try:
            # TCP ping all Pi-holes → populates ARP tables on the Docker bridge
            for ip in [PRIMARY_IP, SECONDARY_IP, VIP_IP]:
                reachable = tcp_ping(ip)
                if cycle % 12 == 0:  # Log every ~60s at default interval
                    logger.debug(f"  {ip}: {'OK' if reachable else 'unreachable'}")

            cycle += 1
            time.sleep(PING_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Shutting down")
            break
        except Exception as e:
            logger.error(f"Error in ping cycle: {e}")
            time.sleep(PING_INTERVAL)


if __name__ == "__main__":
    main()
