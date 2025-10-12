#!/usr/bin/env python3
"""
Pi-hole HA Setup Configuration Script
===================================

This script helps you configure your Pi-hole High Availability setup by:
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
            vip = input("Virtual IP (VIP) address [10.10.100.1]: ").strip() or "10.10.100.1"
            gateway = input("Network gateway IP [10.10.100.254]: ").strip() or "10.10.100.254"
            
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
                    if self.check_host_reachable(monitor_ip):
                        self.config['monitor_ip'] = monitor_ip
                        break
                    else:
                        proceed = input("Warning: Monitor server not reachable. Proceed anyway? (y/N): ").lower()
                        if proceed == 'y':
                            self.config['monitor_ip'] = monitor_ip
                            break
                print("Please enter a valid IP address")
        else:
            self.config['monitor_ip'] = self.config['primary_ip']

    def collect_pihole_config(self):
        """Collect Pi-hole configuration."""
        print("\n=== Pi-hole Configuration ===")
        
        print("\nPi-hole web interface passwords:")
        self.config['primary_password'] = getpass("Primary Pi-hole password: ")
        self.config['secondary_password'] = getpass("Secondary Pi-hole password: ")
        
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
            subprocess.run(["sudo", "cp", "generated_configs/monitor.env", "/opt/pihole-monitor/.env"], check=True)
            subprocess.run(["sudo", "cp", "dashboard/service/pihole-monitor.service", 
                          "/etc/systemd/system/"], check=True)
            
            # Set correct ownership and permissions
            print("Setting permissions...")
            
            # Main directory: 755 pihole-monitor:pihole-monitor
            subprocess.run(["sudo", "chown", "pihole-monitor:pihole-monitor", "/opt/pihole-monitor"], check=True)
            subprocess.run(["sudo", "chmod", "755", "/opt/pihole-monitor"], check=True)
            
            # Application files: 644 pihole-monitor:pihole-monitor
            for file in ["monitor.py", "index.html"]:
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
                subprocess.run(["sudo", "cp", f"keepalived/scripts/{script}",
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

def main():
    try:
        setup = SetupConfig()
        
        print("""
Pi-hole High Availability Setup
============================

This script will help you set up:
1. Automatic failover between your Pi-holes
2. Optional DHCP failover
3. Monitoring dashboard

Requirements:
- Two working Pi-holes
- Network information ready
- Pi-hole web interface passwords
""")
        
        # Collect configurations
        setup.collect_network_config()
        setup.collect_dhcp_config()
        setup.collect_monitor_config()
        setup.collect_pihole_config()
        setup.verify_configuration()
        
        print("""

Choose deployment mode:
1. Generate configuration files only
2. Deploy complete setup (recommended)
3. Deploy monitor only
4. Deploy primary node only
5. Deploy secondary node only
""")
        
        mode = input("Enter your choice (1-5): ").strip()
        
        # Generate configurations
        setup.generate_configs()

        if mode == "1":
            setup.show_next_steps()
        elif mode == "2":
            setup.deploy_monitor()
        elif mode == "3":
            setup.deploy_keepalived("primary")
        elif mode == "4":
            setup.deploy_keepalived("secondary")
        elif mode == "5":
            print("\nStarting complete deployment...")
            if setup.deploy_monitor():
                if setup.deploy_keepalived("primary"):
                    if setup.deploy_keepalived("secondary"):
                        print("\nComplete setup deployed successfully!")
                    else:
                        print("\nError deploying secondary node")
                else:
                    print("\nError deploying primary node")
            else:
                print("\nError deploying monitor")
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