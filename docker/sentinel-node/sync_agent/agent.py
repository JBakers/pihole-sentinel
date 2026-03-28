#!/usr/bin/env python3
"""
Pi-hole Sentinel Node - Sync Agent

Lightweight FastAPI service that runs alongside keepalived in the sentinel-node
container. Responsibilities:

1. Health API      - /health endpoint for external monitoring
2. State API       - /state endpoint to report VRRP state (MASTER/BACKUP/FAULT)
3. Sync API        - /sync/gravity endpoint to receive/push Pi-hole gravity DB
4. Internal API    - /internal/* endpoints called by keepalived notify scripts

All peer-to-peer communication uses a shared SYNC_TOKEN for authentication.
"""

import os
import hmac
import json
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Header, Request, BackgroundTasks, Depends
from fastapi.responses import FileResponse, JSONResponse

# ── Configuration ───────────────────────────────────────────
NODE_NAME = os.getenv("NODE_NAME", os.getenv("HOSTNAME", "unknown"))
NODE_ROLE = os.getenv("NODE_ROLE", "backup")
SYNC_TOKEN = os.getenv("SYNC_TOKEN", "")
SYNC_PEERS = [p.strip() for p in os.getenv("SYNC_PEERS", "").split(",") if p.strip()]
PIHOLE_HOST = os.getenv("PIHOLE_HOST", "127.0.0.1")
PIHOLE_WEB_PORT = os.getenv("PIHOLE_WEB_PORT", "80")
PIHOLE_PASSWORD = os.getenv("PIHOLE_PASSWORD", "")
VIP_IP = os.getenv("VIP_IP", "")
DATA_DIR = Path("/data")
GRAVITY_DB = Path("/etc/pihole/gravity.db")  # Default Pi-hole gravity path

# ── Logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("sentinel-node")

# ── State ───────────────────────────────────────────────────
node_state = {
    "vrrp_state": "INIT",
    "last_transition": None,
    "start_time": datetime.now(timezone.utc).isoformat(),
    "sync_status": {
        "last_sync": None,
        "last_sync_result": None,
        "peers_reachable": {}
    }
}

# ── App ─────────────────────────────────────────────────────
app = FastAPI(
    title="Sentinel Node Sync Agent",
    version="0.1.0",
    docs_url="/docs"
)


