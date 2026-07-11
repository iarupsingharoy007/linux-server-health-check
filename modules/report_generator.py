"""
report_generator.py
=====================
Renders the collected health-check results into a self-contained,
interactive HTML dashboard using Jinja2, inlining the project's CSS and
JavaScript so the resulting report is a single portable file.
"""

import os
import shutil
from datetime import datetime
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import settings
from modules.logger import get_logger
from modules.utils import worst_status

logger = get_logger(__name__)


def _summarize(results: List[Dict]) -> Dict:
    """Build the summary-card statistics shown at the top of the dashboard."""
    total = len(results)
    healthy = sum(1 for r in results if r["status"] == "healthy")
    warning = sum(1 for r in results if r["status"] == "warning")
    critical = sum(1 for r in results if r["status"] == "critical")
    unreachable = sum(1 for r in results if not r.get("ssh_reachable"))

    return {
        "total": total,
        "healthy": healthy,
        "warning": warning,
        "critical": critical,
        "unreachable": unreachable,
    }


def generate_report(
    results: List[Dict],
    execution_time_seconds: float,
    output_dir: str = None,
) -> str:
    """
    Render the full HTML dashboard from a list of per-server results.

    Args:
        results: List of result dicts produced by
            ``health_evaluator.evaluate_server``.
        execution_time_seconds: Total wall-clock time for the whole run.
        output_dir: Directory to write the report into. Defaults to
            ``settings.REPORTS_DIR``.

    Returns:
        The absolute path to the generated HTML report file.
    """
    output_dir = output_dir or settings.REPORTS_DIR
    os.makedirs(output_dir, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(settings.TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report_template.html")

    overall_status = worst_status(*(r["status"] for r in results)) if results else "unknown"

    for result in results:
        _attach_template_helpers(result)

    css_content = _read_static("css/style.css")
    js_content = _read_static("js/dashboard.js")

    generated_at = datetime.now()

    html = template.render(
        title=settings.DASHBOARD_TITLE,
        company_name=settings.COMPANY_NAME,
        generated_at=generated_at.strftime("%Y-%m-%d %H:%M:%S"),
        generated_at_iso=generated_at.isoformat(),
        execution_time_seconds=round(execution_time_seconds, 2),
        summary=_summarize(results),
        overall_status=overall_status,
        servers=results,
        css_content=css_content,
        js_content=js_content,
    )

    filename = generated_at.strftime(settings.REPORT_FILENAME_FORMAT)
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(html)

    # Also maintain a stable "latest" symlink/copy for convenience.
    latest_path = os.path.join(output_dir, "latest_report.html")
    try:
        shutil.copyfile(output_path, latest_path)
    except OSError as exc:
        logger.warning("Could not write latest_report.html copy: %s", exc)

    logger.info("HTML report generated at %s", output_path)
    return output_path


def _attach_template_helpers(result: Dict) -> None:
    """
    Attach small derived fields to a server result dict that make the
    Jinja2 template simpler (e.g. joined strings for missing items, the
    worst disk usage percentage for the quick-stats row).

    Mutates `result` in place. Safe to call even if some checks failed
    (missing keys default sensibly).
    """
    disk = result.get("disk") or {}
    filesystems = disk.get("filesystems") or []
    result["disk_max_percent"] = max(
        (fs["use_percent"] for fs in filesystems), default=0.0
    )

    mounts = result.get("mounts") or {}
    result["missing_mounts_str"] = ", ".join(mounts.get("missing", [])) or "None"

    processes = result.get("processes") or {}
    result["missing_processes_str"] = ", ".join(processes.get("missing", [])) or "None"

    services = result.get("services") or {}
    result["missing_services_str"] = ", ".join(services.get("missing", [])) or "None"

    system_info = result.get("system_info") or {}
    result["search_blob"] = " ".join([
        result.get("hostname", ""),
        result.get("ip", ""),
        system_info.get("os_version", ""),
        system_info.get("kernel_version", ""),
    ]).lower()


def _read_static(relative_path: str) -> str:
    """Read a static asset (CSS/JS) as text so it can be inlined in the report."""
    full_path = os.path.join(settings.STATIC_DIR, relative_path)
    try:
        with open(full_path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        logger.error("Could not read static asset %s: %s", full_path, exc)
        return ""
