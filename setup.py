#!/usr/bin/env python3
"""
Pi-hole Sentinel Setup Configuration Script
==========================================

This script helps you configure your Pi-hole Sentinel High Availability setup by:
1. Collecting network configuration
2. Validating inputs
3. Generating secure passwords
4. Creating all necessary config files
"""

import os
import re
import sys
import json
import socket
import secrets
import string
import subprocess
import datetime
import urllib.request
import urllib.error
from ipaddress import ip_network, ip_address
from getpass import getpass

# Global verbose flag
VERBOSE = False

# Color codes for terminal output
class Colors:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    @staticmethod
    def disable():
        Colors.PURPLE = ''
        Colors.BLUE = ''
        Colors.CYAN = ''
        Colors.GREEN = ''
        Colors.YELLOW = ''
        Colors.RED = ''
        Colors.BOLD = ''
        Colors.UNDERLINE = ''
        Colors.END = ''

def detect_local_ip_range():
    """Best-effort detection of the first 3 octets of the primary IP.

    Tries to open a UDP socket to a public IP (no traffic sent) and inspects
    the local socket address. Falls back to None if detection fails.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('1.1.1.1', 80))
            local_ip = s.getsockname()[0]
        parts = local_ip.split('.')
        if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            return '.'.join(parts[:3])
    except Exception:
        pass
    return None

# ASCII art logo (aligned with logo.svg / logo-horizontal.svg styling)
def _get_version_banner():
    version_file = os.path.join(os.path.dirname(__file__), "VERSION")
    try:
        with open(version_file, "r", encoding="utf-8") as vf:
            return vf.read().strip()
    except Exception:
        return "unknown"


LOGO = f"""{Colors.PURPLE}{Colors.BOLD}
    ██████╗ ██╗██╗  ██╗ ██████╗ ██╗     ███████╗
    ██╔══██╗██║██║  ██║██╔═══██╗██║     ██╔════╝
    ██████╔╝██║███████║██║   ██║██║     █████╗  
    ██╔═══╝ ██║██╔══██║██║   ██║██║     ██╔══╝  
    ██║     ██║██║  ██║╚██████╔╝███████╗███████╗
    ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝
{Colors.END}{Colors.CYAN}{Colors.BOLD}
        ███████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗     
        ██╔════╝██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║     
        ███████╗█████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║     
        ╚════██║██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║     
        ███████║███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
        ╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝{Colors.END}{Colors.CYAN}{Colors.BOLD}
