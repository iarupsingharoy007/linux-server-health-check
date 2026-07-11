# Linux Server Health Check Automation

**Automated health validation for Linux servers with interactive HTML reporting.**

A production-quality Python tool that connects to a fleet of Linux servers over SSH, runs a full suite of health checks, and renders the results into a single-file, interactive HTML dashboard — no server, database, or browser plugin required.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Folder Structure](#folder-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Screenshots](#screenshots)
- [Testing](#testing)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Running the same manual SSH checks across a fleet of servers doesn't scale. This tool automates it end to end:

1. Reads a JSON inventory of servers (`servers.json`).
2. Connects to each server concurrently over SSH (Paramiko).
3. Runs checks for connectivity, CPU, memory, swap, disk, mount points, required processes, and required services.
4. Classifies every metric as **Healthy**, **Warning**, or **Critical** against configurable thresholds.
5. Renders everything into one portable HTML dashboard (Jinja2 + hand-written CSS/JS — no frameworks).

A failure on any single server — bad credentials, a timeout, a missing command — is isolated and logged; the rest of the fleet is still checked and reported.

## Architecture

```
                      ┌─────────────────┐
                      │    servers.json  │
                      └────────┬─────────┘
                               │
                         config_loader.py
                               │
                               ▼
                      ┌─────────────────┐
                      │     main.py      │  (ThreadPoolExecutor — concurrent)
                      └────────┬─────────┘
                               │  for each server
                               ▼
                     health_evaluator.py
           ┌──────────────┬────┴────┬──────────────┬───────────────┐
           ▼              ▼         ▼              ▼               ▼
     system_info.py  cpu_check.py  memory_check.py disk_check.py  mount_check.py
                                                                     │
                                          ┌──────────────────────────┘
                                          ▼
                              process_check.py / service_check.py
                                          │
                                          ▼
                               (aggregated result dict)
                                          │
                                          ▼
                              report_generator.py (Jinja2)
                                          │
                                          ▼
                          reports/health_report_<timestamp>.html
```

Every remote command runs through a single choke point, `modules/ssh_connector.py`, so connection handling, retries, and timeouts are consistent across every check.

## Features

**Connectivity & identity**
SSH reachability, hostname, IP, OS version, kernel version, uptime, server date/time.

**System health**
CPU usage, load average (1/5/15 min, normalized per core), memory usage, swap usage.

**Disk**
Per-filesystem usage, size, available space, and mount point — with a dedicated validation pass confirming expected mounts (e.g. `/`, `/home`, `/opt`, `/app`, `/data`) actually exist.

**Processes & services**
Configurable list of required processes (`pgrep`) and services (`systemctl`/`service`), per-server or global.

**Dashboard**
- Summary cards (total / healthy / warning / critical / execution time)
- Signature animated "vitals" pulse trace, color-coded to fleet health
- Live search across hostname, IP, OS, kernel
- Collapsible per-server sections, expand/collapse all
- Dark mode / light mode toggle
- Export to CSV, export to PDF (print-to-PDF), print report
- Fully responsive, keyboard-accessible, `prefers-reduced-motion` aware

**Engineering**
- Modular architecture — one responsibility per file, no monolith
- Every threshold and expected value is configurable (env vars or `servers.json`), nothing hardcoded
- Structured logging to `logs/application.log` (rotating) and console
- Per-check error isolation — one failing check never blocks the others
- Concurrent execution across servers (`ThreadPoolExecutor`)
- Type hints and docstrings throughout
- Unit tests with mocked SSH (no live servers needed to test logic)

## Folder Structure

```
linux-server-health-check/
├── README.md
├── requirements.txt
├── main.py                    # Entry point / CLI
├── servers.json                # Sample server inventory
├── .gitignore
├── LICENSE
├── config/
│   ├── __init__.py
│   └── settings.py             # All thresholds, paths, expected state
├── modules/
│   ├── logger.py                # Rotating file + console logging
│   ├── config_loader.py         # Loads & validates servers.json
│   ├── ssh_connector.py         # Paramiko connection + command execution
│   ├── system_info.py           # Hostname, OS, kernel, uptime
│   ├── cpu_check.py              # CPU usage + load average
│   ├── memory_check.py          # Memory + swap
│   ├── disk_check.py             # Disk usage per filesystem
│   ├── mount_check.py            # Expected mount point validation
│   ├── process_check.py         # Required process validation
│   ├── service_check.py         # Required service validation
│   ├── health_evaluator.py      # Orchestrates all checks per server
│   ├── report_generator.py      # Renders the Jinja2 HTML dashboard
│   └── utils.py                  # Shared parsing/classification helpers
├── templates/
│   └── report_template.html     # Jinja2 dashboard template
├── static/
│   ├── css/style.css             # Hand-written dashboard styling
│   └── js/dashboard.js           # Search, collapse, theme, export
├── reports/                      # Generated HTML reports land here
├── logs/                         # application.log (rotating)
├── screenshots/                  # Sample dashboard output
└── tests/                        # Unit tests (mocked SSH)
```

## Installation

**Requirements:** Python 3.9+, SSH access to target servers.

```bash
git clone https://github.com/<your-username>/linux-server-health-check.git
cd linux-server-health-check
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

### 1. Server inventory — `servers.json`

```json
{
  "servers": [
    {
      "hostname": "web-prod-01",
      "ip": "10.0.1.11",
      "username": "healthcheck",
      "ssh_key_path": "~/.ssh/id_rsa_healthcheck",
      "port": 22,
      "expected_mounts": ["/", "/home", "/opt", "/app"],
      "expected_processes": ["nginx", "python"],
      "expected_services": ["sshd", "cron", "nginx"]
    }
  ]
}
```

Each server needs either `password` **or** `ssh_key_path` (SSH keys are recommended). `expected_mounts`, `expected_processes`, and `expected_services` are optional per-server overrides — omit them to fall back to the global defaults in `config/settings.py`.

> **Security note:** never commit real credentials. Use SSH keys, and add any file with real secrets to `.gitignore` (a `servers.local.json` pattern is already ignored).

### 2. Thresholds & defaults — `config/settings.py`

All thresholds can also be overridden with environment variables without touching code:

| Setting | Env var | Default |
|---|---|---|
| CPU warning / critical | `HC_CPU_WARNING` / `HC_CPU_CRITICAL` | 70% / 90% |
| Memory warning / critical | `HC_MEM_WARNING` / `HC_MEM_CRITICAL` | 75% / 90% |
| Swap warning / critical | `HC_SWAP_WARNING` / `HC_SWAP_CRITICAL` | 50% / 80% |
| Disk warning / critical | `HC_DISK_WARNING` / `HC_DISK_CRITICAL` | 80% / 90% |
| Load ratio warning / critical | `HC_LOAD_WARNING` / `HC_LOAD_CRITICAL` | 0.7 / 1.0 |
| Expected mounts | `HC_EXPECTED_MOUNTS` | `/,/home,/opt,/app,/data` |
| Expected processes | `HC_EXPECTED_PROCESSES` | `java,python,nginx,tomcat,mysqld` |
| Expected services | `HC_EXPECTED_SERVICES` | `sshd,cron,nginx,docker,tomcat` |
| SSH connect / command timeout | `HC_SSH_CONNECT_TIMEOUT` / `HC_SSH_COMMAND_TIMEOUT` | 10s / 15s |
| Concurrent workers | `HC_MAX_WORKERS` | 8 |

## Usage

```bash
# Run against the default servers.json
python main.py

# Use a different inventory file
python main.py --servers production_servers.json

# Change the report output directory
python main.py --output-dir /var/www/reports

# Limit concurrency
python main.py --workers 4
```

The tool prints a summary to the console and writes a timestamped report to `reports/health_report_<timestamp>.html` (plus a `reports/latest_report.html` convenience copy). Exit code is `2` if any server is critical, `1` on a configuration error, and `0` otherwise — convenient for cron/CI alerting.

## Screenshots

A sample dashboard rendered from mock data is included at [`screenshots/sample_dashboard.html`](screenshots/sample_dashboard.html) — open it directly in a browser to explore the dark mode toggle, search, collapsible sections, and export buttons without needing real servers.

## Testing

```bash
python -m unittest discover -s tests -v
```

Tests mock the SSH layer (`unittest.mock`), so they run without network access or real Linux servers, and verify: inventory loading/validation, threshold classification, status aggregation, and that a failing individual check never blocks the rest of the evaluation.

## Future Enhancements

- [ ] Email notifications on critical status
- [ ] Slack integration
- [ ] Microsoft Teams integration
- [ ] Historical trend charts (store results over time)
- [ ] Grafana / Prometheus exporter
- [ ] Docker support (containerized runner)
- [ ] REST API for triggering checks and fetching results
- [ ] Built-in scheduler (cron-free)
- [ ] Live web dashboard (instead of static HTML per run)

## Contributing

Contributions are welcome:

1. Fork the repository and create a feature branch.
2. Follow the existing style: PEP 8, type hints, docstrings on every public function.
3. Add or update unit tests for any behavior change.
4. Open a pull request describing the change and why it's needed.

Please keep modules single-purpose — if a change doesn't fit an existing module's responsibility, add a new one rather than growing a file into a monolith.

## License

Released under the [MIT License](LICENSE).
