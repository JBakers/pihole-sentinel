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
        """Execute command on remote host via SSH."""
        cmd = ["ssh", "-p", port, "-o", "StrictHostKeyChecking=no"]
        
        if password:
            cmd = ["sshpass", "-p", password] + cmd
        else:
            cmd = cmd + ["-o", "BatchMode=yes"]
        
        cmd = cmd + [f"{user}@{host}", command]
        
        return subprocess.run(cmd, check=True)
    
    def remote_copy(self, local_file, host, user, port, remote_path, password=None):
        """Copy file to remote host via SCP."""
        cmd = ["scp", "-P", port, "-o", "StrictHostKeyChecking=no"]
        
        if password:
            cmd = ["sshpass", "-p", password] + cmd
        else:
            cmd = cmd + ["-o", "BatchMode=yes"]
        
        cmd = cmd + [local_file, f"{user}@{host}:{remote_path}"]
        
        return subprocess.run(cmd, check=True)
    
    def install_remote_dependencies(self, host, user, port, password=None, packages=None):
        """Install system dependencies on remote host."""
        if packages is None:
            packages = [
                "build-essential", "python3.11-dev", "python3-pip",
                "keepalived", "arping", "iproute2", "iputils-ping",
                "sqlite3", "python3.11-venv"
            ]
        
        print(f"Installing system dependencies on {host}...")
        
        try:
            # Update package lists
            self.remote_exec(host, user, port, "apt-get update -qq", password)
            
            # Install packages
            pkg_list = " ".join(packages)
            self.remote_exec(host, user, port, f"DEBIAN_FRONTEND=noninteractive apt-get install -y -qq {pkg_list}", password)
            
            print(f"✓ Dependencies installed on {host}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install dependencies on {host}: {e}")
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
        """Get list of network interfaces."""
        interfaces = []
        try:
            if os.path.exists('/sys/class/net'):
                interfaces = os.listdir('/sys/class/net')
        except:
            pass
        return interfaces or ['eth0', 'ens18', 'enp3s0']

    def collect_network_config(self):
        """Collect network configuration interactively."""
        print("\n=== Network Configuration ===")
        
        # Get network interface
        interfaces = self.get_interface_names()
        print("\nAvailable network interfaces:", ", ".join(interfaces))
        while True:
            interface = input(f"Enter network interface name [{interfaces[0]}]: ").strip()
            if not interface:
                interface = interfaces[0]
            if interface in interfaces:
                self.config['interface'] = interface
                break
            print("Invalid interface name!")

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
        print("\n=== DHCP Configuration ===")
        
        while True:
            dhcp = input("\nDo you use DHCP on your Pi-holes? (y/N): ").lower()
            if dhcp in ['y', 'n', '']:
                self.config['dhcp_enabled'] = dhcp == 'y'
                break
            print("Please enter 'y' or 'n'")
            
    def collect_monitor_config(self):
        """Collect monitoring server configuration."""
        print("\n=== Monitor Configuration ===")
        
        while True:
            monitor_type = input("\nWhere to install the monitor?\n1. Separate server (recommended)\n2. On primary Pi-hole\nChoice (1/2): ")
            if monitor_type in ['1', '2']:
                self.config['separate_monitor'] = monitor_type == '1'
                break
            print("Please enter '1' or '2'")
            
        if self.config['separate_monitor']:
            while True:
                monitor_ip = input("\nMonitor server IP: ")
                if self.validate_ip(monitor_ip):
                    self.config['monitor_ip'] = monitor_ip
                    # Ask for SSH access
                    self.config['monitor_ssh_user'] = input(f"SSH user for {monitor_ip} [root]: ").strip() or "root"
                    self.config['monitor_ssh_port'] = input(f"SSH port for {monitor_ip} [22]: ").strip() or "22"
                    
                    print("\nSSH Authentication:")
                    print("1. Use SSH key (passwordless - must be setup first!)")
                    print("2. Use password (will ask once, used for all operations)")
                    auth_choice = input("Choice (1/2) [1]: ").strip() or "1"
                    
                    if auth_choice == "2":
                        self.config['monitor_ssh_pass'] = getpass(f"SSH password for {self.config['monitor_ssh_user']}@{monitor_ip}: ")
                    else:
                        self.config['monitor_ssh_pass'] = None
                        print("\n💡 Tip: If you don't have SSH keys setup, choose option 2 (password)")
                    
                    if self.check_host_reachable(monitor_ip):
                        # Test SSH connection
                        test_cmd = ["ssh", "-p", self.config['monitor_ssh_port'],
                                   "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                                   f"{self.config['monitor_ssh_user']}@{monitor_ip}", "echo 'SSH OK'"]
                        
                        if self.config.get('monitor_ssh_pass'):
                            test_cmd = ["sshpass", "-p", self.config['monitor_ssh_pass']] + test_cmd
                        
                        test_ssh = subprocess.run(test_cmd, capture_output=True, timeout=10)
                        
                        if test_ssh.returncode == 0:
                            print(f"✓ SSH connection to monitor server successful!")
                            break
                        else:
                            if not self.config.get('monitor_ssh_pass'):
                                print(f"✗ SSH key authentication failed!")
                                print(f"   Either setup SSH keys first (ssh-copy-id {self.config['monitor_ssh_user']}@{monitor_ip})")
                                print(f"   OR choose password authentication (option 2)")
                            else:
                                print(f"✗ SSH password authentication failed! Check your password.")
                            retry = input("Try again? (Y/n): ").lower()
                            if retry == 'n':
                                sys.exit(1)
                    else:
                        proceed = input("Warning: Monitor server not reachable. Proceed anyway? (y/N): ").lower()
                        if proceed == 'y':
                            break
                print("Please enter a valid IP address")
        else:
            self.config['monitor_ip'] = self.config['primary_ip']
            self.config['monitor_ssh_user'] = None
            self.config['monitor_ssh_port'] = None
            self.config['monitor_ssh_pass'] = None
            print(f"\n✓ Monitor will be installed on primary Pi-hole: {self.config['monitor_ip']}")

    def collect_pihole_config(self):
        """Collect Pi-hole configuration."""
        print("\n=== Pi-hole Configuration ===")
        
        print("\nPi-hole web interface passwords:")
        self.config['primary_password'] = getpass("Primary Pi-hole password: ")
        self.config['secondary_password'] = getpass("Secondary Pi-hole password: ")
        
        # Collect SSH access for Pi-holes
        print("\nSSH access for remote deployment:")
        
        # Primary
        self.config['primary_ssh_user'] = input(f"SSH user for primary ({self.config['primary_ip']}) [root]: ").strip() or "root"
        self.config['primary_ssh_port'] = input(f"SSH port for primary [22]: ").strip() or "22"
        
        print("\nSSH Authentication for primary:")
        print("1. Use SSH key (passwordless - must be setup first!)")
        print("2. Use password (will ask once)")
        auth_choice = input("Choice (1/2) [1]: ").strip() or "1"
        
        if auth_choice == "2":
            self.config['primary_ssh_pass'] = getpass(f"SSH password for {self.config['primary_ssh_user']}@{self.config['primary_ip']}: ")
        else:
            self.config['primary_ssh_pass'] = None
            print("💡 Tip: If you don't have SSH keys setup, choose option 2")
        
        # Secondary
        self.config['secondary_ssh_user'] = input(f"\nSSH user for secondary ({self.config['secondary_ip']}) [root]: ").strip() or "root"
        self.config['secondary_ssh_port'] = input(f"SSH port for secondary [22]: ").strip() or "22"
        
        print("\nSSH Authentication for secondary:")
        print("1. Use SSH key (passwordless - must be setup first!)")
        print("2. Use password (will ask once)")
        auth_choice = input("Choice (1/2) [1]: ").strip() or "1"
        
        if auth_choice == "2":
            self.config['secondary_ssh_pass'] = getpass(f"SSH password for {self.config['secondary_ssh_user']}@{self.config['secondary_ip']}: ")
        else:
            self.config['secondary_ssh_pass'] = None
            print("💡 Tip: If you don't have SSH keys setup, choose option 2")
        
        # Generate secure keepalived password
        self.config['keepalived_password'] = self.generate_secure_password()

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
            
            # Install system dependencies first
            if not self.install_remote_dependencies(host, user, port, password):
                return False
            
            # Create remote temp directory
            print("Preparing remote server...")
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
            ]
            
            for local, remote in files_to_copy:
                self.remote_copy(local, host, user, port, remote, password)
            
            # Execute installation commands
            print("Installing monitor service...")
            commands = [
                "useradd -r -s /bin/false pihole-monitor 2>/dev/null || true",
                "mkdir -p /opt/pihole-monitor",
                "python3 -m venv /opt/pihole-monitor/venv",
                "cd /tmp/pihole-sentinel-deploy && /opt/pihole-monitor/venv/bin/pip install -r requirements.txt",
                "cp /tmp/pihole-sentinel-deploy/monitor.py /opt/pihole-monitor/",
                "cp /tmp/pihole-sentinel-deploy/index.html /opt/pihole-monitor/",
                "cp /tmp/pihole-sentinel-deploy/settings.html /opt/pihole-monitor/",
                "cp /tmp/pihole-sentinel-deploy/monitor.env /opt/pihole-monitor/.env",
                "cp /tmp/pihole-sentinel-deploy/pihole-monitor.service /etc/systemd/system/",
                "chown -R pihole-monitor:pihole-monitor /opt/pihole-monitor",
                "chmod 755 /opt/pihole-monitor",
                "chmod 644 /opt/pihole-monitor/*.py /opt/pihole-monitor/*.html",
                "chmod 600 /opt/pihole-monitor/.env",
                "chmod 755 -R /opt/pihole-monitor/venv",
                "chown root:root /etc/systemd/system/pihole-monitor.service",
                "chmod 644 /etc/systemd/system/pihole-monitor.service",
                "systemctl daemon-reload",
                "systemctl enable pihole-monitor",
                "systemctl restart pihole-monitor",
                "rm -rf /tmp/pihole-sentinel-deploy"
            ]
            
            for cmd in commands:
                self.remote_exec(host, user, port, cmd, password)
            
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
            for script in ["check_pihole_service.sh", "dhcp_control.sh", "keepalived_notify.sh"]:
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
            
            # Install system dependencies first
            if not self.install_remote_dependencies(host, user, port, password):
                return False
            
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
                "for script in check_pihole_service.sh dhcp_control.sh keepalived_notify.sh; do " +
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
        """Show next steps for deployment."""
        print("""
=== Next Steps ===

1. Copy the configuration files to their respective locations:

   On Primary Pi-hole:
   - Copy primary_keepalived.conf to /etc/keepalived/keepalived.conf
   - Copy primary.env to /etc/keepalived/.env

   On Secondary Pi-hole:
   - Copy secondary_keepalived.conf to /etc/keepalived/keepalived.conf
   - Copy secondary.env to /etc/keepalived/.env

   On Monitor Server:
   - Copy monitor.env to /opt/pihole-monitor/.env

2. Restart services:
   - On both Pi-holes: systemctl restart keepalived
   - On monitor: systemctl restart pihole-monitor

3. Verify the setup:
   - Check keepalived status: systemctl status keepalived
   - Monitor logs: tail -f /var/log/keepalived-notify.log
   - Access monitor dashboard: http://<monitor-ip>:8080

4. Test failover:
   - Stop pihole-FTL on primary: systemctl stop pihole-FTL
   - Watch the dashboard for failover
   - Check that DNS still works

For security, delete the generated_configs directory after deployment.
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
    
    # Check Python packages from requirements.txt
    print("\nChecking Python packages...")
    if os.path.exists("requirements.txt"):
        with open("requirements.txt") as f:
            py_pkgs = [line.strip().split('==')[0] for line in f if line.strip() and not line.startswith('#')]
        
        for pkg in py_pkgs:
            try:
                __import__(pkg.replace('-', '_'))
                print(f"  ✓ {pkg} - installed")
            except ImportError:
                missing_python.append(pkg)
                print(f"  ✗ {pkg} - NOT INSTALLED")
    
    # Report summary
    print("\n" + "="*50)
    if not missing_system and not missing_commands and not missing_python:
        print("✓ All dependencies are satisfied!")
        return True
    else:
        print("✗ Missing dependencies detected:\n")
        
        if missing_system:
            print("System packages:")
            for pkg in missing_system:
                print(f"  - {pkg}")
        
        if missing_commands:
            print("\nRequired commands:")
            for cmd in missing_commands:
                print(f"  - {cmd}")
        
        if missing_python:
            print("\nPython packages:")
            for pkg in missing_python:
                print(f"  - {pkg}")
        
        return False

def main():

    import platform
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
        # Check for root/sudo
        if not is_root():
            print("\nERROR: This setup script must be run as root or with sudo privileges!")
            print("Please run: sudo python3 setup.py")
            sys.exit(1)

        # Check all dependencies
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
            print("\nInstalling system packages...")
            sysreq_file = "system-requirements.txt"
            if os.path.exists(sysreq_file):
                with open(sysreq_file) as f:
                    pkgs = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
                # Detect package manager
                if platform.system() == "Linux":
                    if os.path.exists("/usr/bin/apt-get"):
                        print("Using apt-get...")
                        run_with_sudo(["apt-get", "update"])
                        run_with_sudo(["apt-get", "install", "-y"] + pkgs)
                    elif os.path.exists("/usr/bin/yum"):
                        print("Using yum...")
                        run_with_sudo(["yum", "install", "-y"] + pkgs)
                    elif os.path.exists("/usr/bin/pacman"):
                        print("Using pacman...")
                        run_with_sudo(["pacman", "-Sy"])
                        run_with_sudo(["pacman", "-S", "--noconfirm"] + pkgs)
                    else:
                        print("ERROR: No supported package manager found.")
                        sys.exit(1)
                elif platform.system() == "Windows":
                    print("WARNING: System requirements must be installed manually on Windows.")
            
            print("\n✓ Dependencies installed successfully!")
        else:
            print("\n✓ All dependencies already satisfied, continuing with setup...")

        # Continue with interactive setup
        setup = SetupConfig()
        print("""
Pi-hole Sentinel - High Availability Setup
=========================================

This script will help you set up:
1. Automatic failover between your Pi-holes
2. Optional DHCP failover
3. Monitoring dashboard

Requirements:
- Two working Pi-holes
- Network information ready
- Pi-hole web interface passwords

SSH Authentication Options:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Option 1: SSH Keys (Recommended)
  Setup BEFORE running this script:
    ssh-keygen -t ed25519
    ssh-copy-id root@<monitor-ip>
    ssh-copy-id root@<primary-ip>
    ssh-copy-id root@<secondary-ip>

Option 2: Passwords (Simpler)
  You'll be asked for each server's SSH password
  Passwords are stored in memory only during setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
        # ...existing code...
        setup.collect_network_config()
        setup.collect_dhcp_config()
        setup.collect_monitor_config()
        setup.collect_pihole_config()
        setup.verify_configuration()

        print("""

Choose deployment mode:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Generate configuration files only (manual deployment)
2. Deploy complete setup via SSH (recommended - deploys to all servers)
3. Deploy monitor only (local installation)
4. Deploy primary node only (local installation)
5. Deploy secondary node only (local installation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

        mode = input("Enter your choice (1-5): ").strip()

        # Generate configurations
        setup.generate_configs()

        if mode == "1":
            setup.show_next_steps()
        elif mode == "2":
            print("\n=== Remote Deployment via SSH ===")
            print("This will deploy to all configured servers via SSH.\n")
            
            # Deploy monitor
            if setup.config['separate_monitor']:
                print(f"\n[1/3] Deploying monitor to {setup.config['monitor_ip']}...")
                setup.deploy_monitor_remote()
            else:
                print(f"\n[1/3] Deploying monitor locally on primary...")
                setup.deploy_monitor()
            
            # Deploy primary
            print(f"\n[2/3] Deploying primary keepalived to {setup.config['primary_ip']}...")
            setup.deploy_keepalived_remote("primary")
            
            # Deploy secondary
            print(f"\n[3/3] Deploying secondary keepalived to {setup.config['secondary_ip']}...")
            setup.deploy_keepalived_remote("secondary")
            
            print("\n✓ Complete setup deployed to all servers!")
        elif mode == "3":
            setup.deploy_monitor()
        elif mode == "4":
            setup.deploy_keepalived("primary")
        elif mode == "5":
            setup.deploy_keepalived("secondary")
        else:
            print("\nInvalid choice!")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()