resilient dns · simple ops · keep dns up when others drop{Colors.END}{Colors.BOLD}
Version: {_get_version_banner()}
{Colors.END}
"""

class SetupConfig:
    def __init__(self):
        self.config = {}

    @staticmethod
    def _ask_required(prompt, validator=None, error_msg=None):
        """Ask for input and repeat until a non-empty, valid value is given."""
        while True:
            value = input(prompt).strip()
            if not value:
                print(f"{Colors.RED}This field is required.{Colors.END}")
                continue
            if validator and not validator(value):
                print(f"{Colors.RED}{error_msg or 'Invalid input.'}{Colors.END}")
                continue
            return value

    def validate_ip(self, ip):
        """Validate IP address format."""
        try:
            ip_address(ip)
            return True
        except ValueError:
            return False
    
    def validate_subnet(self, ip, netmask):
        """Validate if IP and netmask form a valid subnet."""
        try:
            ip_network(f"{ip}/{netmask}")
            return True
        except ValueError:
            return False

    def validate_interface_name(self, interface):
        """Validate network interface name to prevent command injection.

        Only allows alphanumeric characters, hyphens, underscores, and dots.
        """
        if not interface:
            return False
        # Interface names should be alphanumeric with limited special chars
        pattern = r'^[a-zA-Z0-9._-]{1,15}$'
        return bool(re.match(pattern, interface))

    def validate_port(self, port):
        """Validate port number is within valid range."""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False

    def validate_username(self, username):
        """Validate username to prevent injection attacks.

        Only allows alphanumeric characters, hyphens, underscores, and dots.
        """
        if not username:
            return False
        # Usernames should be alphanumeric with limited special chars
        pattern = r'^[a-zA-Z0-9._-]{1,32}$'
        return bool(re.match(pattern, username))

    def sanitize_input(self, input_str):
        """Sanitize user input by removing potentially dangerous characters.

        Returns sanitized string or None if input is invalid.
        """
        if not input_str:
            return None
        # Remove any shell metacharacters
        dangerous_chars = ['`', '$', ';', '|', '&', '>', '<', '(', ')', '{', '}', '[', ']', '\\', '"', "'", '\n', '\r']
        sanitized = input_str
        for char in dangerous_chars:
            if char in sanitized:
                return None
        return sanitized

    def escape_for_sed(self, text):
        """Escape special characters for safe use in sed replacement string.

        Escapes: /  \\  &  newline
        Uses # as delimiter to avoid issues with / in the text.
        """
        if not text:
            return text
        # Escape backslashes first (must be done before other escapes)
        escaped = text.replace('\\', '\\\\')
        # Escape & (special meaning in sed replacement)
        escaped = escaped.replace('&', '\\&')
        # Escape # (our delimiter)
        escaped = escaped.replace('#', '\\#')
        # Escape newlines
        escaped = escaped.replace('\n', '\\n')
        return escaped

    def check_host_reachable(self, ip):
        """Check if host is reachable."""
        try:
            return subprocess.run(
                ["ping", "-c", "1", "-W", "2", ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ).returncode == 0
        except:
            return False

    def generate_secure_password(self, length=32):
        """Generate a secure random password.
        
        Uses only alphanumeric characters to ensure compatibility with
        keepalived auth_pass and other config files that may have issues
        with special characters like !@#$%^&* in shell/config parsing.
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def validate_timezone(self, tz):
        """Validate timezone format to prevent shell injection."""
        if not tz:
            return False
        # Timezone format: Region/City or just a region (e.g., UTC)
        pattern = r'^[A-Za-z_]+(/[A-Za-z_]+)?$'
        return bool(re.match(pattern, tz)) and len(tz) <= 64
    
    def escape_for_env_file(self, value):
        """Escape value for safe use in .env file."""
        if not value:
            return ""
        value_str = str(value)
        # If value contains special chars, wrap in quotes and escape
        if any(c in value_str for c in ['"', "'", ' ', '\n', '\r', '=', '#', '$', '`']):
            escaped = value_str.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
        return value_str
    
    @staticmethod
    def _s(user):
        """Return 'sudo ' when the SSH user is not root, empty string otherwise.

        Usage: S = self._s(user)  →  f"{S}apt-get install ..."
        """
        return "" if user == "root" else "sudo "

    def remote_exec(self, host, user, port, command, password=None, retries=3, retry_delay=10):
        """Execute command on remote host via SSH.

        Uses environment variable for password to avoid exposure in process lists.
        Retries automatically on SSH connection failures (exit code 255) which can
        occur briefly after keepalived stops or when the remote host is recovering.
        """
        import time as _time

        ssh_opts = [
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=30",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=4",
        ]

        if self.config.get('ssh_key_path') and not password:
            cmd = ["ssh", "-i", self.config['ssh_key_path'], "-p", port] + ssh_opts
            env = None
        elif password:
            cmd = ["sshpass", "-e", "ssh", "-p", port] + ssh_opts
            env = os.environ.copy()
            env['SSHPASS'] = password
        else:
            cmd = ["ssh", "-p", port] + ssh_opts + ["-o", "BatchMode=yes"]
            env = None

        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                kwargs = {"check": True}
                if env:
                    kwargs["env"] = env
                return subprocess.run(cmd + [f"{user}@{host}", command], **kwargs)
            except subprocess.CalledProcessError as e:
                last_exc = e
                # Exit code 255 = SSH connection-level failure (not remote command failure).
                # This can happen after keepalived restart, brief sshd reload, or OOM recovery.
                if e.returncode == 255 and attempt < retries:
                    if VERBOSE:
                        print(f"\n│  SSH connection to {host} dropped (attempt {attempt}/{retries}), retrying in {retry_delay}s...")
                    _time.sleep(retry_delay)
                    continue
                raise
        raise last_exc  # unreachable, but satisfies type checkers
    
    def remote_copy(self, local_file, host, user, port, remote_path, password=None):
        """Copy file to remote host via SCP.

        Uses environment variable for password to avoid exposure in process lists.
        """
        # Use SSH key if available
        if self.config.get('ssh_key_path') and not password:
            cmd = ["scp", "-i", self.config['ssh_key_path'], "-P", port, "-o", "StrictHostKeyChecking=no"]
            return subprocess.run(cmd + [local_file, f"{user}@{host}:{remote_path}"], check=True)
        elif password:
            # Use environment variable instead of CLI argument for security
            cmd = ["sshpass", "-e", "scp", "-P", port, "-o", "StrictHostKeyChecking=no"]
            env = os.environ.copy()
            env['SSHPASS'] = password
            return subprocess.run(cmd + [local_file, f"{user}@{host}:{remote_path}"], check=True, env=env)
        else:
            cmd = ["scp", "-P", port, "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
            return subprocess.run(cmd + [local_file, f"{user}@{host}:{remote_path}"], check=True)
    
    def configure_timezone_and_ntp(self, host, user, port, password=None, timezone=None):
        """Configure timezone and enable NTP synchronization on remote host."""
        # Auto-detect timezone if not specified
        if timezone is None:
            try:
                result = subprocess.run(['timedatectl', 'show', '--property=Timezone', '--value'], 
                                      capture_output=True, text=True, timeout=5)
                timezone = result.stdout.strip() or "Europe/Amsterdam"
            except Exception:
                timezone = "Europe/Amsterdam"  # Fallback
        
        # Validate timezone format to prevent shell injection
        if not self.validate_timezone(timezone):
            print(f"{Colors.YELLOW}├─ Invalid timezone format '{timezone}', using Europe/Amsterdam{Colors.END}")
            timezone = "Europe/Amsterdam"
        
        print(f"{Colors.CYAN}├─ Configuring timezone ({timezone}) and NTP...{Colors.END}")
        S = self._s(user)
        try:
            # Set timezone — pass as positional argument, not embedded in shell string
            self.remote_exec(host, user, port,
                f"{S}timedatectl set-timezone -- {timezone}", password)

            # Try to enable NTP (will be skipped in containers, which sync from host)
            try:
                self.remote_exec(host, user, port, f"{S}systemctl enable systemd-timesyncd >/dev/null 2>&1 || true", password)
                self.remote_exec(host, user, port, f"{S}systemctl start systemd-timesyncd >/dev/null 2>&1 || true", password)
                self.remote_exec(host, user, port, f"{S}timedatectl set-ntp true >/dev/null 2>&1 || true", password)
            except:
                pass  # Containers sync time from host, so NTP service not needed
            
            print(f"{Colors.GREEN}├─ ✓ Timezone set to {timezone}{Colors.END}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}├─ ✗ Failed to configure timezone: {e}{Colors.END}")
            return False
    
    def install_remote_dependencies(self, host, user, port, password=None, packages=None):
        """Install system dependencies on remote host."""
        if packages is None:
            packages = [
                "build-essential", "python3-dev", "python3-pip",
                "keepalived", "arping", "iproute2", "iputils-ping",
                "sqlite3", "python3-venv", "sshpass", "dnsutils"
            ]
        
        print(f"\n┌─ Installing system dependencies on {host}")
        print(f"│  Packages: {len(packages)} total")

        S = self._s(user)

        try:
            # Update package lists
            print(f"│  [░░░░░░░░░░░░░░░░░░░░] 0%   Updating package lists...", end='\r')
            if VERBOSE:
                self.remote_exec(host, user, port, f"{S}apt-get update -o Acquire::Retries=3", password)
            else:
                # Keep stdout quiet but let stderr through so failures are visible
                self.remote_exec(host, user, port, f"{S}apt-get update -o Acquire::Retries=3 -qq >/dev/null", password)
            print(f"│  [████░░░░░░░░░░░░░░░░] 20%  Package lists updated     ")

            # Install packages (this is the slow part)
            print(f"│  [████░░░░░░░░░░░░░░░░] 20%  Installing packages...", end='\r')
            pkg_list = " ".join(packages)
            if VERBOSE:
                print(f"\n│  Installing: {pkg_list}")
            self.remote_exec(
                host,
                user,
                port,
                (
                    f"{S}env DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a "
                    "apt-get install -y "
                    "-o Dpkg::Use-Pty=0 "
                    "-o DPkg::Lock::Timeout=120 "
                    "-o Acquire::Retries=3 "
                    f"{pkg_list}"
                ),
                password,
            )
            
            print(f"│  [████████████████████] 100% Installation complete!    ")
            print(f"└─ ✓ Dependencies installed on {host}\n")
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n└─ ✗ Failed to install dependencies on {host}: {e}\n")
            return False
    
    def deploy_to_remote(self, host, user, port, files_to_copy, commands_to_run):
        """Deploy files and run commands on remote host."""
        try:
            print(f"\nDeploying to {host}...")
            
            # Copy files
            for local_file, remote_path in files_to_copy:
                print(f"  Copying {local_file} to {remote_path}...")
                self.remote_copy(local_file, host, user, port, remote_path)
            
            # Run commands
            for cmd in commands_to_run:
                print(f"  Running: {cmd[:50]}...")
                self.remote_exec(host, user, port, cmd)
            
            print(f"✓ Deployment to {host} successful!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Deployment to {host} failed: {e}")
            return False

    def get_interface_names(self):
        """Get list of physical network interfaces (filtered)."""
        interfaces = []
        try:
            if os.path.exists('/sys/class/net'):
                all_interfaces = os.listdir('/sys/class/net')
                # Filter out virtual/unwanted interfaces
                skip_prefixes = ('lo', 'docker', 'br-', 'veth', 'tailscale', 'bonding_masters', 'virbr', 'tun', 'tap')
                interfaces = [
                    iface for iface in all_interfaces
                    if not any(iface.startswith(prefix) for prefix in skip_prefixes)
                ]
                # Sort to prioritize common physical interface names
                priority = ['eth0', 'ens18', 'enp3s0', 'eno1']
                interfaces.sort(key=lambda x: (x not in priority, priority.index(x) if x in priority else 999, x))
        except:
            pass
        return interfaces or ['eth0', 'ens18', 'enp3s0']

    def collect_network_config(self):
        """Collect network configuration interactively."""
        print("\n=== Network Configuration ===")

        # Get network interface
        interfaces = self.get_interface_names()
        if len(interfaces) == 0:
            interfaces = ['eth0']

        print(f"\n{Colors.CYAN}Physical network interfaces detected:{Colors.END}")
        for i, iface in enumerate(interfaces[:5], 1):  # Show max 5
            marker = f"{Colors.GREEN}(default){Colors.END}" if i == 1 else ""
            print(f"  {i}. {iface} {marker}")
        if len(interfaces) > 5:
            print(f"  ... and {len(interfaces) - 5} more")

        while True:
            interface = input(f"\n{Colors.BOLD}Enter network interface name [{Colors.CYAN}{interfaces[0]}{Colors.END}]:{Colors.END} ").strip()
            if not interface:
                interface = interfaces[0]
            # Validate interface name to prevent command injection
            if not self.validate_interface_name(interface):
                print(f"{Colors.RED}Error: Invalid interface name! Only alphanumeric characters, dots, hyphens, and underscores allowed.{Colors.END}")
                continue
            if interface in interfaces:
                self.config['interface'] = interface
                print(f"{Colors.GREEN}✓ Using interface: {interface}{Colors.END}")
                break
            print(f"{Colors.YELLOW}Warning: '{interface}' not in detected physical interfaces.{Colors.END}")
            confirm = input(f"Are you sure you want to use '{interface}'? (y/N): ").strip().lower()
            if confirm == 'y':
                self.config['interface'] = interface
                break

        # Get IP addresses
        detected_range = detect_local_ip_range()
        if detected_range:
            self.config['ip_range'] = detected_range

        print(f"\n{Colors.YELLOW}NOTE: All IP addresses must be in the same subnet!{Colors.END}")
        while True:
            print(f"\n{Colors.BOLD}Choose IP configuration method:{Colors.END}")
            print(f"  1. {Colors.CYAN}Quick setup{Colors.END} (enter IP range once, then last octet for each device)")
            print(f"  2. Manual setup (enter full IP addresses)")

            setup_choice = input(f"\n{Colors.BOLD}Choice [1]:{Colors.END} ").strip() or "1"

            if setup_choice == "1":
                # Quick setup - IP range + last octet
                print(f"\n{Colors.CYAN}Quick Setup:{Colors.END}")
                default_range = self.config.get('ip_range') or detected_range
                if not default_range:
                    print(f"{Colors.YELLOW}No IP range auto-detected; please enter it manually.{Colors.END}")
                else:
                    print(f"Auto-detected range: {Colors.CYAN}{default_range}.x{Colors.END}")

                print("Enter the first 3 octets of your IP range (e.g., 192.168.178)")
                prompt = f"{Colors.BOLD}IP range{Colors.END}"
                if default_range:
                    prompt += f" [{default_range}]"
                prompt += ": "
                ip_range = input(prompt).strip()
                if not ip_range and default_range:
                    ip_range = default_range
                if not ip_range:
                    print(f"{Colors.RED}Error: IP range is required.{Colors.END}")
                    continue

                # Validate IP range format
                parts = ip_range.split('.')
                if len(parts) != 3:
                    print(f"{Colors.RED}Error: Invalid IP range! Must be exactly 3 octets (e.g., 192.168.178){Colors.END}")
                    continue

                if not all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                    print(f"{Colors.RED}Error: Invalid IP range! Each octet must be 0-255{Colors.END}")
                    continue

                def _valid_octet(v):
                    return v.isdigit() and 0 <= int(v) <= 255

                print(f"\n{Colors.CYAN}Enter last octet for each device (using {ip_range}.X):{Colors.END}")
                primary_octet = self._ask_required(f"Primary Pi-hole    ({ip_range}.): ", _valid_octet, "Must be 0-255")
                secondary_octet = self._ask_required(f"Secondary Pi-hole  ({ip_range}.): ", _valid_octet, "Must be 0-255")
                vip_octet = self._ask_required(f"Virtual IP (VIP)   ({ip_range}.): ", _valid_octet, "Must be 0-255")
                gateway_octet = self._ask_required(f"Network gateway    ({ip_range}.): ", _valid_octet, "Must be 0-255")

                # Validate octets
                try:
                    octets = [primary_octet, secondary_octet, vip_octet, gateway_octet]

                    primary_ip = f"{ip_range}.{primary_octet}"
                    secondary_ip = f"{ip_range}.{secondary_octet}"
                    vip = f"{ip_range}.{vip_octet}"
                    gateway = f"{ip_range}.{gateway_octet}"
                    self.config['ip_range'] = ip_range
                except ValueError:
                    print(f"{Colors.RED}Error: Invalid octet value!{Colors.END}")
                    continue
            else:
                # Manual setup - full IP addresses
                print(f"\n{Colors.CYAN}Manual Setup:{Colors.END}")
                print("Enter full IP addresses:")
                primary_ip = self._ask_required("Primary Pi-hole IP: ", self.validate_ip, "Invalid IP address")
                secondary_ip = self._ask_required("Secondary Pi-hole IP: ", self.validate_ip, "Invalid IP address")
                vip = self._ask_required("Virtual IP (VIP) address: ", self.validate_ip, "Invalid IP address")
                gateway = self._ask_required("Network gateway IP: ", self.validate_ip, "Invalid IP address")

            # Validate all IPs
            if not all(map(self.validate_ip, [primary_ip, secondary_ip, vip, gateway])):
                print(f"{Colors.RED}Error: Invalid IP address format!{Colors.END}")
                continue

            # Check if IPs are in same subnet
            try:
                netmask = "24"  # Assuming /24 network
                network = str(ip_network(f"{primary_ip}/{netmask}", strict=False).network_address)
                if not all(ip_address(ip) in ip_network(f"{network}/{netmask}")
                          for ip in [primary_ip, secondary_ip, vip, gateway]):
                    print(f"{Colors.RED}Error: IP addresses must be in the same subnet!{Colors.END}")
                    continue
            except ValueError as e:
                print(f"{Colors.RED}Error: {e}{Colors.END}")
                continue

            # Show summary
            print(f"\n{Colors.GREEN}✓ IP Configuration:{Colors.END}")
            print(f"  Primary Pi-hole:  {primary_ip}")
            print(f"  Secondary Pi-hole: {secondary_ip}")
            print(f"  Virtual IP (VIP):  {vip}")
            print(f"  Network gateway:   {gateway}")

            confirm = input(f"\n{Colors.BOLD}Is this correct? (Y/n):{Colors.END} ").strip().lower()
            if confirm == 'n':
                continue

            self.config.update({
                'primary_ip': primary_ip,
                'secondary_ip': secondary_ip,
                'vip': vip,
                'gateway': gateway,
                'netmask': netmask
            })
            break

    def collect_dhcp_config(self):
        """Collect DHCP failover configuration."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}=== DHCP Configuration ==={Colors.END}")
        
        while True:
            dhcp = input(f"\n{Colors.BOLD}Do you use DHCP on your Pi-holes? (Y/n):{Colors.END} ").lower()
            if dhcp in ['y', 'n', '']:
                # Default to 'y' if user just presses Enter
                self.config['dhcp_enabled'] = dhcp != 'n'
                break
            print(f"{Colors.RED}Please enter 'y' or 'n'{Colors.END}")

        # Config sync interval (deployed to primary, syncs to secondary)
        print(f"\n{Colors.CYAN}{Colors.BOLD}=== Configuration Sync ==={Colors.END}")
        print(f"{Colors.CYAN}Pi-hole Sentinel automatically syncs settings from primary → secondary.{Colors.END}")
        print(f"{Colors.CYAN}This replaces tools like nebula-sync. Syncs: gravity, DNS, DHCP, config.{Colors.END}")
        while True:
            interval = input(f"\n{Colors.BOLD}Sync interval in minutes [{Colors.CYAN}10{Colors.END}]:{Colors.END} ").strip() or "10"
            if interval.isdigit() and 1 <= int(interval) <= 1440:
                self.config['sync_interval'] = int(interval)
                print(f"{Colors.GREEN}✓ Config sync every {interval} minutes{Colors.END}")
                break
            print(f"{Colors.RED}Enter a number between 1 and 1440 (24 hours){Colors.END}")
            
    def setup_ssh_keys(self):
        """Generate SSH key and distribute to all servers."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}=== SSH Key Setup ==={Colors.END}")
        print(f"Setting up passwordless SSH access to all servers...")
        
        # Check if SSH key already exists
        ssh_key_path = os.path.expanduser("~/.ssh/id_pihole_sentinel")
        if os.path.exists(ssh_key_path):
            print(f"\n{Colors.YELLOW}Existing SSH key found: {ssh_key_path}{Colors.END}")
            reuse = input("Use existing key? (Y/n): ").strip().lower()
            if reuse != 'n':
                print(f"{Colors.GREEN}✓ Using existing SSH key{Colors.END}")
                return ssh_key_path
        
        # Generate new SSH key
        print(f"\n{Colors.CYAN}Generating new SSH key...{Colors.END}")
        try:
            subprocess.run([
                "ssh-keygen", "-t", "ed25519", 
                "-f", ssh_key_path,
                "-N", "",  # No passphrase
                "-C", "pihole-sentinel-setup"
            ], check=True, capture_output=True)
            print(f"{Colors.GREEN}✓ SSH key generated{Colors.END}")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}✗ Failed to generate SSH key: {e}{Colors.END}")
            return None
        
        return ssh_key_path
    
    def distribute_ssh_key(self, host, user, port, password, key_path):
        """Distribute SSH public key to a remote host."""
        pub_key_path = f"{key_path}.pub"
        
        try:
            # Read public key
            with open(pub_key_path, 'r') as f:
                pub_key = f.read().strip()
            
            # Copy key to remote host
            print(f"  Copying SSH key to {user}@{host}...", end=' ')
            
            # Use sshpass with environment variable to authenticate and add key (secure)
            cmd = [
                "sshpass", "-e",
                "ssh", "-p", port,
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=10",
                f"{user}@{host}",
                f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys << 'SENTINEL_EOF'\n{pub_key}\nSENTINEL_EOF\nchmod 600 ~/.ssh/authorized_keys"
            ]

            env = os.environ.copy()
            env['SSHPASS'] = password
            result = subprocess.run(cmd, capture_output=True, timeout=15, env=env)
            
            if result.returncode == 0:
                # Test the key
                test_cmd = [
                    "ssh", "-i", key_path, "-p", port,
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "BatchMode=yes",
                    "-o", "ConnectTimeout=5",
                    f"{user}@{host}",
                    "echo 'OK'"
                ]
                test = subprocess.run(test_cmd, capture_output=True, timeout=10)
                
                if test.returncode == 0:
                    print(f"{Colors.GREEN}✓{Colors.END}")
                    return True
                else:
                    print(f"{Colors.RED}✗ (key test failed){Colors.END}")
                    return False
            else:
                print(f"{Colors.RED}✗ (copy failed){Colors.END}")
                return False
                
        except Exception as e:
            print(f"{Colors.RED}✗ (error: {e}){Colors.END}")
            return False

    def _setup_cross_node_ssh(self, host_a, user_a, port_a, host_b, user_b, port_b):
        """Setup passwordless SSH between two Pi-hole nodes.

        Generates an ed25519 key on host_a (if not present) and adds its
        public key to host_b's authorized_keys, then vice versa.
        Uses the already-established SSH from the installer to orchestrate.
        """
        try:
            for src, src_u, src_p, dst, dst_u, dst_p, label in [
                (host_a, user_a, port_a, host_b, user_b, port_b, f"{host_a} → {host_b}"),
                (host_b, user_b, port_b, host_a, user_a, port_a, f"{host_b} → {host_a}"),
            ]:
                print(f"  Setting up {label}...", end=" ", flush=True)
                # Generate key on source if it doesn't exist
                self.remote_exec(src, src_u, src_p,
                    'test -f /root/.ssh/id_ed25519 || '
                    'ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N "" -q')
                # Read public key from source
                ssh_cmd = ["ssh", "-p", src_p,
                           "-o", "StrictHostKeyChecking=no",
                           "-o", "ConnectTimeout=10"]
                if self.config.get('ssh_key_path'):
                    ssh_cmd += ["-i", self.config['ssh_key_path']]
                else:
                    ssh_cmd += ["-o", "BatchMode=yes"]
                result = subprocess.run(
                    ssh_cmd + [f"{src_u}@{src}", "cat /root/.ssh/id_ed25519.pub"],
                    capture_output=True, text=True, timeout=15)
                if result.returncode != 0:
                    print(f"{Colors.RED}✗ (failed to read key){Colors.END}")
                    return False
                pub_key = result.stdout.strip()
                # Add to destination authorized_keys (idempotent — skip if already present)
                self.remote_exec(dst, dst_u, dst_p,
                    f'mkdir -p /root/.ssh && chmod 700 /root/.ssh && '
                    f'grep -qF "{pub_key}" /root/.ssh/authorized_keys 2>/dev/null || '
                    f'cat >> /root/.ssh/authorized_keys << \'SENTINEL_CROSS_EOF\'\n{pub_key}\nSENTINEL_CROSS_EOF\n'
                    f'chmod 600 /root/.ssh/authorized_keys')
                # Accept host key on source so first sync doesn't hang on prompt
                self.remote_exec(src, src_u, src_p,
                    f'ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 '
                    f'{dst_u}@{dst} "echo ok" >/dev/null 2>&1 || true')
                print(f"{Colors.GREEN}✓{Colors.END}")
            return True
        except Exception as e:
            print(f"{Colors.RED}✗ (error: {e}){Colors.END}")
            return False

    def collect_monitor_config(self):
        """Collect monitoring server configuration."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}=== Monitor Configuration ==={Colors.END}")
        
        while True:
            monitor_type = input(f"\n{Colors.BOLD}Where to install the monitor?{Colors.END}\n1. Separate server {Colors.GREEN}(recommended){Colors.END}\n2. On primary Pi-hole\nChoice [{Colors.CYAN}1{Colors.END}]: ").strip() or "1"
            if monitor_type in ['1', '2']:
                self.config['separate_monitor'] = monitor_type == '1'
                break
            print(f"{Colors.RED}Please enter '1' or '2'{Colors.END}")
            
        if self.config['separate_monitor']:
            while True:
                default_range = self.config.get('ip_range')

                if default_range:
                    print(f"\n{Colors.CYAN}Monitor IP (quick){Colors.END} — using range {default_range}.X")
                    monitor_octet = input(f"Last octet for monitor ({default_range}.): ").strip()

                    try:
                        if not monitor_octet.isdigit() or not (0 <= int(monitor_octet) <= 255):
                            print(f"{Colors.RED}Error: Invalid octet! Must be 0-255{Colors.END}")
                            continue
                        monitor_ip = f"{default_range}.{monitor_octet}"
                    except ValueError:
                        print(f"{Colors.RED}Error: Invalid octet!{Colors.END}")
                        continue
                else:
                    monitor_ip = input(f"\n{Colors.BOLD}Monitor server IP:{Colors.END} ").strip()

                if self.validate_ip(monitor_ip):
                    self.config['monitor_ip'] = monitor_ip

                    # Validate SSH user
                    while True:
                        ssh_user = input(f"SSH user [{Colors.CYAN}root{Colors.END}]: ").strip() or "root"
                        if self.validate_username(ssh_user):
                            self.config['monitor_ssh_user'] = ssh_user
                            break
                        print(f"{Colors.RED}Error: Invalid username!{Colors.END}")

                    # Validate SSH port
                    while True:
                        ssh_port = input(f"SSH port [{Colors.CYAN}22{Colors.END}]: ").strip() or "22"
                        if self.validate_port(ssh_port):
                            self.config['monitor_ssh_port'] = ssh_port
                            break
                        print(f"{Colors.RED}Error: Invalid port! Must be between 1-65535.{Colors.END}")
                    
                    if self.check_host_reachable(monitor_ip):
                        print(f"{Colors.GREEN}✓ Monitor server is reachable{Colors.END}")
                        break
                    else:
                        proceed = input(f"{Colors.YELLOW}⚠ Warning: Monitor server not reachable. Proceed anyway? (y/N):{Colors.END} ").lower()
                        if proceed == 'y':
                            break
                print(f"{Colors.RED}Please enter a valid IP address{Colors.END}")
        else:
            self.config['monitor_ip'] = self.config['primary_ip']
            self.config['monitor_ssh_user'] = "root"
            self.config['monitor_ssh_port'] = "22"
            print(f"\n{Colors.GREEN}✓ Monitor will be installed on primary Pi-hole: {self.config['monitor_ip']}{Colors.END}")

    def collect_pihole_config(self):
        """Collect Pi-hole SSH configuration."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}=== Pi-hole SSH Configuration ==={Colors.END}")
        
        # Set defaults for all servers
        print(f"\nSSH access configuration (same for all servers):")

        # Validate SSH user
        while True:
            ssh_user = input(f"SSH user [{Colors.CYAN}root{Colors.END}]: ").strip() or "root"
            if self.validate_username(ssh_user):
                break
            print(f"{Colors.RED}Error: Invalid username! Only alphanumeric, dots, hyphens, and underscores allowed.{Colors.END}")

        # Validate SSH port
        while True:
            ssh_port = input(f"SSH port [{Colors.CYAN}22{Colors.END}]: ").strip() or "22"
            if self.validate_port(ssh_port):
                break
            print(f"{Colors.RED}Error: Invalid port! Must be between 1-65535.{Colors.END}")

        # Apply to all servers
        self.config['primary_ssh_user'] = ssh_user
        self.config['primary_ssh_port'] = ssh_port
        self.config['secondary_ssh_user'] = ssh_user
        self.config['secondary_ssh_port'] = ssh_port
        
        if self.config.get('monitor_ssh_user') is None:
            self.config['monitor_ssh_user'] = ssh_user
            self.config['monitor_ssh_port'] = ssh_port
        
        print(f"\n{Colors.CYAN}Now we'll ask for SSH passwords to setup passwordless access.{Colors.END}")
        print(f"{Colors.CYAN}Passwords are only needed once to distribute SSH keys.{Colors.END}")
        
        # Collect passwords for all servers
        servers = []
        if self.config['separate_monitor']:
            servers.append(('monitor', self.config['monitor_ip'], self.config['monitor_ssh_user'], self.config['monitor_ssh_port']))
        servers.append(('primary', self.config['primary_ip'], self.config['primary_ssh_user'], self.config['primary_ssh_port']))
        servers.append(('secondary', self.config['secondary_ip'], self.config['secondary_ssh_user'], self.config['secondary_ssh_port']))
        
        passwords = {}
        same_pw = input(f"\n{Colors.BOLD}Use the same SSH password for all servers? (Y/n):{Colors.END} ").strip().lower()
        if same_pw != 'n':
            shared_pw = getpass(f"{Colors.BOLD}SSH password for all servers:{Colors.END} ")
            for name, ip, user, port in servers:
                passwords[name] = shared_pw
            # Clear reference immediately
            shared_pw = None
        else:
            print()
            for name, ip, user, port in servers:
                passwords[name] = getpass(f"{Colors.BOLD}SSH password for {user}@{ip}:{Colors.END} ")
        
        # Setup SSH keys
        key_path = self.setup_ssh_keys()
        if not key_path:
            print(f"\n{Colors.RED}Failed to setup SSH keys. Exiting.{Colors.END}")
            # Securely clear passwords from memory
            for key in passwords:
                passwords[key] = None
            passwords.clear()
            sys.exit(1)
        
        # Distribute keys to all servers
        print(f"\n{Colors.CYAN}Distributing SSH keys to servers...{Colors.END}")
        success = True
        for name, ip, user, port in servers:
            if not self.distribute_ssh_key(ip, user, port, passwords[name], key_path):
                print(f"{Colors.RED}✗ Failed to setup SSH key for {name}{Colors.END}")
                success = False
        
        if not success:
            for key in passwords:
                passwords[key] = None
            passwords.clear()
            del passwords
            print(f"\n{Colors.RED}Failed to distribute SSH keys to all servers.{Colors.END}")
            sys.exit(1)

        # Store key path NOW so remote_exec can use it for cross-node setup
        self.config['ssh_key_path'] = key_path

        # Setup cross-node SSH: primary ↔ secondary (needed for config sync)
        print(f"\n{Colors.CYAN}Setting up cross-node SSH between Pi-holes...{Colors.END}")
        cross_ok = self._setup_cross_node_ssh(
            self.config['primary_ip'], self.config['primary_ssh_user'], self.config['primary_ssh_port'],
            self.config['secondary_ip'], self.config['secondary_ssh_user'], self.config['secondary_ssh_port'],
        )
        if not cross_ok:
            print(f"{Colors.YELLOW}⚠ Cross-node SSH setup failed — config sync may not work automatically{Colors.END}")
            print(f"{Colors.YELLOW}  You can fix this manually: ssh-copy-id root@pihole2 (from pihole1){Colors.END}")

        # Securely clear passwords from memory immediately after use
        for key in passwords:
            passwords[key] = None
        passwords.clear()
        del passwords
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ SSH keys successfully distributed to all servers!{Colors.END}")
        print(f"{Colors.GREEN}  Passwordless access is now configured.{Colors.END}")
        
        # Clear passwords - not needed anymore (defense in depth)
        self.config['primary_ssh_pass'] = None
        self.config['secondary_ssh_pass'] = None
        self.config['monitor_ssh_pass'] = None
        
        # Generate secure keepalived password
        # keepalived PASS auth truncates to 8 characters — generate exactly 8
        self.config['keepalived_password'] = self.generate_secure_password(length=8)
    
    def collect_pihole_passwords(self):
        """Collect Pi-hole web interface passwords (for monitoring)."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}=== Pi-hole Web Interface Passwords ==={Colors.END}")
        print(f"\n{Colors.YELLOW}These passwords are used by the monitor to access Pi-hole API for statistics.{Colors.END}")
        print(f"{Colors.YELLOW}This is the same password you use to login to the Pi-hole web interface.{Colors.END}")
        print(f"\n{Colors.CYAN}How to find your Pi-hole password:{Colors.END}")
        print(f"  1. If you know it: Use your existing Pi-hole admin password")
        print(f"  2. If you forgot it: SSH to Pi-hole and run: {Colors.BOLD}pihole -a -p{Colors.END}")
        print(f"  3. First time setup: The password was shown during Pi-hole installation")
        print(f"\n{Colors.GREEN}Tip: You can test if password works by logging into http://<pihole-ip>/admin{Colors.END}\n")
        
        self.config['primary_password'] = getpass(f"{Colors.BOLD}Primary Pi-hole ({self.config['primary_ip']}) web password:{Colors.END} ")
        self.config['secondary_password'] = getpass(f"{Colors.BOLD}Secondary Pi-hole ({self.config['secondary_ip']}) web password:{Colors.END} ")

    def verify_configuration(self):
        """Verify the collected configuration."""
        print("\n=== Configuration Verification ===")
        
        print("\nTesting connectivity...")
        unreachable = []
        for name, ip in [("Primary", self.config['primary_ip']),
                        ("Secondary", self.config['secondary_ip']),
                        ("Gateway", self.config['gateway'])]:
            if not self.check_host_reachable(ip):
                unreachable.append(f"{name} ({ip})")
        
        if unreachable:
            print("\nWarning: The following hosts are not reachable:")
            for host in unreachable:
                print(f"  - {host}")
            proceed = input("\nDo you want to proceed anyway? (y/N): ").lower() == 'y'
            if not proceed:
                sys.exit(1)

    def _check_pihole_api(self, ip, password):
        """Return (ok: bool, message: str) for Pi-hole v6 API authentication."""
        url = f"http://{ip}/api/auth"
        payload = json.dumps({"password": password}).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                body = json.loads(resp.read().decode())
            if body.get("session", {}).get("valid"):
                return True, "OK"
            return False, "wrong password (API returned invalid session)"
        except urllib.error.HTTPError as e:
            return False, f"HTTP {e.code}"
        except urllib.error.URLError as e:
            return False, f"unreachable ({e.reason})"
        except Exception as e:
            return False, str(e)

    def preflight_checks(self):
        """Validate all credentials and SSH access before touching any server.

        Checks (in order):
          1. SSH connectivity + command execution on every target host
          2. Pi-hole web API password for primary and secondary

        Calls sys.exit(1) with a clear summary if anything fails so the user
        can fix credentials before any files are modified on the servers.
        """
        print(f"\n{Colors.CYAN}{Colors.BOLD}═══ Pre-flight Credential Check ═══{Colors.END}")
        failures = []

        # --- SSH checks ---
        ssh_targets = []
        if self.config.get('separate_monitor'):
            ssh_targets.append(("Monitor",
                                self.config['monitor_ip'],
                                self.config['monitor_ssh_user'],
                                self.config['monitor_ssh_port']))
        ssh_targets += [
            ("Primary Pi-hole",
             self.config['primary_ip'],
             self.config['primary_ssh_user'],
             self.config['primary_ssh_port']),
            ("Secondary Pi-hole",
             self.config['secondary_ip'],
             self.config['secondary_ssh_user'],
             self.config['secondary_ssh_port']),
        ]

        for name, host, user, port in ssh_targets:
            label = f"SSH {user}@{host}"
            print(f"  Checking {label} … ", end="", flush=True)
            try:
                self.remote_exec(host, user, port, "echo ok")
                print(f"{Colors.GREEN}✓{Colors.END}")
            except subprocess.CalledProcessError:
                print(f"{Colors.RED}✗  authentication failed{Colors.END}")
                failures.append(f"{name}: SSH login failed for {user}@{host}:{port}")
            except FileNotFoundError:
                print(f"{Colors.RED}✗  ssh not found{Colors.END}")
                failures.append(f"{name}: 'ssh' command not found on this machine")
            except Exception as e:
                print(f"{Colors.RED}✗  {e}{Colors.END}")
                failures.append(f"{name}: SSH error — {e}")

        # --- Pi-hole API checks (only when passwords have been collected) ---
        for name, ip, pw_key in [
            ("Primary Pi-hole API",   self.config['primary_ip'],   'primary_password'),
            ("Secondary Pi-hole API", self.config['secondary_ip'], 'secondary_password'),
        ]:
            password = self.config.get(pw_key, "")
            print(f"  Checking {name} ({ip}) … ", end="", flush=True)
            ok, msg = self._check_pihole_api(ip, password)
            if ok:
                print(f"{Colors.GREEN}✓{Colors.END}")
            else:
                print(f"{Colors.RED}✗  {msg}{Colors.END}")
                failures.append(f"{name}: {msg}")

        if failures:
            print(f"\n{Colors.RED}{Colors.BOLD}Pre-flight check failed — no files have been changed on any server.{Colors.END}")
            print(f"{Colors.RED}Fix the following issues and re-run setup:{Colors.END}")
            for f in failures:
                print(f"  {Colors.RED}✗{Colors.END}  {f}")
            sys.exit(1)

        print(f"\n{Colors.GREEN}✓ All credentials verified — starting deployment.{Colors.END}\n")

    def generate_configs(self):
        """Generate configuration files."""
        print("\n=== Generating Configuration Files ===")
        
        # Create primary keepalived config
        primary_keepalived = f"""# Keepalived configuration for Primary Pi-hole
