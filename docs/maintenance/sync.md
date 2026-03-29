# Pi-hole Sentinel - Configuration Sync Setup

## Overzicht

Deze sync oplossing zorgt ervoor dat beide Pi-hole servers altijd dezelfde configuratie hebben:
- ✅ Adlists (blocklists)
- ✅ Whitelist / Blacklist
- ✅ Regex filters
- ✅ Groups
- ✅ Client assignments
- ✅ Custom DNS records
- ✅ CNAME records
- ✅ Pi-hole settings
- ✅ DHCP static leases

**Wat wordt NIET gesynchroniseerd:**
- ❌ DHCP 'active' flag (beheerd door Keepalived)
- ❌ Query logs (historische data blijft lokaal)
- ❌ Statistics (blijven per server)

## Architectuur

```
┌─────────────────────┐         ┌─────────────────────┐
│   Primary Pi-hole   │         │  Secondary Pi-hole  │
│   (192.168.1.10)    │         │   (192.168.1.11)    │
│                     │         │                     │
│  gravity.db         │ ──────> │  gravity.db         │
│  custom.list        │  Sync   │  custom.list        │
│  pihole.toml        │ ──────> │  pihole.toml        │
│                     │         │                     │
│  [Manual Changes]   │         │  [Auto Updated]     │
└─────────────────────┘         └─────────────────────┘
```

**Sync Richting:**
- Primary → Secondary (one-way sync)
- Maak alle wijzigingen op PRIMARY
- Secondary wordt automatisch bijgewerkt

## Installatie

### Stap 1: SSH Keys Configureren

Voor automatische sync zonder wachtwoord prompts:

**Op PRIMARY (192.168.1.10):**

```bash
# Genereer SSH key als deze nog niet bestaat
if [ ! -f ~/.ssh/id_rsa ]; then
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
fi

# Kopieer key naar secondary
ssh-copy-id root@192.168.1.11

# Test verbinding
ssh root@192.168.1.11 "echo 'SSH connection successful'"
```

**Op SECONDARY (192.168.1.11):**

```bash
# Genereer SSH key
if [ ! -f ~/.ssh/id_rsa ]; then
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
fi

# Kopieer key naar primary
ssh-copy-id root@192.168.1.10

# Test verbinding
ssh root@192.168.1.10 "echo 'SSH connection successful'"
```

### Stap 2: Installeer Sync Script

The recommended approach is to use `setup.py`, which deploys the sync script,
configuration, and systemd timer automatically. For manual installation:

**Op BEIDE servers (primary en secondary):**

```bash
# Kopieer sync script
scp sync-pihole-config.sh root@192.168.1.10:/usr/local/bin/
scp sync-pihole-config.sh root@192.168.1.11:/usr/local/bin/

# Maak executable
ssh root@192.168.1.10 "chmod +x /usr/local/bin/sync-pihole-config.sh"
ssh root@192.168.1.11 "chmod +x /usr/local/bin/sync-pihole-config.sh"
```

The sync script loads IPs from `/etc/keepalived/.env` (deployed by setup.py)
or `/etc/pihole-sentinel/sync.conf`. For manual setup, create the config:

```bash
ssh root@192.168.1.10 "mkdir -p /etc/pihole-sentinel && cat > /etc/pihole-sentinel/sync.conf << 'EOF'
PRIMARY_IP=192.168.1.10
SECONDARY_IP=192.168.1.11
EOF"
```

### Stap 3: Installeer Automatische Sync (Optioneel)

Voor automatische sync elke 6 uur:

**Alleen op PRIMARY (192.168.1.10):**

```bash
# Kopieer systemd service files
scp systemd/pihole-sync.service root@192.168.1.10:/etc/systemd/system/
scp systemd/pihole-sync.timer root@192.168.1.10:/etc/systemd/system/

# Reload systemd
ssh root@192.168.1.10 "systemctl daemon-reload"

# Enable en start timer
ssh root@192.168.1.10 "systemctl enable pihole-sync.timer"
ssh root@192.168.1.10 "systemctl start pihole-sync.timer"

# Check status
ssh root@192.168.1.10 "systemctl status pihole-sync.timer"
```

### Stap 4: Eerste Sync

**Initiële synchronisatie van PRIMARY naar SECONDARY:**

```bash
# Op primary (node type is auto-detected from /etc/keepalived/.env)
ssh root@192.168.1.10
/usr/local/bin/sync-pihole-config.sh

# Or specify node type explicitly
/usr/local/bin/sync-pihole-config.sh primary
```

## Gebruik

### Handmatige Sync

**Op PRIMARY - Push configuratie naar secondary:**
```bash
/usr/local/bin/sync-pihole-config.sh
# Kies optie 1: Sync TO secondary
```

**Op SECONDARY - Pull configuratie van primary:**
```bash
/usr/local/bin/sync-pihole-config.sh
# Kies optie 1: Sync FROM primary
```

### Check Sync Status

**Vergelijk configuraties:**
```bash
# Op beide servers
/usr/local/bin/sync-pihole-config.sh --diff
```

