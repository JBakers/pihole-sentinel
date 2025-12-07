import time

# =============================================================================
# Command Execution API (System Commands)
# =============================================================================

# Command whitelist - only these commands can be executed
COMMANDS_WHITELIST = {
    'monitor_status': {
        'cmd': ['systemctl', 'status', 'pihole-monitor', '--no-pager', '--lines=20'],
        'description': 'Monitor Service Status',
        'icon': '📊',
    },
    'monitor_logs': {
        'cmd': ['journalctl', '-u', 'pihole-monitor', '-n', '50', '--no-pager'],
        'description': 'Monitor Logs (last 50 lines)',
        'icon': '📄',
    },
    'keepalived_status': {
        'cmd': ['systemctl', 'status', 'keepalived', '--no-pager', '--lines=20'],
        'description': 'Keepalived Service Status',
        'icon': '🔄',
    },
    'keepalived_logs': {
        'cmd': ['journalctl', '-u', 'keepalived', '-n', '50', '--no-pager'],
        'description': 'Keepalived Logs (last 50 lines)',
        'icon': '📜',
    },
    'vip_check': {
        'cmd': ['ip', 'addr', 'show'],
        'description': 'Network Interfaces (VIP Check)',
        'icon': '🌐',
    },
    'db_recent_events': {
        'cmd': ['sqlite3', CONFIG["db_path"],
                'SELECT timestamp, event_type, message FROM events ORDER BY timestamp DESC LIMIT 20'],
        'description': 'Recent Database Events',
        'icon': '📊',
    },
}

# Rate limiting voor command execution
command_rate_limit_store = defaultdict(list)
COMMAND_RATE_LIMIT_REQUESTS = 5  # Max 5 commands
COMMAND_RATE_LIMIT_WINDOW = 60   # Per 60 seconds

async def command_rate_limit_check(request: Request):
    """Rate limit command execution to prevent spam"""
    client_ip = request.client.host
    now = time.time()

    # Remove old entries
    command_rate_limit_store[client_ip] = [
        timestamp for timestamp in command_rate_limit_store[client_ip]
        if now - timestamp < COMMAND_RATE_LIMIT_WINDOW
    ]

    # Check limit
    if len(command_rate_limit_store[client_ip]) >= COMMAND_RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {COMMAND_RATE_LIMIT_REQUESTS} commands per {COMMAND_RATE_LIMIT_WINDOW}s"
        )

    # Add current timestamp
    command_rate_limit_store[client_ip].append(now)
    return True

@app.get("/api/commands")
async def list_commands(api_key: str = Depends(verify_api_key)):
    """List available system commands"""
    return {
        "commands": {
            name: {
                "description": info['description'],
                "icon": info['icon']
            }
            for name, info in COMMANDS_WHITELIST.items()
        }
    }