# Generated by setup script - DO NOT EDIT MANUALLY

global_defs {{
    router_id PIHOLE1
    vrrp_version 2
    vrrp_garp_master_delay 1
    enable_script_security
    script_user root
}}

vrrp_script chk_pihole_service {{
    script "/usr/local/bin/check_pihole_service.sh"
    interval 5
    fall 5
    rise 3
}}

{f'''vrrp_script chk_dhcp_service {{
    script "/usr/local/bin/check_dhcp_service.sh"
    interval 5
    fall 2
    rise 1
}}''' if self.config.get('dhcp_enabled', False) else ''}

vrrp_instance VI_1 {{
    state MASTER
    interface {self.config['interface']}
    virtual_router_id 51
    priority 150
    advert_int 1
    
    authentication {{
        auth_type PASS
        auth_pass {self.config['keepalived_password']}
    }}
    
    virtual_ipaddress {{
        {self.config['vip']}/{self.config['netmask']}
    }}
    
    track_script {{
        chk_pihole_service weight -60
        {'''chk_dhcp_service weight -40''' if self.config.get('dhcp_enabled', False) else ''}
    }}
    
    notify_master "/usr/local/bin/keepalived_notify.sh MASTER"
    notify_backup "/usr/local/bin/keepalived_notify.sh BACKUP"
    notify_fault "/usr/local/bin/keepalived_notify.sh FAULT"
}}"""

        # Create secondary keepalived config (similar but with BACKUP state).
        # preempt_delay only applies to BACKUP nodes attempting to preempt;
        # it is not valid on state MASTER and keepalived 2.3.x exits with
        # code 1 if it is present — so it is absent from the template above.
        secondary_keepalived = primary_keepalived.replace(
            "state MASTER", "state BACKUP"
        ).replace(
            "priority 150", "priority 100"
        ).replace(
            "router_id PIHOLE1", "router_id PIHOLE2"
        )

        # Create monitor configuration
        # Generate secure API key for monitor dashboard (or reuse existing)
        api_key = self.config.get('api_key')
        if not api_key:
            # Check if monitor.env already exists from previous deployment
            if os.path.exists('generated_configs/monitor.env'):
                try:
                    with open('generated_configs/monitor.env', 'r') as f:
                        for line in f:
                            if line.startswith('API_KEY='):
                                api_key = line.split('=', 1)[1].strip()
                                break
                except:
                    pass

            # Generate new key if still not found
            if not api_key:
                api_key = secrets.token_urlsafe(32)

            self.config['api_key'] = api_key  # Store for later use

        monitor_env = f"""# Pi-hole HA Monitor Configuration
# Generated by setup script

# Primary Pi-hole
PRIMARY_IP={self.config['primary_ip']}
PRIMARY_NAME="Primary Pi-hole"
PRIMARY_PASSWORD={self.config['primary_password']}

# Secondary Pi-hole
SECONDARY_IP={self.config['secondary_ip']}
SECONDARY_NAME="Secondary Pi-hole"
SECONDARY_PASSWORD={self.config['secondary_password']}

# VIP Configuration
VIP_ADDRESS={self.config['vip']}

# Monitor Settings
CHECK_INTERVAL=10
DB_PATH=/opt/pihole-monitor/monitor.db

# API Security
API_KEY={api_key}
"""

        # Create environment files
        primary_env = f"""# Primary Pi-hole Keepalived Environment
# Generated by setup script