Output voorbeeld:
```
Configuration Comparison:
=========================
Item                  Primary  Secondary
----                 -------  ---------
Adlists                   12         12
Whitelist                 45         45
Blacklist                  8          8

Configurations are IN SYNC
```

### Automatische Sync

Als je de systemd timer hebt geïnstalleerd:

**Check timer status:**
```bash
systemctl status pihole-sync.timer
```

**Check laatste sync:**
```bash
journalctl -u pihole-sync.service -n 50
```

**Forceer een sync nu:**
```bash
systemctl start pihole-sync.service
```

**Check volgende geplande sync:**
```bash
systemctl list-timers pihole-sync.timer
```

## Workflow

### Wijzigingen Aanbrengen

**Altijd wijzigingen maken op PRIMARY:**

1. **Via Web Interface:**
   - Login op http://192.168.1.10/admin
   - Maak wijzigingen (add blocklist, whitelist domain, etc.)
   - Sla op

2. **Sync naar Secondary:**
   ```bash
   # Automatisch (als timer actief is)
   # OF handmatig:
   ssh root@192.168.1.10 "/usr/local/bin/sync-pihole-config.sh --auto"
   ```

3. **Verificatie:**
   ```bash
   # Check of wijzigingen zijn overgenomen
   ssh root@192.168.1.11 "pihole -q example.com"
   ```

### Voorbeelden

**Voorbeeld 1: Nieuwe Blocklist Toevoegen**

```bash
# 1. Op primary - add via web interface of CLI
ssh root@192.168.1.10
pihole -a addlist "https://example.com/blocklist.txt"
pihole -g  # Update gravity

# 2. Sync naar secondary
/usr/local/bin/sync-pihole-config.sh --auto

# 3. Verify op secondary
ssh root@192.168.1.11
pihole -q -adlists
```

**Voorbeeld 2: Domain Whitelisten**

```bash
# 1. Op primary
ssh root@192.168.1.10
pihole -w example.com

# 2. Sync
/usr/local/bin/sync-pihole-config.sh --auto

# 3. Test op secondary
ssh root@192.168.1.11
pihole -q example.com  # Should show as whitelisted
```

**Voorbeeld 3: Custom DNS Record**

```bash
# 1. Op primary - edit /etc/pihole/custom.list
ssh root@192.168.1.10
echo "192.168.1.100 myserver.local" >> /etc/pihole/custom.list
systemctl restart pihole-FTL

# 2. Sync
/usr/local/bin/sync-pihole-config.sh --auto

# 3. Test op secondary
ssh root@192.168.1.11
dig @localhost myserver.local
```

## Backup en Restore

### Automatische Backups

Het sync script maakt automatisch backups voor elke sync:
- Locatie: `/root/pihole-sync-backup/`
- Behoudt laatste 5 backups
- Backup bevat: gravity.db, custom.list, pihole.toml

**Lijst backups:**
```bash
ls -lh /root/pihole-sync-backup/
```

### Handmatige Backup

**Create backup:**
```bash
# Via web interface: Settings → Teleporter → Backup

# Via CLI:
pihole -a -t
# Saved to: /etc/pihole/
```

### Restore van Backup

**Als sync fout gaat:**
```bash
# Automatic restore (script detecteert problemen)
# Gebeurt automatisch als Pi-hole niet start na sync

# Manual restore:
cd /root/pihole-sync-backup
tar xzf pihole-backup-YYYYMMDD-HHMMSS.tar.gz -C /
systemctl restart pihole-FTL
```

## Troubleshooting

### Sync Faalt

**Probleem:** "Cannot connect to secondary Pi-hole"

**Oplossing:**
```bash
# Test SSH connectie
ssh root@192.168.1.11 "echo OK"

# Herinstalleer SSH key
ssh-copy-id root@192.168.1.11

# Check firewall
ssh root@192.168.1.11 "iptables -L"
```

**Probleem:** "Failed to sync gravity.db"

**Oplossing:**
```bash
# Check of Pi-hole draait
ssh root@192.168.1.11 "systemctl status pihole-FTL"

# Check disk space
ssh root@192.168.1.11 "df -h"

# Check permissions
ssh root@192.168.1.11 "ls -la /etc/pihole/gravity.db"
```

### Secondary Start Niet Na Sync

**Automatische restore:**
```bash
# Script restore automatisch van laatste backup
# Check logs:
journalctl -u pihole-sync.service -n 50
```

**Handmatige restore:**
```bash
ssh root@192.168.1.11
cd /root/pihole-sync-backup
ls -lt  # Find latest backup
tar xzf pihole-backup-YYYYMMDD-HHMMSS.tar.gz -C /
systemctl restart pihole-FTL
```

### Configuraties Out of Sync

**Check verschillen:**
```bash
# Op beide servers
/usr/local/bin/sync-pihole-config.sh --diff
```

**Forceer volledige sync:**
```bash
# Op primary
/usr/local/bin/sync-pihole-config.sh --auto
```