@app.post("/api/commands/{command_name}")
async def execute_command(
    command_name: str,
    api_key: str = Depends(verify_api_key),
    _rate_limit: bool = Depends(command_rate_limit_check)
):
    """Execute a whitelisted system command"""
    if command_name not in COMMANDS_WHITELIST:
        raise HTTPException(
            status_code=400,
            detail=f"Command '{command_name}' not whitelisted. Use /api/commands to see available commands."
        )

    cmd_info = COMMANDS_WHITELIST[command_name]
    cmd = cmd_info['cmd']

    try:
        # Execute command with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )

        logger.info(f"Command executed: {command_name} (exit code: {result.returncode})")

        return {
            "status": "success" if result.returncode == 0 else "error",
            "command": command_name,
            "description": cmd_info['description'],
            "icon": cmd_info['icon'],
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "exit_code": result.returncode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except subprocess.TimeoutExpired:
        logger.warning(f"Command timeout: {command_name}")
        return {
            "status": "error",
            "command": command_name,
            "error": "Command execution timed out (10s limit)",
            "exit_code": 124,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Command execution failed: {command_name}", exc_info=True)
        return {
            "status": "error",
            "command": command_name,
            "error": str(e),
            "exit_code": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
#!/usr/bin/env python3
"""
Pi-hole Keepalived Monitor - Simple Standalone Version
No SSH required, simple API calls
"""

import os
import sys
import asyncio
import aiohttp
import aiosqlite
import uvicorn
import subprocess
import socket
import copy
import logging
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Dict
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import secrets

# Configure logging with rotation
from logging.handlers import RotatingFileHandler

handlers: list[logging.Handler] = [logging.StreamHandler()]
try:
    if os.path.exists('/var/log'):
        # Rotating file handler: 10MB per file, keep 5 backup files
        rotating_handler = RotatingFileHandler(
            '/var/log/pihole-monitor.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        handlers.append(rotating_handler)
except (PermissionError, OSError):
    pass  # Fall back to console-only logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration from environment
CONFIG = {
    "primary": {
        "ip": os.getenv("PRIMARY_IP"),
        "name": os.getenv("PRIMARY_NAME", "Primary Pi-hole"),
        "password": os.getenv("PRIMARY_PASSWORD")
    },
    "secondary": {
        "ip": os.getenv("SECONDARY_IP"),
        "name": os.getenv("SECONDARY_NAME", "Secondary Pi-hole"),
        "password": os.getenv("SECONDARY_PASSWORD")
    },
    "vip": os.getenv("VIP_ADDRESS"),
    "check_interval": int(os.getenv("CHECK_INTERVAL", "10")),
    "db_path": os.getenv("DB_PATH", "/opt/pihole-monitor/monitor.db"),
    "notify_config_path": os.getenv("NOTIFY_CONFIG_PATH", "/opt/pihole-monitor/notify_settings.json"),
    "api_key": os.getenv("API_KEY")
}

# Generate API key if not set (for backward compatibility during transition)
if not CONFIG["api_key"]:
    # Generate a secure random API key
    CONFIG["api_key"] = secrets.token_urlsafe(32)
    logger.warning("=" * 80)
    logger.warning("NO API_KEY FOUND - GENERATED TEMPORARY KEY FOR THIS SESSION")
    logger.warning(f"API Key: {CONFIG['api_key']}")
    logger.warning("Add this to your .env file: API_KEY=" + CONFIG['api_key'])
    logger.warning("=" * 80)

# Verify required environment variables
required_vars = ["PRIMARY_IP", "PRIMARY_PASSWORD", "SECONDARY_IP", "SECONDARY_PASSWORD", "VIP_ADDRESS"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    await init_db()
    await get_http_session()
    await log_event("info", "Monitor started")
    asyncio.create_task(monitor_loop())
    asyncio.create_task(daily_cleanup_loop())
    logger.info("Pi-hole Sentinel Monitor started")

    yield

    # Shutdown
    await close_http_session()
    logger.info("Monitor stopped, HTTP session closed")

app = FastAPI(title="Pi-hole Keepalived Monitor", lifespan=lifespan)

# Security: API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key for protected endpoints."""
    if api_key != CONFIG["api_key"]:
        logger.warning(f"Invalid API key attempt from client")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    return api_key

# Rate limiting for notification test endpoint
# Stores {ip_address: [timestamp1, timestamp2, ...]}
rate_limit_store = defaultdict(list)
RATE_LIMIT_REQUESTS = 3  # Max 3 requests
RATE_LIMIT_WINDOW = 60  # Per 60 seconds

async def rate_limit_check(request: Request):
    """Rate limiting: max 3 requests per 60 seconds per IP."""
    client_ip = request.client.host if request.client else "unknown"
    now = datetime.now()

    # Clean old entries
    rate_limit_store[client_ip] = [
        ts for ts in rate_limit_store[client_ip]
        if now - ts < timedelta(seconds=RATE_LIMIT_WINDOW)
    ]

    # Check rate limit
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        logger.warning(f"Rate limit exceeded for {client_ip}")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds."
        )

    # Add current request
    rate_limit_store[client_ip].append(now)
    return True

# Global aiohttp ClientSession for connection pooling
# Reusing sessions improves performance and prevents connection exhaustion
http_session: aiohttp.ClientSession | None = None

async def get_http_session() -> aiohttp.ClientSession:
    """Get or create global HTTP session for connection pooling."""
    global http_session
    if http_session is None or http_session.closed:
        # Create session with connection pooling and timeouts
        timeout = aiohttp.ClientTimeout(total=10)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
        http_session = aiohttp.ClientSession(timeout=timeout, connector=connector)
    return http_session

async def close_http_session():
    """Close global HTTP session on shutdown."""
    global http_session
    if http_session and not http_session.closed:
        await http_session.close()

# Track notification state for repeat/reminder functionality
notification_state = {
    "last_notification_time": {},  # {event_type: datetime}
    "active_issues": {},  # {event_type: bool} - is issue still active?
}

def is_snoozed(settings: dict) -> bool:
    """Check if notifications are currently snoozed."""
    snooze = settings.get('snooze', {})
    if not snooze.get('enabled', False):
        return False
    
    until_str = snooze.get('until')
    if not until_str:
        return False
    
    try:
        until = datetime.fromisoformat(until_str.replace('Z', '+00:00'))
        # Handle timezone-naive comparison
        if until.tzinfo:
            until = until.replace(tzinfo=None)
        return datetime.now() < until
    except (ValueError, TypeError):
        return False

def should_send_reminder(event_type: str, settings: dict) -> bool:
    """Check if a reminder notification should be sent based on repeat settings."""
    repeat = settings.get('repeat', {})
    if not repeat.get('enabled', False):
        return False
    
    interval_minutes = repeat.get('interval', 0)
    if interval_minutes <= 0:
        return False
    
    # Check if issue is still active
    if not notification_state["active_issues"].get(event_type, False):
        return False
    
    # Check if enough time has passed since last notification
    last_time = notification_state["last_notification_time"].get(event_type)
    if not last_time:
        return False
    
    elapsed = datetime.now() - last_time
    return elapsed >= timedelta(minutes=interval_minutes)

async def send_notification(event_type: str, template_vars: dict, is_reminder: bool = False):
    """Send notification via configured services using custom templates"""
    import json

    config_path = CONFIG["notify_config_path"]

    if not os.path.exists(config_path):
        logger.debug(f"Notification config not found: {config_path}")
        return

    # Load notification settings from JSON
    try:
        with open(config_path, 'r') as f:
            settings = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read notification settings: {e}")
        await log_event("warning", f"⚠️ Failed to load notification settings: {e}")
        return

    # Check if notifications are snoozed
    if is_snoozed(settings):
        logger.debug(f"Notification snoozed, skipping {event_type}")
        return

    # Check if event type is enabled
    events_config = settings.get('events', {})
    if not events_config.get(event_type, True):
        logger.debug(f"Event type {event_type} is disabled in settings")
        return

    # Load template and substitute variables
    templates = settings.get('templates', {})
    template = templates.get(event_type, "")

    if not template:
        # Fallback to default template if not found
        template = f"Pi-hole Sentinel Alert: {event_type}"

    try:
        message = template.format(**template_vars)
        # Add reminder prefix if this is a repeat notification
        if is_reminder:
            message = f"🔔 REMINDER:\n{message}"
    except KeyError as e:
        logger.error(f"Template variable missing: {e}")
        await log_event("warning", f"⚠️ Notification template error: missing variable {e}")
        return

    # Track if any notification was sent
    sent_count = 0
    failed_services = []

    # Send Telegram notification
    if settings.get('telegram', {}).get('enabled'):
        telegram_token = settings['telegram'].get('bot_token')
        telegram_chat = settings['telegram'].get('chat_id')

        if telegram_token and telegram_chat:
            try:
                session = await get_http_session()
                url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                payload = {
                    "chat_id": telegram_chat,
                    "text": message,
                    "parse_mode": "HTML"
                }
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        logger.info(f"Telegram notification sent: {event_type}")
                        sent_count += 1
                    else:
                        logger.warning(f"Telegram notification failed: HTTP {resp.status}")
                        failed_services.append(f"Telegram (HTTP {resp.status})")
            except Exception as e:
                logger.error(f"Failed to send Telegram notification: {e}")
                failed_services.append(f"Telegram ({type(e).__name__})")

    # Send Discord notification
    if settings.get('discord', {}).get('enabled'):
        webhook_url = settings['discord'].get('webhook_url')

        if webhook_url:
            try:
                session = await get_http_session()
                # Convert HTML formatting to Discord markdown
                discord_message = message.replace('<b>', '**').replace('</b>', '**')
                payload = {
                    "content": discord_message
                }
                async with session.post(webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status in [200, 204]:
                        logger.info(f"Discord notification sent: {event_type}")
                        sent_count += 1
                    else:
                        logger.warning(f"Discord notification failed: HTTP {resp.status}")
                        failed_services.append(f"Discord (HTTP {resp.status})")
            except Exception as e:
                logger.error(f"Failed to send Discord notification: {e}")
                failed_services.append(f"Discord ({type(e).__name__})")

    # Send Pushover notification
    if settings.get('pushover', {}).get('enabled'):
        user_key = settings['pushover'].get('user_key')
        app_token = settings['pushover'].get('app_token')

        if user_key and app_token:
            try:
                session = await get_http_session()
                # Remove HTML tags for Pushover
                pushover_message = message.replace('<b>', '').replace('</b>', '')
                async with session.post('https://api.pushover.net/1/messages.json', data={
                    'token': app_token,
                    'user': user_key,
                    'title': 'Pi-hole Sentinel',
                    'message': pushover_message
                }, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        logger.info(f"Pushover notification sent: {event_type}")
                        sent_count += 1
                    else:
                        logger.warning(f"Pushover notification failed: HTTP {resp.status}")
                        failed_services.append(f"Pushover (HTTP {resp.status})")
            except Exception as e:
                logger.error(f"Failed to send Pushover notification: {e}")
                failed_services.append(f"Pushover ({type(e).__name__})")

    # Send Ntfy notification
    if settings.get('ntfy', {}).get('enabled'):
        topic = settings['ntfy'].get('topic')
        server = settings['ntfy'].get('server', 'https://ntfy.sh')

        if topic:
            try:
                session = await get_http_session()
                url = f"{server}/{topic}"
                # Remove HTML tags for Ntfy
                ntfy_message = message.replace('<b>', '').replace('</b>', '')
                async with session.post(url, data=ntfy_message.encode('utf-8'), headers={
                    'Title': 'Pi-hole Sentinel',
                    'Priority': 'default'
                }, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        logger.info(f"Ntfy notification sent: {event_type}")
                        sent_count += 1
                    else:
                        logger.warning(f"Ntfy notification failed: HTTP {resp.status}")
                        failed_services.append(f"Ntfy (HTTP {resp.status})")
            except Exception as e:
                logger.error(f"Failed to send Ntfy notification: {e}")
                failed_services.append(f"Ntfy ({type(e).__name__})")

    # Send custom webhook notification
    if settings.get('webhook', {}).get('enabled'):
        webhook_url = settings['webhook'].get('url')

        if webhook_url:
            try:
                session = await get_http_session()
                payload = {
                    'service': 'pihole-sentinel',
                    'event_type': event_type,
                    'message': message,
                    'variables': template_vars,
                    'timestamp': datetime.now().isoformat()
                }
                async with session.post(webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status in [200, 201, 202, 204]:
                        logger.info(f"Webhook notification sent: {event_type}")
                        sent_count += 1
                    else:
                        logger.warning(f"Webhook notification failed: HTTP {resp.status}")
                        failed_services.append(f"Webhook (HTTP {resp.status})")
            except Exception as e:
                logger.error(f"Failed to send Webhook notification: {e}")
                failed_services.append(f"Webhook ({type(e).__name__})")

    # Log notification status
    if sent_count > 0:
        await log_event("notification", f"✉️ Notification sent: {event_type}{' (reminder)' if is_reminder else ''} ({sent_count} service{'s' if sent_count > 1 else ''})")
        # Track last notification time for repeat/reminder functionality
        notification_state["last_notification_time"][event_type] = datetime.now()

    if failed_services:
        await log_event("warning", f"⚠️ Notification failed for: {', '.join(failed_services)}")

async def check_and_send_reminders():
    """Check if any reminder notifications should be sent for active issues."""
    import json
    
    config_path = CONFIG["notify_config_path"]
    if not os.path.exists(config_path):
        return
    
    try:
        with open(config_path, 'r') as f:
            settings = json.load(f)
    except Exception:
        return
    
    # Check repeat settings
    repeat = settings.get('repeat', {})
    if not repeat.get('enabled', False) or repeat.get('interval', 0) <= 0:
        return
    
    # Check each active issue type
    for event_type in ['failover', 'fault']:
        if should_send_reminder(event_type, settings):
            # Build template vars for reminder
            template_vars = {
                "node_name": "Unknown",
                "node": "Unknown",
                "master": CONFIG.get('secondary', {}).get('name', 'Secondary-Pi-hole'),
                "backup": CONFIG.get('primary', {}).get('name', 'Primary-Pi-hole'),
                "primary": CONFIG.get('primary', {}).get('name', 'Primary-Pi-hole'),
                "secondary": CONFIG.get('secondary', {}).get('name', 'Secondary-Pi-hole'),
                "reason": "Issue still active",
                "vip_address": CONFIG.get('vip', ''),
                "vip": CONFIG.get('vip', ''),
                "time": datetime.now().strftime("%H:%M:%S"),
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            await send_notification(event_type, template_vars, is_reminder=True)
            logger.info(f"Sent reminder notification for {event_type}")

# CORS middleware - restricted to localhost for security
# If you need remote access, add specific origins here
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        # Add your monitor server IP here if accessing remotely
        # "http://your-monitor-ip:8080"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# Serve HTML files
@app.get("/")
async def serve_index():
    return FileResponse("index.html")

@app.get("/settings.html")
async def serve_settings():
    return FileResponse("settings.html")

@app.get("/api/version")
async def get_version():
    """Get current Pi-hole Sentinel version from VERSION file"""
    try:
        # Check multiple locations for VERSION file
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "VERSION"),      # Same dir as monitor.py
            os.path.join(os.path.dirname(__file__), "..", "VERSION"), # Parent dir (dev)
            "/opt/pihole-monitor/VERSION",                            # Production location
            "/opt/VERSION",                                           # Legacy location
        ]
        
        for version_file in possible_paths:
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    version = f.read().strip()
                    if version:
                        return {"version": version}
        
        # Fallback if VERSION file not found
        return {"version": "0.11.0"}
    except Exception as e:
        logger.error(f"Failed to read VERSION file: {e}")
        return {"version": "unknown"}


# Cache for update checks (avoid spamming GitHub API)
_update_cache = {
    "last_check": None,
    "latest_version": None,
    "release_url": None,
    "check_interval": 6 * 60 * 60  # 6 hours in seconds
}

@app.get("/api/check-update")
async def check_for_updates(api_key: str = Security(verify_api_key)):
    """Check GitHub for available updates.
    
    Returns cached result if checked within last 6 hours.
    """
    global _update_cache
    
    now = datetime.now()
    
    # Return cached result if recent
    if (_update_cache["last_check"] and 
        (now - _update_cache["last_check"]).total_seconds() < _update_cache["check_interval"] and
        _update_cache["latest_version"]):
        
        current = (await get_version())["version"]
        return {
            "current_version": current,
            "latest_version": _update_cache["latest_version"],
            "update_available": _is_newer_version(_update_cache["latest_version"], current),
            "release_url": _update_cache["release_url"],
            "cached": True
        }
    
    try:
        session = await get_http_session()
        github_url = "https://api.github.com/repos/JBakers/pihole-sentinel/releases/latest"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PiholeSentinel-UpdateChecker"
        }
        
        async with session.get(github_url, headers=headers, timeout=10) as resp:
            if resp.status == 404:
                # No releases yet
                return {
                    "current_version": (await get_version())["version"],
                    "latest_version": None,
                    "update_available": False,
                    "message": "No releases found"
                }
            
            if resp.status == 403:
                # Rate limited - return cached or unknown
                return {
                    "current_version": (await get_version())["version"],
                    "latest_version": _update_cache.get("latest_version"),
                    "update_available": False,
                    "message": "GitHub API rate limited"
                }
            
            if resp.status != 200:
                return {
                    "current_version": (await get_version())["version"],
                    "update_available": False,
                    "error": f"GitHub API returned {resp.status}"
                }
            
            data = await resp.json()
        
        # Parse release info
        latest = data.get("tag_name", "").lstrip("v")
        release_url = data.get("html_url", "")
        
        # Update cache
        _update_cache["last_check"] = now
        _update_cache["latest_version"] = latest
        _update_cache["release_url"] = release_url
        
        current = (await get_version())["version"]
        
        return {
            "current_version": current,
            "latest_version": latest,
            "update_available": _is_newer_version(latest, current),
            "release_url": release_url,
            "cached": False
        }
        
    except asyncio.TimeoutError:
        logger.warning("Timeout checking for updates")
        return {
            "current_version": (await get_version())["version"],
            "update_available": False,
            "error": "Timeout connecting to GitHub"
        }
    except Exception as e:
        logger.error(f"Failed to check for updates: {e}")
        return {
            "current_version": (await get_version())["version"],
            "update_available": False,
            "error": str(e)
        }


def _is_newer_version(latest: str, current: str) -> bool:
    """Compare versions to check if update is available.
    
    Handles semantic versioning including pre-release tags like:
    - 0.11.0, 0.11.0-beta.4, 1.0.0-rc.1
    """
    if not latest or not current or current == "unknown":
        return False
    
    try:
        # Clean version strings
        latest_clean = latest.lstrip("v").strip()
        current_clean = current.lstrip("v").strip()
        
        # Simple version comparison using packaging library if available
        try:
            from packaging import version as pkg_version
            return pkg_version.parse(latest_clean) > pkg_version.parse(current_clean)
        except ImportError:
            # Fallback: basic comparison
            return latest_clean != current_clean and latest_clean > current_clean
    except Exception as e:
        logger.warning(f"Version comparison failed: {e}")
        return False


async def init_db():
    """Initialize SQLite database"""
    async with aiosqlite.connect(CONFIG["db_path"]) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                primary_state TEXT,
                secondary_state TEXT,
                primary_has_vip BOOLEAN,
                secondary_has_vip BOOLEAN,
                primary_online BOOLEAN,
                secondary_online BOOLEAN,
                primary_pihole BOOLEAN,
                secondary_pihole BOOLEAN,
                primary_dns BOOLEAN,
                secondary_dns BOOLEAN,
                dhcp_leases INTEGER,
                primary_dhcp BOOLEAN,
                secondary_dhcp BOOLEAN
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT,
                message TEXT
            )
        """)

        # Create indexes for better query performance
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_status_timestamp
            ON status_history(timestamp DESC)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp
            ON events(timestamp DESC)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type
            ON events(event_type, timestamp DESC)
        """)

        await db.commit()

async def cleanup_old_data():
    """Remove old status history and events to prevent database growth."""
    retention_days_history = int(os.getenv('RETENTION_DAYS_HISTORY', '30'))
    retention_days_events = int(os.getenv('RETENTION_DAYS_EVENTS', '90'))

    cutoff_history = datetime.now() - timedelta(days=retention_days_history)
    cutoff_events = datetime.now() - timedelta(days=retention_days_events)

    try:
        async with aiosqlite.connect(CONFIG["db_path"]) as db:
            # Delete old status_history records
            cursor_history = await db.execute(
                "DELETE FROM status_history WHERE timestamp < ?",
                (cutoff_history.isoformat(),)
            )

            # Delete old events
            cursor_events = await db.execute(
                "DELETE FROM events WHERE timestamp < ?",
                (cutoff_events.isoformat(),)
            )

            await db.commit()

            # Get row counts (SQLite doesn't return rowcount reliably, so we log what we attempted)
            logger.info(
                f"Database cleanup completed: "
                f"removed status_history older than {retention_days_history} days, "
                f"removed events older than {retention_days_events} days"
            )
    except Exception as e:
        logger.error(f"Database cleanup failed: {e}", exc_info=True)

async def daily_cleanup_loop():
    """Run database cleanup once per day."""
    while True:
        try:
            # Run cleanup immediately on startup
            await cleanup_old_data()

            # Then wait 24 hours before next cleanup
            await asyncio.sleep(24 * 60 * 60)  # 24 hours
        except asyncio.CancelledError:
            logger.info("Daily cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in daily cleanup loop: {e}", exc_info=True)
            # Wait 1 hour before retrying on error
            await asyncio.sleep(60 * 60)

async def check_pihole_simple(ip: str, password: str) -> Dict:
    """Simple Pi-hole check - uses global session pool for better performance."""
    result = {
        "online": False,
        "pihole": False,
        "queries": 0,
        "blocked": 0,
        "clients": 0,
        "dhcp_leases": 0,
        "dhcp_enabled": False
    }

    # Use TCP socket connection test instead of ping to avoid capability issues
    # Use context manager to prevent file descriptor leaks
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            result["online"] = sock.connect_ex((ip, 80)) == 0
    except Exception as e:
        logger.warning(f"Connection check error for {ip}: {e}")
        return result

    if not result["online"]:
        return result

    try:
        # Use global session pool instead of creating new session each time
        session = await get_http_session()
        sid = None

        try:
            async with session.post(f"http://{ip}/api/auth", json={"password": password}, timeout=aiohttp.ClientTimeout(total=10)) as auth_resp:
                if auth_resp.status == 200:
                    auth_data = await auth_resp.json()
                    # Pi-hole v6 returns sid within a session object
                    session_data = auth_data.get("session", {})
                    sid = session_data.get("sid")
        except Exception as e:
            logger.warning(f"FTL Auth exception for {ip}: {e.__class__.__name__}: {e}")
            return result

        if not sid:
            logger.warning(f"Could not get session ID for {ip}. Check password.")
            return result

        headers = {"X-FTL-SID": sid}

        try:
            async with session.get(f"http://{ip}/api/stats/summary", headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as stats_resp:
                if stats_resp.status == 200:
                    stats = await stats_resp.json()
                    result["pihole"] = True
                    result["queries"] = stats.get("dns_queries_today", 0)
                    result["blocked"] = stats.get("ads_blocked_today", 0)
                    result["clients"] = stats.get("unique_clients", 0)
        except Exception:
            result["pihole"] = False

        if result["pihole"]:
            # Check DHCP configuration via config API
            try:
                async with session.get(f"http://{ip}/api/config/dhcp", headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as dhcp_resp:
                    if dhcp_resp.status == 200:
                        dhcp_config = await dhcp_resp.json()
                        result["dhcp_enabled"] = dhcp_config.get("config", {}).get("dhcp", {}).get("active", False)
                        logger.debug(f"DHCP for {ip}: active={result['dhcp_enabled']}")
                    else:
                        result["dhcp_enabled"] = False
                        logger.debug(f"DHCP config API returned status {dhcp_resp.status} for {ip}")
            except Exception as e:
                logger.debug(f"DHCP config check exception for {ip}: {e}")
                result["dhcp_enabled"] = False

            # Check DHCP leases count
            # Pi-hole v6 API - use content_type=None to accept any content-type header
            try:
                async with session.get(f"http://{ip}/api/dhcp/leases", headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as leases_resp:
                    if leases_resp.status == 200:
                        leases_data = await leases_resp.json(content_type=None)
                        # Get leases list, default to empty list if None or missing
                        all_leases = leases_data.get("leases", [])
                        if all_leases is None:
                            all_leases = []
                        result["dhcp_leases"] = len(all_leases)
                        logger.debug(f"DHCP leases count for {ip}: {result['dhcp_leases']}")
                    else:
                        logger.warning(f"DHCP leases API returned status {leases_resp.status} for {ip}")
                        result["dhcp_leases"] = 0
            except Exception as e:
                logger.debug(f"DHCP leases check exception for {ip}: {e}")
                result["dhcp_leases"] = 0

        # Logout from Pi-hole API
        try:
            await session.delete(f"http://{ip}/api/auth", headers=headers, timeout=aiohttp.ClientTimeout(total=2))
        except Exception:
            # Logout is non-critical, ignore failures
            pass
    except Exception as e:
        logger.warning(f"Main session exception for {ip}: {e}")
    
    return result

async def check_dns(ip: str) -> bool:
    """Check if DNS resolver is working by doing actual query.

    Uses asyncio subprocess to avoid blocking the event loop.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "/usr/bin/dig", "+short", "+time=2", f"@{ip}", "google.com",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
        return proc.returncode == 0 and len(stdout.decode().strip()) > 0
    except asyncio.TimeoutError:
        logger.debug(f"DNS check timeout for {ip}")
        return False
    except Exception as e:
        logger.debug(f"DNS check error for {ip}: {e}")
        return False

async def check_who_has_vip(vip: str, primary_ip: str, secondary_ip: str, max_retries: int = 3) -> tuple:
    """
    Check which Pi-hole has the VIP by comparing MAC addresses.
    Connect to VIP and both servers, then compare which server's MAC matches the VIP's MAC.
    Includes retry logic for reliability.
    """
    for attempt in range(max_retries):
        try:
            # Get MAC address by checking ARP table after making connections
            # First connect to each IP to ensure ARP entries exist
            # Use context manager to prevent file descriptor leaks
            for ip in [vip, primary_ip, secondary_ip]:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.settimeout(1)
                        sock.connect_ex((ip, 80))
                except (OSError, socket.error):
                    # Socket errors are expected for unreachable hosts
                    pass
            
            # Small delay for ARP table to populate
            await asyncio.sleep(0.2)
            
            # Read ARP table entries using async subprocess
            async def get_arp_entry(ip_addr: str) -> str:
                """Get ARP entry for IP address using async subprocess."""
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "/usr/sbin/ip", "neigh", "show", ip_addr,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=2)
                    return stdout.decode()
                except Exception:
                    return ""

            # Run ARP lookups concurrently for better performance
            vip_output, primary_output, secondary_output = await asyncio.gather(
                get_arp_entry(vip),
                get_arp_entry(primary_ip),
                get_arp_entry(secondary_ip)
            )

            def extract_mac(output):
                """Extract MAC address from 'ip neigh show' output"""
                parts = output.split()
                try:
                    lladdr_idx = parts.index('lladdr')
                    return parts[lladdr_idx + 1].upper()
                except (ValueError, IndexError):
                    return None

            vip_mac = extract_mac(vip_output)
            primary_mac = extract_mac(primary_output)
            secondary_mac = extract_mac(secondary_output)
            
            logger.debug(f"VIP check (attempt {attempt + 1}/{max_retries}): VIP_MAC={vip_mac}, Primary_MAC={primary_mac}, Secondary_MAC={secondary_mac}")
            
            if vip_mac and primary_mac and vip_mac == primary_mac:
                return True, False
            elif vip_mac and secondary_mac and vip_mac == secondary_mac:
                return False, True
            else:
                # If VIP MAC not found, likely no MASTER (both BACKUP)
                if not vip_mac:
                    logger.warning(f"VIP {vip} has no ARP entry (attempt {attempt + 1}/{max_retries}) - possible keepalived failure")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)  # Wait before retry
                        continue
                return False, False
            
        except Exception as e:
            logger.error(f"Error checking VIP (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)  # Wait before retry
            else:
                return False, False
    
    return False, False

async def log_event(event_type: str, message: str):
    async with aiosqlite.connect(CONFIG["db_path"]) as db:
        await db.execute("INSERT INTO events (event_type, message) VALUES (?, ?)", (event_type, message))
        await db.commit()

async def monitor_loop():
    previous_state = None
    previous_primary_online = None
    previous_secondary_online = None
    previous_primary_pihole = None
    previous_secondary_pihole = None
    previous_primary_has_vip = None
    previous_secondary_has_vip = None
    startup = True
    
    while True:
        try:
            primary_data = await check_pihole_simple(CONFIG["primary"]["ip"], CONFIG["primary"]["password"])
            secondary_data = await check_pihole_simple(CONFIG["secondary"]["ip"], CONFIG["secondary"]["password"])
            
            # Check DNS functionality separately
            primary_dns = await check_dns(CONFIG["primary"]["ip"]) if primary_data["online"] else False
            secondary_dns = await check_dns(CONFIG["secondary"]["ip"]) if secondary_data["online"] else False
            
            primary_has_vip, secondary_has_vip = await check_who_has_vip(CONFIG["vip"], CONFIG["primary"]["ip"], CONFIG["secondary"]["ip"])
            
            primary_state = "MASTER" if primary_has_vip else "BACKUP"
            secondary_state = "MASTER" if secondary_has_vip else "BACKUP"
            
            # Log initial status on startup
            if startup:
                current_master = "Primary" if primary_state == "MASTER" else "Secondary"
                await log_event("info", f"Monitor started - {current_master} is MASTER")
                await log_event("info", f"Primary: {'Online' if primary_data['online'] else 'Offline'}, Pi-hole: {'OK' if primary_data['pihole'] else 'Down'}")
                await log_event("info", f"Secondary: {'Online' if secondary_data['online'] else 'Offline'}, Pi-hole: {'OK' if secondary_data['pihole'] else 'Down'}")
                startup = False
            
            # Detect online/offline changes
            if previous_primary_online is not None:
                if previous_primary_online and not primary_data["online"]:
                    await log_event("warning", "Primary went OFFLINE")
                    logger.warning("Primary went OFFLINE")
                elif not previous_primary_online and primary_data["online"]:
                    await log_event("success", "Primary is back ONLINE")
                    logger.info("Primary is back ONLINE")
            
            if previous_secondary_online is not None:
                if previous_secondary_online and not secondary_data["online"]:
                    await log_event("warning", "Secondary went OFFLINE")
                    logger.warning("Secondary went OFFLINE")
                elif not previous_secondary_online and secondary_data["online"]:
                    await log_event("success", "Secondary is back ONLINE")
                    logger.info("Secondary is back ONLINE")
            
            # Detect Pi-hole service changes
            if previous_primary_pihole is not None:
                if previous_primary_pihole and not primary_data["pihole"] and primary_data["online"]:
                    await log_event("warning", "Pi-hole service on Primary is DOWN")
                    logger.warning("Primary Pi-hole service is DOWN")
                elif not previous_primary_pihole and primary_data["pihole"]:
                    await log_event("success", "Pi-hole service on Primary is back UP")
                    logger.info("Primary Pi-hole service is back UP")
            
            if previous_secondary_pihole is not None:
                if previous_secondary_pihole and not secondary_data["pihole"] and secondary_data["online"]:
                    await log_event("warning", "Pi-hole service on Secondary is DOWN")
                    logger.warning("Secondary Pi-hole service is DOWN")
                elif not previous_secondary_pihole and secondary_data["pihole"]:
                    await log_event("success", "Pi-hole service on Secondary is back UP")
                    logger.info("Secondary Pi-hole service is back UP")
            
            # Detect VIP changes (not during failover)
            if previous_primary_has_vip is not None and previous_secondary_has_vip is not None:
                if previous_primary_has_vip != primary_has_vip or previous_secondary_has_vip != secondary_has_vip:
                    current = "Primary" if primary_has_vip else "Secondary"
                    previous = "Primary" if previous_primary_has_vip else "Secondary"
                    await log_event("warning", f"VIP switched from {previous} to {current}")
                    logger.warning(f"VIP switched from {previous} to {current}")
            
            dhcp_leases = 0
            if primary_state == "MASTER":
                dhcp_leases = primary_data.get("dhcp_leases", 0)
            elif secondary_state == "MASTER":
                dhcp_leases = secondary_data.get("dhcp_leases", 0)
            
            async with aiosqlite.connect(CONFIG["db_path"]) as db:
                await db.execute("""
                    INSERT INTO status_history (primary_state, secondary_state, primary_has_vip, secondary_has_vip, primary_online, secondary_online, primary_pihole, secondary_pihole, primary_dns, secondary_dns, dhcp_leases, primary_dhcp, secondary_dhcp) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (primary_state, secondary_state, primary_has_vip, secondary_has_vip, primary_data["online"], secondary_data["online"], primary_data["pihole"], secondary_data["pihole"], primary_dns, secondary_dns, dhcp_leases, primary_data.get("dhcp_enabled", False), secondary_data.get("dhcp_enabled", False)))
                await db.commit()
            
            # Detect failover
            current_master = "primary" if primary_state == "MASTER" else "secondary"
            if previous_state and previous_state != current_master:
                master_name = "Primary" if current_master == "primary" else "Secondary"
                await log_event("failover", f"{master_name} became MASTER")
                logger.warning(f"FAILOVER: {master_name} is now MASTER")

                # Determine failover reason
                reason = ""
                if current_master == "secondary":
                    if not primary_data["online"]:
                        reason = "Primary is offline"
                        await log_event("info", f"Failover reason: {reason}")
                    elif not primary_data["pihole"]:
                        reason = "Pi-hole service on Primary is down"
                        await log_event("info", f"Failover reason: {reason}")
                else:
                    if not secondary_data["online"]:
                        reason = "Secondary is offline"
                        await log_event("info", f"Failback reason: {reason}")
                    elif not secondary_data["pihole"]:
                        reason = "Pi-hole service on Secondary is down"
                        await log_event("info", f"Failback reason: {reason}")

                # Send notification
                # Determine which node is master and which is backup
                if current_master == "Primary":
                    master_node = CONFIG.get('primary_name', 'Primary-Pi-hole')
                    backup_node = CONFIG.get('secondary_name', 'Secondary-Pi-hole')
                else:
                    master_node = CONFIG.get('secondary_name', 'Secondary-Pi-hole')
                    backup_node = CONFIG.get('primary_name', 'Primary-Pi-hole')
                
                template_vars = {
                    "node_name": master_name,
                    "node": master_name,
                    "master": master_node,
                    "backup": backup_node,
                    "primary": CONFIG.get('primary_name', 'Primary-Pi-hole'),
                    "secondary": CONFIG.get('secondary_name', 'Secondary-Pi-hole'),
                    "reason": reason if reason else "Unknown",
                    "vip_address": CONFIG['vip'],
                    "vip": CONFIG['vip'],
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "date": datetime.now().strftime("%Y-%m-%d")
                }
                await send_notification("failover", template_vars)
                # Mark failover as active issue for reminders
                notification_state["active_issues"]["failover"] = True
            
            # Check for recovery - clear active issues
            if previous_state and previous_state != current_master:
                # If we switched back to primary as master, clear failover issue
                if current_master == "primary":
                    notification_state["active_issues"]["failover"] = False
                    notification_state["active_issues"]["fault"] = False
            
            # Track fault state (both offline or both pihole down)
            both_offline = not primary_data["online"] and not secondary_data["online"]
            both_pihole_down = not primary_data["pihole"] and not secondary_data["pihole"]
            if both_offline or both_pihole_down:
                notification_state["active_issues"]["fault"] = True
            else:
                notification_state["active_issues"]["fault"] = False
            
            # Check and send reminder notifications if needed
            await check_and_send_reminders()
            
            previous_state = current_master
            previous_primary_online = primary_data["online"]
            previous_secondary_online = secondary_data["online"]
            previous_primary_pihole = primary_data["pihole"]
            previous_secondary_pihole = secondary_data["pihole"]
            previous_primary_has_vip = primary_has_vip
            previous_secondary_has_vip = secondary_has_vip
            
            # Check DHCP misconfiguration
            primary_dhcp = primary_data.get("dhcp_enabled", False)
            secondary_dhcp = secondary_data.get("dhcp_enabled", False)
            
            # MASTER should have DHCP enabled, BACKUP should have it disabled
            if primary_state == "MASTER" and not primary_dhcp:
                await log_event("warning", "⚠️ DHCP misconfiguration: Primary is MASTER but DHCP is DISABLED")
                logger.warning("DHCP misconfiguration: Primary is MASTER but DHCP is DISABLED")
            elif primary_state == "BACKUP" and primary_dhcp:
                await log_event("warning", "⚠️ DHCP misconfiguration: Primary is BACKUP but DHCP is ENABLED")
                logger.warning("DHCP misconfiguration: Primary is BACKUP but DHCP is ENABLED")
            
            if secondary_state == "MASTER" and not secondary_dhcp:
                await log_event("warning", "⚠️ DHCP misconfiguration: Secondary is MASTER but DHCP is DISABLED")
                logger.warning("DHCP misconfiguration: Secondary is MASTER but DHCP is DISABLED")
            elif secondary_state == "BACKUP" and secondary_dhcp:
                await log_event("warning", "⚠️ DHCP misconfiguration: Secondary is BACKUP but DHCP is ENABLED")
                logger.warning("DHCP misconfiguration: Secondary is BACKUP but DHCP is ENABLED")
            
            logger.debug(f"[{datetime.now()}] Primary: {primary_state}, Secondary: {secondary_state}, Leases: {dhcp_leases}")
            
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}", exc_info=True)
            await log_event("error", f"Monitor error: {str(e)}")
        await asyncio.sleep(CONFIG["check_interval"])

@app.get("/api/status")
async def get_status(api_key: str = Depends(verify_api_key)):
    async with aiosqlite.connect(CONFIG["db_path"]) as db:
        async with db.execute("SELECT * FROM status_history ORDER BY timestamp DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="No status data available")
            return {
                "timestamp": row[1],
                "primary": {
                    "ip": CONFIG["primary"]["ip"],
                    "name": CONFIG["primary"]["name"],
                    "state": row[2],
                    "has_vip": bool(row[4]),
                    "online": bool(row[6]),
                    "pihole": bool(row[8]),
                    "dns": bool(row[10]) if len(row) > 10 else bool(row[6]),  # Fallback to online for backward compatibility
                    "dhcp": bool(row[13]) if len(row) > 13 else False  # New DHCP status
                },
                "secondary": {
                    "ip": CONFIG["secondary"]["ip"],
                    "name": CONFIG["secondary"]["name"],
                    "state": row[3],
                    "has_vip": bool(row[5]),
                    "online": bool(row[7]),
                    "pihole": bool(row[9]),
                    "dns": bool(row[11]) if len(row) > 11 else bool(row[7]),  # Fallback to online for backward compatibility
                    "dhcp": bool(row[14]) if len(row) > 14 else False  # New DHCP status
                },
                "vip": CONFIG["vip"],
                "dhcp_leases": row[12] if len(row) > 12 else row[10]  # Adjust for new column
            }

@app.get("/api/history")
async def get_history(hours: float = 24, api_key: str = Depends(verify_api_key)):
    async with aiosqlite.connect(CONFIG["db_path"]) as db:
        async with db.execute("SELECT timestamp, primary_state, secondary_state FROM status_history WHERE timestamp > datetime('now', '-' || ? || ' hours') ORDER BY timestamp ASC", (hours,)) as cursor:
            rows = await cursor.fetchall()
            return [{"time": row[0], "primary": 1 if row[1] == "MASTER" else 0, "secondary": 1 if row[2] == "MASTER" else 0} for row in rows]

@app.get("/api/events")
async def get_events(limit: int = 50, api_key: str = Depends(verify_api_key)):
    async with aiosqlite.connect(CONFIG["db_path"]) as db:
        async with db.execute("SELECT timestamp, event_type, message FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [{"time": row[0], "type": row[1], "message": row[2]} for row in rows]

@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def root():
    html_path = "/opt/pihole-monitor/index.html"
    if os.path.exists(html_path):
        with open(html_path, 'r') as f:
            return f.read()
    else:
        return HTMLResponse(content=f"<h1>Error: index.html not found</h1>", status_code=404)

@app.get("/api/notifications/settings")
async def get_notification_settings(api_key: str = Depends(verify_api_key)):
    """Get current notification settings (with masked sensitive data)"""
    import json
    
    config_path = CONFIG["notify_config_path"]
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                settings = json.load(f)
                # Mask sensitive fields
                settings = mask_sensitive_data(settings)
                return settings
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load settings: {str(e)}")
    
    # Return default empty settings
    return {
        "events": {"failover": True, "recovery": True, "fault": True, "startup": False},
        "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
        "discord": {"enabled": False, "webhook_url": ""},
        "pushover": {"enabled": False, "user_key": "", "app_token": ""},
        "ntfy": {"enabled": False, "topic": "", "server": "https://ntfy.sh"},
        "webhook": {"enabled": False, "url": ""},
        "templates": {
            "failover": "🚨 Failover Alert!\n{master} is now MASTER\n{backup} issue: {reason}",
            "recovery": "✅ Recovery: {primary} is back online\n{master} is now MASTER",
            "fault": "⚠️ FAULT: Both Pi-holes may have issues!\nCheck immediately!",
            "startup": "🚀 Pi-hole Sentinel started\nMonitoring {primary} and {secondary}"
        },
        "repeat": {
            "enabled": False,
            "interval": 0  # 0=disabled, 5/10/30/60 minutes
        },
        "snooze": {
            "enabled": False,
            "until": None  # ISO timestamp when snooze ends
        }
    }

# SECURITY: Removed insecure test-settings endpoint that exposed credentials
# The /api/notifications/settings endpoint now properly masks sensitive data

def mask_sensitive_data(settings):
    """Mask sensitive fields with *** but indicate if they're set"""
    masked = copy.deepcopy(settings)
    
    # Telegram
    if masked.get("telegram", {}).get("bot_token"):
        masked["telegram"]["bot_token"] = "••••••••" + masked["telegram"]["bot_token"][-4:]
    if masked.get("telegram", {}).get("chat_id"):
        masked["telegram"]["chat_id"] = "••••" + masked["telegram"]["chat_id"][-4:]
    
    # Discord
    if masked.get("discord", {}).get("webhook_url"):
        masked["discord"]["webhook_url"] = "••••••••" + masked["discord"]["webhook_url"][-8:]
    
    # Pushover
    if masked.get("pushover", {}).get("user_key"):
        masked["pushover"]["user_key"] = "••••••••" + masked["pushover"]["user_key"][-4:]
    if masked.get("pushover", {}).get("app_token"):
        masked["pushover"]["app_token"] = "••••••••" + masked["pushover"]["app_token"][-4:]
    
    # Ntfy (topic and server are not sensitive)
    
    # Webhook
    if masked.get("webhook", {}).get("url"):
        masked["webhook"]["url"] = "••••••••" + masked["webhook"]["url"][-8:]
    
    return masked

def merge_settings(existing, new):
    """Merge new settings with existing, preserving values where new is None or masked"""
    merged = existing.copy()

    def is_masked_value(value):
        """Check if a value appears to be masked (starts with bullets)"""
        if not isinstance(value, str):
            return False
        return value.startswith('••••') or value.startswith('****')

    for service, config in new.items():
        if service not in merged:
            merged[service] = {}

        for key, value in config.items():
            # Skip if value is None (means "keep existing")
            if value is None:
                if key in existing.get(service, {}):
                    merged[service][key] = existing[service][key]
            # Skip if value appears to be masked (security protection)
            elif is_masked_value(value):
                logger.warning(f"Rejecting masked value for {service}.{key} - keeping existing value")
                if key in existing.get(service, {}):
                    merged[service][key] = existing[service][key]
                else:
                    merged[service][key] = ""
            # Use new value
            else:
                merged[service][key] = value

    return merged

@app.post("/api/notifications/settings")
async def save_notification_settings(settings: dict, api_key: str = Depends(verify_api_key)):
    """Save notification settings (preserving masked values)"""
    import json
    
    config_path = CONFIG["notify_config_path"]
    config_dir = os.path.dirname(config_path)
    
    # Create directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    
    # Load existing settings to preserve masked values
    existing_settings = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                existing_settings = json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            # Config file corrupted or unreadable, use defaults
            pass
    
    # Merge settings, keeping existing values where new value is None
    merged_settings = merge_settings(existing_settings, settings)
    
    def escape_for_bash_config(value):
        """Escape value for safe use in bash double-quoted string."""
        if not value:
            return ""
        # Escape backslashes first, then other special chars
        escaped = str(value).replace('\\', '\\\\')
        escaped = escaped.replace('"', '\\"')
        escaped = escaped.replace('$', '\\$')
        escaped = escaped.replace('`', '\\`')
        escaped = escaped.replace('!', '\\!')
        return escaped
    
    try:
        with open(config_path, 'w') as f:
            json.dump(merged_settings, f, indent=2)
        
        # Also update the bash config file for keepalived scripts
        bash_config = "/etc/pihole-sentinel/notify.conf"
        os.makedirs(os.path.dirname(bash_config), exist_ok=True)
        
        with open(bash_config, 'w') as f:
            f.write("# Pi-hole Sentinel Notification Configuration\n")
            f.write("# Auto-generated from web interface\n\n")
            
            # Event settings
            events = merged_settings.get('events', {})
            f.write("# Notification Event Controls\n")
            f.write(f"NOTIFY_FAILOVER=\"{'true' if events.get('failover', True) else 'false'}\"\n")
            f.write(f"NOTIFY_RECOVERY=\"{'true' if events.get('recovery', True) else 'false'}\"\n")
            f.write(f"NOTIFY_FAULT=\"{'true' if events.get('fault', True) else 'false'}\"\n")
            f.write(f"NOTIFY_STARTUP=\"{'true' if events.get('startup', False) else 'false'}\"\n\n")
            
            # Service credentials - escape all values for bash safety
            if merged_settings.get('telegram', {}).get('enabled'):
                f.write("# Telegram\n")
                f.write(f"TELEGRAM_BOT_TOKEN=\"{escape_for_bash_config(merged_settings['telegram'].get('bot_token', ''))}\"\n")
                f.write(f"TELEGRAM_CHAT_ID=\"{escape_for_bash_config(merged_settings['telegram'].get('chat_id', ''))}\"\n\n")
            
            if merged_settings.get('discord', {}).get('enabled'):
                f.write("# Discord\n")
                f.write(f"DISCORD_WEBHOOK_URL=\"{escape_for_bash_config(merged_settings['discord'].get('webhook_url', ''))}\"\n\n")
            
            if merged_settings.get('pushover', {}).get('enabled'):
                f.write("# Pushover\n")
                f.write(f"PUSHOVER_USER_KEY=\"{escape_for_bash_config(merged_settings['pushover'].get('user_key', ''))}\"\n")
                f.write(f"PUSHOVER_APP_TOKEN=\"{escape_for_bash_config(merged_settings['pushover'].get('app_token', ''))}\"\n\n")
            
            if merged_settings.get('ntfy', {}).get('enabled'):
                f.write("# Ntfy\n")
                f.write(f"NTFY_TOPIC=\"{escape_for_bash_config(merged_settings['ntfy'].get('topic', ''))}\"\n")
                f.write(f"NTFY_SERVER=\"{escape_for_bash_config(merged_settings['ntfy'].get('server', 'https://ntfy.sh'))}\"\n\n")
            
            if merged_settings.get('webhook', {}).get('enabled'):
                f.write("# Custom Webhook\n")
                f.write(f"CUSTOM_WEBHOOK_URL=\"{escape_for_bash_config(merged_settings['webhook'].get('url', ''))}\"\n\n")
        
        return {"status": "success", "message": "Settings saved successfully"}

    except Exception as e:
        logger.error(f"Failed to save notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

@app.post("/api/notifications/test")
async def test_notification(
    request: Request,
    data: dict,
    api_key: str = Depends(verify_api_key),
    _rate_limit: bool = Depends(rate_limit_check)
):
    """Test a notification service - loads settings from server to avoid masked values"""
    import json

    service = data.get('service')

    if not service:
        raise HTTPException(status_code=400, detail="Service not specified")

    # Load REAL (unmasked) settings from server
    config_path = CONFIG["notify_config_path"]
    if not os.path.exists(config_path):
        raise HTTPException(status_code=400, detail="No notification settings configured yet. Please save settings first.")

    try:
        with open(config_path, 'r') as f:
            all_settings = json.load(f)
            settings = all_settings.get(service, {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load settings: {str(e)}")

    if not settings.get('enabled'):
        raise HTTPException(status_code=400, detail=f"{service.capitalize()} is not enabled")

    try:
        if service == 'telegram':
            if not settings.get('bot_token') or not settings.get('chat_id'):
                raise HTTPException(status_code=400, detail="Bot token and chat ID required")
            
            test_message = (
                "🧪 <b>Pi-hole Sentinel Test Notification</b>\n\n"
                "📋 <b>Default Template Examples:</b>\n\n"
                "🚨 <b>Failover:</b>\n"
                "🚨 Failover Alert!\n"
                "Secondary Pi-hole is now MASTER\n"
                "Primary Pi-hole issue: Service stopped\n\n"
                "✅ <b>Recovery:</b>\n"
                "✅ Recovery: Primary Pi-hole is back online\n"
                "Primary Pi-hole is now MASTER\n\n"
                "⚠️ <b>Fault:</b>\n"
                "⚠️ FAULT: Both Pi-holes may have issues!\n"
                "Check immediately!\n\n"
                "🚀 <b>Startup:</b>\n"
                "🚀 Pi-hole Sentinel started\n"
                "Monitoring Primary Pi-hole and Secondary Pi-hole\n\n"
                "✅ If you see this, notifications are working!"
            )
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{settings['bot_token']}/sendMessage"
                async with session.post(url, json={
                    'chat_id': settings['chat_id'],
                    'text': test_message,
                    'parse_mode': 'HTML'
                }) as response:
                    if response.status != 200:
                        raise Exception(f"Telegram API returned {response.status}")
        
        elif service == 'discord':
            if not settings.get('webhook_url'):
                raise HTTPException(status_code=400, detail="Webhook URL required")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(settings['webhook_url'], json={
                    'embeds': [
                        {
                            'title': '🧪 Pi-hole Sentinel Test Notification',
                            'description': '**Default Template Examples:**',
                            'color': 3447003,
                            'fields': [
                                {
                                    'name': '🚨 Failover',
                                    'value': '🚨 Failover Alert!\nSecondary Pi-hole is now MASTER\nPrimary Pi-hole issue: Service stopped',
                                    'inline': False
                                },
                                {
                                    'name': '✅ Recovery',
                                    'value': '✅ Recovery: Primary Pi-hole is back online\nPrimary Pi-hole is now MASTER',
                                    'inline': False
                                },
                                {
                                    'name': '⚠️ Fault',
                                    'value': '⚠️ FAULT: Both Pi-holes may have issues!\nCheck immediately!',
                                    'inline': False
                                },
                                {
                                    'name': '🚀 Startup',
                                    'value': '🚀 Pi-hole Sentinel started\nMonitoring Primary Pi-hole and Secondary Pi-hole',
                                    'inline': False
                                },
                                {
                                    'name': '✅ Status',
                                    'value': 'If you see this, notifications are working!',
                                    'inline': False
                                }
                            ],
                            'footer': {'text': 'Pi-hole Sentinel HA Monitor'}
                        }
                    ]
                }) as response:
                    if response.status not in [200, 204]:
                        raise Exception(f"Discord API returned {response.status}")
        
        elif service == 'pushover':
            if not settings.get('user_key') or not settings.get('app_token'):
                raise HTTPException(status_code=400, detail="User key and app token required")
            
            test_message = (
                "🧪 Pi-hole Sentinel Test\n\n"
                "Default Template Examples:\n\n"
                "🚨 Failover:\n"
                "Secondary Pi-hole is now MASTER\n"
                "Primary Pi-hole issue: Service stopped\n\n"
                "✅ Recovery:\n"
                "Primary Pi-hole is back online\n"
                "Primary Pi-hole is now MASTER\n\n"
                "⚠️ Fault:\n"
                "Both Pi-holes may have issues!\n"
                "Check immediately!\n\n"
                "🚀 Startup:\n"
                "Pi-hole Sentinel started\n"
                "Monitoring Primary and Secondary\n\n"
                "✅ Notifications are working!"
            )
            
            async with aiohttp.ClientSession() as session:
                async with session.post('https://api.pushover.net/1/messages.json', data={
                    'token': settings['app_token'],
                    'user': settings['user_key'],
                    'title': 'Pi-hole Sentinel Test',
                    'message': test_message
                }) as response:
                    if response.status != 200:
                        raise Exception(f"Pushover API returned {response.status}")
        
        elif service == 'ntfy':
            if not settings.get('topic'):
                raise HTTPException(status_code=400, detail="Topic required")
            
            server = settings.get('server', 'https://ntfy.sh')
            url = f"{server}/{settings['topic']}"
            
            test_message = (
                "🧪 Pi-hole Sentinel Test\n\n"
                "Default Template Examples:\n\n"
                "🚨 Failover: Secondary Pi-hole is now MASTER (Primary issue: Service stopped)\n"
                "✅ Recovery: Primary Pi-hole is back online (Primary is now MASTER)\n"
                "⚠️ Fault: Both Pi-holes may have issues! Check immediately!\n"
                "🚀 Startup: Pi-hole Sentinel started (Monitoring Primary and Secondary)\n\n"
                "✅ If you see this, notifications are working!"
            )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=test_message, headers={
                    'Title': 'Pi-hole Sentinel Test',
                    'Priority': 'default',
                    'Tags': 'white_check_mark,test_tube'
                }) as response:
                    if response.status != 200:
                        raise Exception(f"Ntfy returned {response.status}")
        
        elif service == 'webhook':
            if not settings.get('url'):
                raise HTTPException(status_code=400, detail="Webhook URL required")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(settings['url'], json={
                    'service': 'pihole-sentinel',
                    'type': 'test',
                    'message': 'Test notification - Default template examples',
                    'templates': {
                        'failover': '🚨 Failover Alert! Secondary Pi-hole is now MASTER (Primary Pi-hole issue: Service stopped)',
                        'recovery': '✅ Recovery: Primary Pi-hole is back online (Primary Pi-hole is now MASTER)',
                        'fault': '⚠️ FAULT: Both Pi-holes may have issues! Check immediately!',
                        'startup': '🚀 Pi-hole Sentinel started (Monitoring Primary Pi-hole and Secondary Pi-hole)'
                    },
                    'status': 'Notifications are working!',
                    'timestamp': datetime.now().isoformat()
                }) as response:
                    if response.status not in [200, 201, 202, 204]:
                        raise Exception(f"Webhook returned {response.status}")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown service: {service}")
        
        return {"status": "success", "message": f"Test notification sent via {service}"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

@app.post("/api/notifications/test-template")
async def test_template_notification(
    request: Request,
    data: dict,
    api_key: str = Depends(verify_api_key),
    _rate_limit: bool = Depends(rate_limit_check)
):
    """Test a template notification with sample data"""
    template_type = data.get('template_type', 'failover')
    
    if template_type not in ['failover', 'recovery', 'fault', 'startup']:
        raise HTTPException(status_code=400, detail="Invalid template type")
    
    # Sample data for testing - use configured names or defaults
    primary_name = CONFIG.get('primary_name', 'Primary-Pi-hole')
    secondary_name = CONFIG.get('secondary_name', 'Secondary-Pi-hole')
    
    sample_vars = {
        "node_name": secondary_name,
        "node": secondary_name,
        "master": secondary_name,
        "backup": primary_name,
        "primary": primary_name,
        "secondary": secondary_name,
        "reason": "Test notification - simulated failover",
        "vip_address": CONFIG.get('vip', '192.168.1.100'),
        "vip": CONFIG.get('vip', '192.168.1.100'),
        "time": datetime.now().strftime("%H:%M:%S"),
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    
    try:
        await send_notification(template_type, sample_vars)
        return {"status": "success", "message": f"Test {template_type} notification sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

@app.get("/api/notifications/snooze")
async def get_snooze_status(api_key: str = Depends(verify_api_key)):
    """Get current snooze status"""
    import json
    
    config_path = CONFIG["notify_config_path"]
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                settings = json.load(f)
                snooze = settings.get('snooze', {})
                
                # Check if snooze is still active
                if snooze.get('enabled') and snooze.get('until'):
                    try:
                        until = datetime.fromisoformat(snooze['until'].replace('Z', '+00:00'))
                        if until.tzinfo:
                            until = until.replace(tzinfo=None)
                        if datetime.now() >= until:
                            # Snooze has expired
                            snooze['enabled'] = False
                            snooze['until'] = None
                    except (ValueError, TypeError):
                        pass
                
                return {
                    "enabled": snooze.get('enabled', False),
                    "until": snooze.get('until'),
                    "active": is_snoozed(settings)
                }
        except Exception:
            pass
    
    return {"enabled": False, "until": None, "active": False}

@app.post("/api/notifications/snooze")
async def set_snooze(data: dict, api_key: str = Depends(verify_api_key)):
    """Set snooze for notifications"""
    import json
    
    duration_minutes = data.get('duration', 60)  # Default 1 hour
    
    if duration_minutes <= 0:
        raise HTTPException(status_code=400, detail="Duration must be positive")
    
    if duration_minutes > 1440:  # Max 24 hours
        raise HTTPException(status_code=400, detail="Maximum snooze duration is 24 hours")
    
    until = datetime.now() + timedelta(minutes=duration_minutes)
    
    config_path = CONFIG["notify_config_path"]
    
    # Load existing settings
    settings = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                settings = json.load(f)
        except Exception:
            pass
    
    # Update snooze settings
    settings['snooze'] = {
        'enabled': True,
        'until': until.isoformat()
    }
    
    # Save settings
    try:
        with open(config_path, 'w') as f:
            json.dump(settings, f, indent=2)
        
        await log_event("info", f"🔕 Notifications snoozed until {until.strftime('%H:%M')}")
        return {
            "status": "success",
            "message": f"Notifications snoozed for {duration_minutes} minutes",
            "until": until.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set snooze: {str(e)}")

@app.delete("/api/notifications/snooze")
async def cancel_snooze(api_key: str = Depends(verify_api_key)):
    """Cancel active snooze"""
    import json
    
    config_path = CONFIG["notify_config_path"]
    
    # Load existing settings
    settings = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                settings = json.load(f)
        except Exception:
            pass
    
    # Clear snooze settings
    settings['snooze'] = {
        'enabled': False,
        'until': None
    }
    
    # Save settings
    try:
        with open(config_path, 'w') as f:
            json.dump(settings, f, indent=2)
        
        await log_event("info", "🔔 Snooze cancelled, notifications re-enabled")
        return {"status": "success", "message": "Snooze cancelled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel snooze: {str(e)}")


# =============================================================================
# Command Execution API (System Commands)
# =============================================================================

# Command whitelist - only these commands can be executed
COMMANDS_WHITELIST = {
    'monitor_status': {
        'cmd': ['systemctl', 'status', 'pihole-monitor', '--no-pager', '--lines=20'],
        'description': 'Monitor Service Status',
        'icon': '📊',
    },
    'monitor_logs': {
        'cmd': ['journalctl', '-u', 'pihole-monitor', '-n', '50', '--no-pager'],
        'description': 'Monitor Logs (last 50 lines)',
        'icon': '📄',
    },
    'keepalived_status': {
        'cmd': ['systemctl', 'status', 'keepalived', '--no-pager', '--lines=20'],
        'description': 'Keepalived Service Status',
        'icon': '🔄',
    },
    'keepalived_logs': {
        'cmd': ['journalctl', '-u', 'keepalived', '-n', '50', '--no-pager'],
        'description': 'Keepalived Logs (last 50 lines)',
        'icon': '📜',
    },
    'vip_check': {
        'cmd': ['ip', 'addr', 'show'],
        'description': 'Network Interfaces (VIP Check)',
        'icon': '🌐',
    },
    'db_recent_events': {
        'cmd': ['sqlite3', CONFIG["db_path"],
                'SELECT timestamp, event_type, message FROM events ORDER BY timestamp DESC LIMIT 20'],
        'description': 'Recent Database Events',
        'icon': '📊',
    },
}

# Rate limiting voor command execution
command_rate_limit_store = defaultdict(list)
COMMAND_RATE_LIMIT_REQUESTS = 5  # Max 5 commands
COMMAND_RATE_LIMIT_WINDOW = 60   # Per 60 seconds

async def command_rate_limit_check(request: Request):
    """Rate limit command execution to prevent spam"""
    client_ip = request.client.host
    now = time.time()

    # Remove old entries
    command_rate_limit_store[client_ip] = [
        timestamp for timestamp in command_rate_limit_store[client_ip]
        if now - timestamp < COMMAND_RATE_LIMIT_WINDOW
    ]

    # Check limit
    if len(command_rate_limit_store[client_ip]) >= COMMAND_RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {COMMAND_RATE_LIMIT_REQUESTS} commands per {COMMAND_RATE_LIMIT_WINDOW}s"
        )

    # Add current timestamp
    command_rate_limit_store[client_ip].append(now)
    return True

@app.get("/api/commands")
async def list_commands(api_key: str = Depends(verify_api_key)):
    """List available system commands"""
    return {
        "commands": {
            name: {
                "description": info['description'],
                "icon": info['icon']
            }
            for name, info in COMMANDS_WHITELIST.items()
        }
    }

@app.post("/api/commands/{command_name}")
async def execute_command(
    command_name: str,
    api_key: str = Depends(verify_api_key),
    _rate_limit: bool = Depends(command_rate_limit_check)
):
    """Execute a whitelisted system command"""
    if command_name not in COMMANDS_WHITELIST:
        raise HTTPException(
            status_code=400,
            detail=f"Command '{command_name}' not whitelisted. Use /api/commands to see available commands."
        )

    cmd_info = COMMANDS_WHITELIST[command_name]
    cmd = cmd_info['cmd']

    try:
        # Execute command with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )

        logger.info(f"Command executed: {command_name} (exit code: {result.returncode})")

        return {
            "status": "success" if result.returncode == 0 else "error",
            "command": command_name,
            "description": cmd_info['description'],
            "icon": cmd_info['icon'],
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "exit_code": result.returncode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except subprocess.TimeoutExpired:
        logger.warning(f"Command timeout: {command_name}")
        return {
            "status": "error",
            "command": command_name,
            "error": "Command execution timed out (10s limit)",
            "exit_code": 124,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Command execution failed: {command_name}", exc_info=True)
        return {
            "status": "error",
            "command": command_name,
            "error": str(e),
            "exit_code": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


if __name__ == "__main__":
    if not os.path.exists(os.path.dirname(CONFIG["db_path"])):
        os.makedirs(os.path.dirname(CONFIG["db_path"]))
    uvicorn.run(app, host="0.0.0.0", port=8080)