INTERFACE={self.config['interface']}
VIP_ADDRESS={self.config['vip']}
VIP_NETMASK={self.config['netmask']}
NETWORK_GATEWAY={self.config['gateway']}
VRRP_AUTH_PASS={self.config['keepalived_password']}
NODE_PRIORITY=150
NODE_STATE=MASTER
PRIMARY_IP={self.config['primary_ip']}
SECONDARY_IP={self.config['secondary_ip']}
"""

        secondary_env = primary_env.replace(
            "NODE_PRIORITY=150", "NODE_PRIORITY=100"
        ).replace(
            "NODE_STATE=MASTER", "NODE_STATE=BACKUP"
        )

        # Save configurations
        configs = {
            'primary_keepalived.conf': primary_keepalived,
            'secondary_keepalived.conf': secondary_keepalived,
            'monitor.env': monitor_env,
            'primary.env': primary_env,
            'secondary.env': secondary_env
        }

        os.makedirs('generated_configs', mode=0o700, exist_ok=True)
        for filename, content in configs.items():
            with open(f"generated_configs/{filename}", 'w') as f:
                f.write(content)

        print("\nConfiguration files generated in 'generated_configs/' directory:")
        for filename in configs:
            print(f"  - {filename}")

    def deploy_monitor(self):
        """Deploy the monitor service."""
        try:
            print("\nSetting up monitor service...")
            
            # Create monitor user
            print("Creating service user...")
            subprocess.run(["sudo", "useradd", "-r", "-s", "/bin/false", "pihole-monitor"], check=False)
            
            # Create directory structure
            print("Creating directory structure...")
            subprocess.run(["sudo", "mkdir", "-p", "/opt/pihole-monitor"], check=True)
            
            # Setup Python virtual environment
            print("Setting up Python environment...")
            subprocess.run(["sudo", "python3", "-m", "venv", "/opt/pihole-monitor/venv"], check=True)
            subprocess.run(["sudo", "/opt/pihole-monitor/venv/bin/pip", "install", "-r", "requirements.txt"], check=True)
            
            # Copy files
            print("Copying application files...")
            subprocess.run(["sudo", "cp", "dashboard/monitor.py", "/opt/pihole-monitor/"], check=True)
            subprocess.run(["sudo", "cp", "dashboard/index.html", "/opt/pihole-monitor/"], check=True)
            subprocess.run(["sudo", "cp", "dashboard/settings.html", "/opt/pihole-monitor/"], check=True)
            subprocess.run(["sudo", "cp", "generated_configs/monitor.env", "/opt/pihole-monitor/.env"], check=True)
            subprocess.run(["sudo", "cp", "systemd/pihole-monitor.service",
                          "/etc/systemd/system/"], check=True)

            # Inject API key into HTML files
            print("Configuring API authentication...")
            api_key = self.config.get('api_key')
            if api_key:
                subprocess.run([
                    "sudo", "sed", "-i",
                    f"s/YOUR_API_KEY_HERE/{api_key}/g",
                    "/opt/pihole-monitor/index.html"
                ], check=True)
                subprocess.run([
                    "sudo", "sed", "-i",
                    f"s/YOUR_API_KEY_HERE/{api_key}/g",
                    "/opt/pihole-monitor/settings.html"
                ], check=True)
                print(f"  → API key configured successfully")

            # Set correct ownership and permissions
            print("Setting permissions...")
            
            # Main directory: 755 pihole-monitor:pihole-monitor
            subprocess.run(["sudo", "chown", "pihole-monitor:pihole-monitor", "/opt/pihole-monitor"], check=True)
            subprocess.run(["sudo", "chmod", "755", "/opt/pihole-monitor"], check=True)
            
            # Application files: 644 pihole-monitor:pihole-monitor
            for file in ["monitor.py", "index.html", "settings.html"]:
                subprocess.run(["sudo", "chown", "pihole-monitor:pihole-monitor", 
                              f"/opt/pihole-monitor/{file}"], check=True)
                subprocess.run(["sudo", "chmod", "644", f"/opt/pihole-monitor/{file}"], check=True)
            
            # Environment file: 600 pihole-monitor:pihole-monitor (contains secrets)
            subprocess.run(["sudo", "chown", "pihole-monitor:pihole-monitor", 
                          "/opt/pihole-monitor/.env"], check=True)
            subprocess.run(["sudo", "chmod", "600", "/opt/pihole-monitor/.env"], check=True)
            
            # Virtual environment: 755 pihole-monitor:pihole-monitor
            subprocess.run(["sudo", "chown", "-R", "pihole-monitor:pihole-monitor", 
                          "/opt/pihole-monitor/venv"], check=True)
            subprocess.run(["sudo", "chmod", "-R", "755", "/opt/pihole-monitor/venv"], check=True)
            
            # Service file: 644 root:root
            subprocess.run(["sudo", "chown", "root:root", 
                          "/etc/systemd/system/pihole-monitor.service"], check=True)
            subprocess.run(["sudo", "chmod", "644", 
                          "/etc/systemd/system/pihole-monitor.service"], check=True)
            
            # Enable and start service
            print("Starting service...")
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
            subprocess.run(["sudo", "systemctl", "enable", "pihole-monitor"], check=True)
            subprocess.run(["sudo", "systemctl", "start", "pihole-monitor"], check=True)
            
            print("Monitor service deployed successfully!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error deploying monitor: {e}")
            return False

    def deploy_monitor_remote(self):
        """Deploy monitor service to remote server via SSH."""
        if not self.config.get('monitor_ssh_user'):
            print("No remote monitor configured, deploying locally...")
            return self.deploy_monitor()

        host = self.config['monitor_ip']
        user = self.config['monitor_ssh_user']
        port = self.config['monitor_ssh_port']
        password = self.config.get('monitor_ssh_pass')
        S = self._s(user)

        try:
            print(f"\nDeploying monitor to {host} via SSH...")

            # Install system dependencies first
            if not self.install_remote_dependencies(host, user, port, password):
                return False

            # Configure timezone and NTP
            self.configure_timezone_and_ntp(host, user, port, password)

            # Pre-deployment checks and directory setup
            print("Running pre-deployment checks...")
            print("├─ Creating required directories...")
            # Create /etc/pihole-sentinel (required by systemd ReadWritePaths)
            self.remote_exec(host, user, port, f"{S}mkdir -p /etc/pihole-sentinel", password)

            # Create remote temp directory
            print("├─ Preparing deployment staging area...")
            self.remote_exec(host, user, port, "mkdir -p /tmp/pihole-sentinel-deploy", password)
            
            # Copy necessary files
            print("Copying files...")
            files_to_copy = [
                ("dashboard/monitor.py", "/tmp/pihole-sentinel-deploy/monitor.py"),
                ("dashboard/index.html", "/tmp/pihole-sentinel-deploy/index.html"),
                ("dashboard/settings.html", "/tmp/pihole-sentinel-deploy/settings.html"),
                ("generated_configs/monitor.env", "/tmp/pihole-sentinel-deploy/monitor.env"),
                ("systemd/pihole-monitor.service", "/tmp/pihole-sentinel-deploy/pihole-monitor.service"),
                ("requirements.txt", "/tmp/pihole-sentinel-deploy/requirements.txt"),
                ("VERSION", "/tmp/pihole-sentinel-deploy/VERSION"),
            ]

            total_files = len(files_to_copy)
            for idx, (local, remote) in enumerate(files_to_copy, 1):
                progress = int((idx / total_files) * 20)
                bar = "█" * progress + "░" * (20 - progress)
                percent = int((idx / total_files) * 100)
                filename = os.path.basename(local)
                print(f"├─ [{bar}] {percent:3d}% {filename:30s}", end='\r')
                self.remote_copy(local, host, user, port, remote, password)
            print(f"├─ [████████████████████] 100% All files copied{' ' * 30}")
            
            # Execute installation commands
            print("Installing monitor service...")
            print("├─ Creating service user...")
            self.remote_exec(host, user, port, f"{S}useradd -r -s /bin/false pihole-monitor 2>/dev/null || true", password)

            print("├─ Setting up directories...")
            self.remote_exec(host, user, port, f"{S}mkdir -p /opt/pihole-monitor", password)

            print("├─ [░░░░░░░░░░░░░░░░░░░░] 0%   Creating virtual environment...", end='\r')
            self.remote_exec(host, user, port, f"{S}python3 -m venv /opt/pihole-monitor/venv", password)
            print("├─ [████░░░░░░░░░░░░░░░░] 20%  Virtual environment created      ")

            print("├─ [████░░░░░░░░░░░░░░░░] 20%  Installing Python packages (this may take 1-2 minutes)...", end='\r')
            if VERBOSE:
                self.remote_exec(host, user, port,
                    f"cd /tmp/pihole-sentinel-deploy && {S}/opt/pihole-monitor/venv/bin/pip install -r requirements.txt",
                    password)
                print("├─ [████████████████████] 100% Python packages installed                              ")
            else:
                self.remote_exec(host, user, port,
                    f"cd /tmp/pihole-sentinel-deploy && {S}/opt/pihole-monitor/venv/bin/pip install -q -r requirements.txt >/dev/null 2>&1",
                    password)
                print("├─ [████████████████████] 100% Python packages installed                              ")

            print("├─ Copying application files...")
            commands = [
                f"{S}cp /tmp/pihole-sentinel-deploy/monitor.py /opt/pihole-monitor/",
                f"{S}cp /tmp/pihole-sentinel-deploy/index.html /opt/pihole-monitor/",
                f"{S}cp /tmp/pihole-sentinel-deploy/settings.html /opt/pihole-monitor/",
                f"{S}cp /tmp/pihole-sentinel-deploy/monitor.env /opt/pihole-monitor/.env",
                f"{S}cp /tmp/pihole-sentinel-deploy/pihole-monitor.service /etc/systemd/system/",
                f"{S}cp /tmp/pihole-sentinel-deploy/VERSION /opt/VERSION",
            ]
            for cmd in commands:
                self.remote_exec(host, user, port, cmd, password)

            # Inject API key into HTML files
            print("├─ Configuring API authentication...")
            api_key = self.config.get('api_key')
            if api_key:
                # Escape API key for safe use in sed (prevents injection if key contains special chars)
                escaped_key = self.escape_for_sed(api_key)
                # Use # as delimiter to avoid issues with / in the key
                self.remote_exec(host, user, port,
                    f"{S}sed -i 's#YOUR_API_KEY_HERE#{escaped_key}#g' /opt/pihole-monitor/index.html",
                    password)
                self.remote_exec(host, user, port,
                    f"{S}sed -i 's#YOUR_API_KEY_HERE#{escaped_key}#g' /opt/pihole-monitor/settings.html",
                    password)
                print("│  → API key configured successfully")

            print("├─ Setting permissions...")
            perms_commands = [
                f"{S}chown -R pihole-monitor:pihole-monitor /opt/pihole-monitor",
                f"{S}chmod 755 /opt/pihole-monitor",
                f"{S}chmod 644 /opt/pihole-monitor/*.py /opt/pihole-monitor/*.html",
                f"{S}chmod 600 /opt/pihole-monitor/.env",
                f"{S}chmod 755 -R /opt/pihole-monitor/venv",
                f"{S}chown root:root /etc/systemd/system/pihole-monitor.service",
                f"{S}chmod 644 /etc/systemd/system/pihole-monitor.service",
                f"{S}chown pihole-monitor:pihole-monitor /etc/pihole-sentinel",
                f"{S}chmod 755 /etc/pihole-sentinel",
                f"{S}chmod 644 /opt/VERSION",
            ]
            for cmd in perms_commands:
                self.remote_exec(host, user, port, cmd, password)

            print("└─ Starting service...")
            self.remote_exec(host, user, port, f"{S}systemctl daemon-reload", password)
            self.remote_exec(host, user, port, f"{S}systemctl enable pihole-monitor >/dev/null 2>&1", password)
            self.remote_exec(host, user, port, f"{S}systemctl restart pihole-monitor", password)
            self.remote_exec(host, user, port, "rm -rf /tmp/pihole-sentinel-deploy", password)
            
            print(f"✓ Monitor deployed successfully to {host}!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Error deploying monitor to {host}: {e}")
            return False

    def deploy_keepalived(self, node_type="primary"):
        """Deploy keepalived configuration to a node."""
        try:
            print(f"\nDeploying {node_type} keepalived configuration...")
            
            # Install keepalived if not present
            if subprocess.run(["which", "keepalived"], capture_output=True).returncode != 0:
                print("Installing required packages...")
                subprocess.run(["sudo", "apt-get", "update"], check=True)
                subprocess.run(["sudo", "apt-get", "install", "-y", "keepalived", "arping"], check=True)
            
            # Create directories with correct permissions
            print("Creating directories...")
            subprocess.run(["sudo", "mkdir", "-p", "/etc/keepalived"], check=True)
            subprocess.run(["sudo", "chmod", "755", "/etc/keepalived"], check=True)
            subprocess.run(["sudo", "mkdir", "-p", "/usr/local/bin"], check=True)
            subprocess.run(["sudo", "chmod", "755", "/usr/local/bin"], check=True)
            
            # Copy and set permissions for configuration files
            print("Setting up configuration files...")
            config_suffix = "primary" if node_type == "primary" else "secondary"
            
            # keepalived.conf: 644 root:root
            subprocess.run(["sudo", "cp", f"generated_configs/{config_suffix}_keepalived.conf",
                          "/etc/keepalived/keepalived.conf"], check=True)
            subprocess.run(["sudo", "chown", "root:root", "/etc/keepalived/keepalived.conf"], check=True)
            subprocess.run(["sudo", "chmod", "644", "/etc/keepalived/keepalived.conf"], check=True)
            
            # .env file: 600 root:root (contains secrets)
            subprocess.run(["sudo", "cp", f"generated_configs/{config_suffix}.env",
                          "/etc/keepalived/.env"], check=True)
            subprocess.run(["sudo", "chown", "root:root", "/etc/keepalived/.env"], check=True)
            subprocess.run(["sudo", "chmod", "600", "/etc/keepalived/.env"], check=True)
            
            # Copy and set permissions for scripts
            print("Setting up monitoring scripts...")
            for script in ["check_pihole_service.sh", "check_dhcp_service.sh", "dhcp_control.sh", "keepalived_notify.sh"]:
                # Scripts: 755 root:root (executable by root only)
                # First copy to temp location and fix line endings
                subprocess.run(["sudo", "cp", f"keepalived/scripts/{script}",
                              f"/tmp/{script}"], check=True)
                # Convert CRLF to LF (fix Windows line endings)
                subprocess.run(["sudo", "sed", "-i", "s/\\r$//", f"/tmp/{script}"], check=True)
                # Move to final location
                subprocess.run(["sudo", "mv", f"/tmp/{script}", 
                              f"/usr/local/bin/{script}"], check=True)
                subprocess.run(["sudo", "chown", "root:root", f"/usr/local/bin/{script}"], check=True)
                subprocess.run(["sudo", "chmod", "755", f"/usr/local/bin/{script}"], check=True)
            
            # Enable and start keepalived
            print("Starting keepalived service...")
            subprocess.run(["sudo", "systemctl", "enable", "keepalived"], check=True)
            subprocess.run(["sudo", "systemctl", "restart", "keepalived"], check=True)
            
            print(f"Keepalived {node_type} configuration deployed successfully!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error deploying keepalived: {e}")
            return False

    def deploy_keepalived_remote(self, node_type="primary"):
        """Deploy keepalived configuration to remote Pi-hole via SSH."""
        host = self.config[f'{node_type}_ip']
        user = self.config[f'{node_type}_ssh_user']
        port = self.config[f'{node_type}_ssh_port']
        password = self.config.get(f'{node_type}_ssh_pass')
        S = self._s(user)

        try:
            print(f"\nDeploying {node_type} keepalived to {host} via SSH...")

            # Install system dependencies first
            if not self.install_remote_dependencies(host, user, port, password):
                return False
            
            # Configure timezone and NTP
            self.configure_timezone_and_ntp(host, user, port, password)

            # Pre-deployment checks and directory setup
            print("Running pre-deployment checks...")
            # Create remote temp directory
            print("├─ Preparing deployment staging area...")
            self.remote_exec(host, user, port, "mkdir -p /tmp/pihole-sentinel-deploy", password)
            
            # Copy necessary files
            print("Copying files...")
            config_suffix = "primary" if node_type == "primary" else "secondary"
            files_to_copy = [
                (f"generated_configs/{config_suffix}_keepalived.conf", "/tmp/pihole-sentinel-deploy/keepalived.conf"),
                (f"generated_configs/{config_suffix}.env", "/tmp/pihole-sentinel-deploy/.env"),
                ("keepalived/scripts/check_pihole_service.sh", "/tmp/pihole-sentinel-deploy/check_pihole_service.sh"),
                ("keepalived/scripts/check_dhcp_service.sh", "/tmp/pihole-sentinel-deploy/check_dhcp_service.sh"),
                ("keepalived/scripts/dhcp_control.sh", "/tmp/pihole-sentinel-deploy/dhcp_control.sh"),
                ("keepalived/scripts/keepalived_notify.sh", "/tmp/pihole-sentinel-deploy/keepalived_notify.sh"),
                ("bin/pisen", "/tmp/pihole-sentinel-deploy/pisen"),
            ]

            total_files = len(files_to_copy)
            for idx, (local, remote) in enumerate(files_to_copy, 1):
                progress = int((idx / total_files) * 20)
                bar = "█" * progress + "░" * (20 - progress)
                percent = int((idx / total_files) * 100)
                filename = os.path.basename(local)
                print(f"├─ [{bar}] {percent:3d}% {filename:30s}", end='\r')
                self.remote_copy(local, host, user, port, remote, password)
            print(f"├─ [████████████████████] 100% All files copied{' ' * 30}")
            
            # Execute installation commands
            print("Installing keepalived...")
            commands = [
                f"command -v keepalived >/dev/null 2>&1 || ({S}env DEBIAN_FRONTEND=noninteractive apt-get update -qq && {S}env DEBIAN_FRONTEND=noninteractive apt-get install -y keepalived arping)",
                f"{S}mkdir -p /etc/keepalived",
                f"{S}chmod 755 /etc/keepalived",
                f"{S}mkdir -p /usr/local/bin",
                f"{S}chmod 755 /usr/local/bin",
                f"{S}cp /tmp/pihole-sentinel-deploy/keepalived.conf /etc/keepalived/keepalived.conf",
                f"{S}chown root:root /etc/keepalived/keepalived.conf",
                f"{S}chmod 644 /etc/keepalived/keepalived.conf",
                # Auto-detect actual network interface on this host and patch keepalived.conf.
                # The config was generated on the installer machine (which may use eno1/wlan0/etc.)
                # but this Pi-hole may use a completely different interface name (eth0, enp3s0, …).
                # We use the interface of the default IPv4 route — that is always the correct one
                # for VRRP to run on.
                "REMOTE_IFACE=$(ip route get 8.8.8.8 2>/dev/null "
                "| awk '{for(i=1;i<=NF;i++) if($i==\"dev\") print $(i+1)}' "
                "| head -1 | tr -d '[:space:]') && "
                "[ -n \"$REMOTE_IFACE\" ] && "
                f"{S}sed -i \"s/^    interface .*/    interface $REMOTE_IFACE/\" /etc/keepalived/keepalived.conf && "
                "echo \"Auto-configured VRRP interface: $REMOTE_IFACE\" || "
                "echo 'Warning: could not auto-detect interface, keeping installer value'",
                f"{S}cp /tmp/pihole-sentinel-deploy/.env /etc/keepalived/.env",
                f"{S}chown root:root /etc/keepalived/.env",
                f"{S}chmod 600 /etc/keepalived/.env",
                # Copy and fix line endings for scripts
                "for script in check_pihole_service.sh check_dhcp_service.sh dhcp_control.sh keepalived_notify.sh; do " +
                "cp /tmp/pihole-sentinel-deploy/$script /tmp/$script && " +
                "sed -i 's/\\r$//' /tmp/$script && " +
                f"{S}mv /tmp/$script /usr/local/bin/$script && " +
                f"{S}chown root:root /usr/local/bin/$script && " +
                f"{S}chmod 755 /usr/local/bin/$script; done",
                # Install pisen CLI tool
                f"{S}cp /tmp/pihole-sentinel-deploy/pisen /usr/local/bin/pisen && "
                f"{S}sed -i 's/\\r$//' /usr/local/bin/pisen && "
                f"{S}chown root:root /usr/local/bin/pisen && "
                f"{S}chmod 755 /usr/local/bin/pisen",
                f"{S}systemctl enable keepalived",
            ]

            for cmd in commands:
                self.remote_exec(host, user, port, cmd, password)

            # Validate config before starting — surfacing errors early
            print("├─ Validating keepalived configuration...")
            self.remote_exec(host, user, port,
                f"{S}keepalived --config-test 2>&1 || "
                f"(echo ''; echo '=== keepalived config test output ===' && "
                f"{S}keepalived --config-test 2>&1; "
                "echo '=== keepalived.conf content ===' && "
                "cat /etc/keepalived/keepalived.conf; exit 1)",
                password)

            # Start service and show diagnostics on failure
            print("├─ Starting keepalived service...")
            self.remote_exec(host, user, port,
                f"{S}systemctl stop keepalived 2>/dev/null || true && "
                f"{S}systemctl restart keepalived 2>&1 || ("
                "echo '' && "
                "echo '=== keepalived failed to start — diagnostic output ===' && "
                f"{S}systemctl status keepalived --no-pager -l 2>&1 || true && "
                "echo '' && "
                "echo '=== last 40 journal lines ===' && "
                f"{S}journalctl -xeu keepalived --no-pager -n 40 2>&1 || true && "
                "echo '' && "
                "echo '=== keepalived.conf ===' && "
                "cat /etc/keepalived/keepalived.conf && "
                "exit 1)",
                password)

            # Cleanup staging area
            self.remote_exec(host, user, port, "rm -rf /tmp/pihole-sentinel-deploy", password)
            
            print(f"✓ Keepalived {node_type} deployed successfully to {host}!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"\n{Colors.RED}✗ Error deploying keepalived to {host}: {e}{Colors.END}")
            print(f"\n{Colors.YELLOW}Config files are deployed to {host} but the service failed to start.{Colors.END}")
            print(f"{Colors.YELLOW}Diagnose manually:{Colors.END}")
            print(f"  ssh root@{host} 'systemctl status keepalived --no-pager -l'")
            print(f"  ssh root@{host} 'journalctl -xeu keepalived --no-pager -n 50'")
            print(f"  ssh root@{host} 'keepalived --config-test'")
            return False

    def deploy_sync_remote(self, sync_interval=10, sync_options=None):
        """Deploy the sync script and systemd timer to the primary Pi-hole.

        Args:
            sync_interval: Sync interval in minutes (default: 10)
            sync_options: Dict of sync toggles (SYNC_GRAVITY, SYNC_CUSTOM_DNS, etc.)
        """
        host = self.config['primary_ip']
        user = self.config.get('primary_ssh_user', 'root')
        port = self.config.get('primary_ssh_port', '22')
        password = self.config.get('primary_ssh_pass')

        if sync_options is None:
            sync_options = {}

        try:
            print(f"\nDeploying sync service to primary Pi-hole ({host})...")

            # Generate sync config
            sync_conf_lines = [
                "# Pi-hole Sentinel Sync Configuration",
                "# Auto-generated by setup.py",
                "",
                f"PRIMARY_IP={self.config['primary_ip']}",
                f"SECONDARY_IP={self.config['secondary_ip']}",
                f"SYNC_INTERVAL_MINUTES={sync_interval}",
                f"SYNC_GRAVITY={sync_options.get('gravity', 'true')}",
                f"SYNC_CUSTOM_DNS={sync_options.get('custom_dns', 'true')}",
                f"SYNC_CNAME={sync_options.get('cname', 'true')}",
                f"SYNC_DHCP_LEASES={sync_options.get('dhcp_leases', 'true')}",
                f"SYNC_CONFIG_DHCP={sync_options.get('config_dhcp', 'true')}",
                f"SYNC_CONFIG_DHCP_EXCLUDE_ACTIVE={sync_options.get('dhcp_exclude_active', 'true')}",
                f"SYNC_CONFIG_DNS={sync_options.get('config_dns', 'true')}",
                f"SYNC_RESTART_FTL={sync_options.get('restart_ftl', 'true')}",
            ]
            sync_conf = "\n".join(sync_conf_lines) + "\n"

            # Generate timer with custom interval
            timer_content = f"""[Unit]
