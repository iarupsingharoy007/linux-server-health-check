"""
settings.py
===========
Central, non-hardcoded configuration for the Linux Server Health Check
Automation tool.

Every threshold, expected mount point, expected process/service, timeout,
and path used by the application is defined here so the rest of the
codebase never contains magic numbers or hardcoded infrastructure
assumptions. Change these values (or override them with environment
variables) to adapt the tool to a new environment without touching any
module code.
"""

import os

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SERVERS_FILE = os.path.join(BASE_DIR, "servers.json")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

LOG_FILE = os.path.join(LOGS_DIR, "application.log")

# --------------------------------------------------------------------------
# SSH / connection behaviour
# --------------------------------------------------------------------------
SSH_CONNECT_TIMEOUT = int(os.getenv("HC_SSH_CONNECT_TIMEOUT", 10))      # seconds
SSH_COMMAND_TIMEOUT = int(os.getenv("HC_SSH_COMMAND_TIMEOUT", 15))      # seconds
SSH_PORT_DEFAULT = int(os.getenv("HC_SSH_PORT_DEFAULT", 22))
MAX_RETRIES = int(os.getenv("HC_MAX_RETRIES", 2))
RETRY_DELAY_SECONDS = int(os.getenv("HC_RETRY_DELAY_SECONDS", 3))

# Number of servers to check concurrently.
MAX_CONCURRENT_WORKERS = int(os.getenv("HC_MAX_WORKERS", 8))

# --------------------------------------------------------------------------
# Health thresholds (percentages, unless noted otherwise)
# --------------------------------------------------------------------------
THRESHOLDS = {
    "cpu": {
        "warning": float(os.getenv("HC_CPU_WARNING", 70)),
        "critical": float(os.getenv("HC_CPU_CRITICAL", 90)),
    },
    "memory": {
        "warning": float(os.getenv("HC_MEM_WARNING", 75)),
        "critical": float(os.getenv("HC_MEM_CRITICAL", 90)),
    },
    "swap": {
        "warning": float(os.getenv("HC_SWAP_WARNING", 50)),
        "critical": float(os.getenv("HC_SWAP_CRITICAL", 80)),
    },
    "disk": {
        "warning": float(os.getenv("HC_DISK_WARNING", 80)),
        "critical": float(os.getenv("HC_DISK_CRITICAL", 90)),
    },
    # Load average is evaluated relative to the number of CPU cores
    # (load / cores). A ratio of 1.0 means the system is fully saturated.
    "load_average": {
        "warning": float(os.getenv("HC_LOAD_WARNING", 0.7)),
        "critical": float(os.getenv("HC_LOAD_CRITICAL", 1.0)),
    },
}

# --------------------------------------------------------------------------
# Expected infrastructure state (used for validation checks)
# --------------------------------------------------------------------------
EXPECTED_MOUNTS = os.getenv(
    "HC_EXPECTED_MOUNTS", "/,/home,/opt,/app,/data"
).split(",")

EXPECTED_PROCESSES = os.getenv(
    "HC_EXPECTED_PROCESSES", "java,python,nginx,tomcat,mysqld"
).split(",")

EXPECTED_SERVICES = os.getenv(
    "HC_EXPECTED_SERVICES", "sshd,cron,nginx,docker,tomcat"
).split(",")

# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
REPORT_FILENAME_FORMAT = "health_report_%Y%m%d_%H%M%S.html"
COMPANY_NAME = os.getenv("HC_COMPANY_NAME", "Acme Infrastructure")
DASHBOARD_TITLE = os.getenv("HC_DASHBOARD_TITLE", "Linux Server Health Check")

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
LOG_LEVEL = os.getenv("HC_LOG_LEVEL", "INFO")
LOG_MAX_BYTES = int(os.getenv("HC_LOG_MAX_BYTES", 5 * 1024 * 1024))  # 5 MB
LOG_BACKUP_COUNT = int(os.getenv("HC_LOG_BACKUP_COUNT", 5))
