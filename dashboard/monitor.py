#!/usr/bin/env python3
"""
Pi-hole Keepalived Monitor - Simple Standalone Version
No SSH required, simple API calls
"""

import asyncio
import copy
import hmac
import ipaddress as _ipaddress
import json
import logging
import os
import secrets
import socket
import subprocess
import sys
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

# Configure logging with rotation
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiohttp
import aiosqlite
import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

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

# ============================================================================
# Configuration Loading (N-node support)
# ============================================================================

def load_node_config_from_env() -> list[dict]:
    """
    Load N-node configuration from environment variables.
    
    Supports both old format (PRIMARY_IP/SECONDARY_IP) and new format (PIHOLE_1_IP, PIHOLE_2_IP, ...).
    
    Returns list of node dicts: [{index, ip, name, password, ssh_user, ssh_port}, ...]
    """
    nodes = []
    node_index = 1
    
    # Try new format first (PIHOLE_1_IP, PIHOLE_2_IP, ...)
    while True:
        ip_var = f"PIHOLE_{node_index}_IP"
        password_var = f"PIHOLE_{node_index}_PASSWORD"
        name_var = f"PIHOLE_{node_index}_NAME"
        ssh_user_var = f"PIHOLE_{node_index}_SSH_USER"
        ssh_port_var = f"PIHOLE_{node_index}_SSH_PORT"
        
        ip = os.getenv(ip_var)
        if not ip:
            # End of node list
            break
        
        password = os.getenv(password_var)
        if not password:
            raise ValueError(f"Missing required {password_var}")
        
        node = {
            "index": node_index,
            "ip": ip,
            "name": os.getenv(name_var, f"Node-{node_index}"),
            "password": password,
            "ssh_user": os.getenv(ssh_user_var, "root"),
            "ssh_port": int(os.getenv(ssh_port_var, "22")),
        }
        nodes.append(node)
        node_index += 1
    
    # Fallback: old 2-node format (PRIMARY_IP, SECONDARY_IP)
    if not nodes:
        logger.info("No PIHOLE_N_IP format found; attempting legacy PRIMARY_IP/SECONDARY_IP...")
        
        primary_ip = os.getenv("PRIMARY_IP")
        secondary_ip = os.getenv("SECONDARY_IP")
        
        if primary_ip and secondary_ip:
            logger.warning("Using deprecated PRIMARY_IP/SECONDARY_IP format. Please migrate to PIHOLE_N_IP format.")
            nodes = [
                {
                    "index": 1,
                    "ip": primary_ip,
                    "name": os.getenv("PRIMARY_NAME", "Primary Pi-hole"),
                    "password": os.getenv("PRIMARY_PASSWORD", ""),
                    "ssh_user": os.getenv("PRIMARY_SSH_USER", "root"),
                    "ssh_port": int(os.getenv("PRIMARY_SSH_PORT", "22")),
                },
                {
                    "index": 2,
                    "ip": secondary_ip,
                    "name": os.getenv("SECONDARY_NAME", "Secondary Pi-hole"),
                    "password": os.getenv("SECONDARY_PASSWORD", ""),
                    "ssh_user": os.getenv("SECONDARY_SSH_USER", "root"),
                    "ssh_port": int(os.getenv("SECONDARY_SSH_PORT", "22")),
                },
            ]
    
    # Validation
    if not nodes:
        raise ValueError("No Pi-hole nodes configured. Set PIHOLE_1_IP/PIHOLE_1_PASSWORD or PRIMARY_IP/SECONDARY_IP")
    
    if len(nodes) < 2:
        raise ValueError(f"Minimum 2 nodes required, got {len(nodes)}")
    
    logger.info(f"Loaded {len(nodes)} Pi-hole nodes: {', '.join(n['name'] for n in nodes)}")
    return nodes


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
    "nodes": None,  # Lazy-loaded during app initialization
    "check_interval": int(os.getenv("CHECK_INTERVAL", "10")),
    "db_path": os.getenv("DB_PATH", "/opt/pihole-monitor/monitor.db"),
    "notify_config_path": os.getenv("NOTIFY_CONFIG_PATH", "/opt/pihole-monitor/notify_settings.json"),
    "api_key": os.getenv("API_KEY"),
    "ssh": {
        "key_path": os.getenv("SSH_KEY_PATH", "/opt/pihole-monitor/.ssh/id_pihole_sentinel"),
        "primary_user": os.getenv("PRIMARY_SSH_USER", "root"),
        "primary_port": os.getenv("PRIMARY_SSH_PORT", "22"),
        "secondary_user": os.getenv("SECONDARY_SSH_USER", "root"),
        "secondary_port": os.getenv("SECONDARY_SSH_PORT", "22"),
    },
}

# Generate API key if not set (for backward compatibility during transition)
if not CONFIG["api_key"]:
    # Generate a secure random API key and write to .env-safe file
    CONFIG["api_key"] = secrets.token_urlsafe(32)
    logger.warning("NO API_KEY FOUND - GENERATED TEMPORARY KEY FOR THIS SESSION")
    logger.warning("Set API_KEY in your .env file to make it persistent.")
    # Write to a secured file so the user can retrieve it without log exposure
    try:
        key_file = os.path.join(os.path.dirname(CONFIG["db_path"]), ".api_key")
        with open(key_file, 'w') as f:
            f.write(CONFIG["api_key"])
        os.chmod(key_file, 0o600)
        logger.info(f"Generated API key written to {key_file} (mode 600)")
    except Exception as e:
        logger.error(f"Could not write API key file: {e}")

# Initialize nodes (lazy load - called during app startup)
def _init_nodes():
    """Load node configuration on app startup."""
    if CONFIG["nodes"] is None:
        CONFIG["nodes"] = load_node_config_from_env()
    if CONFIG["nodes"]:
        CONFIG["primary"] = {
            "ip": CONFIG["nodes"][0]["ip"],
            "name": CONFIG["nodes"][0]["name"],
            "password": CONFIG["nodes"][0]["password"],
        }
    if len(CONFIG["nodes"]) > 1:
        CONFIG["secondary"] = {
            "ip": CONFIG["nodes"][1]["ip"],
            "name": CONFIG["nodes"][1]["name"],
            "password": CONFIG["nodes"][1]["password"],
        }
    return CONFIG["nodes"]

# Verify required environment variables (minimal check now, nodes validated in load_node_config_from_env)
# NOTE: This check is deferred to app startup (see _validate_config) to allow testing/importing
# without requiring all env vars to be set at module load time.


# ============================================================================
# Startup validation (called during app initialization)
# ============================================================================

def _validate_config():
    """Validate configuration at app startup."""
    required_vars = ["VIP_ADDRESS"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Initialize nodes
    _init_nodes()
    
    if not CONFIG["vip"]:
        logger.error("VIP_ADDRESS not set in environment")
        sys.exit(1)

# ============================================================================
# Version reading (must be before FastAPI app initialization)
# ============================================================================

def read_version_string() -> str:
    """Read the version from disk, with fallbacks."""
    try:
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
                        return version
    except Exception as e:
        logger.error(f"Failed to read VERSION file: {e}")

    return "unknown"


# ============================================================================
# Pydantic Models for OpenAPI/Swagger Documentation
# ============================================================================

class VersionResponse(BaseModel):
    """Version information response"""
    version: str = Field(..., description="Current Pi-hole Sentinel version")


class ClientConfigResponse(BaseModel):
    """Client configuration for dashboard UI"""
    api_key: str = Field(..., description="API key for dashboard requests")
    version: str = Field(..., description="Current Pi-hole Sentinel version")


class UpdateCheckResponse(BaseModel):
    """Update availability check response"""
    current_version: str = Field(..., description="Currently installed version")
    latest_version: Optional[str] = Field(None, description="Latest available version from GitHub")
    update_available: bool = Field(..., description="Whether an update is available")
    release_url: Optional[str] = Field(None, description="URL to the latest release")
    cached: bool = Field(False, description="Whether this result was cached from recent check")
    message: Optional[str] = Field(None, description="Additional message if applicable")


class PiHoleStatus(BaseModel):
    """Status of a single Pi-hole instance"""
    ip: str = Field(..., description="IP address of the Pi-hole instance")
    name: str = Field(..., description="Pi-hole instance name (Primary or Secondary)")
    state: str = Field(..., description="Keepalived state (MASTER/BACKUP)")
    has_vip: bool = Field(..., description="Whether this node holds the VIP")
    online: bool = Field(..., description="Whether the Pi-hole is reachable")
    pihole: bool = Field(..., description="Whether pihole-FTL service is running")
    dns: bool = Field(False, description="Whether DNS resolution is working")
    dns_latency_ms: Optional[float] = Field(None, description="DNS response latency in milliseconds (None if not measured)")
    dhcp: bool = Field(False, description="Whether DHCP server is running")
    queries: int = Field(0, description="Total DNS queries today")
    blocked: int = Field(0, description="Blocked queries today")
    clients: int = Field(0, description="Unique clients today")


class StatusResponse(BaseModel):
    """Overall system status response"""
    timestamp: str = Field(..., description="Timestamp of status check")
    primary: PiHoleStatus = Field(..., description="Primary Pi-hole status")
    secondary: PiHoleStatus = Field(..., description="Secondary Pi-hole status")
    vip: str = Field(..., description="Virtual IP address")
    dhcp_leases: int = Field(0, description="Number of active DHCP leases")
    dhcp_failover: bool = Field(False, description="Whether DHCP failover monitoring is enabled")
    dns_latency_warn_ms: float = Field(500.0, description="Configured DNS latency warning threshold in milliseconds")


class HistoryEntry(BaseModel):
    """Single history event entry"""
    timestamp: str = Field(..., description="ISO timestamp of event")
    event_type: str = Field(..., description="Type of event (failover, recovery, fault, etc.)")
    description: str = Field(..., description="Human-readable event description")
    details: Optional[Dict] = Field(None, description="Additional event details")


class EventsResponse(BaseModel):
    """Events and history response"""
    total_events: int = Field(..., description="Total number of events in history")
    recent_events: List[HistoryEntry] = Field(..., description="List of recent events")
    failover_count: int = Field(..., description="Total number of failovers")
    last_failover: Optional[str] = Field(None, description="ISO timestamp of last failover")


class NotificationSettingsRequest(BaseModel):
    """Notification settings update request"""
    enabled: bool = Field(True, description="Enable or disable notifications")
    events: Dict[str, bool] = Field(default_factory=dict, description="Which event types to notify on")
    telegram: Optional[Dict] = Field(None, description="Telegram bot configuration")
    discord: Optional[Dict] = Field(None, description="Discord webhook configuration")
    pushover: Optional[Dict] = Field(None, description="Pushover service configuration")
    ntfy: Optional[Dict] = Field(None, description="Ntfy service configuration")
    webhook: Optional[Dict] = Field(None, description="Custom webhook configuration")
    templates: Optional[Dict[str, str]] = Field(None, description="Custom message templates per event")
    repeat: Optional[Dict] = Field(None, description="Reminder/repeat notification settings")
    snooze: Optional[Dict] = Field(None, description="Snooze settings")


class NotificationTestRequest(BaseModel):
    """Request to send a test notification"""
    service: str = Field(..., description="Service to test (telegram, discord, pushover, ntfy, webhook)")
    event_type: str = Field(default="test", description="Event type for template selection")


class NotificationTestResponse(BaseModel):
    """Response from test notification request"""
    success: bool = Field(..., description="Whether notification was sent")
    message: str = Field(..., description="Status message")
    service: str = Field(..., description="Service that was tested")


class SnoozeRequest(BaseModel):
    """Request to snooze notifications"""
    minutes: int = Field(..., description="Duration to snooze in minutes (1-480)")


class SnoozeResponse(BaseModel):
    """Snooze status response"""
    snoozed: bool = Field(..., description="Whether notifications are currently snoozed")
    until: Optional[str] = Field(None, description="ISO timestamp when snooze expires")
    remaining_seconds: Optional[int] = Field(None, description="Seconds remaining in snooze")


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    status_code: int = Field(..., description="HTTP status code")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    if "PYTEST_CURRENT_TEST" not in os.environ:
        _validate_config()
    await init_db()
    await get_http_session()
    # Duplicate log removed here - log_event is called inside monitor_loop startup logic
    # await log_event("info", "Monitor started")
    asyncio.create_task(monitor_loop())
    asyncio.create_task(daily_cleanup_loop())
    logger.info("Pi-hole Sentinel Monitor started")

    yield

    # Shutdown
    await close_http_session()
    logger.info("Monitor stopped, HTTP session closed")

app = FastAPI(
    title="Pi-hole Keepalived Monitor API",
    description="REST API for Pi-hole Sentinel high availability monitoring and management",
    version=read_version_string(),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    servers=[
        {
            "url": "http://localhost:8080",
            "description": "Local monitor server"
        },
        {
            "url": "http://{monitor_ip}:8080",
            "description": "Remote monitor server",
            "variables": {
                "monitor_ip": {
                    "description": "IP address of monitor server",
                    "default": "192.168.1.100"
                }
            }
        }
    ]
)

# Security: API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key for protected endpoints (timing-safe comparison)."""
    if not hmac.compare_digest(api_key, CONFIG["api_key"]):
        logger.warning("Invalid API key attempt from client")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    return api_key

def validate_webhook_url(url: str) -> bool:
    """Validate that a webhook URL is safe to call (anti-SSRF).

    Blocks private/loopback/reserved IPs and non-HTTP schemes.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # Check if hostname resolves to a private/reserved IP
        try:
            addr = _ipaddress.ip_address(hostname)
            if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local:
                return False
        except ValueError:
            pass  # Hostname is a domain name, not an IP — allowed
        return True
    except Exception:
        return False

# Rate limiting configuration
# Stores {ip_address: [timestamp1, timestamp2, ...]}
rate_limit_store = defaultdict(list)
RATE_LIMIT_REQUESTS = 3  # Max 3 requests
RATE_LIMIT_WINDOW = 60  # Per 60 seconds

# Separate, more generous rate limiter for general write endpoints
write_rate_limit_store = defaultdict(list)
WRITE_RATE_LIMIT_REQUESTS = 20  # Max 20 requests
WRITE_RATE_LIMIT_WINDOW = 60  # Per 60 seconds

def _get_client_ip(request: Request) -> str:
    """Extract client IP. Only honour X-Forwarded-For when TRUST_PROXY_HEADERS=true
    is explicitly set, to prevent header spoofing and unbounded rate-limit store growth."""
    if os.environ.get("TRUST_PROXY_HEADERS", "false").lower() == "true":
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_check(request: Request):
    """Rate limiting: max 3 requests per 60 seconds per IP."""
    client_ip = _get_client_ip(request)
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

async def write_rate_limit_check(request: Request):
    """Rate limiting for general write endpoints: max 20 requests per 60 seconds per IP."""
    client_ip = _get_client_ip(request)
    now = datetime.now()
    write_rate_limit_store[client_ip] = [
        ts for ts in write_rate_limit_store[client_ip]
        if now - ts < timedelta(seconds=WRITE_RATE_LIMIT_WINDOW)
    ]
    if len(write_rate_limit_store[client_ip]) >= WRITE_RATE_LIMIT_REQUESTS:
        logger.warning(f"Write rate limit exceeded for {client_ip}")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {WRITE_RATE_LIMIT_REQUESTS} requests per {WRITE_RATE_LIMIT_WINDOW} seconds."
        )
    write_rate_limit_store[client_ip].append(now)
    return True

# Global aiohttp ClientSession for connection pooling
# Reusing sessions improves performance and prevents connection exhaustion
http_session: aiohttp.ClientSession | None = None

# ============================================================================
# Custom Exception Classes for Better Error Handling
# ============================================================================

class PiholeSentinelException(Exception):
    """Base exception for Pi-hole Sentinel errors"""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(PiholeSentinelException):
    """Raised when configuration is invalid or missing"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, status_code=400, details=details)


class AuthenticationError(PiholeSentinelException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Invalid or missing API key", details: Optional[Dict] = None):
        super().__init__(message, status_code=403, details=details)


class RateLimitError(PiholeSentinelException):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str = "Too many requests", details: Optional[Dict] = None):
        super().__init__(message, status_code=429, details=details)


class NotificationError(PiholeSentinelException):
    """Raised when notification sending fails"""
    def __init__(self, message: str, service: str = "", details: Optional[Dict] = None):
        if details is None:
            details = {}
        details['service'] = service
        super().__init__(f"Notification failed ({service}): {message}", status_code=500, details=details)


class DatabaseError(PiholeSentinelException):
    """Raised when database operation fails"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(f"Database error: {message}", status_code=500, details=details)


# ============================================================================
# Global Exception Handlers
# ============================================================================

async def handle_pihole_exception(request: Request, exc: PiholeSentinelException):
    """Handle Pi-hole Sentinel exceptions with standard error response"""
    logger.error(f"PiholeSentinelException: {exc.message}", extra=exc.details)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details if exc.details else None,
            "status_code": exc.status_code
        }
    )


async def handle_http_exception(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPException with standardized format"""
    # Log the error
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP {exc.status_code}",
            "details": exc.detail,
            "status_code": exc.status_code
        }
    )


