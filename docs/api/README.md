# Pi-hole Sentinel API Documentation

**Version:** See [VERSION](../../VERSION) file  
**Last Updated:** 2026-03-28  
**Base URL:** `http://<monitor-ip>:8080`

---

## Quick Links

- **Interactive Docs:** `http://monitor-ip:8080/api/docs` (Swagger UI)
- **Alternative Docs:** `http://monitor-ip:8080/api/redoc` (ReDoc)
- **OpenAPI Schema:** `http://monitor-ip:8080/api/openapi.json`

---

## Table of Contents

- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Endpoints Overview](#endpoints-overview)
- [Detailed Endpoints](#detailed-endpoints)
- [Error Responses](#error-responses)
- [Examples](#examples)

---

## Authentication

All API endpoints (except UI pages) require authentication using an API key.

### API Key Header

```http
X-API-Key: your-api-key-here
```

### Obtaining an API Key

The API key is set in the `.env` file on the monitor server:

```bash
# Generate a secure API key
python3 -c "import secrets; print('API_KEY=' + secrets.token_urlsafe(32))"

# Add to /opt/pihole-monitor/.env
echo "API_KEY=<generated-key>" >> /opt/pihole-monitor/.env

# Restart monitor service
sudo systemctl restart pihole-monitor
```

### Error Responses

**Missing API Key:**
```json
{
  "detail": "Not authenticated"
}
```
HTTP Status: `403 Forbidden`

**Invalid API Key:**
```json
{
  "detail": "Invalid API key"
}
```
HTTP Status: `403 Forbidden`

---

## Rate Limiting

**Protection:** Test notification endpoints are rate-limited

**Limits:**
- **3 requests per 60 seconds** per IP address
- Applies to:
  - `POST /api/notifications/test`
  - `POST /api/notifications/test-template`

**Error Response (Rate Limit Exceeded):**
```json
{
  "detail": "Rate limit exceeded. Max 3 requests per 60 seconds."
}
```
HTTP Status: `429 Too Many Requests`

---

## Endpoints Overview

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/version` | Yes | Get current version |
| GET | `/api/client-config` | Yes | Get API key + version for UI |
| GET | `/api/check-update` | Yes | Check for available updates |
| GET | `/api/status` | Yes | Get real-time system status |
| GET | `/api/history` | Yes | Get historical data (24h default) |
| GET | `/api/events` | Yes | Get events & failover history |
| GET | `/api/notifications/settings` | Yes | Get notification config |
| POST | `/api/notifications/settings` | Yes | Update notification config |
| POST | `/api/notifications/test` | Yes | Send test notification |
| POST | `/api/notifications/test-template` | Yes | Preview template (no send) |
| GET | `/api/notifications/snooze` | Yes | Get snooze status |
| POST | `/api/notifications/snooze` | Yes | Start snooze |
| DELETE | `/api/notifications/snooze` | Yes | Cancel snooze |

---

## Detailed Endpoints

### System Information

#### Get Version
```http
GET /api/version
```

**Description:** Get current Pi-hole Sentinel version

**Authentication:** Yes

**Response:**
```json
{
  "version": "<current version>"
}
```

#### Get Client Config
```http
GET /api/client-config
```

**Description:** Get API key and version for the dashboard UI

**Authentication:** Yes

**Response:**
```json
{
  "api_key": "your-api-key",
  "version": "<current version>"
}
```

#### Check for Updates
```http
GET /api/check-update
X-API-Key: your-api-key
```

**Description:** Check GitHub for available updates. Results cached 6 hours.

**Authentication:** Yes

**Response:**
```json
{
  "current_version": "<current version>",
  "latest_version": "<latest version>",
  "update_available": true,
  "release_url": "https://github.com/JBakers/pihole-sentinel/releases/tag/0.13.0-beta.1",
  "cached": false
}
```

---

### Status and Monitoring

#### Get Current Status
```http
GET /api/status
X-API-Key: your-api-key
```

**Description:** Get real-time status of both Pi-holes and VIP location

**Authentication:** Yes

**Response:**
```json
{
  "master": "Primary Pi-hole",
  "backup": "Secondary Pi-hole",
  "vip_address": "192.168.1.100",
  "primary": {
    "name": "Primary Pi-hole",
    "ip": "192.168.1.10",
    "ftl_running": true,
    "dns_working": true,
    "dhcp_running": true,
    "last_check": "2025-12-07T14:32:15.123456"
  },
  "secondary": {
    "name": "Secondary Pi-hole",
    "ip": "192.168.1.11",
    "ftl_running": true,
    "dns_working": true,
    "dhcp_running": false,
    "last_check": "2025-12-07T14:32:15.123456"
  },
  "uptime_seconds": 86400,
  "last_check": "2025-12-07T14:32:15.123456"
}
```

#### Get Historical Data
```http
GET /api/history?hours=24
X-API-Key: your-api-key
```

**Description:** Get status history for dashboard graphs

**Authentication:** Yes

**Query Parameters:**
- `hours` (float, default: 24, max: 720): Hours of history to retrieve

**Response:**
```json
[
  {
    "time": "2025-12-07T00:00:00",
    "primary": 1,
    "secondary": 0
  },
  {
    "time": "2025-12-07T01:00:00",
    "primary": 0,
    "secondary": 1
  }
]
```

#### Get Events
```http
GET /api/events?limit=50
X-API-Key: your-api-key
```

**Description:** Get recent system events and failover history

**Authentication:** Yes

**Query Parameters:**
- `limit` (int, default: 50, max: 500): Maximum events to return

**Response:**
```json
{
  "total_events": 147,
  "recent_events": [
    {
      "timestamp": "2025-12-07T14:30:00",
      "event_type": "failover",
      "description": "Secondary Pi-hole is now MASTER",
      "details": {
        "reason": "Primary service stopped",
        "vip_moved_to": "192.168.1.11"
      }
    }
  ],
  "failover_count": 3,
  "last_failover": "2025-12-07T14:30:00"
}
```

---

### Notification Management

#### Get Notification Settings
```http
GET /api/notifications/settings
X-API-Key: your-api-key
```

**Description:** Get current notification configuration (sensitive data masked)

**Authentication:** Yes

**Response:**
```json
{
  "enabled": true,
  "events": {
    "failover": true,
    "recovery": true,
    "fault": true,
    "startup": false
  },
  "telegram": {
    "enabled": true,
    "bot_token": "••••••••1234",
    "chat_id": "••••5678"
  },
  "discord": {
    "enabled": false,
    "webhook_url": null
  },
  "templates": {
    "failover": "🚨 {node} is now MASTER\nReason: {reason}",
    "recovery": "✅ {node} recovered"
  },
  "repeat": {
    "enabled": true,
    "interval": 60
  },
  "snooze": {
    "enabled": false,
    "until": null
  }
}
```

#### Update Notification Settings
```http
POST /api/notifications/settings
X-API-Key: your-api-key
Content-Type: application/json

{
  "enabled": true,
  "events": {
    "failover": true,
    "recovery": true
  },
  "telegram": {
    "enabled": true,
    "bot_token": "123456:ABCdef-GHIJ...",
    "chat_id": "987654321"
  },
  "templates": {
    "failover": "🚨 FAILOVER: {node} is now MASTER"
  }
}
```

**Description:** Save notification service configuration

**Authentication:** Yes (required)

**Security:** Masked values from previous GET are not overwritten

**Response:**
```json
{
  "status": "success",
  "message": "Settings saved successfully"
}
```

#### Test Notification Service
```http
POST /api/notifications/test
X-API-Key: your-api-key
Content-Type: application/json

{
  "service": "telegram",
  "event_type": "failover"
}
```

**Description:** Send a test notification to verify service configuration

**Authentication:** Yes (required)

**Rate Limited:** Yes (3 per 60 seconds)

**Request Parameters:**
- `service` (required): `telegram`, `discord`, `pushover`, `ntfy`, or `webhook`
- `event_type` (optional): Event type for template selection

**Response:**
```json
{
  "success": true,
  "message": "Test notification sent via telegram",
  "service": "telegram"
}
```

#### Preview Notification Template
```http
POST /api/notifications/test-template
X-API-Key: your-api-key
Content-Type: application/json

{
  "template": "Failover: {node} is MASTER",
  "variables": {
    "node": "Primary Pi-hole"
  }
}
```

**Description:** Preview rendered template without sending notification

**Authentication:** Yes (required)

**Rate Limited:** Yes (3 per 60 seconds)

**Response:**
```json
{
  "rendered": "Failover: Primary Pi-hole is MASTER",
  "status": "success"
}
```

---

### Notification Snooze

#### Get Snooze Status
```http
GET /api/notifications/snooze
X-API-Key: your-api-key
```

**Description:** Get current notification snooze status

**Authentication:** Yes

**Response:**
```json
{
  "snoozed": true,
  "until": "2025-12-07T15:30:00",
  "remaining_seconds": 1800
}
```

#### Start Snooze
```http
POST /api/notifications/snooze
X-API-Key: your-api-key
Content-Type: application/json

{
  "minutes": 60
}
```

**Description:** Snooze all notifications for specified duration

**Authentication:** Yes

**Request Parameters:**
- `minutes` (required): Duration in minutes (1-1440, max 24 hours)

**Response:**
```json
{
  "snoozed": true,
  "until": "2025-12-07T15:30:00",
  "remaining_seconds": 3600
}
```

#### Cancel Snooze
```http
DELETE /api/notifications/snooze
X-API-Key: your-api-key
```

**Description:** Immediately cancel active snooze and re-enable notifications

**Authentication:** Yes

**Response:**
```json
{
  "snoozed": false,
  "until": null,
  "remaining_seconds": null
}
```

---


- Historical graphs (1h/6h/24h/7d/30d)
- Event timeline
- Dark mode support
- Mobile responsive

---

### Settings Page

```http
GET /settings.html
```

**Description:** Serves the notification settings interface

**Authentication:** None required (API calls from page require key)

**Response:** HTML page

**Features:**
- Notification service configuration
- Test notification buttons
- Sensitive field masking
- Dark mode support

---

## Status & Monitoring

### Get Current Status

```http
GET /api/status
```

**Description:** Returns current status of both Pi-hole servers, VIP location, and DHCP state

**Authentication:** Required

**Response:**

```json
{
  "timestamp": "2025-12-07T14:30:00",
  "primary": {
    "ip": "10.10.100.10",
    "name": "Primary Pi-hole",
    "state": "MASTER",
    "has_vip": true,
    "online": true,
    "pihole": true,
    "dns": true,
    "dhcp": true
  },
  "secondary": {
    "ip": "10.10.100.20",
    "name": "Secondary Pi-hole",
    "state": "BACKUP",
    "has_vip": false,
    "online": true,
    "pihole": true,
    "dns": true,
    "dhcp": false
  },
  "vip": {
    "address": "10.10.100.2",
    "location": "primary"
  },
  "dhcp": {
    "total_leases": 42,
    "misconfigured": false
  }
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 timestamp of status check |
| `primary.state` | string | Keepalived state: `MASTER`, `BACKUP`, or `FAULT` |
| `primary.has_vip` | boolean | Whether this server currently has the VIP |
| `primary.online` | boolean | TCP connectivity (port 80) |
| `primary.pihole` | boolean | Pi-hole FTL service responding |
| `primary.dns` | boolean | DNS resolution working |
| `primary.dhcp` | boolean | DHCP service enabled |
| `vip.location` | string | Which server has VIP: `primary`, `secondary`, or `unknown` |
| `dhcp.misconfigured` | boolean | DHCP enabled on wrong server |

---

### Get Historical Data

```http
GET /api/history?hours=24
```

**Description:** Returns historical status data for graphing

**Authentication:** Required

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hours` | float | 24 | Number of hours of history to return |

**Example Request:**

```bash
curl -H "X-API-Key: your-key" \
  "http://10.10.100.30:8080/api/history?hours=6"
```

**Response:**

```json
{
  "data": [
    {
      "timestamp": "2025-12-07T08:00:00",
      "primary_online": true,
      "secondary_online": true,
      "primary_pihole": true,
      "secondary_pihole": true,
      "primary_dns": true,
      "secondary_dns": true,
      "primary_has_vip": true,
      "secondary_has_vip": false,
      "dhcp_leases": 42
    },
    {
      "timestamp": "2025-12-07T08:10:00",
      "primary_online": true,
      "secondary_online": true,
      ...
    }
  ]
}
```

**Data Points:**
- Interval: Every 10 seconds (configurable via `CHECK_INTERVAL`)
- Retention: 30 days (configurable via `RETENTION_DAYS_HISTORY`)
- Automatic cleanup: Daily

---

### Get Event Timeline

```http
GET /api/events?limit=50
```

**Description:** Returns event log (failovers, state changes, errors)

**Authentication:** Required

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Maximum number of events to return |

**Example Request:**

```bash
curl -H "X-API-Key: your-key" \
  "http://10.10.100.30:8080/api/events?limit=100"
```

**Response:**

```json
{
  "events": [
    {
      "id": 123,
      "timestamp": "2025-12-07T14:25:33",
      "event_type": "failover",
      "message": "FAILOVER: Secondary is now MASTER (Primary → Secondary)"
    },
    {
      "id": 122,
      "timestamp": "2025-12-07T12:00:00",
      "event_type": "info",
      "message": "Monitor started"
    },
    {
      "id": 121,
      "timestamp": "2025-12-07T10:15:42",
      "event_type": "warning",
      "message": "DHCP misconfigured: BACKUP has DHCP enabled"
    }
  ]
}
```

**Event Types:**
- `info` - Informational messages (startup, normal events)
- `warning` - Warning conditions (DHCP misconfiguration)
- `failover` - Failover/failback events
- `error` - Error conditions

**Retention:** 90 days (configurable via `RETENTION_DAYS_EVENTS`)

---

## Notification Management

### Get Notification Settings

```http
GET /api/notifications/settings
```

**Description:** Returns current notification configuration (with masked sensitive data)

**Authentication:** Required

**Response:**

```json
{
  "telegram": {
    "enabled": true,
    "bot_token": "***MASKED***",
    "chat_id": "***MASKED***"
  },
  "discord": {
    "enabled": false,
    "webhook_url": null
  },
  "pushover": {
    "enabled": false,
    "user_key": null,
    "app_token": null
  },
  "ntfy": {
    "enabled": true,
    "topic": "pihole-sentinel",
    "server": "https://ntfy.sh"
  },
  "webhook": {
    "enabled": false,
    "url": null
  },
  "events": {
    "on_failover": true,
    "on_failback": true,
    "on_fault": true,
    "on_dhcp_misconfigured": true,
    "on_startup": false
  },
  "repeat_alerts": {
    "enabled": true,
    "interval_minutes": 30
  },
  "snooze": {
    "active": false,
    "until": null
  }
}
```

**Sensitive Data Masking:**
- `***MASKED***` - Field has a value but is hidden for security
- `null` - Field is not configured

---

### Update Notification Settings

```http
POST /api/notifications/settings
```

**Description:** Update notification configuration

**Authentication:** Required

**Request Body:**

```json
{
  "telegram": {
    "enabled": true,
    "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
    "chat_id": "987654321"
  },
  "events": {
    "on_failover": true,
    "on_failback": true,
    "on_fault": true,
    "on_dhcp_misconfigured": true,
    "on_startup": false
  },
  "repeat_alerts": {
    "enabled": true,
    "interval_minutes": 30
  }
}
```

**Notes:**
- Only include fields you want to update
- Masked values (`***MASKED***`) are preserved if sent
- `null` values clear the field
- Partial updates supported

**Success Response:**

```json
{
  "status": "success",
  "message": "Settings saved successfully"
}
```
HTTP Status: `200 OK`

**Error Response:**

```json
{
  "detail": "Invalid settings format"
}
```
HTTP Status: `400 Bad Request`

---

### Test Notification

```http
POST /api/notifications/test
```

**Description:** Send a test notification via a specific service

**Authentication:** Required

**Rate Limit:** 3 requests per 60 seconds per IP

**Request Body:**

```json
{
  "service": "telegram"
}
```

**Supported Services:**
- `telegram`
- `discord`
- `pushover`
- `ntfy`
- `webhook`

**Example Request:**

```bash
curl -X POST \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"service":"telegram"}' \
  http://10.10.100.30:8080/api/notifications/test
```

**Success Response:**

```json
{
  "status": "success",
  "message": "Test notification sent successfully via telegram"
}
```
HTTP Status: `200 OK`

**Error Responses:**

**Service Not Configured:**
```json
{
  "detail": "telegram is not configured or enabled"
}
```
HTTP Status: `400 Bad Request`

**Service Failed:**
```json
{
  "detail": "Failed to send test notification: Connection timeout"
}
```
HTTP Status: `500 Internal Server Error`

**Rate Limit Exceeded:**
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```
HTTP Status: `429 Too Many Requests`

---

## Error Responses

### HTTP Status Codes

| Status | Description | Example |
|--------|-------------|---------|
| **200** | Request successful | Status retrieved |
| **400** | Bad request parameters | Invalid duration (must be 1-1440) |
| **403** | Authentication required/failed | Invalid or missing X-API-Key |
| **429** | Rate limit exceeded | Too many test requests in 60s |
| **500** | Server error | Database error, file I/O error |

### Standard Error Response Format

All errors return JSON with details:

```json
{
  "detail": "Human-readable error message"
}
```

## Examples

### Complete Python Example

```python
import requests

# Configuration
API_BASE = "http://10.10.100.30:8080"
API_KEY = "your-api-key-here"
HEADERS = {"X-API-Key": API_KEY}

# Get current status
response = requests.get(f"{API_BASE}/api/status", headers=HEADERS)
if response.status_code == 200:
    status = response.json()
    print(f"Primary: {status['primary']['state']}")
    print(f"VIP on: {status['vip']['location']}")
else:
    print(f"Error: {response.status_code} - {response.json()['detail']}")

# Get 6 hours of history
response = requests.get(
    f"{API_BASE}/api/history",
    headers=HEADERS,
    params={"hours": 6}
)
history = response.json()
print(f"Data points: {len(history['data'])}")

# Update notification settings
settings = {
    "telegram": {
        "enabled": True,
        "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
        "chat_id": "987654321"
    },
    "events": {
        "on_failover": True,
        "on_failback": True
    }
}

response = requests.post(
    f"{API_BASE}/api/notifications/settings",
    headers=HEADERS,
    json=settings
)
print(response.json())

# Test notification
response = requests.post(
    f"{API_BASE}/api/notifications/test",
    headers=HEADERS,
    json={"service": "telegram"}
)
print(response.json())
```

### Complete Bash Example (curl)

```bash
#!/bin/bash

API_BASE="http://10.10.100.30:8080"
API_KEY="your-api-key-here"

# Get status
curl -s -H "X-API-Key: $API_KEY" "$API_BASE/api/status" | jq .

# Get 24h history
curl -s -H "X-API-Key: $API_KEY" "$API_BASE/api/history?hours=24" | jq .

# Get last 10 events
curl -s -H "X-API-Key: $API_KEY" "$API_BASE/api/events?limit=10" | jq .

# Update notification settings
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "telegram": {
      "enabled": true,
      "bot_token": "your-token",
      "chat_id": "your-chat-id"
    },
    "events": {
      "on_failover": true,
      "on_failback": true
    }
  }' \
  "$API_BASE/api/notifications/settings"

# Test Telegram notification
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"service":"telegram"}' \
  "$API_BASE/api/notifications/test"
```

### JavaScript/TypeScript Example

```typescript
const API_BASE = 'http://10.10.100.30:8080';
const API_KEY = 'your-api-key-here';

const headers = {
  'X-API-Key': API_KEY,
  'Content-Type': 'application/json'
};

// Get status
async function getStatus() {
  const response = await fetch(`${API_BASE}/api/status`, { headers });
  const status = await response.json();

  console.log(`Primary: ${status.primary.state}`);
  console.log(`VIP on: ${status.vip.location}`);

  return status;
}

// Get history
async function getHistory(hours = 24) {
  const response = await fetch(
    `${API_BASE}/api/history?hours=${hours}`,
    { headers }
  );
  return await response.json();
}

// Update settings
async function updateSettings(settings) {
  const response = await fetch(`${API_BASE}/api/notifications/settings`, {
    method: 'POST',
    headers,
    body: JSON.stringify(settings)
  });
  return await response.json();
}

// Test notification
async function testNotification(service) {
  const response = await fetch(`${API_BASE}/api/notifications/test`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ service })
  });

  if (response.status === 429) {
    console.error('Rate limit exceeded, try again later');
    return null;
  }

  return await response.json();
}

// Usage
getStatus().then(status => {
  if (status.dhcp.misconfigured) {
    console.warn('DHCP is misconfigured!');
  }
});
```

---

## Webhook Payload Format

When using custom webhooks, Pi-hole Sentinel sends notifications as JSON POST requests:

### Failover Event

```json
{
  "event": "failover",
  "timestamp": "2025-12-07T14:25:33",
  "severity": "warning",
  "message": "FAILOVER: Secondary is now MASTER",
  "details": {
    "previous_master": "primary",
    "new_master": "secondary",
    "vip": "10.10.100.2",
    "primary_state": "FAULT",
    "secondary_state": "MASTER"
  }
}
```

### DHCP Misconfiguration Warning

```json
{
  "event": "dhcp_misconfigured",
  "timestamp": "2025-12-07T14:30:00",
  "severity": "warning",
  "message": "DHCP misconfigured: BACKUP has DHCP enabled",
  "details": {
    "primary_dhcp": false,
    "secondary_dhcp": true,
    "expected_behavior": "Only MASTER should have DHCP enabled"
  }
}
```

---

## Notes

### Database Cleanup

The monitor automatically cleans old data to prevent database growth:

- **Status History:** Retained for 30 days (default)
- **Events:** Retained for 90 days (default)
- **Cleanup Schedule:** Daily at startup + every 24 hours

**Configure Retention:**

Edit `/opt/pihole-monitor/.env`:
```bash
RETENTION_DAYS_HISTORY=60  # Keep status for 60 days
RETENTION_DAYS_EVENTS=180  # Keep events for 180 days
```

Restart after changes:
```bash
sudo systemctl restart pihole-monitor
```

### CORS Configuration

By default, API access is restricted to localhost. For remote access, edit `/opt/pihole-monitor/monitor.py` (lines 154-167) to add your IP to the `allow_origins` list.

See [README.md - Remote Dashboard Access](README.md#remote-dashboard-access) for details.

---

## Support

For questions or issues:
- **Documentation:** [README.md](README.md)
- **Troubleshooting:** [README.md#troubleshooting](README.md#troubleshooting)
- **Issues:** https://github.com/JBakers/pihole-sentinel/issues

---

**Last Updated:** 2026-03-28
**Version:** See [VERSION](../../VERSION) file
**Project:** Pi-hole Sentinel - High Availability for Pi-hole
