from __future__ import annotations

import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .research import ResearchSession

C_RESET = "\033[0m"
C_BLUE = "\033[34m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_CYAN = "\033[36m"


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>QuantumRandy Lab</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b0e11;
      --panel: #1e2329;
      --text: #eaecef;
      --muted: #848e9c;
      --line: #2b3139;
      --good: #0ecb81;
      --bad: #f6465d;
      --warn: #f0b90b;
      --gold: #f0b90b;
      --gold-dim: #5e4810;
      --blue: #1e3050;
    }
    body.local-mode {
      --accent: #848e9c;
      --accent-dim: #1e2329;
    }
    body.llm-mode {
      --accent: #f0b90b;
      --accent-dim: #5e4810;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Segoe UI", "Inter", Arial, sans-serif; background: var(--bg); color: var(--text); }
    .mode-strip { height: 3px; background: var(--accent); }
    header { padding: 18px 24px; border-bottom: 1px solid var(--line); background: var(--panel); display: flex; align-items: center; justify-content: space-between; gap: 16px; }
    body.local-mode header { border-bottom-color: #848e9c40; }
    body.llm-mode header { border-bottom-color: var(--gold-dim); }
    h1 { margin: 0; font-size: 22px; color: var(--accent); }
    main { padding: 18px 24px 28px; display: grid; gap: 16px; }
    .toolbar, .metrics, .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }
    .toolbar { padding: 12px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    button { border: 1px solid var(--line); background: var(--panel); color: var(--text); border-radius: 6px; padding: 9px 12px; cursor: pointer; font-weight: 600; transition: all .15s; }
    button:hover { border-color: var(--accent); color: var(--accent); }
    button.primary { background: var(--gold); border-color: var(--gold); color: #0b0e11; }
    button.primary:hover { background: #f8c832; color: #0b0e11; }
    button.danger { background: var(--bad); border-color: var(--bad); color: #fff; }
    button.warn { background: var(--gold-dim); border-color: var(--gold); color: var(--gold); }
    input { width: 90px; border: 1px solid var(--line); border-radius: 6px; padding: 9px; background: var(--bg); color: var(--text); }
    label { color: var(--muted); font-size: 13px; display: flex; align-items: center; gap: 6px; }
    .metrics { padding: 12px; display: grid; grid-template-columns: repeat(6, minmax(120px, 1fr)); gap: 12px; }
    .metric { border-left: 3px solid var(--accent); padding-left: 10px; }
    .metric span { display: block; color: var(--muted); font-size: 12px; }
    .metric strong { display: block; font-size: 18px; margin-top: 3px; }
    .badge { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:700; margin-left:8px; }
    .badge.local { background:#2b3139; color:#848e9c; border:1px solid #848e9c; }
    .badge.llm { background:var(--gold-dim); color:var(--gold); border:1px solid var(--gold); }
    .panel { overflow: hidden; }
    .panel h2 { margin: 0; padding: 12px 14px; font-size: 16px; border-bottom: 1px solid var(--line); }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 9px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
    th { color: var(--muted); background: #181a20; position: sticky; top: 0; user-select: none; }
    th.sortable { cursor: pointer; }
    th.sortable:hover { color: var(--gold); }
    th .sort-arrow { font-size: 10px; margin-left: 3px; opacity: 0.4; }
    th.sort-asc .sort-arrow { opacity: 1; color: var(--gold); }
    th.sort-desc .sort-arrow { opacity: 1; color: var(--gold); }
    td.formula { font-family: Consolas, monospace; max-width: 520px; overflow-wrap: anywhere; color: var(--gold); }
    .pass { color: var(--good); font-weight: 700; }
    .fail { color: var(--bad); font-weight: 700; }
    .muted { color: var(--muted); }
    tr:hover td { background: rgba(240,185,11,0.04); }
    tr { cursor: pointer; }

    .modal-overlay {
      display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.75); z-index: 9999;
      justify-content: center; align-items: flex-start; padding-top: 40px;
      overflow-y: auto;
    }
    .modal-overlay.active { display: flex; }
    .modal-box {
      background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
      max-width: 800px; width: 95%; margin-bottom: 40px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.5);
      animation: modalIn .2s ease-out;
    }
    @keyframes modalIn { from { opacity:0; transform: translateY(-20px) scale(.97); } to { opacity:1; transform: translateY(0) scale(1); } }
    .modal-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 16px 20px; border-bottom: 1px solid var(--line);
    }
    .modal-header h2 { margin: 0; font-size: 18px; border: none; padding: 0; }
    .modal-close {
      background: none; border: 1px solid var(--line); color: var(--muted); font-size: 18px;
      width: 34px; height: 34px; border-radius: 50%; cursor: pointer; display: flex;
      align-items: center; justify-content: center; transition: all .15s;
    }
    .modal-close:hover { border-color: var(--bad); color: var(--bad); }
    .modal-body { padding: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 14px 24px; font-size: 13px; }
    .modal-body .full { grid-column: 1 / -1; }

    @media (max-width: 900px) {
      header { align-items: flex-start; flex-direction: column; }
      .metrics { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
      main { padding: 12px; }
      .panel { overflow-x: auto; }
      .modal-body { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body class="local-mode">
  <div class="mode-strip"></div>
  <header>
    <div>
      <h1>QuantumRandy Lab <span id="modeBadge" class="badge local">LOCAL</span></h1>
      <div class="muted">BTC 4h MCTS Alpha Mining</div>
    </div>
    <div id="message" class="muted">Loading...</div>
  </header>
  <main>
    <section class="toolbar">
      <label>小时 <input id="hours" type="number" min="0.05" step="0.25" value="24"></label>
      <label><input id="useLlm" type="checkbox"> 使用 DeepSeek</label>
      <button class="primary" onclick="post('/api/start', {hours: Number(hours.value), use_llm: useLlm.checked})">开始 / 继续研究</button>
      <button onclick="testDeepSeek()" style="border-color:var(--gold);color:var(--gold)">测试 DeepSeek 连通性</button>
      <button class="warn" onclick="post('/api/stop', {})">跑完当前轮保存停止</button>
      <button onclick="post('/api/save', {})">立即保存并备份</button>
      <button class="danger" onclick="post('/api/emergency', {})">急停</button>
      <button class="warn" onclick="post('/api/purge', {})">清理被杀因子</button>
      <button onclick="refresh()">读取之前因子</button>
    </section>
    <section class="metrics">
      <div class="metric"><span>状态</span><strong id="status">-</strong></div>
      <div class="metric"><span>已跑轮数</span><strong id="iterations">0</strong></div>
      <div class="metric"><span>候选因子</span><strong id="candidates">0</strong></div>
      <div class="metric"><span>通过四关</span><strong id="accepted">0</strong></div>
      <div class="metric"><span>最佳分</span><strong id="bestScore">-</strong></div>
      <div class="metric"><span>已耗时</span><strong id="elapsed">0m</strong></div>
      <div class="metric"><span>阶段</span><strong id="phase">-</strong></div>
      <div class="metric"><span>DS状态</span><strong id="llmStatus" style="font-size:14px">-</strong></div>
    </section>
    <section class="panel">
      <h2>因子天梯 <span class="muted" style="font-size:12px;font-weight:400">(点击行查看详情 · 点击列头排序)</span></h2>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th class="sortable" onclick="sortTable('passed')">生死 <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('brutal_score')">残酷分 <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('rank_ic')">Rank IC <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('sharpe')">Sharpe <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('max_dd')">回撤 <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('max_corr_to_library')">相关 <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('halflife_bars')">半衰 <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('depth')">深 <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('operators')">算 <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('generated_at')">生成时间 <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('formula')">公式 <span class="sort-arrow">&#9650;</span></th>
            <th>逻辑解释</th>
          </tr>
        </thead>
        <tbody id="leaderboard"></tbody>
      </table>
    </section>
    <section class="panel" id="llmLogPanel">
      <h2>DeepSeek 调用日志</h2>
      <div id="llmLog" style="padding:8px 14px;max-height:200px;overflow-y:auto;font-family:Consolas,monospace;font-size:12px">
        <span class="muted">暂无记录</span>
      </div>
    </section>
  </main>

  <div id="modalOverlay" class="modal-overlay" onclick="if(event.target===this)closeModal()">
    <div class="modal-box">
      <div class="modal-header">
        <h2 id="modalTitle">因子详情</h2>
        <button class="modal-close" onclick="closeModal()">&times;</button>
      </div>
      <div class="modal-body" id="modalBody"></div>
    </div>
  </div>

  <script>
    let _sortState = { key: null, dir: 0 };
    let _defaultOrder = null;

    async function post(url, body) {
      const res = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
      await res.json();
      closeModal();
      refresh();
    }
    function fmt(x, n=3) {
      if (x === undefined || x === null || Number.isNaN(Number(x))) return '-';
      return Number(x).toFixed(n);
    }
    function elapsed(sec) {
      sec = Number(sec || 0);
      if (sec < 3600) return Math.round(sec / 60) + 'm';
      return (sec / 3600).toFixed(1) + 'h';
    }
    function closeModal() { document.getElementById('modalOverlay').classList.remove('active'); }

    function sortTable(key) {
      if (_sortState.key === key) {
        _sortState.dir = (_sortState.dir + 1) % 3;
      } else {
        _sortState.key = key;
        _sortState.dir = 1;
      }
      if (_sortState.dir === 0) {
        _sortState.key = null;
      }
      document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
      });
      if (_sortState.dir > 0) {
        const th = document.querySelector(`th.sortable[onclick*="${key}"]`);
        if (th) th.classList.add(_sortState.dir === 1 ? 'sort-asc' : 'sort-desc');
      }
      renderTable();
    }

    function getSortVal(row, key) {
      let v = row[key];
      if (v === undefined || v === null || (typeof v === 'number' && isNaN(v))) {
        if (key === 'halflife_bars' || key === 'depth' || key === 'operators') return -Infinity;
        return -Infinity;
      }
      if (key === 'passed') return v === true || v === 'PASS' ? 1 : 0;
      if (key === 'max_dd') return -Math.abs(Number(v));
      if (key === 'generated_at') return String(v);
      return Number(v);
    }

    function renderTable() {
      let factors = window._factorsCache || [];
      if (_defaultOrder === null && factors.length > 0) {
        _defaultOrder = factors.map((_, i) => i);
      }
      let indices = factors.map((_, i) => i);
      if (_sortState.key && _sortState.dir > 0) {
        const key = _sortState.key;
        const asc = _sortState.dir === 1;
        indices.sort((a, b) => {
          const va = getSortVal(factors[a], key);
          const vb = getSortVal(factors[b], key);
          if (va < vb) return asc ? -1 : 1;
          if (va > vb) return asc ? 1 : -1;
          return 0;
        });
      }
      leaderboard.innerHTML = indices.slice(0, 100).map((idx) => {
        const row = factors[idx];
        return `
        <tr onclick="showDetail(${idx})" title="点击查看完整信息">
          <td>${idx + 1}</td>
          <td class="${row.passed ? 'pass' : 'fail'}">${row.passed ? 'PASS' : 'KILL'}</td>
          <td>${fmt(row.brutal_score, 2)}</td>
          <td>${fmt(row.rank_ic, 4)}</td>
          <td>${fmt(row.sharpe, 2)}</td>
          <td>${fmt(row.max_dd, 3)}</td>
          <td>${fmt(row.max_corr_to_library, 3)}</td>
          <td>${row.halflife_bars ?? '-'}</td>
          <td>${row.depth ?? '-'}</td>
          <td>${row.operators ?? '-'}</td>
          <td class="muted" style="font-size:11px">${(row.generated_at || '').substring(11, 19) || '-'}</td>
          <td class="formula">${row.formula}</td>
          <td class="muted" style="max-width:280px;font-size:12px">${(row.description || '').substring(0, 100)}${(row.description || '').length > 100 ? '...' : ''}</td>
        </tr>`;
      }).join('');
    }

    async function refresh() {
      const [state, factors, llmLog] = await Promise.all([
        fetch('/api/status').then(r => r.json()),
        fetch('/api/factors').then(r => r.json()),
        fetch('/api/llm_log').then(r => r.json()).catch(() => [])
      ]);
      status.textContent = state.status;
      iterations.textContent = state.iterations_done;
      candidates.textContent = state.candidate_count;
      accepted.textContent = state.accepted_count;
      bestScore.textContent = state.best_score === null ? '-' : fmt(state.best_score, 2);
      elapsed.textContent = elapsed(state.elapsed_seconds);
      message.textContent = state.message || '';
      phase.textContent = state.phase || '-';
      const llmStatus = document.getElementById('llmStatus');
      if (state.last_llm_status) {
        llmStatus.textContent = state.last_llm_status;
        llmStatus.style.color = state.last_llm_status.startsWith('ok') ? 'var(--good)' : 'var(--warn)';
      } else {
        llmStatus.textContent = '-';
        llmStatus.style.color = '';
      }
      if (state.phase === 'llm_or_local_proposal' && state.llm_wait_started_at) {
        const waitSec = Math.round((Date.now() - new Date(state.llm_wait_started_at + 'Z').getTime()) / 1000);
        if (waitSec > 0) message.textContent = (state.message || '') + ' [waiting ' + waitSec + 's]';
      }
      if (state.use_llm) {
        document.body.className = 'llm-mode';
        modeBadge.className = 'badge llm';
        modeBadge.textContent = 'DEEPSEEK';
      } else {
        document.body.className = 'local-mode';
        modeBadge.className = 'badge local';
        modeBadge.textContent = 'LOCAL';
      }
      window._factorsCache = factors;
      if (_sortState.key && _sortState.dir > 0) {
        renderTable();
      } else {
        _defaultOrder = null;
        renderTable();
      }
      if (llmLog && llmLog.length > 0) {
        document.getElementById('llmLog').innerHTML = llmLog.slice(-12).reverse().map(e => {
          const color = e.source === 'deepseek' ? 'var(--good)' : e.source === 'fallback' ? 'var(--bad)' : 'var(--muted)';
          const acc = e.accepted !== undefined ? ` accepted=${e.accepted}/${e.requested}` : '';
          const dur = e.llm_duration_s ? ` ${e.llm_duration_s}s` : '';
          const chars = e.prompt_chars ? ` ${e.prompt_chars}chars` : '';
          const err = e.error_full || e.error || '';
          return `<div style="color:${color};margin-bottom:2px">[${e.source.toUpperCase()}]${acc}${dur}${chars}${err ? ' err=' + err.substring(0,100) : ''}</div>`;
        }).join('');
      } else {
        document.getElementById('llmLog').innerHTML = '<span class="muted">暂无记录 (勾选DeepSeek并开始研究后出现)</span>';
      }
    }

    function showDetail(idx) {
      const row = (window._factorsCache || [])[idx];
      if (!row) return;
      document.getElementById('modalTitle').innerHTML = '因子详情 <span class="muted" style="font-size:13px;font-weight:400">#' + (idx+1) + '</span>';
      const gates = [];
      if (row.gate_predictive_power !== undefined) gates.push(['预测力', row.gate_predictive_power, 'Rank IC >= 0.01 或 胜率 >= 0.49']);
      if (row.gate_homogeneity !== undefined) gates.push(['同质化', row.gate_homogeneity, 'max_corr < 0.70']);
      if (row.gate_autoquant_audit !== undefined) gates.push(['摩擦成本', row.gate_autoquant_audit, 'cost_sharpe >= 0.30']);
      if (row.gate_lifetime !== undefined) gates.push(['寿命', row.gate_lifetime, 'val_sharpe >= 0, halflife >= 1']);
      document.getElementById('modalBody').innerHTML = `
        <div class="full">
          <div class="muted" style="margin-bottom:4px">公式</div>
          <div style="font-family:Consolas,monospace;color:var(--gold);font-size:16px;word-break:break-all;margin-bottom:12px">${row.formula}</div>
        </div>
        <div class="full">
          <div class="muted" style="margin-bottom:4px">逻辑解释</div>
          <div style="line-height:1.7;margin-bottom:12px;font-size:14px">${row.description || '<span class="muted">无</span>'}</div>
        </div>
        <div>
          <div class="muted" style="margin-bottom:4px">残酷分</div>
          <div style="font-size:20px;font-weight:700;color:${(row.brutal_score||0) >= 50 ? 'var(--good)' : 'var(--warn)'}">${fmt(row.brutal_score, 2)}</div>
        </div>
        <div>
          <div class="muted" style="margin-bottom:4px">MCTS分</div>
          <div style="font-size:20px;font-weight:700">${fmt(row.mcts_score, 4)}</div>
        </div>
        <div><span class="muted">Rank IC</span> <strong>${fmt(row.rank_ic, 6)}</strong></div>
        <div><span class="muted">IC</span> <strong>${fmt(row.ic, 6)}</strong></div>
        <div><span class="muted">Sharpe</span> <strong>${fmt(row.sharpe, 2)}</strong></div>
        <div><span class="muted">CAGR</span> <strong>${fmt(row.cagr, 3)}</strong></div>
        <div><span class="muted">最大回撤</span> <strong>${fmt(row.max_dd, 3)}</strong></div>
        <div><span class="muted">胜率</span> <strong>${fmt(row.directional_win_rate, 3)}</strong></div>
        <div><span class="muted">换手率</span> <strong>${fmt(row.turnover, 3)}</strong></div>
        <div><span class="muted">交易次数</span> <strong>${row.trades ?? '-'}</strong></div>
        <div><span class="muted">最大相关</span> <strong>${fmt(row.max_corr_to_library, 3)}</strong></div>
        <div><span class="muted">半衰期(bars)</span> <strong>${row.halflife_bars ?? '-'}</strong></div>
        <div><span class="muted">验证Sharpe</span> <strong>${fmt(row.validation_sharpe, 2)}</strong></div>
        <div><span class="muted">验证Rank IC</span> <strong>${fmt(row.validation_rank_ic, 6)}</strong></div>
        <div><span class="muted">算子数</span> <strong>${row.operators ?? '-'}</strong></div>
        <div><span class="muted">深度</span> <strong>${row.depth ?? '-'}</strong></div>
        <div><span class="muted">生成时间</span> <strong>${row.generated_at || '-'}</strong></div>
        <div></div>
        <div class="full" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px">
          ${gates.map(g => '<span style="padding:4px 12px;border-radius:4px;font-size:12px;font-weight:600;' + (g[1] ? 'background:rgba(14,203,129,.15);color:var(--good)' : 'background:rgba(246,70,93,.15);color:var(--bad)') + '">' + (g[1] ? 'PASS' : 'KILL') + ': ' + g[0] + ' <span class="muted" style="font-weight:400">(' + g[2] + ')</span></span>').join('')}
          ${gates.length === 0 ? '<span class="muted">未审计</span>' : ''}
        </div>
        <div class="full" style="font-size:12px;margin-top:4px">
          <span class="muted"><strong>维度分:</strong>
          effectiveness=${fmt(row.effectiveness,3)} |
          stability=${fmt(row.stability,3)} |
          turnover=${fmt(row.turnover,3)} |
          diversity=${fmt(row.diversity,3)} |
          overfit_risk=${fmt(row.overfit_risk,3)} |
          simplicity=${fmt(row.simplicity,3)}</span>
        </div>`;
      document.getElementById('modalOverlay').classList.add('active');
    }

    async function testDeepSeek() {
      message.textContent = 'Testing DeepSeek connectivity...';
      try {
        const res = await fetch('/api/test_deepseek');
        const data = await res.json();
        if (data.ok) {
          message.innerHTML = '<span style="color:var(--good)">DeepSeek OK: ' + data.message + '</span>';
        } else {
          message.innerHTML = '<span style="color:var(--bad)">DeepSeek FAIL: ' + data.message + '</span>';
        }
      } catch(e) {
        message.innerHTML = '<span style="color:var(--bad)">DeepSeek test error: ' + e.message + '</span>';
      }
    }
    refresh();
    function pollWithJitter() {
      refresh().then(() => {
        const delay = 4000 + Math.random() * 2000;
        setTimeout(pollWithJitter, delay);
      });
    }
    setTimeout(pollWithJitter, 4000 + Math.random() * 2000);
  </script>
</body>
</html>
"""


def run_dashboard(config: str, out: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    import errno
    import socket
    import sys

    session = ResearchSession(config, out)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            ts = datetime.now().strftime("%H:%M:%S")
            if parsed.path == "/":
                self._send(HTML, "text/html; charset=utf-8")
            elif parsed.path == "/api/status":
                snap = session.snapshot()
                self._json(snap)
            elif parsed.path == "/api/factors":
                factors = session.factors()
                self._json(factors)
            elif parsed.path == "/api/llm_log":
                self._json(session.llm_log())
            elif parsed.path == "/api/test_deepseek":
                self._json(session.test_deepseek())
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            body = self._read_json()
            ts = datetime.now().strftime("%H:%M:%S")
            action_label = ""
            if parsed.path == "/api/start":
                hours = float(body.get("hours", 24.0))
                use_llm = bool(body.get("use_llm", True))
                action_label = f"START research: hours={hours}, use_llm={use_llm}"
                print(f"{C_BLUE}[{ts}] *** USER ACTION: {action_label} ***{C_RESET}", flush=True)
                session.log_ui_event("start", {"hours": hours, "use_llm": use_llm})
                self._json(session.start(hours=hours, use_llm=use_llm))
            elif parsed.path == "/api/stop":
                action_label = "GRACEFUL STOP requested"
                print(f"{C_BLUE}[{ts}] *** USER ACTION: {action_label} ***{C_RESET}", flush=True)
                session.log_ui_event("stop", {})
                self._json(session.request_stop())
            elif parsed.path == "/api/emergency":
                action_label = "EMERGENCY STOP requested"
                print(f"{C_BLUE}[{ts}] *** USER ACTION: {action_label} ***{C_RESET}", flush=True)
                session.log_ui_event("emergency_stop", {})
                self._json(session.emergency_stop())
            elif parsed.path == "/api/save":
                action_label = "SAVE + BACKUP requested"
                print(f"{C_BLUE}[{ts}] *** USER ACTION: {action_label} ***{C_RESET}", flush=True)
                session.log_ui_event("save_backup", {})
                self._json(session.save_now())
            elif parsed.path == "/api/purge":
                action_label = "PURGE killed factors"
                print(f"{C_BLUE}[{ts}] *** USER ACTION: {action_label} ***{C_RESET}", flush=True)
                session.log_ui_event("purge_killed", {})
                self._json(session.purge_killed())
            else:
                self.send_error(404)

        def log_message(self, format: str, *args: object) -> None:
            pass  # suppress default HTTP log noise

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def _json(self, data: object) -> None:
            self._send(json.dumps(data, ensure_ascii=False), "application/json; charset=utf-8")

        def _send(self, data: str, content_type: str) -> None:
            payload = data.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                pass

    print(f"{C_CYAN}QuantumRandy Lab starting...{C_RESET}")
    print(f"  URL:  {C_GREEN}http://{host}:{port}{C_RESET}")
    print(f"  Out:  {Path(out).resolve()}")
    print(f"  Cfg:  {Path(config).resolve()}")
    print(f"  Tip:  Open the URL above in your browser. Keep this window open.")
    print(f"  Stop: Press Ctrl+C to exit", flush=True)

    class ReuseServer(ThreadingHTTPServer):
        allow_reuse_address = True
        daemon_threads = True

    for attempt in range(3):
        try:
            server = ReuseServer((host, port), Handler)
            break
        except OSError as exc:
            if attempt < 2 and (exc.errno == errno.EADDRINUSE or getattr(exc, 'winerror', 0) in (10048,)):
                alt_port = port + 1 + attempt
                print(f"[WARN] Port {port} in use, trying port {alt_port}...", flush=True)
                port = alt_port
                continue
            print(f"\n[ERROR] Cannot start server: {exc}", file=sys.stderr)
            print(f"[HINT] Check which process is using the port:", file=sys.stderr)
            print(f"  netstat -ano | findstr :{port}", file=sys.stderr)
            print(f"  then taskkill /PID <PID> /F to kill it", file=sys.stderr)
            return

    print(f"\n>>> QuantumRandy Lab READY: http://{host}:{port} <<<\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nQuantumRandy Lab stopped.", flush=True)