Description=Pi-hole Configuration Sync Timer
Requires=pihole-sync.service

[Timer]
OnCalendar=*:0/{sync_interval}
OnBootSec=2min
Persistent=true

[Install]
WantedBy=timers.target
"""

            # Write temp files
            os.makedirs('generated_configs', mode=0o700, exist_ok=True)
            with open('generated_configs/sync.conf', 'w') as f:
                f.write(sync_conf)
            with open('generated_configs/pihole-sync.timer', 'w') as f:
                f.write(timer_content)

            # Prepare staging area
            print("├─ Preparing deployment staging area...")
            self.remote_exec(host, user, port, "mkdir -p /tmp/pihole-sentinel-deploy", password)

            # Copy files
            print("├─ Copying sync files...")
            files_to_copy = [
                ("sync-pihole-config.sh", "/tmp/pihole-sentinel-deploy/sync-pihole-config.sh"),
                ("systemd/pihole-sync.service", "/tmp/pihole-sentinel-deploy/pihole-sync.service"),
                ("generated_configs/pihole-sync.timer", "/tmp/pihole-sentinel-deploy/pihole-sync.timer"),
                ("generated_configs/sync.conf", "/tmp/pihole-sentinel-deploy/sync.conf"),
            ]
            for local, remote in files_to_copy:
                self.remote_copy(local, host, user, port, remote, password)

            # Install
            print("├─ Installing sync service...")
            commands = [
                # Install sync script
                "cp /tmp/pihole-sentinel-deploy/sync-pihole-config.sh /usr/local/bin/sync-pihole-config.sh",
                "chown root:root /usr/local/bin/sync-pihole-config.sh",
                "chmod 755 /usr/local/bin/sync-pihole-config.sh",
                # Install sync config
                "mkdir -p /etc/pihole-sentinel",
                "cp /tmp/pihole-sentinel-deploy/sync.conf /etc/pihole-sentinel/sync.conf",
                "chmod 600 /etc/pihole-sentinel/sync.conf",
                # Install systemd units
                "cp /tmp/pihole-sentinel-deploy/pihole-sync.service /etc/systemd/system/pihole-sync.service",
                "cp /tmp/pihole-sentinel-deploy/pihole-sync.timer /etc/systemd/system/pihole-sync.timer",
                "systemctl daemon-reload",
                "systemctl enable --now pihole-sync.timer",
                # Cleanup
                "rm -rf /tmp/pihole-sentinel-deploy",
            ]
            for cmd in commands:
                self.remote_exec(host, user, port, cmd, password)

            # Verify
            print("├─ Verifying sync timer...")
            self.remote_exec(host, user, port, "systemctl is-active pihole-sync.timer", password)

            print(f"✓ Sync service deployed to {host}!")
            print(f"  Interval: every {sync_interval} minutes")
            enabled = [k for k, v in sync_options.items() if v == 'true' or v is True]
            if enabled:
                print(f"  Syncing: {', '.join(enabled)}")
            else:
                print("  Syncing: all (default)")
            return True

        except subprocess.CalledProcessError as e:
            print(f"\n{Colors.RED}✗ Error deploying sync to {host}: {e}{Colors.END}")
            return False

    def show_next_steps(self):
        """Show next steps for manual deployment."""
        print(f"""
{Colors.YELLOW}{Colors.BOLD}═══════════════════════════════════════════════════════════════════════════════{Colors.END}
{Colors.CYAN}{Colors.BOLD}                            Next Steps{Colors.END}
{Colors.YELLOW}{Colors.BOLD}═══════════════════════════════════════════════════════════════════════════════{Colors.END}

{Colors.BOLD}1. Copy configuration files to their respective locations:{Colors.END}

   {Colors.GREEN}On Primary Pi-hole:{Colors.END}
   - Copy primary_keepalived.conf to /etc/keepalived/keepalived.conf
   - Copy primary.env to /etc/keepalived/.env

   {Colors.GREEN}On Secondary Pi-hole:{Colors.END}
   - Copy secondary_keepalived.conf to /etc/keepalived/keepalived.conf
   - Copy secondary.env to /etc/keepalived/.env

   {Colors.GREEN}On Monitor Server:{Colors.END}
   - Copy monitor.env to /opt/pihole-monitor/.env

{Colors.BOLD}2. Restart services:{Colors.END}
   {Colors.CYAN}On both Pi-holes:{Colors.END} systemctl restart keepalived
   {Colors.CYAN}On monitor:{Colors.END} systemctl restart pihole-monitor

{Colors.BOLD}3. Verify the setup:{Colors.END}
   - Check keepalived status: {Colors.CYAN}systemctl status keepalived{Colors.END}
   - Monitor logs: {Colors.CYAN}tail -f /var/log/keepalived-notify.log{Colors.END}
   - Access monitor dashboard: {Colors.CYAN}http://<monitor-ip>:8080{Colors.END}

{Colors.BOLD}4. Test failover:{Colors.END}
   - Stop pihole-FTL on primary: {Colors.CYAN}systemctl stop pihole-FTL{Colors.END}
   - Watch the dashboard for failover
   - Check that DNS still works

