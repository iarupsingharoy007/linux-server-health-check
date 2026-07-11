/**
 * dashboard.js
 * ============
 * Client-side interactivity for the Linux Server Health Check dashboard.
 * No dependencies -- vanilla JS only, since the report is a single
 * portable HTML file with no build step or server.
 *
 * Features implemented:
 *  - Live search/filter across server cards
 *  - Collapse / expand individual server sections
 *  - Dark / light theme toggle (persisted for the session)
 *  - Export visible data to CSV
 *  - Export to PDF (via the browser print dialog)
 *  - Print report
 *  - Smooth scrolling for in-page navigation
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', init);

  function init() {
    setupThemeToggle();
    setupSearch();
    setupCollapsibles();
    setupExportCsv();
    setupExportPdf();
    setupPrint();
    expandFirstCriticalOrWarning();
  }

  /* ------------------------------------------------------------------ */
  /* Theme toggle                                                        */
  /* ------------------------------------------------------------------ */
  function setupThemeToggle() {
    const toggleBtn = document.getElementById('theme-toggle');
    if (!toggleBtn) return;

    const root = document.documentElement;
    const stored = sessionStorage_safe_get('hc-theme');
    if (stored) {
      root.setAttribute('data-theme', stored);
      updateThemeIcon(toggleBtn, stored);
    }

    toggleBtn.addEventListener('click', function () {
      const current = root.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
      const next = current === 'light' ? 'dark' : 'light';
      if (next === 'dark') {
        root.removeAttribute('data-theme');
      } else {
        root.setAttribute('data-theme', 'light');
      }
      updateThemeIcon(toggleBtn, next);
      sessionStorage_safe_set('hc-theme', next);
    });
  }

  function updateThemeIcon(btn, theme) {
    const icon = btn.querySelector('.icon');
    const label = btn.querySelector('.label');
    if (icon) icon.textContent = theme === 'light' ? '\u{1F319}' : '\u2600\uFE0F';
    if (label) label.textContent = theme === 'light' ? 'Dark mode' : 'Light mode';
  }

  // Artifacts/sandboxed contexts may block sessionStorage; fail silently.
  function sessionStorage_safe_get(key) {
    try { return sessionStorage.getItem(key); } catch (e) { return null; }
  }
  function sessionStorage_safe_set(key, value) {
    try { sessionStorage.setItem(key, value); } catch (e) { /* no-op */ }
  }

  /* ------------------------------------------------------------------ */
  /* Search / filter                                                     */
  /* ------------------------------------------------------------------ */
  function setupSearch() {
    const input = document.getElementById('server-search');
    if (!input) return;

    const cards = Array.from(document.querySelectorAll('.server-card'));
    const emptyState = document.getElementById('empty-state');

    input.addEventListener('input', function () {
      const query = input.value.trim().toLowerCase();
      let visibleCount = 0;

      cards.forEach(function (card) {
        const haystack = card.getAttribute('data-search') || '';
        const match = haystack.includes(query);
        card.classList.toggle('-hidden', !match);
        if (match) visibleCount += 1;
      });

      if (emptyState) {
        emptyState.classList.toggle('-visible', visibleCount === 0);
      }
    });
  }

  /* ------------------------------------------------------------------ */
  /* Collapse / expand                                                   */
  /* ------------------------------------------------------------------ */
  function setupCollapsibles() {
    document.querySelectorAll('.server-card__header').forEach(function (header) {
      header.addEventListener('click', function () {
        const card = header.closest('.server-card');
        card.classList.toggle('-expanded');
      });
      header.setAttribute('tabindex', '0');
      header.setAttribute('role', 'button');
      header.addEventListener('keydown', function (evt) {
        if (evt.key === 'Enter' || evt.key === ' ') {
          evt.preventDefault();
          header.click();
        }
      });
    });

    const expandAllBtn = document.getElementById('expand-all');
    if (expandAllBtn) {
      expandAllBtn.addEventListener('click', function () {
        const cards = document.querySelectorAll('.server-card');
        const anyCollapsed = Array.from(cards).some((c) => !c.classList.contains('-expanded'));
        cards.forEach((c) => c.classList.toggle('-expanded', anyCollapsed));
        expandAllBtn.querySelector('.label').textContent = anyCollapsed ? 'Collapse all' : 'Expand all';
      });
    }
  }

  function expandFirstCriticalOrWarning() {
    const priority = document.querySelector('.server-card[data-status="critical"]') ||
      document.querySelector('.server-card[data-status="warning"]');
    if (priority) priority.classList.add('-expanded');
  }

  /* ------------------------------------------------------------------ */
  /* CSV export                                                          */
  /* ------------------------------------------------------------------ */
  function setupExportCsv() {
    const btn = document.getElementById('export-csv');
    if (!btn) return;

    btn.addEventListener('click', function () {
      const rows = [
        ['Hostname', 'IP', 'Status', 'CPU %', 'Memory %', 'Disk (worst) %', 'Missing Mounts', 'Missing Processes', 'Missing Services'],
      ];

      document.querySelectorAll('.server-card').forEach(function (card) {
        rows.push([
          card.getAttribute('data-hostname') || '',
          card.getAttribute('data-ip') || '',
          card.getAttribute('data-status') || '',
          card.getAttribute('data-cpu') || '',
          card.getAttribute('data-mem') || '',
          card.getAttribute('data-disk-max') || '',
          card.getAttribute('data-missing-mounts') || '',
          card.getAttribute('data-missing-processes') || '',
          card.getAttribute('data-missing-services') || '',
        ]);
      });

      const csvContent = rows.map((row) => row.map(csvEscape).join(',')).join('\r\n');
      downloadBlob(csvContent, 'text/csv;charset=utf-8;', buildFilename('csv'));
    });
  }

  function csvEscape(value) {
    const str = String(value == null ? '' : value);
    if (/[",\r\n]/.test(str)) {
      return '"' + str.replace(/"/g, '""') + '"';
    }
    return str;
  }

  function buildFilename(ext) {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    return `health_report_${stamp}.${ext}`;
  }

  function downloadBlob(content, mimeType, filename) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /* ------------------------------------------------------------------ */
  /* PDF export (browser print-to-PDF) & print                          */
  /* ------------------------------------------------------------------ */
  function setupExportPdf() {
    const btn = document.getElementById('export-pdf');
    if (!btn) return;
    btn.addEventListener('click', function () {
      document.querySelectorAll('.server-card').forEach((c) => c.classList.add('-expanded'));
      window.print();
    });
  }

  function setupPrint() {
    const btn = document.getElementById('print-report');
    if (!btn) return;
    btn.addEventListener('click', function () {
      window.print();
    });
  }
})();
