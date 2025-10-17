#!/usr/bin/env python3
"""Test script to preview the colored output"""

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

# ASCII art logo
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

print(LOGO)

print(f"""
{Colors.GREEN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                     ✓ DEPLOYMENT COMPLETED SUCCESSFULLY!                     ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
{Colors.END}

{Colors.CYAN}{Colors.BOLD}📊 Access Your Monitor Dashboard:{Colors.END}
   {Colors.BOLD}→ http://10.10.100.99:8080{Colors.END}

{Colors.CYAN}{Colors.BOLD}🔍 Quick Status Check Commands:{Colors.END}

   {Colors.YELLOW}On Monitor Server (10.10.100.99):{Colors.END}
   {Colors.CYAN}systemctl status pihole-monitor{Colors.END}
   {Colors.CYAN}journalctl -u pihole-monitor -f{Colors.END}

{Colors.GREEN}{Colors.BOLD}🎉 Your Pi-hole High Availability setup is ready!{Colors.END}
""")