{Colors.RED}{Colors.BOLD}⚠ SECURITY WARNING:{Colors.END}
{Colors.RED}The generated_configs directory contains SENSITIVE information:{Colors.END}
{Colors.RED}  • Pi-hole web passwords (plaintext){Colors.END}
{Colors.RED}  • Keepalived authentication passwords{Colors.END}
{Colors.RED}{Colors.BOLD}DELETE this directory immediately after deployment!{Colors.END}
{Colors.CYAN}Command: rm -rf generated_configs/{Colors.END}
""")
    
    def cleanup_sensitive_files(self):
        """Securely remove generated config files containing sensitive data."""
        print(f"\n{Colors.YELLOW}{Colors.BOLD}Security Cleanup{Colors.END}")
        
        if os.path.exists('generated_configs'):
            print(f"{Colors.CYAN}Removing generated configuration files with sensitive data...{Colors.END}")
            try:
                # Overwrite files with random data before deletion (basic secure delete)
                for root, dirs, files in os.walk('generated_configs'):
                    for file in files:
                        filepath = os.path.join(root, file)
                        size = os.path.getsize(filepath)
                        with open(filepath, 'wb') as f:
                            f.write(os.urandom(size))
                
                # Now remove the directory
                import shutil
                shutil.rmtree('generated_configs')
                print(f"{Colors.GREEN}✓ Sensitive configuration files securely deleted{Colors.END}")
            except Exception as e:
                print(f"{Colors.RED}✗ Failed to cleanup: {e}{Colors.END}")
                print(f"{Colors.YELLOW}Please manually delete: rm -rf generated_configs/{Colors.END}")
        else:
            print(f"{Colors.GREEN}✓ No sensitive files to cleanup{Colors.END}")
    
    def backup_existing_configs(self, host, user, port, password=None, config_type="monitor"):
        """Backup existing configuration files on remote server.

        Returns the backup timestamp string so callers can pass it to
        rollback_deployment() if they need to undo this backup later.
        Returns None when nothing was backed up.
        """
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        files_to_backup = []
        
        if config_type == "monitor":
            files_to_backup = [
                ("/opt/pihole-monitor/.env", f"/opt/pihole-monitor/.env.backup_{timestamp}"),
                ("/opt/pihole-monitor/monitor.py", f"/opt/pihole-monitor/monitor.py.backup_{timestamp}"),
                ("/opt/pihole-monitor/index.html", f"/opt/pihole-monitor/index.html.backup_{timestamp}"),
                ("/opt/pihole-monitor/settings.html", f"/opt/pihole-monitor/settings.html.backup_{timestamp}"),
            ]
        elif config_type in ["primary", "secondary"]:
            files_to_backup = [
                ("/etc/keepalived/keepalived.conf", f"/etc/keepalived/keepalived.conf.backup_{timestamp}"),
                ("/etc/keepalived/.env", f"/etc/keepalived/.env.backup_{timestamp}"),
            ]
        
        backed_up = []
        for source, backup in files_to_backup:
            try:
                # Check if file exists and backup
                check_cmd = f"[ -f {source} ] && cp {source} {backup} && echo 'backed_up' || echo 'not_found'"
                
                if self.config.get('ssh_key_path') and not password:
                    result = subprocess.run(
                        ["ssh", "-i", self.config['ssh_key_path'], "-p", port, "-o", "StrictHostKeyChecking=no",
                         f"{user}@{host}", check_cmd],
                        capture_output=True, text=True, timeout=10
                    )
                elif password:
                    env = os.environ.copy()
                    env['SSHPASS'] = password
                    result = subprocess.run(
                        ["sshpass", "-e", "ssh", "-p", port, "-o", "StrictHostKeyChecking=no",
                         f"{user}@{host}", check_cmd],
                        capture_output=True, text=True, timeout=10, env=env
                    )
                else:
                    result = subprocess.run(
                        ["ssh", "-p", port, "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
                         f"{user}@{host}", check_cmd],
                        capture_output=True, text=True, timeout=10
                    )
                
                if 'backed_up' in result.stdout:
                    backed_up.append((source, backup))
            except:
                pass
        
        if backed_up:
            print(f"\n{Colors.GREEN}{Colors.BOLD}📦 Existing Configuration Backup{Colors.END}")
            print(f"{Colors.CYAN}The following existing files have been backed up on {host}:{Colors.END}")
            for source, backup in backed_up:
                print(f"  {Colors.GREEN}✓{Colors.END} {source} → {backup}")
            print(f"\n{Colors.YELLOW}💡 You can restore these backups if needed.{Colors.END}")
            return timestamp

        return None

    def rollback_deployment(self, deployed_hosts):
        """Restore all servers from their backups.

        deployed_hosts is a list of dicts created during mode-2 deployment:
          [
            {"type": "monitor",   "host": ip, "user": user, "port": port,
             "backup_ts": "20260328_101648"},
            {"type": "primary",   "host": ip, "user": user, "port": port,
             "backup_ts": "20260328_101659"},
            {"type": "secondary", "host": ip, "user": user, "port": port,
             "backup_ts": "20260328_101707"},
          ]
        Servers are rolled back in reverse deployment order.
        """
        if not deployed_hosts:
            return

        print(f"\n{Colors.YELLOW}{Colors.BOLD}═══ Rolling Back Deployment ═══{Colors.END}")
        print(f"{Colors.YELLOW}Restoring previous configuration on all touched servers…{Colors.END}\n")

        restore_map = {
            "monitor": [
                ("/opt/pihole-monitor/.env",           "/opt/pihole-monitor/.env"),
                ("/opt/pihole-monitor/monitor.py",     "/opt/pihole-monitor/monitor.py"),
                ("/opt/pihole-monitor/index.html",     "/opt/pihole-monitor/index.html"),
                ("/opt/pihole-monitor/settings.html",  "/opt/pihole-monitor/settings.html"),
            ],
            "keepalived": [
                ("/etc/keepalived/keepalived.conf", "/etc/keepalived/keepalived.conf"),
                ("/etc/keepalived/.env",            "/etc/keepalived/.env"),
            ],
        }
        restart_cmd = {
            "monitor":   "systemctl restart pihole-monitor 2>/dev/null || true",
            "primary":   "systemctl restart keepalived    2>/dev/null || true",
            "secondary": "systemctl restart keepalived    2>/dev/null || true",
        }

        for entry in reversed(deployed_hosts):
            host      = entry["host"]
            user      = entry["user"]
            port      = entry["port"]
            node_type = entry["type"]
            ts        = entry.get("backup_ts")
            label     = f"{node_type} ({host})"

            print(f"  Rolling back {label}…")

            if not ts:
                print(f"    {Colors.YELLOW}⚠ No backup timestamp — skipping file restore{Colors.END}")
            else:
                file_list = restore_map.get(
                    "monitor" if node_type == "monitor" else "keepalived", []
                )
                for _dest, target in file_list:
                    backup_path = f"{target}.backup_{ts}"
                    cmd = (
                        f"[ -f {backup_path} ] "
                        f"&& cp {backup_path} {target} "
                        f"&& echo 'restored' "
                        f"|| echo 'no backup'"
                    )
                    try:
                        self.remote_exec(host, user, port, cmd)
                    except Exception:
                        pass

            # Restart service so the restored config takes effect
            try:
                self.remote_exec(host, user, port, restart_cmd[node_type])
                print(f"    {Colors.GREEN}✓ Restored and restarted {node_type}{Colors.END}")
            except Exception as e:
                print(f"    {Colors.YELLOW}⚠ Restart failed: {e}{Colors.END}")

        print(f"\n{Colors.GREEN}Rollback complete.{Colors.END}")

    def collect_minimal_config(self):
        """Collect only the SSH+server details needed for uninstall/rollback.

        Does not ask for Pi-hole passwords, DHCP settings, or VIP.
        """
        print(f"\n{Colors.CYAN}{Colors.BOLD}=== Which servers should be uninstalled? ==={Colors.END}")
        print(f"{Colors.CYAN}Enter the IP addresses of your Pi-hole servers.{Colors.END}\n")

        self.config['primary_ip']   = self._ask_required(f"{Colors.BOLD}Primary Pi-hole IP:{Colors.END} ", self.validate_ip, "Invalid IP address")
        self.config['secondary_ip'] = self._ask_required(f"{Colors.BOLD}Secondary Pi-hole IP:{Colors.END} ", self.validate_ip, "Invalid IP address")

        has_monitor = input(f"\n{Colors.BOLD}Is the monitor on a separate server? (Y/n):{Colors.END} ").strip().lower() != "n"
        self.config['separate_monitor'] = has_monitor
        if has_monitor:
            self.config['monitor_ip']       = self._ask_required(f"{Colors.BOLD}Monitor server IP:{Colors.END} ", self.validate_ip, "Invalid IP address")
            self.config['monitor_ssh_user'] = input(f"Monitor SSH user [{Colors.CYAN}root{Colors.END}]: ").strip() or "root"
            self.config['monitor_ssh_port'] = input(f"Monitor SSH port [{Colors.CYAN}22{Colors.END}]: ").strip() or "22"
        else:
            self.config['monitor_ip']       = None
            self.config['monitor_ssh_user'] = "root"
            self.config['monitor_ssh_port'] = "22"

        ssh_user = input(f"\nSSH user for Pi-holes [{Colors.CYAN}root{Colors.END}]: ").strip() or "root"
        ssh_port = input(f"SSH port for Pi-holes [{Colors.CYAN}22{Colors.END}]: ").strip() or "22"
        self.config['primary_ssh_user']   = ssh_user
        self.config['primary_ssh_port']   = ssh_port
        self.config['secondary_ssh_user'] = ssh_user
        self.config['secondary_ssh_port'] = ssh_port

        # Set up SSH key (reuse existing if present)
        key_path = os.path.expanduser("~/.ssh/id_pihole_sentinel")
        if os.path.exists(key_path):
            self.config['ssh_key_path'] = key_path
        else:
            self.config['ssh_key_path'] = None

    def uninstall(self):
        """Remove Pi-hole Sentinel from all configured servers.

        Stops and disables services, removes all installed files, and
        optionally removes system users created by the monitor installer.
        Pi-hole itself is never touched.
        """
        print(f"\n{Colors.RED}{Colors.BOLD}═══ Uninstall Pi-hole Sentinel ═══{Colors.END}")
        print(f"{Colors.YELLOW}This will remove Pi-hole Sentinel from all servers.{Colors.END}")
        print(f"{Colors.YELLOW}Pi-hole itself will NOT be touched.{Colors.END}\n")

        confirm = input(
            f"{Colors.RED}{Colors.BOLD}Type 'yes' to confirm uninstall: {Colors.END}"
        ).strip().lower()
        if confirm != "yes":
            print("Uninstall cancelled.")
            return

        errors = []

        def _exec_quiet(host, user, port, cmd):
            """Return True on success, False on failure (never raises)."""
            try:
                self.remote_exec(host, user, port, cmd)
                return True
            except Exception as e:
                errors.append(f"{host}: {e}")
                return False

        # --- Monitor ---
        if self.config.get('separate_monitor') and self.config.get('monitor_ip'):
            host = self.config['monitor_ip']
            user = self.config['monitor_ssh_user']
            port = self.config['monitor_ssh_port']
            print(f"  Uninstalling monitor from {host}…")
            cmds = [
                "systemctl stop  pihole-monitor 2>/dev/null || true",
                "systemctl disable pihole-monitor 2>/dev/null || true",
                "rm -f /etc/systemd/system/pihole-monitor.service",
                "systemctl daemon-reload",
                "rm -rf /opt/pihole-monitor",
                # Remove service user (only if it was created by sentinel)
                "id pihole-monitor >/dev/null 2>&1 && userdel -r pihole-monitor 2>/dev/null || true",
            ]
            ok = all(_exec_quiet(host, user, port, c) for c in cmds)
            print(f"    {Colors.GREEN}✓ Done{Colors.END}" if ok else f"    {Colors.YELLOW}⚠ Some steps failed{Colors.END}")

        # --- Pi-hole nodes (primary + secondary) ---
        for label, ip_key, user_key, port_key in [
            ("Primary Pi-hole",   "primary_ip",   "primary_ssh_user",   "primary_ssh_port"),
            ("Secondary Pi-hole", "secondary_ip", "secondary_ssh_user", "secondary_ssh_port"),
        ]:
            host = self.config.get(ip_key)
            user = self.config.get(user_key, "root")
            port = self.config.get(port_key, "22")
            if not host:
                continue
            print(f"  Uninstalling keepalived sentinel from {label} ({host})…")
            cmds = [
                # Stop keepalived (Pi-hole keeps running — only VRRP/HA bits are removed)
                "systemctl stop  keepalived 2>/dev/null || true",
                "systemctl disable keepalived 2>/dev/null || true",
                # Remove Sentinel-managed files only; keepalived package stays
                "rm -f /etc/keepalived/keepalived.conf",
                "rm -f /etc/keepalived/.env",
                "rm -f /usr/local/bin/check_pihole_service.sh",
                "rm -f /usr/local/bin/check_dhcp_service.sh",
                "rm -f /usr/local/bin/dhcp_control.sh",
                "rm -f /usr/local/bin/keepalived_notify.sh",
                "rm -f /var/log/keepalived-notify.log",
            ]
            ok = all(_exec_quiet(host, user, port, c) for c in cmds)
            print(f"    {Colors.GREEN}✓ Done{Colors.END}" if ok else f"    {Colors.YELLOW}⚠ Some steps failed{Colors.END}")

        if errors:
            print(f"\n{Colors.YELLOW}The following errors occurred during uninstall:{Colors.END}")
            for e in errors:
                print(f"  {Colors.YELLOW}⚠{Colors.END}  {e}")
            print(f"{Colors.YELLOW}You may need to clean up manually on those hosts.{Colors.END}")
        else:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Pi-hole Sentinel has been removed from all servers.{Colors.END}")
            print(f"{Colors.CYAN}Pi-hole continues to run; only the HA layer has been removed.{Colors.END}")

    def show_deployment_success(self):
        """Show successful deployment message with instructions."""
        monitor_ip = self.config.get('monitor_ip', 'monitor-ip')
        primary_ip = self.config['primary_ip']
        secondary_ip = self.config['secondary_ip']
        vip = self.config['vip']
        
        print(f"""
{Colors.GREEN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                     ✓ DEPLOYMENT COMPLETED SUCCESSFULLY!                      ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
{Colors.END}

{Colors.CYAN}{Colors.BOLD}📊 Access Your Monitor Dashboard:{Colors.END}
   {Colors.BOLD}→ http://{monitor_ip}:8080{Colors.END}

{Colors.CYAN}{Colors.BOLD}🔍 Quick Status Check Commands:{Colors.END}

   {Colors.YELLOW}On Monitor Server ({monitor_ip}):{Colors.END}
   {Colors.CYAN}systemctl status pihole-monitor{Colors.END}
   {Colors.CYAN}journalctl -u pihole-monitor -f{Colors.END}
   {Colors.CYAN}sqlite3 /opt/pihole-monitor/monitor.db "SELECT * FROM status_history ORDER BY timestamp DESC LIMIT 5;"{Colors.END}

   {Colors.YELLOW}On Primary Pi-hole ({primary_ip}):{Colors.END}
   {Colors.CYAN}systemctl status keepalived{Colors.END}
   {Colors.CYAN}systemctl status pihole-FTL{Colors.END}
   {Colors.CYAN}ip addr show | grep {vip}{Colors.END}

   {Colors.YELLOW}On Secondary Pi-hole ({secondary_ip}):{Colors.END}
   {Colors.CYAN}systemctl status keepalived{Colors.END}
   {Colors.CYAN}systemctl status pihole-FTL{Colors.END}

{Colors.CYAN}{Colors.BOLD}🧪 Test Failover:{Colors.END}
   {Colors.BOLD}1.{Colors.END} Note which server has the VIP ({vip})
   {Colors.BOLD}2.{Colors.END} On that server: {Colors.CYAN}systemctl stop pihole-FTL{Colors.END}
   {Colors.BOLD}3.{Colors.END} Watch the VIP move to the other server
   {Colors.BOLD}4.{Colors.END} Check the dashboard for status changes
   {Colors.BOLD}5.{Colors.END} Restore service: {Colors.CYAN}systemctl start pihole-FTL{Colors.END}

{Colors.CYAN}{Colors.BOLD}📁 Log Files:{Colors.END}
   {Colors.CYAN}Monitor:{Colors.END} journalctl -u pihole-monitor
   {Colors.CYAN}Keepalived:{Colors.END} journalctl -u keepalived
   {Colors.CYAN}Keepalived events:{Colors.END} /var/log/keepalived-notify.log

{Colors.GREEN}{Colors.BOLD}🎉 Your Pi-hole High Availability setup is ready!{Colors.END}

{Colors.YELLOW}Need help? Check the documentation or open an issue on GitHub.{Colors.END}
""")


class Uninstaller:
    """Uninstall Pi-hole Sentinel components."""
    
    def __init__(self, keep_configs=False, dry_run=False):
        self.keep_configs = keep_configs
        self.dry_run = dry_run
    
    def run_cmd(self, cmd, description=""):
        """Execute command with dry-run support."""
        if self.dry_run:
            print(f"  [DRY-RUN] Would run: {' '.join(cmd)}")
            return True
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            return True
        except subprocess.CalledProcessError:
            return False
        except subprocess.TimeoutExpired:
            print(f"  ⚠ Command timed out: {' '.join(cmd)}")
            return False
    
    def uninstall_monitor(self):
        """Uninstall monitor service from local machine."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}═══ Uninstalling Pi-hole Sentinel Monitor ═══{Colors.END}\n")
        
        # Stop and disable service
        print("Stopping service...")
        self.run_cmd(["systemctl", "stop", "pihole-monitor"])
        self.run_cmd(["systemctl", "disable", "pihole-monitor"])
        
        # Remove service file
        print("Removing systemd service...")
        self.run_cmd(["rm", "-f", "/etc/systemd/system/pihole-monitor.service"])
        self.run_cmd(["systemctl", "daemon-reload"])
        
        # Remove application files
        print("Removing application files...")
        if self.keep_configs:
            print(f"  {Colors.YELLOW}(Keeping configuration files){Colors.END}")
            self.run_cmd(["rm", "-rf", "/opt/pihole-monitor/venv"])
            self.run_cmd(["rm", "-f", "/opt/pihole-monitor/monitor.py"])
            self.run_cmd(["rm", "-f", "/opt/pihole-monitor/index.html"])
            self.run_cmd(["rm", "-f", "/opt/pihole-monitor/settings.html"])
        else:
            self.run_cmd(["rm", "-rf", "/opt/pihole-monitor"])
            self.run_cmd(["rm", "-rf", "/etc/pihole-sentinel"])
        
        self.run_cmd(["rm", "-f", "/opt/VERSION"])
        
        # Remove logs
        print("Removing log files...")
        self.run_cmd(["rm", "-f", "/var/log/pihole-monitor.log"])
        self.run_cmd(["sh", "-c", "rm -f /var/log/pihole-monitor.log.*"])
        
        # Remove user
        print("Removing service user...")
        self.run_cmd(["userdel", "-r", "pihole-monitor"])
        
        print(f"\n{Colors.GREEN}✓ Monitor uninstalled{Colors.END}")
    
    def uninstall_keepalived_config(self):
        """Remove keepalived configuration (not the package)."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}═══ Removing Keepalived Configuration ═══{Colors.END}\n")
        
        print("Stopping keepalived...")
        self.run_cmd(["systemctl", "stop", "keepalived"])
        
        print("Removing configuration...")
        if self.keep_configs:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            print(f"  {Colors.YELLOW}(Backing up config to keepalived.conf.backup_{timestamp}){Colors.END}")
            self.run_cmd(["mv", "/etc/keepalived/keepalived.conf", 
                         f"/etc/keepalived/keepalived.conf.backup_{timestamp}"])
        else:
            self.run_cmd(["rm", "-f", "/etc/keepalived/keepalived.conf"])
            self.run_cmd(["rm", "-f", "/etc/keepalived/.env"])
        
        print("Removing scripts...")
        scripts = [
            "/usr/local/bin/check_pihole_service.sh",
            "/usr/local/bin/check_dhcp_service.sh",
            "/usr/local/bin/dhcp_control.sh",
            "/usr/local/bin/keepalived_notify.sh",
            "/usr/local/bin/notify.sh"
        ]
        for script in scripts:
            self.run_cmd(["rm", "-f", script])
        
        self.run_cmd(["rm", "-f", "/var/log/keepalived-notify.log"])
        
        print(f"\n{Colors.GREEN}✓ Keepalived configuration removed{Colors.END}")
        print(f"  {Colors.YELLOW}Note: keepalived package NOT removed (may be used elsewhere){Colors.END}")
    
    def uninstall_remote(self, host, user, port, password=None, ssh_key=None):
        """Uninstall from remote host via SSH."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}═══ Uninstalling from {host} ═══{Colors.END}\n")
        
        keep_flag = "true" if self.keep_configs else "false"
        
        script = f'''
#!/bin/bash
KEEP_CONFIGS={keep_flag}

echo "Stopping services..."
systemctl stop pihole-monitor 2>/dev/null || true
systemctl disable pihole-monitor 2>/dev/null || true
systemctl stop keepalived 2>/dev/null || true
systemctl disable keepalived 2>/dev/null || true
# Brief pause so sshd / network stack settles after keepalived stops
sleep 2

echo "Removing systemd service..."
rm -f /etc/systemd/system/pihole-monitor.service
systemctl daemon-reload

echo "Removing application files..."
if [ "$KEEP_CONFIGS" = "false" ]; then
    rm -rf /opt/pihole-monitor
    rm -rf /etc/pihole-sentinel
    rm -f /etc/keepalived/keepalived.conf
    rm -f /etc/keepalived/.env
else
    rm -rf /opt/pihole-monitor/venv
    rm -f /opt/pihole-monitor/monitor.py
    rm -f /opt/pihole-monitor/index.html
    rm -f /opt/pihole-monitor/settings.html
    mv /etc/keepalived/keepalived.conf /etc/keepalived/keepalived.conf.backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
fi

rm -f /opt/VERSION

echo "Removing scripts..."
rm -f /usr/local/bin/check_pihole_service.sh
rm -f /usr/local/bin/check_dhcp_service.sh
rm -f /usr/local/bin/dhcp_control.sh
rm -f /usr/local/bin/keepalived_notify.sh
rm -f /usr/local/bin/notify.sh

echo "Removing logs..."
rm -f /var/log/pihole-monitor.log*
rm -f /var/log/keepalived-notify.log

echo "Removing service user..."
userdel -r pihole-monitor 2>/dev/null || true

echo "Done!"
'''
        
        if self.dry_run:
            print(f"  [DRY-RUN] Would execute uninstall script on {host}")
            return True
        
        try:
            # Build SSH command
            if ssh_key:
                ssh_cmd = ["ssh", "-i", ssh_key, "-p", port, "-o", "StrictHostKeyChecking=no"]
            elif password:
                ssh_cmd = ["sshpass", "-e", "ssh", "-p", port, "-o", "StrictHostKeyChecking=no"]
            else:
                ssh_cmd = ["ssh", "-p", port, "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
            
            env = os.environ.copy()
            if password:
                env['SSHPASS'] = password
            
            # Execute script
            result = subprocess.run(
                ssh_cmd + [f"{user}@{host}", "bash -s"],
                input=script,
                capture_output=True,
                text=True,
                timeout=120,
                env=env
            )
            
            if result.returncode == 0:
                print(f"{Colors.GREEN}✓ Uninstalled from {host}{Colors.END}")
                return True
            else:
                raise Exception(result.stderr or "Unknown error")
                
        except Exception as e:
            print(f"\n{Colors.RED}⚠️  Failed to uninstall from {host}: {e}{Colors.END}")
            self._show_troubleshooting(host, user)
            return False
    
    def _show_troubleshooting(self, host, user):
        """Show troubleshooting tips for failed remote uninstall."""
        print(f"""
{Colors.YELLOW}╔══════════════════════════════════════════════════════════════════════╗
║  TROUBLESHOOTING TIPS                                                 ║
╠══════════════════════════════════════════════════════════════════════╣
║  1. Check SSH access:     ssh {user}@{host}                          
║  2. Verify root/sudo permissions                                     
║  3. Check if host is reachable: ping {host}                          
║  4. Try manual uninstall (commands below)                            
╚══════════════════════════════════════════════════════════════════════╝{Colors.END}

{Colors.CYAN}Manual uninstall commands:{Colors.END}
  ssh {user}@{host}
  systemctl stop pihole-monitor keepalived
  rm -rf /opt/pihole-monitor /etc/pihole-sentinel
  rm -f /usr/local/bin/check_*.sh /usr/local/bin/*notify*.sh
  rm -f /etc/keepalived/keepalived.conf /etc/keepalived/.env
  userdel -r pihole-monitor
""")
    
    def run_interactive(self):
        """Run interactive uninstall wizard."""
        print(f"""
{Colors.RED}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════════════╗
║                    PI-HOLE SENTINEL UNINSTALLER                       ║
╚═══════════════════════════════════════════════════════════════════════╝
{Colors.END}
{Colors.YELLOW}This will remove Pi-hole Sentinel components from your system(s).{Colors.END}

What would you like to uninstall?

  {Colors.BOLD}1.{Colors.END} Monitor service (this machine)
  {Colors.BOLD}2.{Colors.END} Keepalived config (this machine - for Pi-hole nodes)
  {Colors.BOLD}3.{Colors.END} Both (this machine)
  {Colors.BOLD}4.{Colors.END} Remote uninstall via SSH
  {Colors.BOLD}5.{Colors.END} Cancel
""")
        choice = input(f"{Colors.BOLD}Enter choice (1-5): {Colors.END}").strip()
        
        if choice == '5' or not choice:
            print("Cancelled.")
            return
        
        if self.dry_run:
            print(f"\n{Colors.YELLOW}═══ DRY-RUN MODE - No changes will be made ═══{Colors.END}")
        
        if choice in ['1', '2', '3']:
            if choice in ['1', '3']:
                self.uninstall_monitor()
            if choice in ['2', '3']:
                self.uninstall_keepalived_config()
        elif choice == '4':
            host = input("Remote host IP: ").strip()
            if not host:
                print("No host provided. Cancelled.")
                return
            user = input("SSH user [root]: ").strip() or "root"
            port = input("SSH port [22]: ").strip() or "22"
            use_password = input("Use password authentication? (y/N): ").strip().lower() == 'y'
            
            password = None
            if use_password:
                password = getpass("SSH password: ")
            
            self.uninstall_remote(host, user, port, password=password)
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}Uninstallation complete!{Colors.END}")


