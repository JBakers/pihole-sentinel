# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.20.x  | ✅ Yes    |
| 0.19.x  | ✅ Yes    |
| < 0.19  | ❌ No     |

## Reporting a Vulnerability

Pi-hole Sentinel manages DNS/DHCP infrastructure. Security issues should be reported **privately** — please do **not** open a public GitHub Issue for vulnerabilities.

**How to report:**

Use [GitHub Private Security Advisories](https://github.com/JBakers/pihole-sentinel/security/advisories/new) to submit a vulnerability report confidentially.

Please include:
- A clear description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

**Response time:** You can expect an acknowledgement within 72 hours and a status update within 7 days.

## Scope

In scope:
- Authentication bypass or weak API key handling
- SSRF vulnerabilities in webhook/notification endpoints
- SQL injection or data leakage via the SQLite database
- Command injection via system command endpoints
- Privilege escalation via the installer (`setup.py`)

Out of scope:
- Vulnerabilities in upstream Pi-hole, keepalived, or the OS
- Issues requiring physical access to the server
- Denial-of-service via resource exhaustion without a realistic attack vector