async def handle_generic_exception(request: Request, exc: Exception):
    """Handle unexpected exceptions with safe error response"""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "details": "An unexpected error occurred. Check server logs for details.",
            "status_code": 500
        }
    )


async def get_http_session() -> aiohttp.ClientSession:
    """Get or create global HTTP session for connection pooling.

    Uses a custom DNS resolver (1.1.1.1 / 8.8.8.8) so that notifications
    still work when both Pi-holes (and therefore the system DNS) are offline.
    """
    global http_session
    if http_session is None or http_session.closed:
        # Bypass system DNS (= Pi-hole VIP) so we can still reach Telegram,
        # Discord, etc. when both Pi-holes are down.
        try:
            resolver = aiohttp.AsyncResolver(nameservers=["1.1.1.1", "8.8.8.8"])
        except Exception:
            # aiodns not available — fall back to system resolver
            resolver = aiohttp.DefaultResolver()
        timeout = aiohttp.ClientTimeout(total=10)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10, resolver=resolver)
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
    "last_vars": {},  # {event_type: dict} - template vars from last real notification for reminders
}

# Event & notification debounce ────────────────────────────────────────────────
# Brief Pi-hole FTL restarts (e.g. config sync, ~12-32 s) should not spam the
# event log or notifications.  A node must stay offline for at least
# EVENT_DEBOUNCE_SECONDS before an event is logged.  Notifications fire after
# an additional FAULT_NOTIFICATION_DELAY seconds (total ≈ 60 s).
# Recovery before the debounce window expires is suppressed silently.
EVENT_DEBOUNCE_SECONDS = int(os.getenv("EVENT_DEBOUNCE_SECONDS", "30"))
FAULT_NOTIFICATION_DELAY = 30  # additional seconds before sending notification
DNS_LATENCY_WARN_MS = float(os.getenv("DNS_LATENCY_WARN_MS", "500"))
_fault_tasks: dict = {}     # key → asyncio.Task (pending debounce timer)
_fault_notified: set = set()  # keys where a fault notification was actually sent

# Event debounce state — tracks when nodes first went offline so transient
# outages (e.g. FTL restart during config sync) are suppressed.
_offline_since: dict = {}           # "primary"/"secondary" → datetime
_offline_event_logged: set = set()  # nodes where "went OFFLINE" was logged
_pihole_down_since: dict = {}       # "primary"/"secondary" → datetime
_pihole_down_event_logged: set = set()  # nodes where "service DOWN" was logged

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
        # Validate template placeholders — only allow simple {varname} to prevent
        # attribute access ({x.y}), indexing ({x[0]}), or format specs ({x!r})
        import re as _re
        _placeholders = _re.findall(r'\{([^}]*)\}', template)
        for ph in _placeholders:
            if not _re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', ph):
                logger.warning(f"Rejected unsafe template placeholder: {{{ph}}}")
                await log_event("warning", f"⚠️ Notification template blocked: unsafe placeholder '{{{ph}}}'")
                return

        message = template.format_map(defaultdict(lambda: "[unknown]", template_vars))
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

        if webhook_url and validate_webhook_url(webhook_url):
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

        if topic and validate_webhook_url(server):
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

        if webhook_url and validate_webhook_url(webhook_url):
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
        # Store vars for reminder reuse (skip for reminders themselves to preserve original context)
        if not is_reminder:
            notification_state["last_vars"][event_type] = template_vars

    if failed_services:
        await log_event("warning", f"⚠️ Notification failed for: {', '.join(failed_services)}")

async def check_and_send_reminders():
    """Check if any reminder notifications should be sent for active issues."""

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
            # Reuse vars from the original notification so the reminder is contextually correct
            last = notification_state.get("last_vars", {}).get(event_type)
            if last:
                template_vars = {**last, "time": datetime.now().strftime("%H:%M:%S"), "date": datetime.now().strftime("%Y-%m-%d")}
            else:
                primary_name = CONFIG.get('primary', {}).get('name', 'Primary Pi-hole')
                secondary_name = CONFIG.get('secondary', {}).get('name', 'Secondary Pi-hole')
                template_vars = {
                    "node_name": secondary_name,
                    "node": secondary_name,
                    "master": secondary_name,
                    "backup": primary_name,
                    "primary": primary_name,
                    "secondary": secondary_name,
                    "reason": "Issue still active",
                    "vip_address": CONFIG.get('vip', ''),
                    "vip": CONFIG.get('vip', ''),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                }
            await send_notification(event_type, template_vars, is_reminder=True)
            logger.info(f"Sent reminder notification for {event_type}")


async def _schedule_fault_notification(key: str, template_vars: dict) -> None:
    """Send a fault notification after FAULT_NOTIFICATION_DELAY seconds.

    Cancelled automatically (via _fault_tasks[key].cancel()) when the fault
    clears before the delay expires — suppressing spam from brief FTL restarts.
    """
    await asyncio.sleep(FAULT_NOTIFICATION_DELAY)
    _fault_notified.add(key)   # mark as sent BEFORE awaiting so cancel sees it
    await send_notification("fault", template_vars)
    _fault_tasks.pop(key, None)


def _arm_fault(key: str, template_vars: dict) -> None:
    """Start the debounce timer for a fault key (idempotent)."""
    if key not in _fault_tasks:
        _fault_tasks[key] = asyncio.create_task(
            _schedule_fault_notification(key, template_vars)
        )


def _cancel_fault_pending(key: str) -> bool:
    """Cancel a still-pending fault task. Returns True if a task was cancelled."""
    task = _fault_tasks.pop(key, None)
    if task:
        task.cancel()
        return True
    return False


async def _cancel_fault(key: str, recovery_vars: dict) -> None:
    """Handle fault recovery for *key*.

    - If the fault timer is still pending (< 30 s after event): cancel
      silently — no notification was sent so no recovery message is needed.
    - If the fault notification was already sent (≥ 30 s after event): send a
      recovery notification so the user knows the issue is resolved.
    """
    was_pending = _cancel_fault_pending(key)
    if not was_pending and key in _fault_notified:
        # Fault notification went out — now confirm recovery
        _fault_notified.discard(key)
        await send_notification("recovery", recovery_vars)

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
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Add security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    return response

# ============================================================================
# Register Custom Exception Handlers
# ============================================================================

app.add_exception_handler(PiholeSentinelException, handle_pihole_exception)
app.add_exception_handler(HTTPException, handle_http_exception)
app.add_exception_handler(Exception, handle_generic_exception)

