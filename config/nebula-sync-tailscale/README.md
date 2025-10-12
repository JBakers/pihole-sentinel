# Nebula/Tailscale Server

Deze server draait Nebula/Tailscale voor VPN connectiviteit en bevat de volgende diensten:

## Diensten

### Pi-hole Monitor
Zie `pihole-monitor/` voor de monitoring service van de Pi-hole high-availability setup:
- Monitoring van beide Pi-hole instances
- Keepalived failover detectie
- Web interface voor status en geschiedenis
- Event logging

## Configuratie
- Nebula/Tailscale configuratie
- Keepalived monitoring setup
- Network monitoring tools

## Scripts
Monitoring en management scripts in `monitoring\pihole-ha`

## Documentatie
Zie de README's in de specifieke service mappen voor meer details.