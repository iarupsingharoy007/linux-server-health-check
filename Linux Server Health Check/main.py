#!/usr/bin/env python3
"""
main.py
=======
Entry point for the Linux Server Health Check Automation tool.

Loads the server inventory, runs health checks concurrently against
every server, and renders the results into an interactive HTML
dashboard.

Usage:
    python main.py
    python main.py --servers custom_servers.json
    python main.py --output-dir /tmp/reports
    python main.py --workers 4
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

from config import settings
from modules.config_loader import ConfigError, ServerConfig, load_servers
from modules.health_evaluator import evaluate_server
from modules.logger import get_logger
from modules.report_generator import generate_report

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Automated Linux server health check with HTML reporting."
    )
    parser.add_argument(
        "--servers",
        default=settings.SERVERS_FILE,
        help="Path to the servers.json inventory file (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        default=settings.REPORTS_DIR,
        help="Directory to write the generated HTML report into.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=settings.MAX_CONCURRENT_WORKERS,
        help="Maximum number of servers to check concurrently (default: %(default)s)",
    )
    return parser.parse_args()


def run_checks(servers: List[ServerConfig], max_workers: int) -> List[Dict]:
    """
    Run health checks against every server concurrently.

    A failure on one server (SSH unreachable, auth failure, etc.) is
    isolated within `evaluate_server` and does not stop the others.

    Args:
        servers: List of ServerConfig objects to check.
        max_workers: Maximum number of concurrent worker threads.

    Returns:
        A list of per-server result dictionaries, in the same order as
        the `servers` input.
    """
    results: List[Dict] = [None] * len(servers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(evaluate_server, server): index
            for index, server in enumerate(servers)
        }
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                results[index] = future.result()
            except Exception as exc:  # noqa: BLE001 - last-resort isolation
                server = servers[index]
                logger.critical(
                    "Unexpected top-level failure checking %s: %s",
                    server.hostname, exc, exc_info=True,
                )
                results[index] = {
                    "hostname": server.hostname,
                    "ip": server.ip,
                    "ssh_reachable": False,
                    "status": "critical",
                    "error": f"Unexpected failure: {exc}",
                    "check_duration_seconds": 0.0,
                }

    return results


def main() -> int:
    """Main program entry point. Returns a process exit code."""
    args = parse_args()
    start_time = time.monotonic()

    logger.info("=" * 70)
    logger.info("Linux Server Health Check Automation - starting run")
    logger.info("=" * 70)

    try:
        servers = load_servers(args.servers)
    except ConfigError as exc:
        logger.critical("Failed to load server inventory: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Checking {len(servers)} server(s) with up to {args.workers} concurrent workers...")
    results = run_checks(servers, args.workers)

    execution_time = time.monotonic() - start_time

    report_path = generate_report(results, execution_time, output_dir=args.output_dir)

    healthy = sum(1 for r in results if r["status"] == "healthy")
    warning = sum(1 for r in results if r["status"] == "warning")
    critical = sum(1 for r in results if r["status"] == "critical")

    print("\nHealth Check Summary")
    print("-" * 40)
    print(f"  Total servers   : {len(results)}")
    print(f"  Healthy         : {healthy}")
    print(f"  Warning         : {warning}")
    print(f"  Critical        : {critical}")
    print(f"  Execution time  : {execution_time:.2f}s")
    print(f"\nReport generated : {report_path}")

    # Non-zero exit code if anything is critical, useful for CI/cron alerting.
    return 2 if critical > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