def check_command_exists(cmd):
    """Check if a command exists on the system."""
    try:
        result = subprocess.run(["which", cmd], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def check_package_available(pkg):
    """Check if a package is available in apt cache."""
    try:
        result = subprocess.run(["apt-cache", "show", pkg], 
                               capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def resolve_package_name(pkg):
    """Resolve package name with version-specific fallbacks.
    
    For Python packages, tries version-specific names first, then generic.
    E.g., python3-dev -> python3.13-dev (if available) -> python3-dev
    """
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    # Packages that might have version-specific variants or Debian-version renames
    versioned_packages = {
        'python3-dev': [f'python{py_version}-dev', 'python3-dev', 'libpython3-dev'],
        'python3-venv': [f'python{py_version}-venv', 'python3-venv'],
        # Debian 12+ renamed dnsutils → bind9-dnsutils (dnsutils is now transitional)
        'dnsutils': ['dnsutils', 'bind9-dnsutils'],
    }
    
    if pkg not in versioned_packages:
        return pkg
    
    alternatives = versioned_packages[pkg]
    for alt in alternatives:
        if check_package_available(alt):
            return alt
    
    # Fallback to original (will fail gracefully)
    return pkg

def resolve_all_packages(packages):
    """Resolve all packages in list to available versions."""
    resolved = []
    for pkg in packages:
        resolved_pkg = resolve_package_name(pkg)
        if resolved_pkg != pkg:
            print(f"  ℹ {pkg} → {resolved_pkg}")
        resolved.append(resolved_pkg)
    return resolved

def check_package_installed(pkg, pkg_manager="apt"):
    """Check if a package is installed.

    Uses dpkg-query for reliable status checking.
    Falls back to checking the command the package provides
    (e.g. dnsutils → dig) for transitional packages on Debian 12+/13
    where `dpkg -l` may return 'un' even when the tools are present.
    """
    # Packages that are considered satisfied when a command exists
    cmd_fallbacks = {
        'dnsutils': 'dig',
        'bind9-dnsutils': 'dig',
        'iputils-ping': 'ping',
        'iproute2': 'ip',
        'arping': 'arping',
        'curl': 'curl',
    }
    try:
        if pkg_manager == "apt":
            result = subprocess.run(
                ["dpkg-query", "-W", "-f=${Status}", pkg],
                capture_output=True, text=True
            )
            if result.returncode == 0 and "install ok installed" in result.stdout:
                return True
            # Fallback: if the command this package provides exists, treat as installed
            fallback_cmd = cmd_fallbacks.get(pkg)
            if fallback_cmd:
                return subprocess.run(
                    ["which", fallback_cmd], capture_output=True
                ).returncode == 0
            return False
        elif pkg_manager == "yum":
            result = subprocess.run(["rpm", "-q", pkg], capture_output=True, text=True)
            return result.returncode == 0
        elif pkg_manager == "pacman":
            result = subprocess.run(["pacman", "-Q", pkg], capture_output=True, text=True)
            return result.returncode == 0
    except:
        return False
    return False

def check_dependencies():
    """Check all required dependencies and report missing ones."""
    import platform
    
    print("\n=== Checking Dependencies ===\n")
    
    missing_system = []
    missing_commands = []
    missing_python = []
    
    # Check system packages from system-requirements.txt
    if os.path.exists("system-requirements.txt"):
        with open("system-requirements.txt") as f:
            sys_pkgs = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        # Detect package manager
        pkg_manager = None
        if os.path.exists("/usr/bin/apt-get"):
            pkg_manager = "apt"
        elif os.path.exists("/usr/bin/yum"):
            pkg_manager = "yum"
        elif os.path.exists("/usr/bin/pacman"):
            pkg_manager = "pacman"
        
        if pkg_manager and platform.system() == "Linux":
            print("Checking system packages...")
            for pkg in sys_pkgs:
                # Resolve to version-specific package name if needed
                resolved_pkg = resolve_package_name(pkg) if pkg_manager == "apt" else pkg
                
                if not check_package_installed(resolved_pkg, pkg_manager):
                    missing_system.append(resolved_pkg)
                    if resolved_pkg != pkg:
                        print(f"  ✗ {pkg} ({resolved_pkg}) - NOT INSTALLED")
                    else:
                        print(f"  ✗ {pkg} - NOT INSTALLED")
                else:
                    if resolved_pkg != pkg:
                        print(f"  ✓ {pkg} ({resolved_pkg}) - installed")
                    else:
                        print(f"  ✓ {pkg} - installed")
    
    # Check required commands
    print("\nChecking required commands...")
    required_commands = {
        'python3': 'Python 3 interpreter',
        'pip3': 'Python package manager (pip)',
        'systemctl': 'Systemd service manager',
        'useradd': 'User management utility',
        'ping': 'Network connectivity tool',
    }
    
    for cmd, description in required_commands.items():
        if not check_command_exists(cmd):
            missing_commands.append(f"{cmd} ({description})")
            print(f"  ✗ {cmd} - NOT FOUND")
        else:
            print(f"  ✓ {cmd} - found")
    
    # Check Python version
    print("\nChecking Python version...")
    py_version = sys.version_info
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 8):
        missing_python.append("Python 3.8+ required")
        print(f"  ✗ Python {py_version.major}.{py_version.minor} - TOO OLD (need 3.8+)")
    else:
        print(f"  ✓ Python {py_version.major}.{py_version.minor} - OK")
    
    # Check Python packages from requirements.txt (system-wide)
    # Note: These are installed in virtual environments during deployment
    print("\nChecking Python packages (system-wide)...")
    print("  ℹ Note: Python packages will be installed in virtual environments during deployment")
    if os.path.exists("requirements.txt"):
        with open("requirements.txt") as f:
            py_pkgs = [line.strip().split('==')[0] for line in f if line.strip() and not line.startswith('#')]
        
        installed_count = 0
        for pkg in py_pkgs:
            try:
                __import__(pkg.replace('-', '_'))
                print(f"  ✓ {pkg} - installed system-wide")
                installed_count += 1
            except ImportError:
                # This is OK - packages will be installed in venv
                pass
        
        if installed_count == 0:
            print(f"  ℹ No packages installed system-wide (will be installed in venv during deployment)")
        else:
            print(f"  ℹ {installed_count}/{len(py_pkgs)} packages installed system-wide")
    
    # Report summary
    print("\n" + "="*50)
    if not missing_system and not missing_commands:
        print("✓ All system dependencies are satisfied!")
        print("\nPython packages will be automatically installed in virtual environments during deployment.")
        return True
    else:
        print("✗ Missing system dependencies detected:\n")
        
        if missing_system:
            print("System packages (required):")
            for pkg in missing_system:
                print(f"  - {pkg}")
        
        if missing_commands:
            print("\nRequired commands:")
            for cmd in missing_commands:
                print(f"  - {cmd}")
        
        return False

def main():
    global VERBOSE
    
    import platform
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Pi-hole Sentinel High Availability Setup')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Show verbose output including all command details')
    parser.add_argument('--uninstall', action='store_true',
                       help='Uninstall Pi-hole Sentinel components')
    parser.add_argument('--keep-configs', action='store_true',
                       help='Keep configuration files during uninstall')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    args = parser.parse_args()
    
    VERBOSE = args.verbose
    
    # Handle uninstall mode
    if args.uninstall:
        uninstaller = Uninstaller(
            keep_configs=args.keep_configs,
            dry_run=args.dry_run
        )
        uninstaller.run_interactive()
        sys.exit(0)
    
    if VERBOSE:
        print("═══ VERBOSE MODE ENABLED ═══\n")
    
    def is_root():
        if platform.system() == "Windows":
            # On Windows, check for admin
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except Exception:
                return False
        else:
            return os.geteuid() == 0

    def run_with_sudo(cmd, check=True):
        if is_root():
            return subprocess.run(cmd, check=check)
        else:
            return subprocess.run(["sudo"] + cmd, check=check)

    try:
        # Show logo
        print(LOGO)
        
        # Pause to let user see the logo
        print(f"{Colors.YELLOW}This script will guide you through setting up High Availability for your Pi-holes.{Colors.END}")
        print(f"{Colors.YELLOW}We'll check system dependencies, collect your network configuration, and deploy the setup.{Colors.END}\n")
        input(f"{Colors.BOLD}Press ENTER to begin...{Colors.END} ")
        
        # Check for root/sudo
        if not is_root():
            print(f"\n{Colors.RED}{Colors.BOLD}ERROR:{Colors.END} This setup script must be run as root or with sudo privileges!")
            print(f"Please run: {Colors.CYAN}sudo python3 setup.py{Colors.END}")
            sys.exit(1)

        # Check all dependencies
        print(f"\n{Colors.CYAN}{Colors.BOLD}═══ Checking System Dependencies ═══{Colors.END}\n")
        deps_ok = check_dependencies()
        
        if not deps_ok:
            print("\n" + "="*50)
            print("Do you want to install missing dependencies automatically?")
            print("This will use your system's package manager (apt/yum/pacman).")
            choice = input("\nInstall missing dependencies? (y/N): ").lower()
            
            if choice != 'y':
                print("\nSetup cancelled. Please install missing dependencies manually.")
                print("\nSystem packages can be installed with:")
                if os.path.exists("/usr/bin/apt-get"):
                    print("  sudo apt-get install <package-name>")
                elif os.path.exists("/usr/bin/yum"):
                    print("  sudo yum install <package-name>")
                elif os.path.exists("/usr/bin/pacman"):
                    print("  sudo pacman -S <package-name>")
                print("\nPython packages can be installed with:")
                print("  pip3 install -r requirements.txt")
                sys.exit(1)
            
            # Install system requirements
            print("\n┌─ Installing system packages")
            sysreq_file = "system-requirements.txt"
            if os.path.exists(sysreq_file):
                with open(sysreq_file) as f:
                    pkgs = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
                print(f"│  Packages: {len(pkgs)} total")
                
                # Detect package manager
                if platform.system() == "Linux":
                    if os.path.exists("/usr/bin/apt-get"):
                        apt_env = os.environ.copy()
                        apt_env["DEBIAN_FRONTEND"] = "noninteractive"
                        apt_env["NEEDRESTART_MODE"] = "a"
                        try:
                            print(f"│  [░░░░░░░░░░░░░░░░░░░░] 0%   Updating package lists...", end='\r')
                            result = subprocess.run(
                                ["apt-get", "update", "-o", "Acquire::Retries=3", "-qq"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                check=True,
                                timeout=300,
                                env=apt_env,
                            )
                            print(f"│  [████░░░░░░░░░░░░░░░░] 20%  Package lists updated     ")

                            # Resolve version-specific package names
                            print(f"│  [████░░░░░░░░░░░░░░░░] 20%  Resolving packages...", end='\r')
                            resolved_pkgs = resolve_all_packages(pkgs)
                            print(f"│  [██████░░░░░░░░░░░░░░] 30%  Packages resolved        ")

                            print(f"│  [██████░░░░░░░░░░░░░░] 30%  Installing packages...", end='\r')
                            print(f"\n│  ℹ apt output enabled to prevent silent hangs")
                            result = subprocess.run(
                                [
                                    "apt-get", "install", "-y",
                                    "-o", "Dpkg::Use-Pty=0",
                                    "-o", "DPkg::Lock::Timeout=120",
                                    "-o", "Acquire::Retries=3",
                                ] + resolved_pkgs,
                                check=True,
                                timeout=1800,
                                env=apt_env,
                            )
                            print(f"│  [████████████████████] 100% Installation complete!    ")
                        except subprocess.TimeoutExpired:
                            print("\n│  ✗ Package installation timed out (30 minutes)")
                            print("│  ℹ Check apt lock/network, then rerun setup with --verbose")
                            print("└─")
                            sys.exit(1)
                    
                    
                    elif os.path.exists("/usr/bin/yum"):
                        print(f"│  [░░░░░░░░░░░░░░░░░░░░] 0%   Installing packages...", end='\r')
                        result = subprocess.run(["yum", "install", "-y", "-q"] + pkgs,
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                        print(f"│  [████████████████████] 100% Installation complete!")
                    elif os.path.exists("/usr/bin/pacman"):
                        print(f"│  [░░░░░░░░░░░░░░░░░░░░] 0%   Syncing databases...", end='\r')
                        result = subprocess.run(["pacman", "-Sy", "--quiet"],
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                        print(f"│  [██████████░░░░░░░░░░] 50%  Installing packages...", end='\r')
                        result = subprocess.run(["pacman", "-S", "--noconfirm", "--quiet"] + pkgs,
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                        print(f"│  [████████████████████] 100% Installation complete!")
                    else:
                        print("│  ✗ ERROR: No supported package manager found.")
                        print("└─")
                        sys.exit(1)
                elif platform.system() == "Windows":
                    print("│  ⚠ WARNING: System requirements must be installed manually on Windows.")
            
            print("└─ ✓ Dependencies installed successfully!\n")
        else:
            print("\n✓ All dependencies already satisfied, continuing with setup...")

        # Continue with interactive setup
        setup = SetupConfig()
        verbose_hint = f" {Colors.YELLOW}(use --verbose for detailed output){Colors.END}" if not VERBOSE else f" {Colors.GREEN}(verbose mode active){Colors.END}"
        print(f"""
{Colors.CYAN}{Colors.BOLD}═══════════════════════════════════════════════════════════════════════════════
                    High Availability Setup Configuration{verbose_hint}
═══════════════════════════════════════════════════════════════════════════════{Colors.END}

{Colors.BOLD}This script will help you set up:{Colors.END}
{Colors.GREEN}✓{Colors.END} Automatic failover between your Pi-holes
{Colors.GREEN}✓{Colors.END} Configuration sync (replaces nebula-sync)
{Colors.GREEN}✓{Colors.END} Optional DHCP failover
{Colors.GREEN}✓{Colors.END} Real-time monitoring dashboard

{Colors.BOLD}Requirements:{Colors.END}
{Colors.CYAN}•{Colors.END} Two working Pi-holes
{Colors.CYAN}•{Colors.END} Network information ready
{Colors.CYAN}•{Colors.END} Pi-hole web interface passwords
{Colors.CYAN}•{Colors.END} SSH root access to all servers (passwords will be asked once)

{Colors.GREEN}{Colors.BOLD}✓ SSH keys will be automatically generated and distributed{Colors.END}
{Colors.GREEN}  No manual SSH setup required!{Colors.END}
""")
        # ...existing code...
        setup.collect_network_config()
        setup.collect_dhcp_config()
        setup.collect_monitor_config()
        setup.collect_pihole_config()
        setup.verify_configuration()

        print(f"""

{Colors.CYAN}{Colors.BOLD}Choose deployment mode:{Colors.END}
{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}
{Colors.BOLD}1.{Colors.END} Full deploy via SSH {Colors.GREEN}(recommended — deploys everything to all servers){Colors.END}
{Colors.BOLD}2.{Colors.END} Generate configuration files only (manual deployment)
{Colors.BOLD}3.{Colors.END} Advanced: deploy single component (monitor/primary/secondary only)
{Colors.RED}{Colors.BOLD}4.{Colors.END} Uninstall Pi-hole Sentinel from all servers
{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}
""")

        mode = input(f"{Colors.BOLD}Enter your choice (1-4):{Colors.END} ").strip()

        # Uninstall path: IPs already collected above, just run uninstall
        if mode == "4":
            setup.uninstall()
            return

        # Collect Pi-hole passwords (needed for monitoring)
        print(f"\n{Colors.CYAN}{Colors.BOLD}═══ Pi-hole Web Interface Passwords ═══{Colors.END}")
        setup.collect_pihole_passwords()

        # Pre-flight: validate all credentials before touching any server
        setup.preflight_checks()

        # Generate configurations
        print(f"\n{Colors.CYAN}{Colors.BOLD}═══ Generating Configuration Files ═══{Colors.END}")
        setup.generate_configs()

        if mode == "2":
            setup.show_next_steps()
        elif mode == "1":
            print(f"\n{Colors.CYAN}{Colors.BOLD}═══ Remote Deployment via SSH ═══{Colors.END}")
            print("This will deploy to all configured servers via SSH.\n")

            # Track which servers have been touched so we can roll back on error
            deployed_hosts = []
            deploy_failed  = False

            try:
                # Deploy monitor
                if setup.config['separate_monitor']:
                    print(f"\n{Colors.BOLD}[1/4] Deploying monitor to {setup.config['monitor_ip']}...{Colors.END}")
                    ts = setup.backup_existing_configs(
                        setup.config['monitor_ip'],
                        setup.config['monitor_ssh_user'],
                        setup.config['monitor_ssh_port'],
                        config_type="monitor"
                    )
                    ok = setup.deploy_monitor_remote()
                    deployed_hosts.append({
                        "type": "monitor",
                        "host": setup.config['monitor_ip'],
                        "user": setup.config['monitor_ssh_user'],
                        "port": setup.config['monitor_ssh_port'],
                        "backup_ts": ts,
                    })
                    if not ok:
                        raise RuntimeError(f"Monitor deployment failed on {setup.config['monitor_ip']}")
                else:
                    print(f"\n{Colors.BOLD}[1/4] Deploying monitor locally on primary...{Colors.END}")
                    setup.deploy_monitor()

                # Deploy primary
                print(f"\n{Colors.BOLD}[2/4] Deploying primary keepalived to {setup.config['primary_ip']}...{Colors.END}")
                ts = setup.backup_existing_configs(
                    setup.config['primary_ip'],
                    setup.config['primary_ssh_user'],
                    setup.config['primary_ssh_port'],
                    config_type="primary"
                )
                ok = setup.deploy_keepalived_remote("primary")
                deployed_hosts.append({
                    "type": "primary",
                    "host": setup.config['primary_ip'],
                    "user": setup.config['primary_ssh_user'],
                    "port": setup.config['primary_ssh_port'],
                    "backup_ts": ts,
                })
                if not ok:
                    raise RuntimeError(f"Primary keepalived deployment failed on {setup.config['primary_ip']}")

                # Deploy secondary
                print(f"\n{Colors.BOLD}[3/4] Deploying secondary keepalived to {setup.config['secondary_ip']}...{Colors.END}")
                ts = setup.backup_existing_configs(
                    setup.config['secondary_ip'],
                    setup.config['secondary_ssh_user'],
                    setup.config['secondary_ssh_port'],
                    config_type="secondary"
                )
                ok = setup.deploy_keepalived_remote("secondary")
                deployed_hosts.append({
                    "type": "secondary",
                    "host": setup.config['secondary_ip'],
                    "user": setup.config['secondary_ssh_user'],
                    "port": setup.config['secondary_ssh_port'],
                    "backup_ts": ts,
                })
                if not ok:
                    raise RuntimeError(f"Secondary keepalived deployment failed on {setup.config['secondary_ip']}")

                # Deploy sync service to primary
                print(f"\n{Colors.BOLD}[4/4] Deploying config sync to {setup.config['primary_ip']}...{Colors.END}")
                sync_interval = setup.config.get('sync_interval', 10)
                ok = setup.deploy_sync_remote(sync_interval=sync_interval)
                if not ok:
                    # Sync failure is non-fatal — warn but continue
                    print(f"{Colors.YELLOW}⚠ Sync deployment failed — you can deploy it later with pisen sync{Colors.END}")

            except Exception as deploy_err:
                deploy_failed = True
                print(f"\n{Colors.RED}{Colors.BOLD}Deployment error: {deploy_err}{Colors.END}")
                setup.cleanup_sensitive_files()
                setup.rollback_deployment(deployed_hosts)
                sys.exit(1)

            # Cleanup sensitive files
            setup.cleanup_sensitive_files()

            # Show success message
            setup.show_deployment_success()
        elif mode == "3":
            sub = input(f"\n{Colors.BOLD}Which component?{Colors.END}\n  a. Monitor (local)\n  b. Primary keepalived (local)\n  c. Secondary keepalived (local)\n\n{Colors.BOLD}Choice (a/b/c):{Colors.END} ").strip().lower()
            if sub == "a":
                setup.deploy_monitor()
            elif sub == "b":
                setup.deploy_keepalived("primary")
            elif sub == "c":
                setup.deploy_keepalived("secondary")
            else:
                print(f"\n{Colors.RED}Invalid choice!{Colors.END}")
                sys.exit(1)
            setup.cleanup_sensitive_files()
            print(f"\n{Colors.GREEN}✓ Component deployed successfully!{Colors.END}")
        else:
            print(f"\n{Colors.RED}Invalid choice!{Colors.END}")
            sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Setup cancelled by user.{Colors.END}")
        # Cleanup on interrupt
        try:
            if 'setup' in locals():
                setup.cleanup_sensitive_files()
        except:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}{Colors.BOLD}Error during setup:{Colors.END} {e}")
        # Cleanup on error
        try:
            if 'setup' in locals():
                setup.cleanup_sensitive_files()
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()