# Serve HTML files
_dashboard_dir = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
async def serve_index():
    """Serve main dashboard UI with API key injected server-side."""
    html_path = os.path.join(_dashboard_dir, "index.html")
    with open(html_path, 'r') as f:
        html_content = f.read()
    # Inject API key and version as meta tags so no unauthenticated endpoint is needed
    import html as html_mod
    meta_tags = (
        f'<meta name="api-key" content="{html_mod.escape(CONFIG["api_key"])}">'
        f'<meta name="app-version" content="{html_mod.escape(read_version_string())}">'
    )
    html_content = html_content.replace('</head>', f'{meta_tags}\n</head>', 1)
    return HTMLResponse(content=html_content)

@app.get("/settings.html")
async def serve_settings():
    """Serve settings UI with API key injected server-side."""
    html_path = os.path.join(_dashboard_dir, "settings.html")
    with open(html_path, 'r') as f:
        html_content = f.read()
    import html as html_mod
    meta_tags = (
        f'<meta name="api-key" content="{html_mod.escape(CONFIG["api_key"])}">'
        f'<meta name="app-version" content="{html_mod.escape(read_version_string())}">'
    )
    html_content = html_content.replace('</head>', f'{meta_tags}\n</head>', 1)
    return HTMLResponse(content=html_content)


@app.get("/api/client-config", response_model=ClientConfigResponse, tags=["System"],
         dependencies=[Depends(verify_api_key)])
async def get_client_config():
    """
    Get client configuration for the dashboard UI.

    Requires valid API key. The key is injected server-side via meta tags
    so this endpoint is only used as a fallback / verification.
    """
    return {
        "api_key": CONFIG["api_key"],
        "version": read_version_string()
    }

@app.get("/api/version", response_model=VersionResponse, tags=["System"])
async def get_version(api_key: str = Depends(verify_api_key)):
    """
    Get current Pi-hole Sentinel version.

    Returns the version number from the VERSION file. Checks multiple locations
    including dev environment and production paths.

    Security:
        - X-API-Key header required

    Returns:
        VersionResponse: Contains the current version string
    """
    return {"version": read_version_string()}


# Cache for update checks (avoid spamming GitHub API)
_update_cache = {
    "last_check": None,
    "latest_version": None,
    "release_url": None,
    "check_interval": 6 * 60 * 60  # 6 hours in seconds
}

