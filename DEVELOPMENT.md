# Development Guide

## Python Environment Setup

### Python 3.13+ (Externally Managed Environment)

Since Debian 13/Python 3.13+, the system Python is externally managed and doesn't allow direct `pip install`. This is a security feature (PEP 668).

### Development Setup

**Voor development/testing gebruik een virtual environment:**

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r dashboard/requirements.txt

# When done developing, deactivate
deactivate
```

**Belangrijke commando's:**

```bash
# Activeer altijd de venv voor development:
source venv/bin/activate

# Test de monitor service:
cd dashboard
python monitor.py

# Run setup.py (alleen voor testen van setup flow):
python ../setup.py --help
```

### Production Deployment

**Voor production gebruik het setup.py script:**

Het setup.py script maakt automatisch een isolated virtual environment aan in `/opt/pihole-monitor/venv/` en installeert alle dependencies daarin. Je hoeft NIETS handmatig te installeren.

```bash
# Production setup (creates venv automatically)
sudo python3 setup.py
```

Het setup script:

- Maakt `/opt/pihole-monitor/venv/` aan
- Installeert alle dependencies in die venv
- Configureert systemd services om de venv te gebruiken
- Installeert system packages (keepalived, arping, etc.)

## Common Issues

### ❌ Error: externally-managed-environment

**Probleem:**

```text
error: externally-managed-environment
× This environment is externally managed
```

**Oplossing:**

```bash
# Gebruik NOOIT --break-system-packages
# Maak in plaats daarvan een venv:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### ❌ Import errors tijdens development

**Probleem:**

```python
ModuleNotFoundError: No module named 'fastapi'
```

**Oplossing:**

```bash
# Check of venv actief is:
which python
# Should show: /home/jochem/pihole-sentinel/venv/bin/python

# Zo niet, activeer:
source venv/bin/activate
```

### ✅ Verify Installation

```bash
source venv/bin/activate
python -c "import fastapi, uvicorn, aiohttp; print('✓ All imports OK')"
```

## Testing Changes

### Test Monitor Service

```bash
source venv/bin/activate
cd dashboard

# Create test .env file if needed
cat > .env << EOF
PIHOLE1_IP=192.168.1.10
PIHOLE2_IP=192.168.1.11
VIP=192.168.1.5
DATABASE_PATH=/tmp/test.db
EOF

# Run monitor
python monitor.py
# Access at http://localhost:8000
```

### Test Setup Script (Dry Run)

```bash
source venv/bin/activate

# Test config validation
python setup.py --help

# Note: Full setup requires sudo and modifies system
```

### Run Syntax Checks

```bash
# Python files
python3 -m py_compile dashboard/monitor.py
python3 -m py_compile setup.py

# Shell scripts
bash -n sync-pihole-config.sh
bash -n keepalived/scripts/*.sh
```

## Project Structure

```text
pihole-sentinel/
├── venv/                    # Virtual environment (gitignored)
├── dashboard/
│   ├── monitor.py          # FastAPI monitoring service
│   ├── requirements.txt    # Dashboard dependencies
│   └── *.html              # Web interface
├── keepalived/
│   ├── scripts/            # Health check scripts
│   └── pihole*/            # Keepalived configs per node
├── systemd/                # Service files
├── setup.py                # Production deployment script
├── sync-pihole-config.sh   # Config synchronization
└── requirements.txt        # Main Python dependencies
```

## Version Information

- **Current Version:** 0.8.0
- **Python:** 3.8+ (tested with 3.13)
- **OS:** Debian 11+/Ubuntu 20.04+

## Contributing

1. Make changes in a virtual environment
2. Test thoroughly
3. Update CHANGELOG.md
4. Bump VERSION if needed
5. Test production deployment in staging

## Useful Commands

```bash
# Activate venv
source venv/bin/activate

# Check installed packages
pip list

# Update dependencies
pip install --upgrade -r requirements.txt

# Freeze current versions
pip freeze > requirements-freeze.txt

# Deactivate venv
deactivate
```

## Documentation

- [README.md](README.md) - Project overview
- [EXISTING-SETUP.md](EXISTING-SETUP.md) - Existing Pi-hole HA setup
- [SYNC-SETUP.md](SYNC-SETUP.md) - Sync configuration guide
- [CHANGELOG.md](CHANGELOG.md) - Version history
