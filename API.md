# Pi-hole Sentinel API Documentation

**Version:** 0.10.0-beta.13
**Last Updated:** 2025-12-07
**Base URL:** `http://<monitor-ip>:8080`

---

## Table of Contents

- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [UI Endpoints](#ui-endpoints)
- [Status & Monitoring](#status--monitoring)
- [Notification Management](#notification-management)
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

**Protection:** Test notification endpoint is rate-limited

**Limits:**
- **3 requests per 60 seconds** per IP address
- Applies only to `POST /api/notifications/test`

**Error Response (Rate Limit Exceeded):**
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```
HTTP Status: `429 Too Many Requests`

---

## UI Endpoints

### Dashboard

```http
GET /
GET /index.html
```

**Description:** Serves the main monitoring dashboard

**Authentication:** None required

**Response:** HTML page

**Features:**
- Real-time status display
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

### Common Error Codes

| Status Code | Meaning |
|-------------|---------|
| `200 OK` | Request successful |
| `400 Bad Request` | Invalid request parameters or body |
| `403 Forbidden` | Missing or invalid API key |
| `404 Not Found` | Endpoint does not exist |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Server-side error |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

---

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

**Last Updated:** 2025-12-07
**Version:** 0.10.0-beta.13
**Project:** Pi-hole Sentinel - High Availability for Pi-hole
