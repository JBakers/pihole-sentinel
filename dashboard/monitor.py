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
from datetime import datetime, timedelta
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

app = FastAPI(title="Pi-hole Keepalived Monitor")

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
http_session: aiohttp.ClientSession = None

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
            async with session.post(f"http://{ip}/api/auth", json={"password": password}, timeout=aiohttp.ClientTimeout(total=5)) as auth_resp:
                if auth_resp.status == 200:
                    auth_data = await auth_resp.json()
                    # Pi-hole v6 returns sid within a session object
                    session_data = auth_data.get("session", {})
                    sid = session_data.get("sid")
        except Exception as e:
            logger.debug(f"FTL Auth exception for {ip}: {e}")
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
            try:
                async with session.get(f"http://{ip}/api/dhcp/leases", headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as leases_resp:
                    if leases_resp.status == 200:
                        leases_data = await leases_resp.json()
                        logger.debug(f"DHCP leases response for {ip}: {leases_data}")

                        # Pi-hole v6 might use different structure
                        # Try multiple possible locations for leases data
                        leases = None
                        if isinstance(leases_data, dict):
                            # Try "leases" key
                            leases = leases_data.get("leases")
                            # Try "dhcp" -> "leases" nested structure
                            if not leases:
                                leases = leases_data.get("dhcp", {}).get("leases")
                            # Try direct list in response
                            if not leases and isinstance(leases_data.get("data"), list):
                                leases = leases_data.get("data")
                        elif isinstance(leases_data, list):
                            # Response is directly a list
                            leases = leases_data

                        if isinstance(leases, list):
                            result["dhcp_leases"] = len(leases)
                            logger.debug(f"DHCP leases count for {ip}: {result['dhcp_leases']}")
                        elif isinstance(leases, dict):
                            # If leases is a dict, count the keys
                            result["dhcp_leases"] = len(leases)
                            logger.debug(f"DHCP leases count (dict) for {ip}: {result['dhcp_leases']}")
                        else:
                            result["dhcp_leases"] = 0
                            logger.warning(f"DHCP leases data type unexpected for {ip}: {type(leases)}")
                    else:
                        logger.warning(f"DHCP leases API returned status {leases_resp.status} for {ip}")
                        result["dhcp_leases"] = 0
            except Exception as e:
                logger.warning(f"DHCP leases check exception for {ip}: {e}")
                result["dhcp_leases"] = 0

        # Logout from Pi-hole API
        try:
            await session.delete(f"http://{ip}/api/auth", headers=headers, timeout=aiohttp.ClientTimeout(total=2))
        except:
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
                except:
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
                
                # Log reason for failover
                if current_master == "secondary":
                    if not primary_data["online"]:
                        await log_event("info", "Failover reason: Primary is offline")
                    elif not primary_data["pihole"]:
                        await log_event("info", "Failover reason: Pi-hole service on Primary is down")
                else:
                    if not secondary_data["online"]:
                        await log_event("info", "Failback reason: Secondary is offline")
                    elif not secondary_data["pihole"]:
                        await log_event("info", "Failback reason: Pi-hole service on Secondary is down")
            
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

@app.on_event("startup")
async def startup_event():
    await init_db()
    # Initialize HTTP session pool on startup
    await get_http_session()
    await log_event("info", "Monitor started")
    asyncio.create_task(monitor_loop())

@app.on_event("shutdown")
async def shutdown_event():
    # Clean up HTTP session on shutdown
    await close_http_session()
    logger.info("Monitor stopped, HTTP session closed")

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
        "webhook": {"enabled": False, "url": ""}
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
        except:
            pass
    
    # Merge settings, keeping existing values where new value is None
    merged_settings = merge_settings(existing_settings, settings)
    
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
            
            # Service credentials
            if merged_settings.get('telegram', {}).get('enabled'):
                f.write("# Telegram\n")
                f.write(f"TELEGRAM_BOT_TOKEN=\"{merged_settings['telegram'].get('bot_token', '')}\"\n")
                f.write(f"TELEGRAM_CHAT_ID=\"{merged_settings['telegram'].get('chat_id', '')}\"\n\n")
            
            if merged_settings.get('discord', {}).get('enabled'):
                f.write("# Discord\n")
                f.write(f"DISCORD_WEBHOOK_URL=\"{merged_settings['discord'].get('webhook_url', '')}\"\n\n")
            
            if merged_settings.get('pushover', {}).get('enabled'):
                f.write("# Pushover\n")
                f.write(f"PUSHOVER_USER_KEY=\"{merged_settings['pushover'].get('user_key', '')}\"\n")
                f.write(f"PUSHOVER_APP_TOKEN=\"{merged_settings['pushover'].get('app_token', '')}\"\n\n")
            
            if merged_settings.get('ntfy', {}).get('enabled'):
                f.write("# Ntfy\n")
                f.write(f"NTFY_TOPIC=\"{merged_settings['ntfy'].get('topic', '')}\"\n")
                f.write(f"NTFY_SERVER=\"{merged_settings['ntfy'].get('server', 'https://ntfy.sh')}\"\n\n")
            
            if merged_settings.get('webhook', {}).get('enabled'):
                f.write("# Custom Webhook\n")
                f.write(f"CUSTOM_WEBHOOK_URL=\"{merged_settings['webhook'].get('url', '')}\"\n\n")
        
        return {"status": "success", "message": "Settings saved successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

@app.post("/api/notifications/test")
async def test_notification(
    request: Request,
    data: dict,
    api_key: str = Depends(verify_api_key),
    _rate_limit: bool = Depends(rate_limit_check)
):
    """Test a notification service"""
    service = data.get('service')
    settings = data.get('settings', {})
    
    if not service:
        raise HTTPException(status_code=400, detail="Service not specified")
    
    try:
        if service == 'telegram':
            if not settings.get('bot_token') or not settings.get('chat_id'):
                raise HTTPException(status_code=400, detail="Bot token and chat ID required")
            
            test_message = (
                "🧪 <b>Pi-hole Sentinel Test Notification</b>\n\n"
                "📋 <b>Example Event Messages:</b>\n\n"
                "🔵 <b>STARTUP Event:</b>\n"
                "Pi-hole Sentinel started\n"
                "🚀 Keepalived initialized\n"
                "📡 Monitoring active\n\n"
                "🟢 <b>MASTER/Recovery Event:</b>\n"
                "Pi-hole is now MASTER\n"
                "✅ DHCP server enabled\n"
                "🌐 Virtual IP active\n\n"
                "🟡 <b>BACKUP/Failover Event:</b>\n"
                "Pi-hole is now BACKUP\n"
                "⏸️ DHCP server disabled\n"
                "👀 Monitoring MASTER\n\n"
                "🔴 <b>FAULT Event:</b>\n"
                "Pi-hole entered FAULT state\n"
                "❌ DHCP server disabled\n"
                "⚠️ Service issues detected\n\n"
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
                            'description': '**Example Event Messages:**',
                            'color': 3447003,
                            'fields': [
                                {
                                    'name': '🔵 STARTUP Event',
                                    'value': 'Pi-hole Sentinel started\n🚀 Keepalived initialized\n📡 Monitoring active',
                                    'inline': False
                                },
                                {
                                    'name': '🟢 MASTER/Recovery Event',
                                    'value': 'Pi-hole is now MASTER\n✅ DHCP enabled\n🌐 Virtual IP active',
                                    'inline': False
                                },
                                {
                                    'name': '🟡 BACKUP/Failover Event',
                                    'value': 'Pi-hole is now BACKUP\n⏸️ DHCP disabled\n👀 Monitoring MASTER',
                                    'inline': False
                                },
                                {
                                    'name': '🔴 FAULT Event',
                                    'value': 'Pi-hole entered FAULT state\n❌ DHCP disabled\n⚠️ Service issues detected',
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
                "🧪 Test Notification\n\n"
                "Example Event Messages:\n\n"
                "🔵 STARTUP:\n"
                "🚀 Keepalived initialized, Monitoring active\n\n"
                "🟢 MASTER/Recovery:\n"
                "✅ DHCP enabled, Virtual IP active\n\n"
                "🟡 BACKUP/Failover:\n"
                "⏸️ DHCP disabled, Monitoring MASTER\n\n"
                "🔴 FAULT:\n"
                "❌ DHCP disabled, Service issues\n\n"
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
                "🧪 Test Notification\n\n"
                "Example Event Messages:\n\n"
                "🔵 STARTUP: Keepalived initialized, Monitoring active\n"
                "🟢 MASTER/Recovery: DHCP enabled, Virtual IP active\n"
                "🟡 BACKUP/Failover: DHCP disabled, Monitoring MASTER\n"
                "🔴 FAULT: DHCP disabled, Service issues detected\n\n"
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
                    'message': 'Test notification - Example events',
                    'examples': {
                        'startup': 'Keepalived initialized, Monitoring active',
                        'master': 'DHCP enabled, Virtual IP active',
                        'backup': 'DHCP disabled, Monitoring MASTER',
                        'fault': 'DHCP disabled, Service issues detected'
                    },
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

if __name__ == "__main__":
    if not os.path.exists(os.path.dirname(CONFIG["db_path"])):
        os.makedirs(os.path.dirname(CONFIG["db_path"]))
    uvicorn.run(app, host="0.0.0.0", port=8080)