# ── Auth ────────────────────────────────────────────────────
def verify_sync_token(x_sync_token: str = Header(default="")):
    """Verify the sync token for peer-to-peer communication (timing-safe)."""
    if not SYNC_TOKEN:
        logger.warning("SYNC_TOKEN is not set — all sync endpoints are OPEN. Set SYNC_TOKEN for production use.")
        return
    if not hmac.compare_digest(x_sync_token, SYNC_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid sync token")


# ── Health Endpoints ────────────────────────────────────────
@app.get("/health")
async def health():
    """Health check endpoint for Docker healthcheck and external monitoring."""
    return {
        "status": "ok",
        "node": NODE_NAME,
        "role": NODE_ROLE,
        "vrrp_state": node_state["vrrp_state"],
        "uptime_since": node_state["start_time"]
    }


@app.get("/state")
async def get_state():
    """Full node state including VRRP status and sync info."""
    # Try to read keepalived state file
    state_file = DATA_DIR / "keepalived_state.json"
    ka_state = None
    if state_file.exists():
        try:
            ka_state = json.loads(state_file.read_text())
        except Exception:
            pass

    return {
        "node_name": NODE_NAME,
        "node_role": NODE_ROLE,
        "vip": VIP_IP,
        "vrrp_state": node_state["vrrp_state"],
        "keepalived": ka_state,
        "last_transition": node_state["last_transition"],
        "sync": node_state["sync_status"],
        "peers": SYNC_PEERS
    }


# ── Internal Endpoints (called by keepalived) ──────────────
@app.post("/internal/state-change", dependencies=[Depends(verify_sync_token)])
async def state_change(request: Request, background_tasks: BackgroundTasks):
    """Called by keepalived notify.sh when VRRP state changes."""
    data = await request.json()
    new_state = data.get("state", "UNKNOWN")
    old_state = node_state["vrrp_state"]

    node_state["vrrp_state"] = new_state
    node_state["last_transition"] = datetime.now(timezone.utc).isoformat()

    logger.info(f"VRRP state change: {old_state} -> {new_state}")

    # If we became MASTER, trigger a gravity sync push to peers
    if new_state == "MASTER" and SYNC_PEERS:
        logger.info("Became MASTER - scheduling gravity sync to peers")
        background_tasks.add_task(push_gravity_to_peers)

    return {"status": "ok", "old_state": old_state, "new_state": new_state}


# ── Sync Endpoints ──────────────────────────────────────────
@app.post("/sync/gravity")
async def receive_gravity(request: Request, x_sync_token: str = Header(default="")):
    """
    Receive a gravity.db from the MASTER node.
    This is called on BACKUP nodes when the MASTER pushes its config.
    """
    verify_sync_token(x_sync_token)

    # Save the incoming gravity database
    gravity_path = DATA_DIR / "gravity.db"
    content = await request.body()

    if not content:
        raise HTTPException(status_code=400, detail="Empty gravity database")

    gravity_path.write_bytes(content)
    logger.info(f"Received gravity.db ({len(content)} bytes) from peer")

    # Optionally: reload Pi-hole after gravity update
    await reload_pihole_gravity()

    node_state["sync_status"]["last_sync"] = datetime.now(timezone.utc).isoformat()
    node_state["sync_status"]["last_sync_result"] = "success"

    return {"status": "ok", "bytes_received": len(content)}


@app.get("/sync/gravity")
async def serve_gravity(x_sync_token: str = Header(default="")):
    """
    Serve the local gravity.db to a requesting peer.
    Used when a BACKUP wants to pull from MASTER.
    """
    verify_sync_token(x_sync_token)

    # Try multiple paths
    for path in [DATA_DIR / "gravity.db", GRAVITY_DB]:
        if path.exists():
            return FileResponse(path, media_type="application/octet-stream")

    raise HTTPException(status_code=404, detail="No gravity.db available")


@app.get("/sync/status")
async def sync_status():
    """Get sync status for all known peers."""
    results = {}
    for peer in SYNC_PEERS:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                headers = {"X-Sync-Token": SYNC_TOKEN} if SYNC_TOKEN else {}
                resp = await client.get(f"http://{peer}:5000/health", headers=headers)
                results[peer] = {
                    "reachable": True,
                    "status": resp.json() if resp.status_code == 200 else None
                }
        except Exception as e:
            results[peer] = {"reachable": False, "error": str(e)}

    node_state["sync_status"]["peers_reachable"] = {
        p: r["reachable"] for p, r in results.items()
    }
    return {"peers": results}


# ── Background Tasks ────────────────────────────────────────
async def push_gravity_to_peers():
    """Push gravity.db to all peer nodes (called when becoming MASTER)."""
    # Find gravity.db
    gravity_path = None
    for path in [DATA_DIR / "gravity.db", GRAVITY_DB]:
        if path.exists():
            gravity_path = path
            break

    if not gravity_path:
        logger.warning("No gravity.db found to sync - skipping push")
        return

    gravity_data = gravity_path.read_bytes()
    logger.info(f"Pushing gravity.db ({len(gravity_data)} bytes) to {len(SYNC_PEERS)} peers")

    for peer in SYNC_PEERS:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"X-Sync-Token": SYNC_TOKEN} if SYNC_TOKEN else {}
                resp = await client.post(
                    f"http://{peer}:5000/sync/gravity",
                    content=gravity_data,
                    headers=headers
                )
                if resp.status_code == 200:
                    logger.info(f"Gravity sync to {peer}: OK")
                else:
                    logger.warning(f"Gravity sync to {peer}: HTTP {resp.status_code}")
        except Exception as e:
            logger.error(f"Gravity sync to {peer} failed: {e}")


async def reload_pihole_gravity():
    """Tell Pi-hole to reload gravity after receiving a new database."""
    # Pi-hole v6 doesn't have a direct gravity reload endpoint
    # but we can call restartdns via the API if authenticated
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Login
            auth_resp = await client.post(
                f"http://{PIHOLE_HOST}:{PIHOLE_WEB_PORT}/api/auth",
                json={"password": PIHOLE_PASSWORD}
            )
            if auth_resp.status_code != 200:
                logger.warning("Could not authenticate with Pi-hole for gravity reload")
                return

            session = auth_resp.json().get("session", {})
            sid = session.get("sid", "")

            # Pi-hole v6: no direct gravity reload yet, log for now
            logger.info("Gravity database updated - Pi-hole will pick up changes")

            # Logout
            await client.delete(
                f"http://{PIHOLE_HOST}:{PIHOLE_WEB_PORT}/api/auth",
                headers={"X-FTL-SID": sid}
            )
    except Exception as e:
        logger.warning(f"Pi-hole gravity reload notification failed: {e}")


# ── Startup ─────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info(f"Sentinel Node Sync Agent starting")
    logger.info(f"  Node:  {NODE_NAME}")
    logger.info(f"  Role:  {NODE_ROLE}")
    logger.info(f"  VIP:   {VIP_IP}")
    logger.info(f"  Peers: {SYNC_PEERS or 'none'}")
    logger.info(f"  Auth:  {'token set' if SYNC_TOKEN else 'OPEN (no token)'}")

    # Ensure data dir exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── Main ────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