**Als secondary volledig corrupt:**
```bash
# Stop secondary
ssh root@192.168.1.11 "systemctl stop pihole-FTL"

# Remove databases
ssh root@192.168.1.11 "rm /etc/pihole/gravity.db"

# Sync from primary
ssh root@192.168.1.10 "/usr/local/bin/sync-pihole-config.sh --auto"

# Rebuild gravity on secondary
ssh root@192.168.1.11 "pihole -g"
```

## Monitoring

### Check Sync Logs

**Laatste sync:**
```bash
journalctl -u pihole-sync.service -n 50
```

**Real-time monitoring:**
```bash
journalctl -u pihole-sync.service -f
```

**Sync geschiedenis:**
```bash
journalctl -u pihole-sync.service --since "24 hours ago"
```

### Sync Status Dashboard

Je kunt de sync status toevoegen aan je monitoring dashboard:

**Check laatste sync tijd:**
```bash
# Op primary
systemctl show pihole-sync.timer | grep LastTriggerUSec
```

**Check volgende sync:**
```bash
systemctl list-timers pihole-sync.timer
```

## Geavanceerde Configuratie

### Sync Frequentie Aanpassen

**Edit timer:**
```bash
systemctl edit pihole-sync.timer
```

**Voorbeelden:**

```ini
# Elk uur
[Timer]
OnCalendar=hourly

# Elke dag om 3:00 AM
[Timer]
OnCalendar=daily
OnCalendar=*-*-* 03:00:00

# Elke 30 minuten
[Timer]
OnCalendar=*:0/30
```

**Herlaad na wijziging:**
```bash
systemctl daemon-reload
systemctl restart pihole-sync.timer
```

### Custom Sync Items

**Edit sync script om meer/minder te syncen:**
```bash
nano /usr/local/bin/sync-pihole-config.sh
```

**Bijvoorbeeld: Ook DNS logs syncen (niet aanbevolen):**
```bash
# Add in sync_from_primary() function:
rsync -avz --progress "root@${PRIMARY_IP}:${PIHOLE_DIR}/pihole-FTL.db" "${PIHOLE_DIR}/"
```

### Sync Notificaties

**Email notificatie bij sync problemen:**
```bash
# Installeer mail tools
apt install mailutils

# Edit service file:
systemctl edit pihole-sync.service
```

```ini
[Service]
OnFailure=notify-email@%n.service
```

## Best Practices

### Do's ✅

1. **Altijd wijzigingen op PRIMARY maken**
2. **Test sync eerst handmatig** voordat je timer activeert
3. **Monitor sync logs** regelmatig
4. **Backup before major changes**
5. **Test failover na sync wijzigingen**
6. **Documenteer custom configuraties**

### Don'ts ❌

1. **Nooit wijzigingen op SECONDARY maken** (worden overschreven)
2. **Geen DHCP via sync** (moet lokaal beheerd worden)
3. **Geen sync tijdens Pi-hole updates** (kan conflicts geven)
4. **Niet te frequent syncen** (verhoogt load)

## Maintenance

### Wekelijks

- Check sync logs voor errors
- Verify configuraties zijn in sync
- Test handmatige failover

### Maandelijks

- Review backup disk usage
- Clean old backups if needed
- Update sync script als nieuwe versie beschikbaar

### Bij Updates

**Voor Pi-hole update:**
```bash
# 1. Stop automatische sync
systemctl stop pihole-sync.timer

# 2. Update beide servers
ssh root@192.168.1.10 "pihole -up"
ssh root@192.168.1.11 "pihole -up"

# 3. Manual sync test
ssh root@192.168.1.10 "/usr/local/bin/sync-pihole-config.sh --auto"

# 4. Re-enable timer
systemctl start pihole-sync.timer
```

## Integration met Monitor Dashboard

De monitor kan sync status ook tonen. Voeg toe aan `monitor.py`:

```python
async def check_sync_status():
    """Check if Pi-holes are in sync"""
    # Compare adlist counts
    primary_count = await query_db(PRIMARY_IP, "SELECT COUNT(*) FROM adlist")
    secondary_count = await query_db(SECONDARY_IP, "SELECT COUNT(*) FROM adlist")
    
    return {
        "in_sync": primary_count == secondary_count,
        "primary_count": primary_count,
        "secondary_count": secondary_count
    }
```

## Support

Voor problemen met sync:

1. Check `/root/pihole-sync-backup/` voor backups
2. Review `journalctl -u pihole-sync.service`
3. Test SSH connectie tussen servers
4. Verify disk space en permissions
5. Restore van backup indien nodig

## Conclusie

Met deze sync setup:
- ✅ Beide Pi-holes hebben altijd dezelfde configuratie
- ✅ Wijzigingen hoef je maar 1x te maken
- ✅ Automatische backup voor elke sync
- ✅ Eenvoudig te monitoren
- ✅ Betrouwbare configuratie management

**Geniet van je gesynchroniseerde Pi-hole HA setup!** 🚀