@app.get("/api/check-update", response_model=UpdateCheckResponse, tags=["System"])
async def check_for_updates(api_key: str = Security(verify_api_key)):
    """
    Check GitHub for available Pi-hole Sentinel updates.

    Queries the GitHub API to find the latest release version. Results are cached
    for 6 hours to avoid rate limiting. Requires valid API key authentication.

    Security:
        - X-API-Key header required
        - GitHub API calls are rate-limited

    Returns:
        UpdateCheckResponse: Current version, latest version, and update URL
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
    """Initialize SQLite database with N-node normalized schema
    
    Supports migration from old 2-node schema to new normalized schema.
    - New schema: poll_cycles + node_status (normalized, extensible)
    - Old schema: status_history (2-node hardcoded, kept for backward compat)
    """
    async with aiosqlite.connect(CONFIG["db_path"]) as db:
        # Check if we need to migrate from old schema
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='status_history'"
        )
        old_table_exists = await cursor.fetchone() is not None
        
        # Create new normalized tables
        await db.execute("""
            CREATE TABLE IF NOT EXISTS poll_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                dhcp_leases INTEGER DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS node_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id INTEGER NOT NULL,
                node_index INTEGER NOT NULL,
                node_name TEXT NOT NULL,
                vrrp_state TEXT,  -- MASTER, BACKUP, FAULT
                has_vip BOOLEAN DEFAULT 0,
                online BOOLEAN DEFAULT 0,
                pihole_ok BOOLEAN DEFAULT 0,
                dns_ok BOOLEAN DEFAULT 0,
                dhcp_ok BOOLEAN DEFAULT 0,
                FOREIGN KEY(poll_id) REFERENCES poll_cycles(id),
                UNIQUE(poll_id, node_index)
            )
        """)

        # Create old table for backward compat (if it doesn't exist yet)
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
        await db.execute("CREATE INDEX IF NOT EXISTS idx_poll_cycles_timestamp ON poll_cycles(timestamp DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_node_status_poll_id ON node_status(poll_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_node_status_node_index ON node_status(node_index)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_status_timestamp ON status_history(timestamp DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type, timestamp DESC)")

        await db.commit()
        
        # Migrate old data if needed (one-time operation)
        if old_table_exists:
            await _migrate_old_schema_to_new()


async def _migrate_old_schema_to_new():
    """Migrate data from old 2-node schema to new N-node normalized schema
    
    Conversion pattern:
    - 1 old status_history row → 1 poll_cycles row + 2 node_status rows
    - Preserves all data and timestamps
    """
    logger.info("Starting database migration: old 2-node schema → new N-node schema")
    
    try:
        async with aiosqlite.connect(CONFIG["db_path"]) as db:
            # Check if migration already done (poll_cycles has data)
            cursor = await db.execute("SELECT COUNT(*) FROM poll_cycles")
            existing_count = (await cursor.fetchone())[0]
            
            if existing_count > 0:
                logger.info(f"Migration already complete: {existing_count} poll cycles exist")
                return
            
            # Fetch all old records
            cursor = await db.execute("""
                SELECT id, timestamp, primary_state, secondary_state,
                       primary_has_vip, secondary_has_vip,
                       primary_online, secondary_online,
                       primary_pihole, secondary_pihole,
                       primary_dns, secondary_dns,
                       dhcp_leases, primary_dhcp, secondary_dhcp
                FROM status_history
                ORDER BY timestamp ASC
            """)
            rows = await cursor.fetchall()
            
            if not rows:
                logger.info("No data to migrate from old schema")
                return
            
            logger.info(f"Migrating {len(rows)} old status_history rows...")
            
            # Migrate in batches
            batch_size = 100
            for batch_start in range(0, len(rows), batch_size):
                batch = rows[batch_start:batch_start + batch_size]
                
                for row in batch:
                    (old_id, timestamp, p_state, s_state,
                     p_has_vip, s_has_vip,
                     p_online, s_online,
                     p_pihole, s_pihole,
                     p_dns, s_dns,
                     dhcp_leases, p_dhcp, s_dhcp) = row
                    
                    # Insert into poll_cycles
                    cursor = await db.execute(
                        """INSERT INTO poll_cycles (timestamp, dhcp_leases)
                           VALUES (?, ?)""",
                        (timestamp, dhcp_leases or 0)
                    )
                    poll_id = cursor.lastrowid
                    
                    # Insert primary node (index 1)
                    await db.execute("""
                        INSERT INTO node_status
                        (poll_id, node_index, node_name, vrrp_state, has_vip, online, pihole_ok, dns_ok, dhcp_ok)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (poll_id, 1, "Primary", p_state,
                          p_has_vip, p_online, p_pihole, p_dns, p_dhcp))
                    
                    # Insert secondary node (index 2)
                    await db.execute("""
                        INSERT INTO node_status
                        (poll_id, node_index, node_name, vrrp_state, has_vip, online, pihole_ok, dns_ok, dhcp_ok)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (poll_id, 2, "Secondary", s_state,
                          s_has_vip, s_online, s_pihole, s_dns, s_dhcp))
                
                await db.commit()
                logger.info(f"Migrated {min(batch_start + batch_size, len(rows))}/{len(rows)} rows...")
            
            logger.info(f"✅ Migration complete: {len(rows)} old records migrated to new schema")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        raise


async def cleanup_old_data():
    """Remove old status history and events to prevent database growth."""
    retention_days_history = int(os.getenv('RETENTION_DAYS_HISTORY', '30'))
    retention_days_events = int(os.getenv('RETENTION_DAYS_EVENTS', '90'))

    cutoff_history = datetime.now() - timedelta(days=retention_days_history)
    cutoff_events = datetime.now() - timedelta(days=retention_days_events)

    try:
        async with aiosqlite.connect(CONFIG["db_path"]) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='poll_cycles'"
            )
            has_poll_cycles = await cursor.fetchone() is not None

            # Delete old poll_cycles records (and cascade to node_status via FK)
            batch_size = 5000
            total_history = 0
            if has_poll_cycles:
                while True:
                    cursor = await db.execute(
                        "DELETE FROM poll_cycles WHERE rowid IN "
                        "(SELECT rowid FROM poll_cycles WHERE timestamp < ? LIMIT ?)",
                        (cutoff_history.isoformat(), batch_size)
                    )
                    deleted = cursor.rowcount
                    total_history += deleted
                    if deleted < batch_size:
                        break
                    await db.commit()
                    await asyncio.sleep(0.1)  # Yield between batches
            else:
                while True:
                    cursor = await db.execute(
                        "DELETE FROM status_history WHERE rowid IN "
                        "(SELECT rowid FROM status_history WHERE timestamp < ? LIMIT ?)",
                        (cutoff_history.isoformat(), batch_size)
                    )
                    deleted = cursor.rowcount
                    total_history += deleted
                    if deleted < batch_size:
                        break
                    await db.commit()
                    await asyncio.sleep(0.1)

            # Delete old events in batches
            total_events = 0
            while True:
                cursor = await db.execute(
                    "DELETE FROM events WHERE rowid IN "
                    "(SELECT rowid FROM events WHERE timestamp < ? LIMIT ?)",
                    (cutoff_events.isoformat(), batch_size)
                )
                deleted = cursor.rowcount
                total_events += deleted
                if deleted < batch_size:
                    break
                await db.commit()
                await asyncio.sleep(0.1)

            await db.commit()

            logger.info(
                f"Database cleanup completed: "
                f"removed {total_history} {'poll_cycles (+ node_status)' if has_poll_cycles else 'status_history'} rows (>{retention_days_history} days), "
                f"removed {total_events} event rows (>{retention_days_events} days)"
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
        "dhcp_enabled": None
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
                    result["queries"] = stats.get("queries", {}).get("total", 0)
                    result["blocked"] = stats.get("queries", {}).get("blocked", 0)
                    result["clients"] = stats.get("clients", {}).get("total", 0)
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
                        result["dhcp_enabled"] = None
                        logger.debug(f"DHCP config API returned status {dhcp_resp.status} for {ip}")
            except Exception as e:
                logger.debug(f"DHCP config check exception for {ip}: {e}")
                result["dhcp_enabled"] = None

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

async def check_dns(ip: str) -> Tuple[bool, Optional[float]]:
    """Check if DNS resolver is working and measure response latency.

    Uses asyncio subprocess to avoid blocking the event loop.

    Returns:
        Tuple[bool, Optional[float]]: (success, latency_ms)
            latency_ms is None on failure.
    """
    try:
        t_start = asyncio.get_running_loop().time()
        proc = await asyncio.create_subprocess_exec(
            "/usr/bin/dig", "+short", "+time=2", f"@{ip}", "google.com",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
        latency_ms = (asyncio.get_running_loop().time() - t_start) * 1000
        ok = proc.returncode == 0 and len(stdout.decode().strip()) > 0
        return ok, round(latency_ms, 1) if ok else None
    except asyncio.TimeoutError:
        logger.debug(f"DNS check timeout for {ip}")
        return False, None
    except Exception as e:
        logger.debug(f"DNS check error for {ip}: {e}")
        return False, None

def _extract_mac_from_arp(output: str) -> Optional[str]:
    """Extract MAC address from `ip neigh show` output."""
    parts = output.split()
    try:
        lladdr_idx = parts.index('lladdr')
        return parts[lladdr_idx + 1].upper()
    except (ValueError, IndexError):
        return None


async def check_who_has_vip(
    vip: str,
    primary_ip: str | list[str],
    secondary_ip: Optional[str] = None,
    max_retries: int = 3,
) -> tuple:
    """
    Check which Pi-hole node has the VIP by comparing MAC addresses.

    Backward compatible with the legacy 2-node signature:
    - check_who_has_vip(vip, primary_ip, secondary_ip)

    New N-node form:
    - check_who_has_vip(vip, [ip1, ip2, ip3, ...])
    """
    if isinstance(primary_ip, list):
        node_ips = primary_ip
    else:
        node_ips = [primary_ip]
        if secondary_ip is not None:
            node_ips.append(secondary_ip)

    for attempt in range(max_retries):
        try:
            for ip in [vip, *node_ips]:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.settimeout(1)
                        sock.connect_ex((ip, 80))
                except (OSError, socket.error):
                    pass

            await asyncio.sleep(0.2)

            async def get_arp_entry(ip_addr: str) -> str:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "/usr/sbin/ip", "neigh", "show", ip_addr,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, _stderr = await asyncio.wait_for(proc.communicate(), timeout=2)
                    return stdout.decode()
                except Exception:
                    return ""

            outputs = await asyncio.gather(get_arp_entry(vip), *[get_arp_entry(ip) for ip in node_ips])
            vip_output = outputs[0]
            node_outputs = outputs[1:]

            vip_mac = _extract_mac_from_arp(vip_output)
            node_macs = [_extract_mac_from_arp(output) for output in node_outputs]

            logger.debug(
                f"VIP check (attempt {attempt + 1}/{max_retries}): VIP_MAC={vip_mac}, NODE_MACS={node_macs}"
            )

            if not vip_mac:
                logger.warning(
                    f"VIP {vip} has no ARP entry (attempt {attempt + 1}/{max_retries}) - possible keepalived failure"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                return tuple(False for _ in node_ips)

            matches = [bool(node_mac and vip_mac == node_mac) for node_mac in node_macs]
            return tuple(matches)

        except Exception as e:
            logger.error(f"Error checking VIP (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            else:
                return tuple(False for _ in node_ips)

    return tuple(False for _ in node_ips)

async def log_event(event_type: str, message: str):
    async with aiosqlite.connect(CONFIG["db_path"]) as db:
        await db.execute("INSERT INTO events (event_type, message) VALUES (?, ?)", (event_type, message))
        await db.commit()


def collect_node_issues(node_label: str, node_data: dict, dns_ok: bool) -> List[str]:
    """Build a short list of user-facing health issues for a node."""
    issues: List[str] = []

    if not node_data.get("online", False):
        return [f"{node_label} host is offline"]

    if not node_data.get("pihole", False):
        issues.append(f"Pi-hole service on {node_label} is down")

    if dns_ok is False:
        issues.append(f"DNS resolution on {node_label} is failing")

    return issues


def describe_master_transition(
    previous_master: Optional[str],
    current_master: str,
    primary_data: dict,
    secondary_data: dict,
    primary_dns: bool,
    secondary_dns: bool,
    previous_primary_online: Optional[bool],
    previous_primary_pihole: Optional[bool],
    previous_primary_dns: Optional[bool],
) -> Tuple[str, str]:
    """Classify a MASTER switch as failover or recovery and explain why."""
    primary_issues = collect_node_issues("Primary", primary_data, primary_dns)
    secondary_issues = collect_node_issues("Secondary", secondary_data, secondary_dns)

    if current_master == "secondary":
        if primary_issues:
            return "failover", "; ".join(primary_issues)
        return "failover", "Primary lost VIP; keepalived switched MASTER to Secondary"

    if current_master == "primary" and previous_master == "secondary":
        if secondary_issues:
            return "failover", "; ".join(secondary_issues)

        recovered_signals = []
        if previous_primary_online is False and primary_data.get("online", False):
            recovered_signals.append("host back online")
        if previous_primary_pihole is False and primary_data.get("pihole", False):
            recovered_signals.append("Pi-hole service restored")
        if previous_primary_dns is False and primary_dns:
            recovered_signals.append("DNS restored")

        if recovered_signals:
            signals_str = ", ".join(recovered_signals)
            return "recovery", signals_str[0].upper() + signals_str[1:]

        return "recovery", "Primary preempted, no issue detected on Secondary"

    return "failover", "MASTER changed"

# Latest Pi-hole stats — updated every poll cycle, served via /api/status
_pihole_stats = {
    "primary": {"queries": 0, "blocked": 0, "clients": 0, "dns_latency_ms": None},
    "secondary": {"queries": 0, "blocked": 0, "clients": 0, "dns_latency_ms": None},
}
# Track previous latency-degraded state per node for event dedup
_dns_degraded: set = set()  # "primary"/"secondary" when latency > DNS_LATENCY_WARN_MS

# ── Test / simulate-outage mode ──────────────────────────────────────────────
# Only active when DEBUG_MODE=true in .env. Lets operators force a node
# offline without touching the real Pi-holes (auto-expires after 10 min).
DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"
_OVERRIDE_TTL_SECONDS = 600  # 10 minutes safety auto-expire
_debug_overrides: dict = {}  # "primary"/"secondary" → {"state": "offline", "expires": float}

async def monitor_loop():
    nodes = _init_nodes()
    previous_states: dict[int, str] = {}
    previous_online: dict[int, bool] = {}
    previous_pihole: dict[int, bool] = {}
    previous_dns: dict[int, bool] = {}
    previous_has_vip: dict[int, bool] = {}
    startup = True

    def _node_role(index: int) -> str:
        if index == 1:
            return "primary"
        if index == 2:
            return "secondary"
        return f"node_{index}"

    def _node_label(node: dict) -> str:
        return node.get("name") or f"Node {node.get('index', '?')}"

    while True:
        try:
            node_payloads = await asyncio.gather(
                *[check_pihole_simple(node["ip"], node["password"]) for node in nodes]
            )

            if DEBUG_MODE:
                now_ts = asyncio.get_running_loop().time()
                for node, node_data in zip(nodes, node_payloads):
                    role = _node_role(node["index"])
                    override = _debug_overrides.get(role)
                    if override and now_ts < override["expires"]:
                        node_data.update({"online": False, "pihole": False, "dns": False, "dhcp_enabled": None})
                    elif override:
                        _debug_overrides.pop(role, None)

            for role, node_data in zip(("primary", "secondary"), node_payloads[:2]):
                for key in ("queries", "blocked", "clients"):
                    _pihole_stats[role][key] = node_data.get(key, 0)

            dns_results = await asyncio.gather(
                *[
                    check_dns(node["ip"]) if node_data["online"] else asyncio.sleep(0, result=(False, None))
                    for node, node_data in zip(nodes, node_payloads)
                ]
            )

            node_states: list[dict] = []
            for node, node_data, (dns_ok, dns_latency) in zip(nodes, node_payloads, dns_results):
                role = _node_role(node["index"])
                node_name = _node_label(node)
                node_data["dns"] = dns_ok
                node_data["dns_latency_ms"] = dns_latency
                if role in ("primary", "secondary"):
                    _pihole_stats[role]["dns_latency_ms"] = dns_latency

                if dns_ok and dns_latency is not None and dns_latency > DNS_LATENCY_WARN_MS:
                    if role not in _dns_degraded:
                        _dns_degraded.add(role)
                        await log_event("warning", f"DNS latency degraded on {node_name}: {dns_latency:.0f} ms (threshold {DNS_LATENCY_WARN_MS:.0f} ms)")
                        logger.warning(f"{node_name} DNS latency degraded: {dns_latency:.0f} ms")
                elif role in _dns_degraded and dns_ok and dns_latency is not None and dns_latency <= DNS_LATENCY_WARN_MS:
                    _dns_degraded.discard(role)
                    await log_event("success", f"DNS latency restored on {node_name}: {dns_latency:.0f} ms")
                    logger.info(f"{node_name} DNS latency restored")
                elif role in _dns_degraded and (not dns_ok or dns_latency is None):
                    _dns_degraded.discard(role)

                node_states.append({
                    "index": node["index"],
                    "role": role,
                    "name": node_name,
                    "ip": node["ip"],
                    "state": "BACKUP",
                    "has_vip": False,
                    "online": node_data["online"],
                    "pihole": node_data["pihole"],
                    "dns": dns_ok,
                    "dns_latency_ms": dns_latency,
                    "dhcp": node_data.get("dhcp_enabled"),
                    "queries": node_data.get("queries", 0),
                    "blocked": node_data.get("blocked", 0),
                    "clients": node_data.get("clients", 0),
                    "dhcp_leases": node_data.get("dhcp_leases", 0),
                })

            vip_hits = await check_who_has_vip(CONFIG["vip"], [node["ip"] for node in nodes])
            vip_hits = list(vip_hits)[:len(node_states)]
            if len(vip_hits) < len(node_states):
                vip_hits.extend([False] * (len(node_states) - len(vip_hits)))

            for node_state, has_vip in zip(node_states, vip_hits):
                node_state["has_vip"] = has_vip
                node_state["state"] = "MASTER" if has_vip else "BACKUP"

            current_master = next((node for node in node_states if node["has_vip"]), None)
            current_master_index = current_master["index"] if current_master else None
            current_master_name = current_master["name"] if current_master else "No MASTER"
            previous_master_index = next((index for index, state in previous_states.items() if state == "MASTER"), None)
            previous_master_name = next((node["name"] for node in node_states if node["index"] == previous_master_index), None)

            if startup:
                if current_master:
                    await log_event("info", f"Monitor started - {current_master_name} is MASTER")
                else:
                    await log_event("warning", "Monitor started - no MASTER detected")

                for node_state in node_states[:2]:
                    await log_event(
                        "info",
                        f"{node_state['name']}: {'Online' if node_state['online'] else 'Offline'}, Pi-hole: {'OK' if node_state['pihole'] else 'Down'}",
                    )

                await send_notification("startup", {
                    "master": current_master_name,
                    "backup": next((node["name"] for node in node_states if not node["has_vip"]), current_master_name),
                    "primary": node_states[0]["name"] if node_states else "Primary Pi-hole",
                    "secondary": node_states[1]["name"] if len(node_states) > 1 else (node_states[0]["name"] if node_states else "Secondary Pi-hole"),
                    "nodes": node_states,
                    "vip": CONFIG["vip"],
                    "vip_address": CONFIG["vip"],
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                })
                startup = False

            for node_state in node_states:
                node_key = f"node_{node_state['index']}"
                node_label = node_state["name"]

                if node_state["online"]:
                    if node_key in _offline_since:
                        was_logged = node_key in _offline_event_logged
                        _offline_since.pop(node_key, None)
                        _offline_event_logged.discard(node_key)
                        if was_logged:
                            await _cancel_fault(node_key, {
                                "node": node_label,
                                "node_name": node_label,
                                "master": current_master_name,
                                "backup": next((n["name"] for n in node_states if n["index"] != node_state["index"]), node_label),
                                "primary": node_states[0]["name"] if node_states else "Primary Pi-hole",
                                "secondary": node_states[1]["name"] if len(node_states) > 1 else (node_states[0]["name"] if node_states else "Secondary Pi-hole"),
                                "reason": f"{node_label} is back online",
                                "vip": CONFIG["vip"],
                                "vip_address": CONFIG["vip"],
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "date": datetime.now().strftime("%Y-%m-%d"),
                            })
                            await log_event("success", f"{node_label} is back ONLINE")
                            logger.info(f"{node_label} is back ONLINE")
                        else:
                            _cancel_fault_pending(node_key)
                            logger.debug(f"{node_label} recovered within debounce window, suppressing event")
                else:
                    if previous_online.get(node_state["index"]) is not None and node_key not in _offline_since:
                        _offline_since[node_key] = datetime.now()
                        logger.debug(f"{node_label} went offline, starting {EVENT_DEBOUNCE_SECONDS}s debounce")
                    elif node_key in _offline_since and node_key not in _offline_event_logged:
                        elapsed = (datetime.now() - _offline_since[node_key]).total_seconds()
                        if elapsed >= EVENT_DEBOUNCE_SECONDS:
                            _offline_event_logged.add(node_key)
                            await log_event("warning", f"{node_label} went OFFLINE")
                            logger.warning(f"{node_label} went OFFLINE")
                            _arm_fault(node_key, {
                                "node": node_label,
                                "node_name": node_label,
                                "primary": node_states[0]["name"] if node_states else "Primary Pi-hole",
                                "secondary": node_states[1]["name"] if len(node_states) > 1 else (node_states[0]["name"] if node_states else "Secondary Pi-hole"),
                                "reason": f"{node_label} is unreachable",
                                "vip": CONFIG["vip"],
                                "vip_address": CONFIG["vip"],
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "date": datetime.now().strftime("%Y-%m-%d"),
                            })

            for node_state in node_states:
                node_key = f"node_{node_state['index']}"

                if not node_state["online"]:
                    _pihole_down_since.pop(node_key, None)
                    continue

                if node_state["pihole"]:
                    if node_key in _pihole_down_since:
                        was_logged = node_key in _pihole_down_event_logged
                        _pihole_down_since.pop(node_key, None)
                        _pihole_down_event_logged.discard(node_key)
                        if was_logged:
                            await _cancel_fault(node_key, {
                                "node": node_state["name"],
                                "node_name": node_state["name"],
                                "master": current_master_name,
                                "backup": next((n["name"] for n in node_states if n["index"] != node_state["index"]), node_state["name"]),
                                "primary": node_states[0]["name"] if node_states else "Primary Pi-hole",
                                "secondary": node_states[1]["name"] if len(node_states) > 1 else (node_states[0]["name"] if node_states else "Secondary Pi-hole"),
                                "reason": f"Pi-hole service on {node_state['name']} is back up",
                                "vip": CONFIG["vip"],
                                "vip_address": CONFIG["vip"],
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "date": datetime.now().strftime("%Y-%m-%d"),
                            })
                            await log_event("success", f"Pi-hole service on {node_state['name']} is back UP")
                            logger.info(f"{node_state['name']} Pi-hole service is back UP")
                        else:
                            _cancel_fault_pending(node_key)
                            logger.debug(f"{node_state['name']} Pi-hole recovered within debounce window")
                    elif previous_pihole.get(node_state["index"]) is False:
                        _cancel_fault_pending(node_key)
                else:
                    if previous_pihole.get(node_state["index"]) is not None and node_key not in _pihole_down_since:
                        _pihole_down_since[node_key] = datetime.now()
                        logger.debug(f"{node_state['name']} Pi-hole service went down, starting {EVENT_DEBOUNCE_SECONDS}s debounce")
                    elif node_key in _pihole_down_since and node_key not in _pihole_down_event_logged:
                        elapsed = (datetime.now() - _pihole_down_since[node_key]).total_seconds()
                        if elapsed >= EVENT_DEBOUNCE_SECONDS:
                            _pihole_down_event_logged.add(node_key)
                            await log_event("warning", f"Pi-hole service on {node_state['name']} is DOWN")
                            logger.warning(f"{node_state['name']} Pi-hole service is DOWN")
                            _arm_fault(node_key, {
                                "node": node_state["name"],
                                "node_name": node_state["name"],
                                "primary": node_states[0]["name"] if node_states else "Primary Pi-hole",
                                "secondary": node_states[1]["name"] if len(node_states) > 1 else (node_states[0]["name"] if node_states else "Secondary Pi-hole"),
                                "reason": f"Pi-hole service on {node_state['name']} is down",
                                "vip": CONFIG["vip"],
                                "vip_address": CONFIG["vip"],
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "date": datetime.now().strftime("%Y-%m-%d"),
                            })

            previous_vip_owner = next((index for index, state in previous_states.items() if state == "MASTER"), None)
            if previous_vip_owner is not None and previous_vip_owner != current_master_index:
                if len(node_states) == 2:
                    transition_event, reason = describe_master_transition(
                        "primary" if previous_vip_owner == 1 else "secondary",
                        "primary" if current_master_index == 1 else "secondary",
                        node_payloads[0],
                        node_payloads[1],
                        node_states[0]["dns"],
                        node_states[1]["dns"],
                        previous_online.get(1),
                        previous_pihole.get(1),
                        previous_dns.get(1),
                    )
                else:
                    transition_event = "failover"
                    reason = f"MASTER changed from {previous_master_name or 'unknown'} to {current_master_name}"

                master_name = current_master_name
                if transition_event == "recovery":
                    await log_event("recovery", f"{master_name} reclaimed MASTER")
                    logger.info(f"RECOVERY: {master_name} reclaimed MASTER")
                    await log_event("info", f"Recovery reason: {reason}")
                else:
                    await log_event("failover", f"{master_name} became MASTER")
                    logger.warning(f"FAILOVER: {master_name} is now MASTER")
                    await log_event("info", f"Failover reason: {reason}")

                backup_name = next((node["name"] for node in node_states if node["index"] != current_master_index), master_name)
                template_vars = {
                    "node_name": master_name,
                    "node": master_name,
                    "master": master_name,
                    "backup": backup_name,
                    "primary": node_states[0]["name"] if node_states else "Primary Pi-hole",
                    "secondary": node_states[1]["name"] if len(node_states) > 1 else (node_states[0]["name"] if node_states else "Secondary Pi-hole"),
                    "nodes": node_states,
                    "reason": reason,
                    "vip_address": CONFIG["vip"],
                    "vip": CONFIG["vip"],
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                }
                await send_notification(transition_event, template_vars)
                notification_state["active_issues"]["failover"] = transition_event == "failover"

            if previous_vip_owner is not None and previous_vip_owner != current_master_index:
                if current_master_index == 1:
                    notification_state["active_issues"]["failover"] = False
                    notification_state["active_issues"]["fault"] = False

            all_offline = all(not node["online"] for node in node_states)
            all_pihole_down = all(not node["pihole"] for node in node_states)
            notification_state["active_issues"]["fault"] = all_offline or all_pihole_down

            dhcp_leases = 0
            if current_master is not None:
                dhcp_leases = current_master.get("dhcp_leases", 0)
            else:
                dhcp_leases = max((node["dhcp_leases"] for node in node_states), default=0)

            async with aiosqlite.connect(CONFIG["db_path"]) as db:
                poll_cursor = await db.execute(
                    "INSERT INTO poll_cycles (dhcp_leases) VALUES (?)",
                    (dhcp_leases,)
                )
                poll_id = poll_cursor.lastrowid

                for node_state in node_states:
                    await db.execute("""
                        INSERT INTO node_status
                        (poll_id, node_index, node_name, vrrp_state, has_vip, online, pihole_ok, dns_ok, dhcp_ok)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        poll_id,
                        node_state["index"],
                        node_state["name"],
                        node_state["state"],
                        node_state["has_vip"],
                        node_state["online"],
                        node_state["pihole"],
                        node_state["dns"],
                        bool(node_state.get("dhcp")) if node_state.get("dhcp") is not None else False,
                    ))

                legacy_primary = node_states[0] if node_states else None
                legacy_secondary = node_states[1] if len(node_states) > 1 else legacy_primary
                if legacy_primary and legacy_secondary:
                    await db.execute("""
                        INSERT INTO status_history (primary_state, secondary_state, primary_has_vip, secondary_has_vip, primary_online, secondary_online, primary_pihole, secondary_pihole, primary_dns, secondary_dns, dhcp_leases, primary_dhcp, secondary_dhcp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        legacy_primary["state"],
                        legacy_secondary["state"],
                        legacy_primary["has_vip"],
                        legacy_secondary["has_vip"],
                        legacy_primary["online"],
                        legacy_secondary["online"],
                        legacy_primary["pihole"],
                        legacy_secondary["pihole"],
                        legacy_primary["dns"],
                        legacy_secondary["dns"],
                        dhcp_leases,
                        bool(legacy_primary.get("dhcp")) if legacy_primary.get("dhcp") is not None else False,
                        bool(legacy_secondary.get("dhcp")) if legacy_secondary.get("dhcp") is not None else False,
                    ))

                await db.commit()

            current_time = time.time()
            if not hasattr(monitor_loop, "_state"):
                monitor_loop._state = {"last_dhcp_warning": current_time}

            primary_dhcp = node_states[0].get("dhcp") if node_states else None
            secondary_dhcp = node_states[1].get("dhcp") if len(node_states) > 1 else None
            await _update_dhcp_auto_detection(primary_dhcp, secondary_dhcp)

            if _dhcp_auto_detected:
                should_warn = (current_time - monitor_loop._state["last_dhcp_warning"]) > 300
                misconfigured_msg = None
                for node_state in node_states:
                    dhcp_enabled = node_state.get("dhcp")
                    if dhcp_enabled is None:
                        continue
                    if node_state["state"] == "MASTER" and not dhcp_enabled:
                        misconfigured_msg = f"⚠️ DHCP misconfiguration: {node_state['name']} is MASTER but DHCP is DISABLED"
                        break
                    if node_state["state"] == "BACKUP" and dhcp_enabled:
                        misconfigured_msg = f"⚠️ DHCP misconfiguration: {node_state['name']} is BACKUP but DHCP is ENABLED"
                        break

                if misconfigured_msg and should_warn:
                    await log_event("warning", misconfigured_msg)
                    logger.warning(misconfigured_msg)
                    monitor_loop._state["last_dhcp_warning"] = current_time
                elif misconfigured_msg and not should_warn:
                    logger.debug(f"Suppressing DHCP warning (debounce): {misconfigured_msg}")

            logger.debug(
                f"[{datetime.now()}] "
                + ", ".join(f"{node['name']}: {node['state']}" for node in node_states)
                + f", Leases: {dhcp_leases}"
            )

            previous_states = {node["index"]: node["state"] for node in node_states}
            previous_online = {node["index"]: node["online"] for node in node_states}
            previous_pihole = {
                node["index"]: node["pihole"]
                for node in node_states
                if node["online"]
            }
            previous_dns = {
                node["index"]: node["dns"]
                for node in node_states
                if node["online"]
            }
            previous_has_vip = {node["index"]: node["has_vip"] for node in node_states}

        except Exception as e:
            logger.error(f"Error in monitor loop: {e}", exc_info=True)
            await log_event("error", f"Monitor error: {str(e)}")
        await asyncio.sleep(CONFIG["check_interval"])


# ============================================================================
# Debug / Test-mode endpoints  (only active when DEBUG_MODE=true)
# ============================================================================

class DebugOverrideRequest(BaseModel):
    """Request body for test-mode node override."""
    node: str = Field(..., description="Which node to override: 'primary' or 'secondary'")
    force_state: str = Field(..., description="'offline' to simulate outage, 'reset' to clear override")


@app.post("/api/debug/override", tags=["Debug"])
async def set_debug_override(
    request: DebugOverrideRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Simulate a node outage for testing failover without touching real Pi-holes.

    Security:
        - Requires DEBUG_MODE=true in .env (disabled by default in production)
        - Requires X-API-Key header
        - Override auto-expires after 10 minutes

    Args:
        request: node ('primary'/'secondary') and force_state ('offline'/'reset')

    Returns:
        JSON with active status and expiry time
    """
    if not DEBUG_MODE:
        raise HTTPException(status_code=403, detail="Debug mode is disabled. Set DEBUG_MODE=true in .env to enable.")

    if request.node not in ("primary", "secondary"):
        raise HTTPException(status_code=422, detail="node must be 'primary' or 'secondary'")

    if request.force_state == "offline":
        expires_at = asyncio.get_running_loop().time() + _OVERRIDE_TTL_SECONDS
        _debug_overrides[request.node] = {"state": "offline", "expires": expires_at}
        expires_iso = (datetime.now() + timedelta(seconds=_OVERRIDE_TTL_SECONDS)).isoformat()
        await log_event("warning", f"[TEST MODE] {request.node.capitalize()} forced offline via debug override (expires {expires_iso})")
        logger.warning(f"[TEST MODE] {request.node} forced offline (expires {expires_iso})")
        return {"active": True, "node": request.node, "state": "offline", "expires": expires_iso}

    elif request.force_state == "reset":
        removed = _debug_overrides.pop(request.node, None)
        if removed:
            await log_event("info", f"[TEST MODE] {request.node.capitalize()} debug override cleared")
            logger.info(f"[TEST MODE] {request.node} override cleared")
        return {"active": False, "node": request.node, "state": "reset"}

    raise HTTPException(status_code=422, detail="force_state must be 'offline' or 'reset'")


@app.get("/api/debug/override/status", tags=["Debug"])
async def get_debug_override_status(api_key: str = Depends(verify_api_key)):
    """
    Get current test-mode override status for all nodes.

    Security:
        - Requires X-API-Key header

    Returns:
        Current debug-mode status and per-node override state. When DEBUG_MODE is
        disabled, this endpoint still returns 200 so dashboard polling does not
        generate continuous 403 responses and warning logs.
    """
    result = {}
    if not DEBUG_MODE:
        for node in ("primary", "secondary"):
            result[node] = {"active": False}
        return {"debug_mode": False, "overrides": result}

    now_ts = asyncio.get_running_loop().time()
    for node in ("primary", "secondary"):
        override = _debug_overrides.get(node)
        if override and now_ts < override["expires"]:
            remaining = int(override["expires"] - now_ts)
            result[node] = {"active": True, "state": override["state"], "remaining_seconds": remaining}
        else:
            result[node] = {"active": False}
    return {"debug_mode": DEBUG_MODE, "overrides": result}


@app.get("/api/status", response_model=StatusResponse, tags=["Status"])
async def get_status(api_key: str = Depends(verify_api_key)):
    """
    Get current Pi-hole Sentinel system status.

    Returns real-time status of both Pi-hole instances including FTL service,
    DNS resolution, DHCP status, and Virtual IP location.

    Security:
        - X-API-Key header required

    Returns:
        StatusResponse: Master/backup status, health of both nodes, VIP location

    Raises:
        HTTPException: 403 if API key invalid, 500 if database error
    """
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
                    "dhcp": bool(row[13]) if len(row) > 13 else False,  # New DHCP status
                    "queries": _pihole_stats["primary"]["queries"],
                    "blocked": _pihole_stats["primary"]["blocked"],
                    "clients": _pihole_stats["primary"]["clients"],
                    "dns_latency_ms": _pihole_stats["primary"]["dns_latency_ms"],
                },
                "secondary": {
                    "ip": CONFIG["secondary"]["ip"],
                    "name": CONFIG["secondary"]["name"],
                    "state": row[3],
                    "has_vip": bool(row[5]),
                    "online": bool(row[7]),
                    "pihole": bool(row[9]),
                    "dns": bool(row[11]) if len(row) > 11 else bool(row[7]),  # Fallback to online for backward compatibility
                    "dhcp": bool(row[14]) if len(row) > 14 else False,  # New DHCP status
                    "queries": _pihole_stats["secondary"]["queries"],
                    "blocked": _pihole_stats["secondary"]["blocked"],
                    "clients": _pihole_stats["secondary"]["clients"],
                    "dns_latency_ms": _pihole_stats["secondary"]["dns_latency_ms"],
                },
                "vip": CONFIG["vip"],
                "dhcp_leases": row[12] if len(row) > 12 else row[10],  # Adjust for new column
                "dhcp_failover": _dhcp_auto_detected,
                "dns_latency_warn_ms": DNS_LATENCY_WARN_MS,
            }

