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
from datetime import datetime
from typing import Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment
CONFIG = {
    "primary": {
<<<<<<< HEAD:monitoring/monitor.py
        "ip": "IP.IP.IP.IP",
        "name": "Primary (LXC)",
        "password": "PASSPASS"
    },
    "secondary": {
        "ip": "IP.IP.IP.IP",
        "name": "Secondary (RPi 3B)",
        "password": "PASSPASS"
    },
    "vip": "IP.IP.IP.IP",
    "check_interval": 10,
    "db_path": "/opt/pihole-monitor/monitor.db"
=======
        "ip": os.getenv("PRIMARY_IP"),
        "name": os.getenv("PRIMARY_NAME"),
        "password": os.getenv("PRIMARY_PASSWORD")
    },
    "secondary": {
        "ip": os.getenv("SECONDARY_IP"),
        "name": os.getenv("SECONDARY_NAME"),
        "password": os.getenv("SECONDARY_PASSWORD")
    },
    "vip": os.getenv("VIP_ADDRESS"),
    "check_interval": int(os.getenv("CHECK_INTERVAL", "10")),
    "db_path": os.getenv("DB_PATH", "/opt/pihole-monitor/monitor.db")
>>>>>>> 7ddc47f (Herstructureer Pi-hole monitor naar volledige HA-oplossing):monitoring/pihole-ha/dashboard/monitor.py
}

