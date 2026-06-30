from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from .runtime_monitor import config_from_dict, load_baseline_summary


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>QuantumRandy Paper Runtime</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #1d2633;
      --muted: #667085;
      --line: #d8dee8;
      --ok: #0f8a5f;
      --warn: #b54708;
      --bad: #b42318;
      --accent: #2563eb;
      --cyan: #0e7490;
      --gold: #a16207;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
      position: sticky;
      top: 0;
      z-index: 10;
    }
    h1 { margin: 0; font-size: 19px; font-weight: 700; }
    h2 { margin: 0 0 10px; font-size: 14px; font-weight: 700; }
    main { padding: 18px 24px 28px; max-width: 1440px; margin: 0 auto; }
    .status {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 28px;
      padding: 4px 9px;
      border: 1px solid var(--line);
      background: #f9fafb;
      border-radius: 7px;
      color: var(--muted);
      white-space: nowrap;
    }
    .pill.ok { color: var(--ok); border-color: #9fd7c1; background: #f0fdf7; }
    .pill.warn { color: var(--warn); border-color: #fed7aa; background: #fff7ed; }
    .pill.bad { color: var(--bad); border-color: #fecaca; background: #fef2f2; }
    .grid { display: grid; gap: 14px; }
    .summary { grid-template-columns: repeat(6, minmax(120px, 1fr)); margin-bottom: 14px; }
    .content { grid-template-columns: 1.25fr .75fr; align-items: start; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-width: 0;
    }
    .metric span { display: block; color: var(--muted); font-size: 12px; }
    .metric strong { display: block; font-size: 18px; margin-top: 4px; }
    .chart-wrap { height: 280px; }
    canvas { width: 100%; height: 100%; display: block; }
    .table-scroll { overflow-x: auto; }
    table { width: 100%; min-width: 100%; border-collapse: collapse; table-layout: auto; }
    th, td {
      padding: 8px 7px;
      border-bottom: 1px solid var(--line);
      text-align: right;
      vertical-align: middle;
      white-space: nowrap;
    }
    th:first-child, td:first-child { text-align: left; }
    th { color: var(--muted); font-size: 12px; font-weight: 650; }
    td { font-variant-numeric: tabular-nums; }
    .stack { display: grid; gap: 14px; }
    .muted { color: var(--muted); }
    .pos { color: var(--ok); }
    .neg { color: var(--bad); }
    .source { color: var(--muted); font-size: 12px; margin-top: -4px; margin-bottom: 8px; }
    @media (max-width: 1000px) {
      header { align-items: flex-start; flex-direction: column; }
      .status { justify-content: flex-start; }
      .summary { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
      .content { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>QuantumRandy Paper Runtime</h1>
    <div class="status" id="status"></div>
  </header>
  <main>
    <section class="grid summary" id="summary"></section>
    <section class="grid content">
      <div class="stack">
        <div class="panel">
          <h2>Strategy Equity</h2>
          <div class="chart-wrap"><canvas id="equity"></canvas></div>
        </div>
        <div class="panel">
          <h2>Strategies</h2>
          <div id="strategies"></div>
        </div>
        <div class="panel">
          <h2>Factors</h2>
          <div id="factors"></div>
        </div>
      </div>
      <div class="stack">
        <div class="panel">
          <h2>RandysLab Baselines</h2>
          <div id="baselines"></div>
        </div>
        <div class="panel">
          <h2>Runtime Feed</h2>
          <div id="feed"></div>
        </div>
      </div>
    </section>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);
    const fmt = (v, d = 4) => v === null || v === undefined || Number.isNaN(Number(v)) ? "-" : Number(v).toFixed(d);
    const pctClass = (v) => Number(v) >= 0 ? "pos" : "neg";
    async function refresh() {
      const res = await fetch("/api/runtime", {cache: "no-store"});
      const data = await res.json();
      render(data);
    }
    function render(data) {
      const record = data.latest || {};
      const health = record.health || {};
      const snapshot = record.snapshot || {};
      const stale = record.stale_bar === true;
      $("status").innerHTML = [
        `<span class="pill ${health.status === "ok" ? "ok" : "bad"}">Status ${health.status || "-"}</span>`,
        `<span class="pill ${stale ? "warn" : "ok"}">Stale ${stale}</span>`,
        `<span class="pill">Generation ${health.generation ?? "-"}</span>`,
        `<span class="pill">Bars ${health.stored_bars ?? "-"}</span>`
      ].join("");
      $("summary").innerHTML = [
        metric("Latest bar", shortTime(health.latest_timestamp)),
        metric("Minutes stale", fmt(record.minutes_since_latest_bar, 1)),
        metric("Strategies", (snapshot.strategies || []).length),
        metric("Factors", (snapshot.factors || []).length),
        metric("Best equity", bestEquity(snapshot.strategies || [])),
        metric("Last observed", shortTime(record.observed_at))
      ].join("");
      $("strategies").innerHTML = table(
        ["Strategy", "Mode", "Equity", "Return %", "Exposure", "Sharpe", "Max DD"],
        (snapshot.strategies || []).map(s => [
          s.strategy_id, s.mode, money(s.equity_usd), cls(fmt(s.return_pct, 2), pctClass(s.return_pct)),
          fmt(s.executed_exposure), fmt((s.metrics || {}).sharpe), fmt((s.metrics || {}).max_dd)
        ])
      );
      $("factors").innerHTML = table(
        ["Factor", "Value", "Target", "Exposure", "Close", "Sharpe", "Rank IC"],
        (snapshot.factors || []).map(f => [
          f.factor_id, fmt(f.factor_value), fmt(f.target_signal), fmt(f.executed_exposure),
          money(f.close), fmt((f.metrics || {}).sharpe), fmt((f.metrics || {}).rank_ic)
        ])
      );
      renderBaselines(data.baseline);
      renderFeed(data.history || []);
      drawEquity(data.history || []);
    }
    function renderBaselines(baseline) {
      if (!baseline || baseline.load_error) {
        $("baselines").innerHTML = `<div class="muted">${baseline?.load_error || "No baseline export configured."}</div>`;
        return;
      }
      const rows = (baseline.strategies || []).map(s => {
        const m = s.metrics || {};
        return [s.strategy_id, fmt(m.sharpe), fmt(m.cagr), fmt(m.max_dd), fmt(m.trades, 0), fmt(m.net_total)];
      });
      $("baselines").innerHTML = `<div class="source">${baseline.symbol || ""} · ${baseline.window?.name || ""}</div>` +
        table(["Baseline", "Sharpe", "CAGR", "Max DD", "Trades", "Net"], rows);
    }
    function renderFeed(history) {
      const rows = history.slice(-8).reverse().map(r => {
        const h = r.health || {};
        return [shortTime(r.observed_at), h.status || "-", h.stored_bars ?? "-", shortTime(h.latest_timestamp), String(r.stale_bar)];
      });
      $("feed").innerHTML = table(["Observed", "Status", "Bars", "Latest", "Stale"], rows);
    }
    function drawEquity(history) {
      const canvas = $("equity");
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      const ctx = canvas.getContext("2d");
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, rect.width, rect.height);
      const series = {};
      history.forEach(r => ((r.snapshot || {}).strategies || []).forEach(s => {
        (series[s.strategy_id] ||= []).push(Number(s.equity_usd));
      }));
      const names = Object.keys(series).filter(k => series[k].length > 1);
      if (!names.length) {
        ctx.fillStyle = "#667085";
        ctx.fillText("Waiting for monitor history", 12, 22);
        return;
      }
      const values = names.flatMap(k => series[k]).filter(Number.isFinite);
      const min = Math.min(...values), max = Math.max(...values);
      const pad = 22, w = rect.width - pad * 2, h = rect.height - pad * 2;
      ctx.strokeStyle = "#d8dee8";
      ctx.beginPath(); ctx.moveTo(pad, pad); ctx.lineTo(pad, pad + h); ctx.lineTo(pad + w, pad + h); ctx.stroke();
      const colors = ["#2563eb", "#0e7490", "#a16207", "#b42318"];
      names.forEach((name, idx) => {
        const arr = series[name];
        ctx.strokeStyle = colors[idx % colors.length];
        ctx.lineWidth = 2;
        ctx.beginPath();
        arr.forEach((v, i) => {
          const x = pad + (arr.length === 1 ? 0 : (i / (arr.length - 1)) * w);
          const y = pad + h - ((v - min) / Math.max(max - min, 1e-9)) * h;
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        ctx.stroke();
        ctx.fillStyle = colors[idx % colors.length];
        ctx.fillText(name, pad + 8, pad + 16 + idx * 16);
      });
    }
    function table(headers, rows) {
      if (!rows.length) return '<div class="muted">No rows.</div>';
      return '<div class="table-scroll"><table><thead><tr>' + headers.map(h => `<th>${h}</th>`).join("") +
        '</tr></thead><tbody>' + rows.map(r => '<tr>' + r.map(c => `<td>${c}</td>`).join("") + '</tr>').join("") +
        '</tbody></table></div>';
    }
    function metric(label, value) { return `<div class="panel metric"><span>${label}</span><strong>${value ?? "-"}</strong></div>`; }
    function money(v) { return v === null || v === undefined ? "-" : "$" + Number(v).toLocaleString(undefined, {maximumFractionDigits: 2}); }
    function cls(v, klass) { return `<span class="${klass}">${v}</span>`; }
    function bestEquity(rows) {
      const vals = rows.map(r => Number(r.equity_usd)).filter(Number.isFinite);
      return vals.length ? money(Math.max(...vals)) : "-";
    }
    function shortTime(v) { return v ? String(v).replace("T", " ").replace("+00:00", "Z").slice(0, 19) : "-"; }
    refresh();
    setInterval(refresh, 30000);
    window.addEventListener("resize", () => refresh());
  </script>
</body>
</html>
"""


def build_dashboard_payload(monitor_config_path: str | Path, *, history_limit: int = 240) -> dict[str, Any]:
    config_path = Path(monitor_config_path).resolve()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    cfg = config_from_dict(raw)
    latest_path = cfg.out_dir / "latest_snapshot.json"
    history_path = cfg.out_dir / "snapshots.jsonl"
    latest = _read_json(latest_path)
    history = _read_jsonl_tail(history_path, history_limit)
    baseline = load_baseline_summary(cfg.baseline_summary_path)
    return {
        "latest": latest,
        "history": history,
        "baseline": baseline,
        "monitor_out_dir": cfg.out_dir.as_posix(),
    }


def run_runtime_dashboard(
    monitor_config_path: str | Path = "configs/runtime_monitor.yaml",
    *,
    host: str = "127.0.0.1",
    port: int = 8790,
) -> None:
    handler = _make_handler(Path(monitor_config_path))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"QuantumRandy runtime dashboard listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _make_handler(monitor_config_path: Path) -> type[BaseHTTPRequestHandler]:
    class RuntimeDashboardHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                if path == "/":
                    self._send(HTTPStatus.OK, HTML, "text/html; charset=utf-8")
                elif path == "/api/runtime":
                    payload = json.dumps(
                        build_dashboard_payload(monitor_config_path),
                        ensure_ascii=True,
                        allow_nan=False,
                    )
                    self._send(HTTPStatus.OK, payload, "application/json; charset=utf-8")
                else:
                    self._send(HTTPStatus.NOT_FOUND, json.dumps({"error": "not_found"}), "application/json")
            except Exception as exc:
                payload = json.dumps({"error": "dashboard_error", "detail": str(exc)}, ensure_ascii=True)
                self._send(HTTPStatus.INTERNAL_SERVER_ERROR, payload, "application/json; charset=utf-8")

        def log_message(self, format: str, *args: Any) -> None:
            print(f"{self.address_string()} - {format % args}", flush=True)

        def _send(self, status: HTTPStatus, body: str, content_type: str) -> None:
            data = body.encode("utf-8")
            self.send_response(int(status))
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

    return RuntimeDashboardHandler


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_jsonl_tail(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-max(1, limit) :]:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve a read-only QuantumRandy runtime paper dashboard.")
    parser.add_argument("--monitor-config", default="configs/runtime_monitor.yaml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args()
    run_runtime_dashboard(args.monitor_config, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