@app.get("/api/history", response_model=List[dict], tags=["History"])
async def get_history(
    hours: float = 24,
    api_key: str = Depends(verify_api_key)
):
    """
    Get historical status data for graph visualization.

    Retrieves status history for the specified time period. Useful for plotting
    VIP location changes and identifying failover patterns.

    Security:
        - X-API-Key header required

    Parameters:
        hours: Number of hours of history to retrieve (default: 24, max: 720)

    Returns:
        List of history entries with timestamps and master/backup status flags
    """
    # Cap to 30 days to prevent DoS via massive queries
    hours = max(0.25, min(hours, 720))
    async with aiosqlite.connect(CONFIG["db_path"]) as db:
        async with db.execute(
            "SELECT timestamp, primary_state, secondary_state, "
            "primary_online, secondary_online, "
            "primary_pihole, secondary_pihole, "
            "primary_dns, secondary_dns, "
            "dhcp_leases "
            "FROM status_history "
            "WHERE timestamp > datetime('now', '-' || ? || ' hours') "
            "ORDER BY timestamp ASC",
            (hours,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{
                "time": row[0],
                "primary": 1 if row[1] == "MASTER" else 0,
                "secondary": 1 if row[2] == "MASTER" else 0,
                "primary_online": 1 if row[3] else 0,
                "secondary_online": 1 if row[4] else 0,
                "primary_pihole": 1 if row[5] else 0,
                "secondary_pihole": 1 if row[6] else 0,
                "primary_dns": 1 if row[7] else 0,
                "secondary_dns": 1 if row[8] else 0,
                "dhcp_leases": row[9] or 0,
            } for row in rows]

@app.get("/api/events", response_model=EventsResponse, tags=["History"])
async def get_events(limit: int = 50, api_key: str = Depends(verify_api_key)):
    """
    Get recent system events and failover history.

    Returns a list of system events including failovers, recoveries, faults,
    and other significant state changes. Includes statistics about failover history.

    Security:
        - X-API-Key header required

    Parameters:
        limit: Maximum number of events to return (default: 50, max: 500)

    Returns:
        EventsResponse: Recent events, failover count, and last failover timestamp
    """
    safe_limit = max(1, min(limit, 500))

    async with aiosqlite.connect(CONFIG["db_path"]) as db:
        async with db.execute(
            "SELECT timestamp, event_type, message FROM events ORDER BY timestamp DESC LIMIT ?",
            (safe_limit,)
        ) as cursor:
            rows = await cursor.fetchall()

        recent_events = [
            {
                "timestamp": row[0],
                "event_type": row[1],
                "description": row[2],
                "details": None
            }
            for row in rows
        ]

        async with db.execute("SELECT COUNT(*) FROM events") as cursor:
            total_events = (await cursor.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM events WHERE event_type = 'failover'") as cursor:
            failover_count = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT timestamp FROM events WHERE event_type = 'failover' ORDER BY timestamp DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            last_failover = row[0] if row else None

        return {
            "total_events": total_events,
            "recent_events": recent_events,
            "failover_count": failover_count,
            "last_failover": last_failover
        }

@app.get("/api/notifications/settings", tags=["Notifications"])
async def get_notification_settings(api_key: str = Depends(verify_api_key)):
    """
    Get current notification settings configuration.

    Returns the notification settings with sensitive data masked (tokens replaced
    with asterisks). Useful for the settings UI to display current configuration
    without exposing secrets.

    Security:
        - X-API-Key header required
        - Sensitive tokens are masked in response

    Returns:
        dict: Notification settings with masked sensitive values
    """

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
            "failover": "🚨 Failover\n{master} is now MASTER\nReason: {reason}",
            "recovery": "✅ Recovery: {master} is now MASTER\n{reason}",
            "fault": "⚠️ FAULT: {reason}\nCheck immediately!",
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

@app.post("/api/notifications/settings", tags=["Notifications"])
async def save_notification_settings(
    request: Request,
    settings: dict,
    api_key: str = Depends(verify_api_key),
    _rate_limit: bool = Depends(write_rate_limit_check)
):
    """
    Save notification service configuration.

    Updates notification settings for services like Telegram, Discord, Pushover, Ntfy,
    and custom webhooks. Supports templated messages and event-based delivery.

    Security:
        - X-API-Key header required
        - Masked values (from GET request) are not overwritten
        - All settings stored securely

    Request Body:
        Settings dictionary with service configurations and templates

    Returns:
        dict: Operation status and message

    Raises:
        HTTPException: 403 if API key invalid, 400 if settings invalid, 500 on save error
    """

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

    # Validate webhook URLs to prevent SSRF
    for svc, url_key in [("discord", "webhook_url"), ("webhook", "url")]:
        svc_cfg = merged_settings.get(svc, {})
        url_val = svc_cfg.get(url_key, "")
        if url_val and not url_val.startswith("***") and not validate_webhook_url(url_val):
            raise HTTPException(status_code=400, detail=f"Invalid {svc} URL: only http/https to public hosts allowed")
    ntfy_server = merged_settings.get("ntfy", {}).get("server", "")
    if ntfy_server and not ntfy_server.startswith("***") and not validate_webhook_url(ntfy_server):
        raise HTTPException(status_code=400, detail="Invalid ntfy server URL: only http/https to public hosts allowed")

    def escape_for_bash_config(value):
        """Escape value for safe use in bash double-quoted string."""
        if not value:
            return ""
        s = str(value)
        # Reject control characters (newlines, carriage returns, etc.) to prevent
        # bash config injection via line breaks
        s = ''.join(c for c in s if c >= ' ' or c == '\t')
        # Escape backslashes first, then other special chars
        escaped = s.replace('\\', '\\\\')
        escaped = escaped.replace('"', '\\"')
        escaped = escaped.replace('$', '\\$')
        escaped = escaped.replace('`', '\\`')
        escaped = escaped.replace('!', '\\!')
        return escaped

    try:
        with _open_secure(config_path) as f:
            json.dump(merged_settings, f, indent=2)

        # Also update the bash config file for keepalived scripts
        bash_config = "/etc/pihole-sentinel/notify.conf"
        os.makedirs(os.path.dirname(bash_config), exist_ok=True)

        with _open_secure(bash_config) as f:
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

# ============================================================================
# System Settings (DHCP failover toggle)
# ============================================================================

def _open_secure(path: str):
    """Open a file for writing with mode 0o600 from creation (avoids TOCTOU race).

    Equivalent to open(path, 'w') + os.chmod(path, 0o600) but without the
    brief window where the file is world-readable between creation and chmod.
    """
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    return open(fd, 'w')


def _load_system_settings() -> dict:
    """Load system settings from the notification config file.

    System settings are stored under the ``system`` key inside
    ``notify_settings.json`` to avoid creating a separate config file.
    Missing keys fall back to safe defaults (DHCP failover disabled until
    auto-detection confirms DHCP is in use on at least one Pi-hole).
    """

    defaults = {"dhcp_failover": False}
    config_path = CONFIG["notify_config_path"]
    if not os.path.exists(config_path):
        return defaults
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
        system = data.get("system", {})
        return {
            "dhcp_failover": system.get("dhcp_failover", False),
        }
    except Exception:
        return defaults


def _save_system_settings(system: dict) -> None:
    """Persist *system* settings into ``notify_settings.json``."""

    config_path = CONFIG["notify_config_path"]
    config_dir = os.path.dirname(config_path)
    os.makedirs(config_dir, exist_ok=True)

    existing = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            pass

    existing["system"] = system
    with _open_secure(config_path) as f:
        json.dump(existing, f, indent=2)


# Cache for system settings — refreshed on POST and at startup
_system_settings: dict = _load_system_settings()

# ============================================================================
# DHCP Auto-Detection & SSH Push
# ============================================================================

# Auto-detected DHCP state — derived from Pi-hole API responses
_dhcp_auto_detected: bool = _system_settings.get("dhcp_failover", False)
_dhcp_detect_counter: int = 0
_DHCP_DETECT_THRESHOLD: int = 3  # require 3 consecutive identical readings


def _ssh_key_available() -> bool:
    """Check if SSH key exists for pushing config to Pi-holes."""
    return os.path.exists(CONFIG["ssh"]["key_path"])


async def _push_dhcp_config(enabled: bool) -> bool:
    """Push DHCP_ENABLED value to keepalived .env on both Pi-holes via SSH.

    Returns True if at least one push succeeded.
    """
    if not _ssh_key_available():
        logger.warning("SSH key not available — cannot push DHCP config to Pi-holes")
        return False

    key_path = CONFIG["ssh"]["key_path"]
    dhcp_val = "true" if enabled else "false"

    async def _push_to_node(ip: str, user: str, port: str) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "ssh",
                "-i", key_path,
                "-o", "BatchMode=yes",
                # accept-new: auto-accept on first connect, reject on change (MITM).
                # If a Pi-hole is reinstalled, remove its entry from
                # /opt/pihole-monitor/.ssh/known_hosts to restore connectivity.
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ConnectTimeout=5",
                "-p", port,
                f"{user}@{ip}",
                "--",
                f"sed -i 's/^DHCP_ENABLED=.*/DHCP_ENABLED={dhcp_val}/' /etc/keepalived/.env",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            if proc.returncode == 0:
                logger.info(f"DHCP config pushed to {ip}: DHCP_ENABLED={dhcp_val}")
                return True
            else:
                logger.error(f"SSH push to {ip} failed (rc={proc.returncode}): {stderr.decode().strip()}")
                return False
        except asyncio.TimeoutError:
            logger.error(f"SSH push to {ip} timed out")
            return False
        except Exception as e:
            logger.error(f"SSH push to {ip} error: {e}")
            return False

    results = await asyncio.gather(
        _push_to_node(
            CONFIG["primary"]["ip"],
            CONFIG["ssh"]["primary_user"],
            CONFIG["ssh"]["primary_port"],
        ),
        _push_to_node(
            CONFIG["secondary"]["ip"],
            CONFIG["ssh"]["secondary_user"],
            CONFIG["ssh"]["secondary_port"],
        ),
        return_exceptions=True,
    )

    success_count = sum(1 for r in results if r is True)
    if success_count == 0:
        logger.error("DHCP config push failed for all nodes")
    return success_count > 0


async def _update_dhcp_auto_detection(primary_dhcp, secondary_dhcp) -> None:
    """Update DHCP auto-detection state based on Pi-hole API responses.

    If either Pi-hole has DHCP active, DHCP failover is considered in use.
    State changes require _DHCP_DETECT_THRESHOLD consecutive identical readings
    (debounce) to prevent flip-flopping.

    When either reading is None (API unreachable), the poll is skipped entirely.
    This prevents API failures from being misinterpreted as "DHCP not in use"
    and incorrectly disabling keepalived DHCP failover.
    """
    global _dhcp_auto_detected, _dhcp_detect_counter, _system_settings

    # Skip when data is incomplete — "unknown" is not "disabled"
    if primary_dhcp is None or secondary_dhcp is None:
        logger.debug(
            f"DHCP detection skipped: incomplete data "
            f"(primary={primary_dhcp}, secondary={secondary_dhcp})"
        )
        return

    dhcp_in_use = primary_dhcp or secondary_dhcp

    if dhcp_in_use == _dhcp_auto_detected:
        # State matches — reset debounce counter
        _dhcp_detect_counter = 0
        return

    # State differs — increment debounce counter
    _dhcp_detect_counter += 1
    logger.debug(
        f"DHCP detection: current={_dhcp_auto_detected}, observed={dhcp_in_use}, "
        f"counter={_dhcp_detect_counter}/{_DHCP_DETECT_THRESHOLD}"
    )

    if _dhcp_detect_counter < _DHCP_DETECT_THRESHOLD:
        return

    # Threshold reached — change state
    old_state = _dhcp_auto_detected
    _dhcp_auto_detected = dhcp_in_use
    _dhcp_detect_counter = 0

    # Persist to settings file
    _system_settings["dhcp_failover"] = dhcp_in_use
    _save_system_settings(_system_settings)

    state_label = "active" if dhcp_in_use else "not in use"
    logger.info(f"DHCP auto-detection changed: {old_state} -> {dhcp_in_use} (DHCP {state_label})")
    await log_event(
        "info",
        f"DHCP failover auto-detected as {state_label} — "
        f"updating keepalived configuration on Pi-holes"
    )

    # Push to Pi-holes
    pushed = await _push_dhcp_config(dhcp_in_use)
    if not pushed:
        await log_event(
            "warning",
            "Failed to push DHCP config to Pi-holes via SSH — will retry on next detection change"
        )


@app.get("/api/settings/system", tags=["System"])
async def get_system_settings(api_key: str = Depends(verify_api_key)):
    """Return current system settings including DHCP auto-detection state."""
    return {
        "dhcp_failover": _dhcp_auto_detected,
        "dhcp_auto_detected": True,
        "ssh_available": _ssh_key_available(),
    }

class CommandRequest(BaseModel):
    command: str

@app.get("/api/commands/available", tags=["System"])
async def get_commands_available(api_key: str = Depends(verify_api_key)):
    """
    Return which system commands are available on this server.

    Commands that require keepalived (status/logs) are only meaningful on
    Pi-hole nodes. This endpoint lets the dashboard disable those buttons
    when the monitor server doesn't have keepalived installed.
    """
    import os as _os
    import subprocess

    keepalived_active = subprocess.run(
        ["systemctl", "is-active", "keepalived"], capture_output=True
    ).returncode == 0
    keepalived_log = _os.path.exists("/var/log/keepalived-notify.log")

    return {
        "monitor_status":    True,
        "monitor_logs":      True,
        "vip_check":         True,
        "db_recent_events":  True,
        "keepalived_status": keepalived_active,
        "keepalived_logs":   keepalived_active or keepalived_log,
    }


@app.post("/api/commands/{command_name}", tags=["System"])
async def execute_command(command_name: str, request: Request, api_key: str = Depends(verify_api_key), _rate_limit: bool = Depends(write_rate_limit_check)):
    """
    Execute a predefined system command and return structured output.

    Returns icon, description, exit_code, status, and output so the
    dashboard modal can render them correctly.
    """
    import os as _os
    import subprocess

    COMMAND_META = {
        "monitor_status":    {"icon": "📊", "label": "Monitor Status"},
        "monitor_logs":      {"icon": "📄", "label": "Monitor Logs (last 200)"},
        "keepalived_status": {"icon": "🔄", "label": "Keepalived Status"},
        "keepalived_logs":   {"icon": "📜", "label": "Keepalived Logs (last 200)"},
        "vip_check":         {"icon": "🌐", "label": "VIP Check"},
        "db_recent_events":  {"icon": "📝", "label": "Recent Events (last 500)"},
    }

    if command_name not in COMMAND_META:
        raise HTTPException(status_code=400, detail=f"Invalid command: {command_name}")

    meta = COMMAND_META[command_name]
    # Force ANSI colour output so the browser can render it
    colored_env = {**_os.environ, "SYSTEMD_COLORS": "1"}

    def _resp(output: str, exit_code: int = 0, status: str = None) -> JSONResponse:
        return JSONResponse({
            "icon": meta["icon"],
            "description": meta["label"],
            "exit_code": exit_code,
            "status": status or ("success" if exit_code == 0 else "error"),
            "output": output or "(No output)",
        })

    def _run(cmd, env=None, timeout=15):
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)

    try:
        if command_name == "db_recent_events":
            async with aiosqlite.connect(CONFIG["db_path"]) as db:
                async with db.execute(
                    "SELECT timestamp, event_type, message FROM events ORDER BY timestamp DESC LIMIT 500"
                ) as cursor:
                    rows = await cursor.fetchall()
            lines = [f"{r[0]} [{r[1]}] {r[2]}" for r in rows]
            return _resp("\n".join(lines) if lines else "(No events found)")

        if command_name == "vip_check":
            vip = CONFIG.get("vip", "")
            primary_ip = CONFIG.get("primary", {}).get("ip", "")
            secondary_ip = CONFIG.get("secondary", {}).get("ip", "")
            parts = []

            # VIP summary
            parts.append(f"=== VIP Configuration ===")
            parts.append(f"VIP address: {vip or '(not configured)'}")
            parts.append(f"Primary:     {primary_ip or '(not configured)'}")
            parts.append(f"Secondary:   {secondary_ip or '(not configured)'}")
            parts.append("")

            # Check which interfaces have VIP
            proc_addr = _run(["ip", "addr", "show"])
            if proc_addr.stdout and vip:
                vip_found = False
                for line in proc_addr.stdout.splitlines():
                    if vip in line:
                        vip_found = True
                        parts.append(f"=== VIP Location (on this server) ===")
                        parts.append(line.strip())
                if not vip_found:
                    parts.append("VIP is NOT assigned to this server.")
            else:
                parts.append("(Could not check VIP assignment)")

            parts.append("")

            # ARP: only show relevant entries (VIP + Pi-hole IPs)
            proc_neigh = _run(["ip", "neigh", "show"])
            if proc_neigh.stdout:
                relevant_ips = {vip, primary_ip, secondary_ip} - {""}
                arp_lines = []
                for line in proc_neigh.stdout.splitlines():
                    for ip in relevant_ips:
                        if ip and ip in line:
                            arp_lines.append(line.strip())
                            break
                if arp_lines:
                    parts.append("=== ARP Table (relevant entries) ===")
                    parts.extend(arp_lines)
                else:
                    parts.append("=== ARP Table ===")
                    parts.append("No ARP entries found for VIP/Pi-hole IPs.")

            return _resp("\n".join(parts))

        if command_name == "monitor_status":
            proc = _run(["systemctl", "status", "pihole-monitor", "--no-pager", "-l"], env=colored_env)
            output = proc.stdout + (("\n--- STDERR ---\n" + proc.stderr) if proc.stderr else "")
            # Non-zero exit codes (1=failed, 3=inactive) are valid status information
            return _resp(output, proc.returncode, "success")

        if command_name == "monitor_logs":
            proc = _run(["journalctl", "-u", "pihole-monitor", "-n", "200", "--no-pager"])
            if proc.returncode != 0 and (
                "insufficient permissions" in proc.stderr or "No journal files" in proc.stderr
            ):
                msg = (
                    "⚠️  Permission denied — the monitor service user cannot read the system journal.\n\n"
                    "Fix by running on the monitor server (as root):\n\n"
                    "    usermod -a -G systemd-journal pihole-monitor\n"
                    "    systemctl restart pihole-monitor\n\n"
                    "After restarting the service this command will work."
                )
                return _resp(msg, proc.returncode, "error")
            output = proc.stdout
            # Suppress journalctl's notice hint — not an error
            if proc.stderr and "Hint:" not in proc.stderr:
                output += "\n--- STDERR ---\n" + proc.stderr
            return _resp(output, proc.returncode)

        if command_name == "keepalived_status":
            proc = _run(["systemctl", "status", "keepalived", "--no-pager", "-l"], env=colored_env)
            combined = (proc.stdout + proc.stderr).lower()
            if proc.returncode == 4 or "could not be found" in combined or "not-found" in combined:
                primary_ip = CONFIG.get("primary", {}).get("ip", "<primary-ip>")
                secondary_ip = CONFIG.get("secondary", {}).get("ip", "<secondary-ip>")
                msg = (
                    "ℹ️  keepalived is not installed on this monitor server.\n\n"
                    "This is expected — keepalived runs on the Pi-hole nodes, not here.\n\n"
                    f"To check keepalived on your Pi-holes:\n\n"
                    f"    ssh root@{primary_ip}   systemctl status keepalived\n"
                    f"    ssh root@{secondary_ip} systemctl status keepalived"
                )
                return _resp(msg, 0, "success")
            # Keepalived found but inactive — add context
            if "inactive" in combined or "dead" in combined:
                note = (
                    "ℹ️  keepalived is installed but not running on this server.\n"
                    "If this is the monitor server, that is expected — keepalived\n"
                    "should run on the Pi-hole nodes, not on the monitor.\n\n"
                    "--- systemctl status keepalived ---\n\n"
                )
                output = note + proc.stdout
            else:
                output = proc.stdout
            if proc.stderr:
                output += "\n--- STDERR ---\n" + proc.stderr
            return _resp(output, proc.returncode, "success")

        if command_name == "keepalived_logs":
            log_path = "/var/log/keepalived-notify.log"
            if not _os.path.exists(log_path):
                primary_ip = CONFIG.get("primary", {}).get("ip", "<primary-ip>")
                secondary_ip = CONFIG.get("secondary", {}).get("ip", "<secondary-ip>")
                msg = (
                    f"ℹ️  Log file not found: {log_path}\n\n"
                    "This is expected — keepalived logs are on the Pi-hole nodes,\n"
                    "not the monitor server.\n\n"
                    f"To read the logs on your Pi-holes:\n\n"
                    f"    ssh root@{primary_ip}   tail -200 /var/log/keepalived-notify.log\n"
                    f"    ssh root@{secondary_ip} tail -200 /var/log/keepalived-notify.log"
                )
                return _resp(msg, 0, "success")
            proc = _run(["tail", "-n", "200", log_path])
            return _resp(proc.stdout or "(Log file is empty)", proc.returncode)

    except subprocess.TimeoutExpired:
        return JSONResponse({
            "icon": meta["icon"], "description": meta["label"],
            "exit_code": -1, "status": "error",
            "output": "Command timed out after 15 seconds",
        })
    except Exception as e:
        logger.error(f"Command execution error: {e}", exc_info=True)
        return JSONResponse({
            "icon": meta["icon"], "description": meta["label"],
            "exit_code": -1, "status": "error",
            "output": f"Error: {str(e)}",
        })

@app.post("/api/notifications/test", response_model=NotificationTestResponse, tags=["Notifications"])
async def test_notification(
    request: Request,
    data: dict,
    api_key: str = Depends(verify_api_key),
    _rate_limit: bool = Depends(rate_limit_check)
):
    """
    Test a notification service by sending a test message.

    Sends a test notification to the specified service to verify configuration.
    Loads unmasked settings from server, so masked values from UI are not used.

    Security:
        - X-API-Key header required
        - Rate limited: max 3 requests per 60 seconds per IP
        - Only unmasked credentials used for testing

    Request Body:
        service: Service to test (telegram, discord, pushover, ntfy, webhook)
        event_type: Optional event type for template selection

    Returns:
        NotificationTestResponse: Success status and message

    Raises:
        HTTPException: 403 if auth fails, 429 if rate limited, 400 if service invalid
    """

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
                "🚨 Failover\n"
                "Secondary Pi-hole is now MASTER\n"
                "Reason: Pi-hole service on Primary is down\n\n"
                "✅ <b>Recovery:</b>\n"
                "✅ Recovery: Primary Pi-hole is now MASTER\n"
                "Host back online, Pi-hole service restored\n\n"
                "⚠️ <b>Fault:</b>\n"
                "⚠️ FAULT: Pi-hole service on Secondary is down\n"
                "Check immediately!\n\n"
                "🚀 <b>Startup:</b>\n"
                "🚀 Pi-hole Sentinel started\n"
                "Monitoring Primary Pi-hole and Secondary Pi-hole\n\n"
                "✅ If you see this, notifications are working!"
            )

            session = await get_http_session()
            url = f"https://api.telegram.org/bot{settings['bot_token']}/sendMessage"
            async with session.post(url, json={
                'chat_id': settings['chat_id'],
                'text': test_message,
                'parse_mode': 'HTML'
            }, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    raise Exception(f"Telegram API returned {response.status}")

        elif service == 'discord':
            if not settings.get('webhook_url'):
                raise HTTPException(status_code=400, detail="Webhook URL required")

            if not validate_webhook_url(settings['webhook_url']):
                raise HTTPException(status_code=400, detail="Discord webhook URL is not allowed (SSRF protection)")
            session = await get_http_session()
            async with session.post(settings['webhook_url'], json={
                'embeds': [
                    {
                        'title': '🧪 Pi-hole Sentinel Test Notification',
                        'description': '**Default Template Examples:**',
                        'color': 3447003,
                        'fields': [
                            {
                                'name': '🚨 Failover',
                                'value': '🚨 Failover\nSecondary Pi-hole is now MASTER\nReason: Pi-hole service on Primary is down',
                                'inline': False
                            },
                            {
                                'name': '✅ Recovery',
                                'value': '✅ Recovery: Primary Pi-hole is now MASTER\nHost back online, Pi-hole service restored',
                                'inline': False
                            },
                            {
                                'name': '⚠️ Fault',
                                'value': '⚠️ FAULT: Pi-hole service on Secondary is down\nCheck immediately!',
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
            }, timeout=aiohttp.ClientTimeout(total=10)) as response:
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
                "Reason: Pi-hole service on Primary is down\n\n"
                "✅ Recovery:\n"
                "Primary Pi-hole is now MASTER\n"
                "Host back online, Pi-hole service restored\n\n"
                "⚠️ Fault:\n"
                "Pi-hole service on Secondary is down\n"
                "Check immediately!\n\n"
                "🚀 Startup:\n"
                "Pi-hole Sentinel started\n"
                "Monitoring Primary and Secondary\n\n"
                "✅ Notifications are working!"
            )

            session = await get_http_session()
            async with session.post('https://api.pushover.net/1/messages.json', data={
                'token': settings['app_token'],
                'user': settings['user_key'],
                'title': 'Pi-hole Sentinel Test',
                'message': test_message
            }, timeout=aiohttp.ClientTimeout(total=10)) as response:
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
                "🚨 Failover: Secondary Pi-hole is now MASTER (Reason: Pi-hole service on Primary is down)\n"
                "✅ Recovery: Primary Pi-hole is now MASTER (Host back online, Pi-hole service restored)\n"
                "⚠️ Fault: Pi-hole service on Secondary is down - Check immediately!\n"
                "🚀 Startup: Pi-hole Sentinel started (Monitoring Primary and Secondary)\n\n"
                "✅ If you see this, notifications are working!"
            )

            if not validate_webhook_url(server):
                raise HTTPException(status_code=400, detail="Ntfy server URL is not allowed (SSRF protection)")
            session = await get_http_session()
            async with session.post(url, data=test_message.encode('utf-8'), headers={
                'Title': 'Pi-hole Sentinel Test',
                'Priority': 'default',
                'Tags': 'white_check_mark,test_tube'
            }, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    raise Exception(f"Ntfy returned {response.status}")

        elif service == 'webhook':
            if not settings.get('url'):
                raise HTTPException(status_code=400, detail="Webhook URL required")

            if not validate_webhook_url(settings['url']):
                raise HTTPException(status_code=400, detail="Webhook URL is not allowed (SSRF protection)")
            session = await get_http_session()
            async with session.post(settings['url'], json={
                'service': 'pihole-sentinel',
                'type': 'test',
                'message': 'Test notification - Default template examples',
                'templates': {
                    'failover': '🚨 Failover: Secondary Pi-hole is now MASTER (Reason: Pi-hole service on Primary is down)',
                    'recovery': '✅ Recovery: Primary Pi-hole is now MASTER (Host back online, Pi-hole service restored)',
                    'fault': '⚠️ FAULT: Pi-hole service on Secondary is down - Check immediately!',
                    'startup': '🚀 Pi-hole Sentinel started (Monitoring Primary Pi-hole and Secondary Pi-hole)'
                },
                'status': 'Notifications are working!',
                'timestamp': datetime.now().isoformat()
            }, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status not in [200, 201, 202, 204]:
                    raise Exception(f"Webhook returned {response.status}")

        else:
            raise HTTPException(status_code=400, detail=f"Unknown service: {service}")

        return {"success": True, "message": f"Test notification sent via {service}", "service": service}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

@app.post("/api/notifications/test-template", tags=["Notifications"])
async def test_template_notification(
    request: Request,
    data: dict,
    api_key: str = Depends(verify_api_key),
    _rate_limit: bool = Depends(rate_limit_check)
):
    """
    Preview a custom notification template without sending.

    Takes a template string and template variables, performs variable substitution,
    and returns the rendered message. Useful for testing custom templates in the UI.

    Security:
        - X-API-Key header required
        - Rate limited: max 3 requests per 60 seconds per IP

    Request Body:
        template: Template string with {variable} placeholders
        variables: Dictionary of variables to substitute

    Returns:
        dict: Rendered message and status

    Raises:
        HTTPException: 403 if auth fails, 429 if rate limited, 400 if template invalid
    """
    template_type = data.get('template_type', 'failover')

    if template_type not in ['failover', 'recovery', 'fault', 'startup']:
        raise HTTPException(status_code=400, detail="Invalid template type")

    # Sample data for testing - use configured names or defaults
    primary_name = CONFIG.get('primary', {}).get('name', 'Primary-Pi-hole')
    secondary_name = CONFIG.get('secondary', {}).get('name', 'Secondary-Pi-hole')

    _reasons = {
        "failover": f"Pi-hole service on {primary_name} is down",
        "recovery": "Host back online, Pi-hole service restored",
        "fault": f"Pi-hole service on {secondary_name} is down",
        "startup": "",
    }
    _master = primary_name if template_type == 'recovery' else secondary_name
    _backup = secondary_name if template_type == 'recovery' else primary_name
    sample_vars = {
        "node_name": _master,
        "node": _master,
        "master": _master,
        "backup": _backup,
        "primary": primary_name,
        "secondary": secondary_name,
        "reason": _reasons.get(template_type, "Test notification"),
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

@app.get("/api/notifications/snooze", response_model=SnoozeResponse, tags=["Notifications"])
async def get_snooze_status(api_key: str = Depends(verify_api_key)):
    """
    Get current notification snooze status.

    Returns whether notifications are currently snoozed and when the snooze
    will expire. Automatically clears expired snoozes.

    Security:
        - X-API-Key header required

    Returns:
        SnoozeResponse: Snooze status, expiration time, and remaining duration
    """

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

                is_active = is_snoozed(settings)
                remaining = None
                if is_active and snooze.get('until'):
                    try:
                        until_dt = datetime.fromisoformat(snooze['until'].replace('Z', '+00:00'))
                        if until_dt.tzinfo:
                            until_dt = until_dt.replace(tzinfo=None)
                        remaining = max(0, int((until_dt - datetime.now()).total_seconds()))
                    except (ValueError, TypeError):
                        pass
                return {
                    "snoozed": is_active,
                    "until": snooze.get('until'),
                    "remaining_seconds": remaining
                }
        except Exception:
            pass

    return {"snoozed": False, "until": None, "remaining_seconds": None}

@app.post("/api/notifications/snooze", response_model=SnoozeResponse, tags=["Notifications"])
async def set_snooze(request: Request, data: dict, api_key: str = Depends(verify_api_key), _rate_limit: bool = Depends(write_rate_limit_check)):
    """
    Snooze notifications for a specified duration.

    Temporarily disables all notifications for the requested time period.
    Useful when performing maintenance or when receiving too many alerts.

    Security:
        - X-API-Key header required

    Request Body:
        duration: Minutes to snooze (1-1440, max 24 hours)

    Returns:
        SnoozeResponse: Updated snooze status and expiration time

    Raises:
        HTTPException: 403 if auth fails, 400 if duration invalid
    """

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
        with _open_secure(config_path) as f:
            json.dump(settings, f, indent=2)

        await log_event("info", f"🔕 Notifications snoozed until {until.strftime('%H:%M')}")
        remaining = int((until - datetime.now()).total_seconds())
        return {
            "snoozed": True,
            "until": until.isoformat(),
            "remaining_seconds": remaining
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set snooze: {str(e)}")

@app.delete("/api/notifications/snooze", response_model=SnoozeResponse, tags=["Notifications"])
async def cancel_snooze(api_key: str = Depends(verify_api_key)):
    """
    Cancel active notification snooze.

    Immediately re-enables notifications if they were previously snoozed.

    Security:
        - X-API-Key header required

    Returns:
        SnoozeResponse: Updated snooze status (should now be enabled=false)

    Raises:
        HTTPException: 403 if API key invalid, 500 on save error
    """

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
        with _open_secure(config_path) as f:
            json.dump(settings, f, indent=2)

        await log_event("info", "🔔 Snooze cancelled, notifications re-enabled")
        return {"snoozed": False, "until": None, "remaining_seconds": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel snooze: {str(e)}")

if __name__ == "__main__":
    # Validate configuration at startup
    _validate_config()
    
    if not os.path.exists(os.path.dirname(CONFIG["db_path"])):
        os.makedirs(os.path.dirname(CONFIG["db_path"]))
    uvicorn.run(
        app,
        host=os.getenv("BIND_HOST", "0.0.0.0"),
        port=int(os.getenv("BIND_PORT", "8080")),
    )