# Verify required environment variables
required_vars = ["PRIMARY_IP", "PRIMARY_PASSWORD", "SECONDARY_IP", "SECONDARY_PASSWORD", "VIP_ADDRESS"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

app = FastAPI(title="Pi-hole Keepalived Monitor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
                dhcp_leases INTEGER
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
        
        await db.commit()

async def check_pihole_simple(ip: str, password: str) -> Dict:
    """Simple Pi-hole check - creates and closes session each time"""
    result = {
        "online": False,
        "pihole": False,
        "queries": 0,
        "blocked": 0,
        "clients": 0,
        "dhcp_leases": 0
    }
    
    try:
        ping = subprocess.run(["/usr/bin/ping", "-c", "1", "-W", "2", ip], capture_output=True, timeout=3)
        result["online"] = ping.returncode == 0
    except Exception as e:
        print(f"Ping error for {ip}: {e}")
        return result
    
    if not result["online"]:
        return result
    
    try:
        async with aiohttp.ClientSession() as session:
            sid = None
            
            try:
                async with session.post(f"http://{ip}/api/auth", json={"password": password}, timeout=aiohttp.ClientTimeout(total=5)) as auth_resp:
                    if auth_resp.status == 200:
                        auth_data = await auth_resp.json()
                        sid = auth_data.get("sid")
            except Exception as e:
                print(f"FTL Auth exception for {ip}: {e}")
                return result

            if not sid:
                print(f"Could not get session ID for {ip}. Check password.")
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
                try:
                    async with session.get(f"http://{ip}/api/dhcp/leases", headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as leases_resp:
                        if leases_resp.status == 200:
                            leases = await leases_resp.json()
                            result["dhcp_leases"] = len(leases)
                except Exception as e:
                    print(f"DHCP check exception for {ip}: {e}")
                    result["dhcp_leases"] = 0

            try:
                await session.delete(f"http://{ip}/api/auth", headers=headers, timeout=aiohttp.ClientTimeout(total=2))
            except:
                pass
    except Exception as e:
        print(f"Main session exception for {ip}: {e}")
    
    return result

async def check_dns(ip: str) -> bool:
    try:
        result = subprocess.run(["/usr/bin/dig", "+short", "+time=2", f"@{ip}", "google.com"], capture_output=True, text=True, timeout=5)
        return bool(result.stdout.strip())
    except Exception as e:
        print(f"DNS check error for {ip}: {e}")
        return False

async def check_who_has_vip(vip: str, primary_ip: str, secondary_ip: str) -> tuple:
    try:
        vip_result = subprocess.run(["/usr/sbin/ip", "neigh", "show", vip], capture_output=True, text=True, timeout=2)
        primary_result = subprocess.run(["/usr/sbin/ip", "neigh", "show", primary_ip], capture_output=True, text=True, timeout=2)
        secondary_result = subprocess.run(["/usr/sbin/ip", "neigh", "show", secondary_ip], capture_output=True, text=True, timeout=2)
        
        def extract_mac(output):
            parts = output.split()
            try:
                lladdr_idx = parts.index('lladdr')
                return parts[lladdr_idx + 1]
            except (ValueError, IndexError):
                return None
        
        vip_mac = extract_mac(vip_result.stdout)
        primary_mac = extract_mac(primary_result.stdout)
        secondary_mac = extract_mac(secondary_result.stdout)
        
        if vip_mac and primary_mac and vip_mac == primary_mac:
            return True, False
        elif vip_mac and secondary_mac and vip_mac == secondary_mac:
            return False, True
        else:
            return True, False
    except Exception as e:
        print(f"Error checking VIP via ARP: {e}")
        return True, False

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
                    print("⚠️  Primary went OFFLINE")
                elif not previous_primary_online and primary_data["online"]:
                    await log_event("success", "Primary is back ONLINE")
                    print("✅ Primary is back ONLINE")
            
            if previous_secondary_online is not None:
                if previous_secondary_online and not secondary_data["online"]:
                    await log_event("warning", "Secondary went OFFLINE")
                    print("⚠️  Secondary went OFFLINE")
                elif not previous_secondary_online and secondary_data["online"]:
                    await log_event("success", "Secondary is back ONLINE")
                    print("✅ Secondary is back ONLINE")
            
            # Detect Pi-hole service changes
            if previous_primary_pihole is not None:
                if previous_primary_pihole and not primary_data["pihole"] and primary_data["online"]:
                    await log_event("warning", "Pi-hole service on Primary is DOWN")
                    print("⚠️  Primary Pi-hole service is DOWN")
                elif not previous_primary_pihole and primary_data["pihole"]:
                    await log_event("success", "Pi-hole service on Primary is back UP")
                    print("✅ Primary Pi-hole service is back UP")
            
            if previous_secondary_pihole is not None:
                if previous_secondary_pihole and not secondary_data["pihole"] and secondary_data["online"]:
                    await log_event("warning", "Pi-hole service on Secondary is DOWN")
                    print("⚠️  Secondary Pi-hole service is DOWN")
                elif not previous_secondary_pihole and secondary_data["pihole"]:
                    await log_event("success", "Pi-hole service on Secondary is back UP")
                    print("✅ Secondary Pi-hole service is back UP")
            
            # Detect VIP changes (not during failover)
            if previous_primary_has_vip is not None and previous_secondary_has_vip is not None:
                if previous_primary_has_vip != primary_has_vip or previous_secondary_has_vip != secondary_has_vip:
                    current = "Primary" if primary_has_vip else "Secondary"
                    previous = "Primary" if previous_primary_has_vip else "Secondary"
                    await log_event("warning", f"VIP switched from {previous} to {current}")
                    print(f"⚠️  VIP switched from {previous} to {current}")
            
            dhcp_leases = 0
            if primary_state == "MASTER":
                dhcp_leases = primary_data.get("dhcp_leases", 0)
            elif secondary_state == "MASTER":
                dhcp_leases = secondary_data.get("dhcp_leases", 0)
            
            async with aiosqlite.connect(CONFIG["db_path"]) as db:
                await db.execute("""
                    INSERT INTO status_history (primary_state, secondary_state, primary_has_vip, secondary_has_vip, primary_online, secondary_online, primary_pihole, secondary_pihole, dhcp_leases) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (primary_state, secondary_state, primary_has_vip, secondary_has_vip, primary_data["online"], secondary_data["online"], primary_data["pihole"], secondary_data["pihole"], dhcp_leases))
                await db.commit()
            
            # Detect failover
            current_master = "primary" if primary_state == "MASTER" else "secondary"
            if previous_state and previous_state != current_master:
                master_name = "Primary" if current_master == "primary" else "Secondary"
                await log_event("failover", f"{master_name} became MASTER")
                print(f"⚠️  FAILOVER: {master_name} is now MASTER")
                
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
            
            print(f"[{datetime.now()}] Primary: {primary_state}, Secondary: {secondary_state}, Leases: {dhcp_leases}")
            
        except Exception as e:
            print(f"Error in monitor loop: {e}")
            await log_event("error", f"Monitor error: {str(e)}")
        await asyncio.sleep(CONFIG["check_interval"])

@app.on_event("startup")
async def startup_event():
    await init_db()
    await log_event("info", "Monitor started")
    asyncio.create_task(monitor_loop())

@app.get("/api/status")
async def get_status():
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
                    "pihole": bool(row[8])
                },
                "secondary": {
                    "ip": CONFIG["secondary"]["ip"],
                    "name": CONFIG["secondary"]["name"],
                    "state": row[3],
                    "has_vip": bool(row[5]),
                    "online": bool(row[7]),
                    "pihole": bool(row[9])
                },
                "vip": CONFIG["vip"],
                "dhcp_leases": row[10]
            }

@app.get("/api/history")
async def get_history(hours: float = 24):
    async with aiosqlite.connect(CONFIG["db_path"]) as db:
        async with db.execute("SELECT timestamp, primary_state, secondary_state FROM status_history WHERE timestamp > datetime('now', '-' || ? || ' hours') ORDER BY timestamp ASC", (hours,)) as cursor:
            rows = await cursor.fetchall()
            return [{"time": row[0], "primary": 1 if row[1] == "MASTER" else 0, "secondary": 1 if row[2] == "MASTER" else 0} for row in rows]

@app.get("/api/events")
async def get_events(limit: int = 50):
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

if __name__ == "__main__":
    if not os.path.exists(os.path.dirname(CONFIG["db_path"])):
        os.makedirs(os.path.dirname(CONFIG["db_path"]))
    uvicorn.run(app, host="0.0.0.0", port=8080)