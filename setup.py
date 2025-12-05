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
import socket
import secrets
import string
import subprocess
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

# ASCII art logo (simplified version of logo.svg)
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
        ╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝
{Colors.END}
          {Colors.BOLD}High Availability Monitoring for Pi-hole{Colors.END}
"""

class SetupConfig:
    def __init__(self):
        self.config = {}
        
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
        r"""Escape special characters for safe use in sed replacement string.

        Escapes: / \ & newline
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
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def remote_exec(self, host, user, port, command, password=None):
        """Execute command on remote host via SSH.

        Uses environment variable for password to avoid exposure in process lists.
        """
        # Use SSH key if available
        if self.config.get('ssh_key_path') and not password:
            cmd = ["ssh", "-i", self.config['ssh_key_path'], "-p", port, "-o", "StrictHostKeyChecking=no"]
            return subprocess.run(cmd + [f"{user}@{host}", command], check=True)
        elif password:
            # Use environment variable instead of CLI argument for security
            cmd = ["sshpass", "-e", "ssh", "-p", port, "-o", "StrictHostKeyChecking=no"]
            env = os.environ.copy()
            env['SSHPASS'] = password
            return subprocess.run(cmd + [f"{user}@{host}", command], check=True, env=env)
        else:
            cmd = ["ssh", "-p", port, "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
            return subprocess.run(cmd + [f"{user}@{host}", command], check=True)
    
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
        
        print(f"{Colors.CYAN}├─ Configuring timezone ({timezone}) and NTP...{Colors.END}")
        try:
            # Set timezone
            self.remote_exec(host, user, port, f"timedatectl set-timezone {timezone}", password)
            
            # Try to enable NTP (will be skipped in containers, which sync from host)
            try:
                self.remote_exec(host, user, port, "systemctl enable systemd-timesyncd >/dev/null 2>&1 || true", password)
                self.remote_exec(host, user, port, "systemctl start systemd-timesyncd >/dev/null 2>&1 || true", password)
                self.remote_exec(host, user, port, "timedatectl set-ntp true >/dev/null 2>&1 || true", password)
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
        
        try:
            # Update package lists
            print(f"│  [░░░░░░░░░░░░░░░░░░░░] 0%   Updating package lists...", end='\r')
            if VERBOSE:
                self.remote_exec(host, user, port, "apt-get update", password)
            else:
                self.remote_exec(host, user, port, "apt-get update -qq >/dev/null 2>&1", password)
            print(f"│  [████░░░░░░░░░░░░░░░░] 20%  Package lists updated     ")
            
            # Install packages (this is the slow part)
            print(f"│  [████░░░░░░░░░░░░░░░░] 20%  Installing packages...", end='\r')
            pkg_list = " ".join(packages)
            if VERBOSE:
                print(f"\n│  Installing: {pkg_list}")
                self.remote_exec(host, user, port, 
                    f"DEBIAN_FRONTEND=noninteractive apt-get install -y {pkg_list}", 
                    password)
            else:
                self.remote_exec(host, user, port, 
                    f"DEBIAN_FRONTEND=noninteractive apt-get install -y -qq {pkg_list} >/dev/null 2>&1", 
                    password)
            
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
        print("\nNOTE: All IP addresses must be in the same subnet!")
        while True:
            print("\nEnter IP addresses (press Enter for defaults):")
            primary_ip = input("Primary Pi-hole IP [10.10.100.10]: ").strip() or "10.10.100.10"
            secondary_ip = input("Secondary Pi-hole IP [10.10.100.20]: ").strip() or "10.10.100.20"
            vip = input("Virtual IP (VIP) address [10.10.100.2]: ").strip() or "10.10.100.2"
            gateway = input("Network gateway IP [10.10.100.1]: ").strip() or "10.10.100.1"
            
            if not all(map(self.validate_ip, [primary_ip, secondary_ip, vip, gateway])):
                print("Error: Invalid IP address format!")
                continue
            
            # Check if IPs are in same subnet
            try:
                netmask = "24"  # Assuming /24 network
                network = str(ip_network(f"{primary_ip}/{netmask}", strict=False).network_address)
                if not all(ip_address(ip) in ip_network(f"{network}/{netmask}")
                          for ip in [primary_ip, secondary_ip, vip, gateway]):
                    print("Error: IP addresses must be in the same subnet!")
                    continue
            except ValueError as e:
                print(f"Error: {e}")
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
                f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '{pub_key}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
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

    def collect_monitor_config(self):
        """Collect monitoring server configuration."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}=== Monitor Configuration ==={Colors.END}")
        
        while True:
            monitor_type = input(f"\n{Colors.BOLD}Where to install the monitor?{Colors.END}\n1. Separate server {Colors.GREEN}(recommended){Colors.END}\n2. On primary Pi-hole\nChoice (1/2): ")
            if monitor_type in ['1', '2']:
                self.config['separate_monitor'] = monitor_type == '1'
                break
            print(f"{Colors.RED}Please enter '1' or '2'{Colors.END}")
            
        if self.config['separate_monitor']:
            while True:
                monitor_ip = input(f"\n{Colors.BOLD}Monitor server IP:{Colors.END} ")
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
        
        # Securely clear passwords from memory immediately after use
        for key in passwords:
            passwords[key] = None
        passwords.clear()
        del passwords
        
        if success:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ SSH keys successfully distributed to all servers!{Colors.END}")
            print(f"{Colors.GREEN}  Passwordless access is now configured.{Colors.END}")
            
            # Store key path for later use
            self.config['ssh_key_path'] = key_path
            # Clear passwords - not needed anymore (defense in depth)
            self.config['primary_ssh_pass'] = None
            self.config['secondary_ssh_pass'] = None
            self.config['monitor_ssh_pass'] = None
        else:
            print(f"\n{Colors.RED}Failed to distribute SSH keys to all servers.{Colors.END}")
            sys.exit(1)
        
        # Generate secure keepalived password
        self.config['keepalived_password'] = self.generate_secure_password()
    
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

    def generate_configs(self):
        """Generate configuration files."""
        print("\n=== Generating Configuration Files ===")
        
        # Create primary keepalived config
        primary_keepalived = f"""# Keepalived configuration for Primary Pi-hole
# Generated by setup script - DO NOT EDIT MANUALLY

global_defs {{
    router_id PIHOLE1
    vrrp_version 3
    vrrp_garp_master_delay 1
    enable_script_security
    script_user root
}}

vrrp_script chk_pihole_service {{
    script "/usr/local/bin/check_pihole_service.sh"
    interval 5
    fall 3
    rise 2
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

        # Create secondary keepalived config (similar but with BACKUP state)
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

        os.makedirs('generated_configs', exist_ok=True)
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

        try:
            print(f"\nDeploying monitor to {host} via SSH...")

            # Backup existing configurations
            self.backup_existing_configs(host, user, port, password, "monitor")

            # Install system dependencies first
            if not self.install_remote_dependencies(host, user, port, password):
                return False

            # Configure timezone and NTP
            self.configure_timezone_and_ntp(host, user, port, password)

            # Pre-deployment checks and directory setup
            print("Running pre-deployment checks...")
            print("├─ Creating required directories...")
            # Create /etc/pihole-sentinel (required by systemd ReadWritePaths)
            self.remote_exec(host, user, port, "mkdir -p /etc/pihole-sentinel", password)

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
            
            for local, remote in files_to_copy:
                self.remote_copy(local, host, user, port, remote, password)
            
            # Execute installation commands
            print("Installing monitor service...")
            print("├─ Creating service user...")
            self.remote_exec(host, user, port, "useradd -r -s /bin/false pihole-monitor 2>/dev/null || true", password)
            
            print("├─ Setting up directories...")
            self.remote_exec(host, user, port, "mkdir -p /opt/pihole-monitor", password)
            self.remote_exec(host, user, port, "python3 -m venv /opt/pihole-monitor/venv", password)
            
            print("├─ Installing Python packages (this may take a moment)...")
            if VERBOSE:
                self.remote_exec(host, user, port, 
                    "cd /tmp/pihole-sentinel-deploy && /opt/pihole-monitor/venv/bin/pip install -r requirements.txt", 
                    password)
            else:
                self.remote_exec(host, user, port, 
                    "cd /tmp/pihole-sentinel-deploy && /opt/pihole-monitor/venv/bin/pip install -q -r requirements.txt >/dev/null 2>&1", 
                    password)
            
            print("├─ Copying application files...")
            commands = [
                "cp /tmp/pihole-sentinel-deploy/monitor.py /opt/pihole-monitor/",
                "cp /tmp/pihole-sentinel-deploy/index.html /opt/pihole-monitor/",
                "cp /tmp/pihole-sentinel-deploy/settings.html /opt/pihole-monitor/",
                "cp /tmp/pihole-sentinel-deploy/monitor.env /opt/pihole-monitor/.env",
                "cp /tmp/pihole-sentinel-deploy/pihole-monitor.service /etc/systemd/system/",
                "cp /tmp/pihole-sentinel-deploy/VERSION /opt/VERSION",
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
                    f"sed -i 's#YOUR_API_KEY_HERE#{escaped_key}#g' /opt/pihole-monitor/index.html",
                    password)
                self.remote_exec(host, user, port,
                    f"sed -i 's#YOUR_API_KEY_HERE#{escaped_key}#g' /opt/pihole-monitor/settings.html",
                    password)
                print("│  → API key configured successfully")

            print("├─ Setting permissions...")
            perms_commands = [
                "chown -R pihole-monitor:pihole-monitor /opt/pihole-monitor",
                "chmod 755 /opt/pihole-monitor",
                "chmod 644 /opt/pihole-monitor/*.py /opt/pihole-monitor/*.html",
                "chmod 600 /opt/pihole-monitor/.env",
                "chmod 755 -R /opt/pihole-monitor/venv",
                "chown root:root /etc/systemd/system/pihole-monitor.service",
                "chmod 644 /etc/systemd/system/pihole-monitor.service",
                "chown pihole-monitor:pihole-monitor /etc/pihole-sentinel",
                "chmod 755 /etc/pihole-sentinel",
                "chmod 644 /opt/VERSION",
            ]
            for cmd in perms_commands:
                self.remote_exec(host, user, port, cmd, password)
            
            print("└─ Starting service...")
            self.remote_exec(host, user, port, "systemctl daemon-reload", password)
            self.remote_exec(host, user, port, "systemctl enable pihole-monitor >/dev/null 2>&1", password)
            self.remote_exec(host, user, port, "systemctl restart pihole-monitor", password)
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
        
        try:
            print(f"\nDeploying {node_type} keepalived to {host} via SSH...")
            
            # Backup existing configurations
            self.backup_existing_configs(host, user, port, password, node_type)
            
            # Install system dependencies first
            if not self.install_remote_dependencies(host, user, port, password):
                return False
            
            # Configure timezone and NTP
            self.configure_timezone_and_ntp(host, user, port, password)
            
            # Create remote temp directory
            print("Preparing remote server...")
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
            ]
            
            for local, remote in files_to_copy:
                self.remote_copy(local, host, user, port, remote, password)
            
            # Execute installation commands
            print("Installing keepalived...")
            commands = [
                "command -v keepalived >/dev/null 2>&1 || (apt-get update && apt-get install -y keepalived arping)",
                "mkdir -p /etc/keepalived",
                "chmod 755 /etc/keepalived",
                "mkdir -p /usr/local/bin",
                "chmod 755 /usr/local/bin",
                "cp /tmp/pihole-sentinel-deploy/keepalived.conf /etc/keepalived/keepalived.conf",
                "chown root:root /etc/keepalived/keepalived.conf",
                "chmod 644 /etc/keepalived/keepalived.conf",
                "cp /tmp/pihole-sentinel-deploy/.env /etc/keepalived/.env",
                "chown root:root /etc/keepalived/.env",
                "chmod 600 /etc/keepalived/.env",
                # Copy and fix line endings for scripts
                "for script in check_pihole_service.sh check_dhcp_service.sh dhcp_control.sh keepalived_notify.sh; do " +
                "cp /tmp/pihole-sentinel-deploy/$script /tmp/$script && " +
                "sed -i 's/\\r$//' /tmp/$script && " +
                "mv /tmp/$script /usr/local/bin/$script && " +
                "chown root:root /usr/local/bin/$script && " +
                "chmod 755 /usr/local/bin/$script; done",
                "systemctl enable keepalived",
                "systemctl restart keepalived",
                "rm -rf /tmp/pihole-sentinel-deploy"
            ]
            
            for cmd in commands:
                self.remote_exec(host, user, port, cmd, password)
            
            print(f"✓ Keepalived {node_type} deployed successfully to {host}!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Error deploying keepalived to {host}: {e}")
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
        """Backup existing configuration files on remote server."""
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
            return True
        
        return False

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
║                     ✓ DEPLOYMENT COMPLETED SUCCESSFULLY!                     ║
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

def check_command_exists(cmd):
    """Check if a command exists on the system."""
    try:
        result = subprocess.run(["which", cmd], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def check_package_installed(pkg, pkg_manager="apt"):
    """Check if a package is installed."""
    try:
        if pkg_manager == "apt":
            result = subprocess.run(["dpkg", "-l", pkg], capture_output=True, text=True)
            return result.returncode == 0 and "ii" in result.stdout
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
                if not check_package_installed(pkg, pkg_manager):
                    missing_system.append(pkg)
                    print(f"  ✗ {pkg} - NOT INSTALLED")
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
    args = parser.parse_args()
    
    VERBOSE = args.verbose
    
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
                        print(f"│  [░░░░░░░░░░░░░░░░░░░░] 0%   Updating package lists...", end='\r')
                        result = subprocess.run(["apt-get", "update", "-qq"], 
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                        print(f"│  [████░░░░░░░░░░░░░░░░] 20%  Package lists updated     ")
                        print(f"│  [████░░░░░░░░░░░░░░░░] 20%  Installing packages...", end='\r')
                        result = subprocess.run(["apt-get", "install", "-y", "-qq"] + pkgs,
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                        print(f"│  [████████████████████] 100% Installation complete!    ")
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
{Colors.BOLD}1.{Colors.END} Generate configuration files only (manual deployment)
{Colors.BOLD}2.{Colors.END} Deploy complete setup via SSH {Colors.GREEN}(recommended - deploys to all servers){Colors.END}
{Colors.BOLD}3.{Colors.END} Deploy monitor only (local installation)
{Colors.BOLD}4.{Colors.END} Deploy primary node only (local installation)
{Colors.BOLD}5.{Colors.END} Deploy secondary node only (local installation)
{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}
""")

        mode = input(f"{Colors.BOLD}Enter your choice (1-5):{Colors.END} ").strip()

        # Collect Pi-hole passwords (needed for monitoring)
        print(f"\n{Colors.CYAN}{Colors.BOLD}═══ Pi-hole Web Interface Passwords ═══{Colors.END}")
        setup.collect_pihole_passwords()
        
        # Generate configurations
        print(f"\n{Colors.CYAN}{Colors.BOLD}═══ Generating Configuration Files ═══{Colors.END}")
        setup.generate_configs()

        if mode == "1":
            setup.show_next_steps()
        elif mode == "2":
            print(f"\n{Colors.CYAN}{Colors.BOLD}═══ Remote Deployment via SSH ═══{Colors.END}")
            print("This will deploy to all configured servers via SSH.\n")
            
            # Deploy monitor
            if setup.config['separate_monitor']:
                print(f"\n{Colors.BOLD}[1/3] Deploying monitor to {setup.config['monitor_ip']}...{Colors.END}")
                setup.deploy_monitor_remote()
            else:
                print(f"\n{Colors.BOLD}[1/3] Deploying monitor locally on primary...{Colors.END}")
                setup.deploy_monitor()
            
            # Deploy primary
            print(f"\n{Colors.BOLD}[2/3] Deploying primary keepalived to {setup.config['primary_ip']}...{Colors.END}")
            setup.deploy_keepalived_remote("primary")
            
            # Deploy secondary
            print(f"\n{Colors.BOLD}[3/3] Deploying secondary keepalived to {setup.config['secondary_ip']}...{Colors.END}")
            setup.deploy_keepalived_remote("secondary")
            
            # Cleanup sensitive files
            setup.cleanup_sensitive_files()
            
            # Show success message
            setup.show_deployment_success()
        elif mode == "3":
            setup.deploy_monitor()
            setup.cleanup_sensitive_files()
            setup.show_deployment_success()
        elif mode == "4":
            setup.deploy_keepalived("primary")
            setup.cleanup_sensitive_files()
            print(f"\n{Colors.GREEN}✓ Primary keepalived deployed successfully!{Colors.END}")
        elif mode == "5":
            setup.deploy_keepalived("secondary")
            setup.cleanup_sensitive_files()
            print(f"\n{Colors.GREEN}✓ Secondary keepalived deployed successfully!{Colors.END}")
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