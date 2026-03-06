# Security Policy

## Supported Versions

| Version | Security Fixes |
|---------|---------------|
| 1.x     | ✅ Active      |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Send a detailed report to: **security@flameiq.dev**

Include:
- A clear description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix if available

We will acknowledge your report within **48 hours** and aim to release a
fix within **14 days** for critical issues.

## Security Model

FlameIQ OSS makes the following guarantees:

| Property | Guarantee |
|----------|-----------|
| **No network calls** | The engine never connects to the internet |
| **No telemetry** | Zero data transmitted without user action |
| **No credentials** | No API keys, tokens, or accounts required |
| **Air-gap compatible** | Fully functional without internet |
| **Local storage only** | All data stays in `.flameiq/` |
| **Read-only providers** | Providers may never write files |
