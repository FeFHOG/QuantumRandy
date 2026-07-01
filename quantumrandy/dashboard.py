from __future__ import annotations

import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd

from .backtest import run_formula_backtest, summarize_ledger, equity_curve, max_drawdown
from .config import CostConfig, ExecutionConfig
from .data import align_funding_to_ohlcv, read_ohlcv, read_funding
from .research import ResearchSession

C_RESET = "\033[0m"
C_BLUE = "\033[34m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_CYAN = "\033[36m"


HTML = r"""<!doctype html>
<html lang="en">
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
    .validate-section { margin-top: 12px; border-top: 1px solid var(--line); padding-top: 12px; }
    .chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }
    .chart-box { background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 10px; }
    .chart-box h4 { margin: 0 0 8px; font-size: 13px; color: var(--muted); }
    .chart-box canvas { width: 100% !important; height: 200px !important; }
    .metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px 16px; margin-top: 8px; }
    .metric-grid .mv { border-left: 2px solid var(--accent); padding-left: 8px; }
    .metric-grid .mv span { display: block; color: var(--muted); font-size: 11px; }
    .metric-grid .mv strong { display: block; font-size: 15px; margin-top: 2px; }
    .review-grid { padding: 12px 14px; display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
    .review-card { background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 12px; min-height: 120px; }
    .review-card h3 { margin: 0 0 10px; font-size: 14px; color: var(--accent); }
    .review-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 10px; }
    .review-stat span { display: block; color: var(--muted); font-size: 11px; }
    .review-stat strong { display: block; font-size: 16px; margin-top: 2px; }
    .review-list { display: grid; gap: 6px; font-size: 12px; }
    .review-row { border-top: 1px solid var(--line); padding-top: 6px; }
    .review-row:first-child { border-top: 0; padding-top: 0; }
    @media (max-width: 900px) { .chart-row { grid-template-columns: 1fr; } .metric-grid { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 1000px) { .review-grid { grid-template-columns: 1fr; } }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
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
      <label>Hours <input id="hours" type="number" min="0.05" step="0.25" value="24"></label>
      <label><input id="useLlm" type="checkbox"> Use LLM</label>
      <button class="primary" onclick="post('/api/start', {hours: Number(hours.value), use_llm: useLlm.checked})">Start / Resume Research</button>
      <button onclick="testLlm()" style="border-color:var(--gold);color:var(--gold)">Test LLM Connection</button>
      <button class="warn" onclick="post('/api/stop', {})">Stop After Current Iteration</button>
      <button onclick="post('/api/save', {})">Save &amp; Backup Now</button>
      <button class="danger" onclick="post('/api/emergency', {})">Emergency Stop</button>
      <button class="warn" onclick="post('/api/purge', {})">Purge Killed Factors</button>
      <button onclick="refresh()">Refresh Factors</button>
    </section>
    <section class="metrics">
      <div class="metric"><span>Status</span><strong id="status">-</strong></div>
      <div class="metric"><span>Iterations</span><strong id="iterations">0</strong></div>
      <div class="metric"><span>Candidates</span><strong id="candidates">0</strong></div>
      <div class="metric"><span>Passed</span><strong id="accepted" style="color:var(--good)">0</strong></div>
      <div class="metric"><span>Killed</span><strong id="killedCount" style="color:var(--bad)">0</strong></div>
      <div class="metric"><span>Best Score</span><strong id="bestScore">-</strong></div>
      <div class="metric"><span>Elapsed</span><strong id="elapsed">0m</strong></div>
      <div class="metric"><span>Phase</span><strong id="phase">-</strong></div>
      <div class="metric"><span>LLM Status</span><strong id="llmStatus" style="font-size:14px">-</strong></div>
    </section>
    <section class="panel" id="killPanel" style="display:none">
      <h2>Kill Breakdown <span class="muted" style="font-size:12px;font-weight:400">(Why factors are killed in the brutal filter)</span></h2>
      <div id="killBreakdown" style="padding:10px 14px;display:flex;gap:16px;flex-wrap:wrap;font-size:13px"></div>
    </section>
    <section class="panel" id="reviewPanel" style="display:none">
      <h2>Research Review <span class="muted" style="font-size:12px;font-weight:400">(Read-only data, universe, selector rewrite, admission, failure memory, and portfolio artifacts)</span></h2>
      <div id="researchReview" class="review-grid"></div>
    </section>
    <section class="panel">
      <h2>Factor Leaderboard <span class="muted" style="font-size:12px;font-weight:400">(Click row for details · Click header to sort)</span></h2>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th class="sortable" onclick="sortTable('passed')">Status <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('brutal_score')">Brutal Score <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('rank_ic')">Rank IC <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('sharpe')">Sharpe <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('max_dd')">Max DD <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('max_corr_to_library')">Max Corr <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('halflife_bars')">Half-life <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('depth')">Depth <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('operators')">Ops <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('generated_at')">Generated <span class="sort-arrow">&#9650;</span></th>
            <th class="sortable" onclick="sortTable('formula')">Formula <span class="sort-arrow">&#9650;</span></th>
            <th>Rationale</th>
          </tr>
        </thead>
        <tbody id="leaderboard"></tbody>
      </table>
    </section>
    <section class="panel" id="llmLogPanel">
      <h2>LLM Call Log</h2>
      <div id="llmLog" style="padding:8px 14px;max-height:200px;overflow-y:auto;font-family:Consolas,monospace;font-size:12px">
        <span class="muted">No records yet</span>
      </div>
    </section>
  </main>

  <div id="modalOverlay" class="modal-overlay" onclick="if(event.target===this)closeModal()">
    <div class="modal-box">
      <div class="modal-header">
        <h2 id="modalTitle">Factor Detail</h2>
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
        <tr onclick="showDetail(${idx})" title="Click to view full details">
          <td>${idx + 1}</td>
          <td class="${row.passed ? 'pass' : 'fail'}" title="${row.passed ? '' : (row.kill_reasons||[]).join(', ')}">${row.passed ? 'PASS' : 'KILL'}</td>
          <td>${fmt(row.brutal_score, 2)}</td>
          <td>${fmt(row.rank_ic, 4)}</td>
          <td>${fmt(row.sharpe, 2)}</td>
          <td>${fmt(row.max_dd, 3)}</td>
          <td>${fmt(row.max_corr_to_library, 3)}</td>
          <td>${row.halflife_bars ?? '-'}</td>
          <td>${row.depth ?? '-'}</td>
          <td>${row.operators ?? '-'}</td>
          <td class="muted" style="font-size:11px">${row.generated_at ? row.generated_at.substring(5,10) + ' ' + row.generated_at.substring(11,16) : '-'}</td>
          <td class="formula">${row.formula}</td>
          <td class="muted" style="max-width:280px;font-size:12px">${(row.description || '').substring(0, 100)}${(row.description || '').length > 100 ? '...' : ''}</td>
        </tr>`;
      }).join('');
    }

    async function refresh() {
      const [state, factors, llmLog, review] = await Promise.all([
        fetch('/api/status').then(r => r.json()),
        fetch('/api/factors').then(r => r.json()),
        fetch('/api/llm_log').then(r => r.json()).catch(() => []),
        fetch('/api/research_review').then(r => r.json()).catch(() => ({available:false}))
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
        modeBadge.textContent = 'LLM';
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
      const totalFactors = (window._factorsCache || []).length;
      const killedFactors = (window._factorsCache || []).filter(function(r){return !r.passed && r.kill_reasons;});
      const killCount = killedFactors.length;
      const passedCount = (window._factorsCache || []).filter(function(r){return r.passed;}).length;
      killedCount.textContent = killCount;
      if (killCount > 0) {
        const reasonCounts = {};
        killedFactors.forEach(function(r){
          (r.kill_reasons||[]).forEach(function(reason){
            reasonCounts[reason] = (reasonCounts[reason]||0) + 1;
          });
        });
        const labels = {
          predictive_power: 'Predictive Power',
          homogeneity: 'Homogeneity',
          friction_audit: 'Friction Audit',
          lifetime: 'Lifetime'
        };
        const rules = {
          predictive_power: 'rank_ic>=0.01 & win_rate>=0.49',
          homogeneity: 'max_corr<0.70',
          friction_audit: 'cost_sharpe>=0.30',
          lifetime: 'val_sharpe>=0 & halflife>=1'
        };
        document.getElementById('killPanel').style.display = '';
        document.getElementById('killBreakdown').innerHTML = Object.keys(reasonCounts).sort(function(a,b){return reasonCounts[b]-reasonCounts[a];}).map(function(reason){
          const pct = (reasonCounts[reason] / killCount * 100).toFixed(0);
          return '<div style="flex:1;min-width:160px;padding:10px 14px;background:var(--bg);border-radius:6px;border-left:3px solid var(--bad)">' +
            '<div style="font-weight:700;color:var(--bad);margin-bottom:4px">' + (labels[reason]||reason) + ': ' + reasonCounts[reason] + ' (' + pct + '%)</div>' +
            '<div class="muted" style="font-size:11px">Rule: ' + (rules[reason]||'') + '</div></div>';
        }).join('');
      } else {
        document.getElementById('killPanel').style.display = 'none';
      }
      if (llmLog && llmLog.length > 0) {
        document.getElementById('llmLog').innerHTML = llmLog.slice(-12).reverse().map(e => {
          const color = e.source === 'llm' || e.source === 'llm_rewrite' ? 'var(--good)' : e.source === 'fallback' ? 'var(--bad)' : 'var(--muted)';
          const acc = e.accepted !== undefined ? ` accepted=${e.accepted}/${e.requested}` : '';
          const dur = e.llm_duration_s ? ` ${e.llm_duration_s}s` : '';
          const chars = e.prompt_chars ? ` ${e.prompt_chars}chars` : '';
          const err = e.error_full || e.error || '';
          return `<div style="color:${color};margin-bottom:2px">[${e.source.toUpperCase()}]${acc}${dur}${chars}${err ? ' err=' + err.substring(0,100) : ''}</div>`;
        }).join('');
      } else {
        document.getElementById('llmLog').innerHTML = '<span class="muted">No records (enable LLM and start research)</span>';
      }
      renderResearchReview(review);
    }

    function renderResearchReview(review) {
      const panel = document.getElementById('reviewPanel');
      const box = document.getElementById('researchReview');
      if (!review || !review.available) {
        panel.style.display = 'none';
        return;
      }
      panel.style.display = '';
      const dataReadiness = review.data_readiness || {};
      const universe = review.universe_robustness || {};
      const portfolioUniverse = review.portfolio_universe || {};
      const selectorEvidence = review.selector_pipeline_evidence || {};
      const selectorPipeline = review.selector_pipeline_review || {};
      const admission = review.admission || {};
      const failure = review.failure_memory || {};
      const portfolio = review.portfolio_walk_forward || {};
      const pareto = review.pareto_archive || {};
      box.innerHTML =
        reviewDataReadinessCard(dataReadiness) +
        reviewUniverseCard(universe) +
        reviewPortfolioUniverseCard(portfolioUniverse) +
        reviewSelectorEvidenceCard(selectorEvidence) +
        reviewSelectorPipelineCard(selectorPipeline) +
        reviewAdmissionCard(admission) +
        reviewFailureCard(failure) +
        reviewPortfolioCard(portfolio) +
        reviewParetoCard(pareto);
    }

    function reviewDataReadinessCard(data) {
      const rows = data.rows || [];
      return '<div class="review-card"><h3>Data Readiness</h3>' +
        '<div class="review-stats">' +
        '<div class="review-stat"><span>Ready</span><strong style="color:var(--good)">' + (data.ready ?? 0) + '/' + (data.assets ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Min Coverage</span><strong>' + fmt(data.min_research_coverage, 2) + '</strong></div>' +
        '<div class="review-stat"><span>Max Gap</span><strong>' + (data.max_missing_bars ?? 0) + '</strong></div>' +
        '</div><div class="muted" style="font-size:11px;margin-bottom:8px">' + (data.source || 'No data readiness artifact') + '</div>' +
        '<div class="review-list">' + rows.map(r =>
          '<div class="review-row"><strong class="' + (r.status === 'ready' ? 'pass' : 'fail') + '">' + escapeHtml(r.symbol || '-') +
          '</strong><br><span class="muted">coverage=' + fmt(r.research_coverage_ratio, 2) +
          ' funding=' + fmt(r.funding_alignment_coverage, 2) + ' stale_h=' + fmt(r.funding_max_staleness_hours, 1) +
          '</span></div>'
        ).join('') + '</div></div>';
    }

    function reviewUniverseCard(data) {
      const rows = data.top || [];
      return '<div class="review-card"><h3>Universe Robustness</h3>' +
        '<div class="review-stats">' +
        '<div class="review-stat"><span>Formulas</span><strong>' + (data.formulas ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Best Pass</span><strong style="color:var(--warn)">' + fmt(data.max_pass_rate ?? data.best_pass_rate, 2) + '</strong></div>' +
        '<div class="review-stat"><span>Assets</span><strong>' + (data.assets ?? 0) + '</strong></div>' +
        '</div><div class="muted" style="font-size:11px;margin-bottom:8px">' + (data.source || 'No universe artifact') + '</div>' +
        '<div class="review-list">' + rows.map(r =>
          '<div class="review-row"><span style="font-family:Consolas,monospace;color:var(--gold)">' + escapeHtml(r.factor_id || '-') +
          '</span><br><span class="muted">pass=' + fmt(r.pass_rate, 2) + ' sharpe=' + fmt(r.mean_sharpe, 2) +
          ' rank_ic=' + fmt(r.median_rank_ic, 4) + '</span></div>'
        ).join('') + '</div></div>';
    }

    function reviewPortfolioUniverseCard(data) {
      const rows = data.top || [];
      return '<div class="review-card"><h3>Portfolio Universe</h3>' +
        '<div class="review-stats">' +
        '<div class="review-stat"><span>Portfolios</span><strong>' + (data.portfolios ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Best Pass</span><strong style="color:var(--warn)">' + fmt(data.max_pass_rate ?? data.best_pass_rate, 2) + '</strong></div>' +
        '<div class="review-stat"><span>Assets</span><strong>' + (data.assets ?? 0) + '</strong></div>' +
        '</div><div class="muted" style="font-size:11px;margin-bottom:8px">' + (data.source || 'No portfolio universe artifact') + '</div>' +
        '<div class="review-list">' + rows.map(r =>
          '<div class="review-row"><strong>' + escapeHtml(r.portfolio_id || '-') +
          '</strong><br><span class="muted">pass=' + fmt(r.pass_rate, 2) + ' sharpe=' + fmt(r.mean_sharpe, 2) +
          ' rank_ic=' + fmt(r.median_rank_ic, 4) + '</span></div>'
        ).join('') + '</div></div>';
    }

    function reviewSelectorPipelineCard(data) {
      const rows = data.top || [];
      const candidateRows = data.candidate_top || [];
      const highlightRows = data.candidate_highlights || [];
      return '<div class="review-card"><h3>Selector Pipeline Review</h3>' +
        '<div class="review-stats">' +
        '<div class="review-stat"><span>Improved</span><strong style="color:var(--good)">' + (data.improved ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Coverage Only</span><strong style="color:var(--warn)">' + (data.coverage_only ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Mixed</span><strong style="color:var(--warn)">' + (data.mixed ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Not Improved</span><strong style="color:var(--bad)">' + (data.not_improved ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Needs Eval</span><strong>' + (data.needs_evaluation ?? 0) + '</strong></div>' +
        '</div><div class="muted" style="font-size:11px;margin-bottom:8px">' + (data.source || 'No selector pipeline review artifact') + '</div>' +
        '<div class="muted" style="font-size:11px;margin-bottom:8px">parents=' + (data.parents ?? 0) +
        ' candidates=' + (data.candidates ?? 0) + ' evaluated=' + (data.evaluated_candidates ?? 0) + '</div>' +
        '<div class="muted" style="font-size:11px;margin-bottom:8px">candidate verdicts: improved=' + (data.candidate_improved ?? 0) +
        ' coverage=' + (data.candidate_coverage_only ?? 0) + ' mixed=' + (data.candidate_mixed ?? 0) +
        ' not=' + (data.candidate_not_improved ?? 0) + '</div>' +
        '<div class="muted" style="font-size:11px;margin-bottom:8px">llm_evidence=' + (data.is_llm_policy_evidence ? 'true' : 'false') +
        ' llm_accepted=' + (data.llm_rewrite_accepted ?? 0) + ' fallback_accepted=' + (data.fallback_rewrite_accepted ?? 0) + '</div>' +
        (highlightRows.length ? '<div class="muted" style="font-size:11px;margin-bottom:8px">highlight queues: true=' +
          (data.candidate_true_improved ?? 0) + ' traps=' + (data.candidate_coverage_traps ?? 0) +
          ' sharpe_only=' + (data.candidate_sharpe_improved_no_pass_lift ?? 0) + '</div>' : '') +
        '<div class="review-list">' + rows.map(r =>
          '<div class="review-row"><strong class="' + (r.verdict === 'improved' ? 'pass' : r.verdict === 'not_improved' ? 'fail' : '') + '">' +
          escapeHtml(r.verdict || '-') + '</strong> <span class="muted">' + escapeHtml(r.parent_factor_id || '-') +
          '</span><br><span class="muted">pass_delta=' + fmt(r.pass_rate_delta, 2) + ' sharpe_delta=' + fmt(r.mean_sharpe_delta, 2) +
          ' best_pass=' + fmt(r.best_candidate_pass_rate, 2) + ' best_sharpe=' + fmt(r.best_candidate_mean_sharpe, 2) +
          ' src=' + escapeHtml(r.best_candidate_generation_source || '-') +
          '</span><br><span style="font-family:Consolas,monospace;color:var(--gold)">' + escapeHtml(r.best_candidate_factor_id || '-') +
          '</span><br><span class="muted">' + escapeHtml(r.best_candidate_formula || '-') + '</span></div>'
        ).join('') + '</div>' +
        (highlightRows.length ? '<div class="review-list" style="margin-top:8px">' + highlightRows.map(r =>
          '<div class="review-row"><strong class="' + (r.highlight_type === 'true_improved' ? 'pass' : r.highlight_type === 'coverage_only_trap' ? 'fail' : '') + '">' +
          escapeHtml(r.highlight_type || '-') + '</strong> <span style="font-family:Consolas,monospace;color:var(--gold)">' +
          escapeHtml(r.factor_id || '-') + '</span><br><span class="muted">parent=' + escapeHtml(r.parent_factor_id || '-') +
          ' src=' + escapeHtml(r.rewrite_generation_source || '-') +
          ' pass_delta=' + fmt(r.pass_rate_delta, 2) + ' sharpe_delta=' + fmt(r.mean_sharpe_delta, 2) +
          ' pass=' + fmt(r.candidate_pass_rate, 2) + ' sharpe=' + fmt(r.candidate_mean_sharpe, 2) +
          '</span><br><span class="muted">failed_assets=' + escapeHtml(r.candidate_failed_assets || 'none') +
          '</span><br><span class="muted">' + escapeHtml(r.formula || '-') + '</span></div>'
        ).join('') + '</div>' : candidateRows.length ? '<div class="review-list" style="margin-top:8px">' + candidateRows.map(r =>
          '<div class="review-row"><strong class="' + (r.verdict === 'improved' ? 'pass' : r.verdict === 'not_improved' ? 'fail' : '') + '">' +
          escapeHtml(r.verdict || '-') + '</strong> <span style="font-family:Consolas,monospace;color:var(--gold)">' +
          escapeHtml(r.factor_id || '-') + '</span><br><span class="muted">parent=' + escapeHtml(r.parent_factor_id || '-') +
          ' src=' + escapeHtml(r.rewrite_generation_source || '-') +
          ' pass_delta=' + fmt(r.pass_rate_delta, 2) + ' sharpe_delta=' + fmt(r.mean_sharpe_delta, 2) +
          ' pass=' + fmt(r.candidate_pass_rate, 2) + ' sharpe=' + fmt(r.candidate_mean_sharpe, 2) +
          '</span><br><span class="muted">failed_assets=' + escapeHtml(r.candidate_failed_assets || 'none') +
          '</span><br><span class="muted">' + escapeHtml(r.formula || '-') + '</span></div>'
        ).join('') + '</div>' : '') + '</div>';
    }

    function reviewSelectorEvidenceCard(data) {
      const rows = data.top || [];
      return '<div class="review-card"><h3>Selector Evidence Runs</h3>' +
        '<div class="review-stats">' +
        '<div class="review-stat"><span>Runs</span><strong>' + (data.runs ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>LLM Evidence</span><strong style="color:var(--warn)">' + (data.llm_policy_evidence_runs ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>LLM Improved</span><strong style="color:var(--good)">' + (data.llm_true_improvement_evidence_runs ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Trap Runs</span><strong style="color:var(--bad)">' + (data.coverage_only_trap_runs ?? 0) + '</strong></div>' +
        '</div><div class="muted" style="font-size:11px;margin-bottom:8px">' + (data.source || 'No selector evidence summary artifact') + '</div>' +
        '<div class="review-list">' + rows.map(r =>
          '<div class="review-row"><strong class="' + (r.is_llm_true_improvement_evidence ? 'pass' : '') + '">' +
          escapeHtml(r.run_id || '-') + '</strong><br><span class="muted">llm=' + (r.is_llm_policy_evidence ? 'true' : 'false') +
          ' llm_improved=' + (r.is_llm_true_improvement_evidence ? 'true' : 'false') +
          ' llm_true=' + (r.llm_true_improved_count ?? 0) +
          ' traps=' + (r.coverage_only_trap_count ?? 0) +
          '</span><br><span class="muted">sources=' + escapeHtml(r.candidate_source_mix || 'none') +
          ' highlights=' + escapeHtml(r.candidate_highlight_source_mix || 'none') +
          '</span><br><span style="font-family:Consolas,monospace;color:var(--gold)">' +
          escapeHtml(r.best_llm_true_improved_factor_id || '-') + '</span><br><span class="muted">' +
          escapeHtml(r.best_llm_true_improved_formula || '-') + '</span></div>'
        ).join('') + '</div></div>';
    }

    function reviewAdmissionCard(data) {
      const top = data.top || [];
      return '<div class="review-card"><h3>Admission</h3>' +
        '<div class="review-stats">' +
        '<div class="review-stat"><span>Approved</span><strong style="color:var(--good)">' + (data.approved ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Review</span><strong style="color:var(--warn)">' + (data.review ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Rejected</span><strong style="color:var(--bad)">' + (data.rejected ?? 0) + '</strong></div>' +
        '</div><div class="muted" style="font-size:11px;margin-bottom:8px">' + (data.source || 'No admission artifact') + '</div>' +
        '<div class="review-list">' + top.map(r =>
          '<div class="review-row"><strong class="' + (r.status === 'approve' ? 'pass' : r.status === 'reject' ? 'fail' : '') + '">' + (r.status || '-') +
          '</strong> <span class="muted">' + fmt(r.score, 1) + '</span><br><span style="font-family:Consolas,monospace;color:var(--gold)">' +
          escapeHtml(r.factor_id || '-') + '</span><br><span class="muted">' + escapeHtml(r.failed_rules || 'all gates pass') + '</span></div>'
        ).join('') + '</div></div>';
    }

    function reviewFailureCard(data) {
      const clusters = data.clusters || [];
      return '<div class="review-card"><h3>Failure Memory</h3>' +
        '<div class="review-stats">' +
        '<div class="review-stat"><span>Failures</span><strong style="color:var(--bad)">' + (data.failures ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Clusters</span><strong>' + (data.cluster_count ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Top Count</span><strong>' + (clusters[0]?.count ?? 0) + '</strong></div>' +
        '</div><div class="muted" style="font-size:11px;margin-bottom:8px">' + (data.source || 'No failure memory artifact') + '</div>' +
        '<div class="review-list">' + clusters.map(r =>
          '<div class="review-row"><span style="font-family:Consolas,monospace;color:var(--gold)">' + escapeHtml(r.subtree || '-') +
          '</span><br><span class="muted">count=' + (r.count ?? '-') + ' gates=' + escapeHtml(r.failed_gates || '-') + '</span></div>'
        ).join('') + '</div></div>';
    }

    function reviewPortfolioCard(data) {
      const rows = data.top || [];
      return '<div class="review-card"><h3>Portfolio Walk-Forward</h3>' +
        '<div class="review-stats">' +
        '<div class="review-stat"><span>Portfolios</span><strong>' + (data.portfolios ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Best Survival</span><strong style="color:var(--good)">' + fmt(data.best_survival, 2) + '</strong></div>' +
        '<div class="review-stat"><span>Windows</span><strong>' + (data.best_windows ?? 0) + '</strong></div>' +
        '</div><div class="muted" style="font-size:11px;margin-bottom:8px">' + (data.source || 'No portfolio walk-forward artifact') + '</div>' +
        '<div class="review-list">' + rows.map(r =>
          '<div class="review-row"><strong>' + escapeHtml(r.portfolio_id || '-') + '</strong><br><span class="muted">survival=' +
          fmt(r.survival_rate, 2) + ' test_sharpe=' + fmt(r.test_sharpe_median, 2) + ' rank_ic=' + fmt(r.test_rank_ic_median, 4) +
          '</span></div>'
        ).join('') + '</div></div>';
    }

    function reviewParetoCard(data) {
      const rows = data.front || [];
      return '<div class="review-card"><h3>Pareto Archive</h3>' +
        '<div class="review-stats">' +
        '<div class="review-stat"><span>Alphas</span><strong>' + (data.alpha_count ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Front</span><strong style="color:var(--good)">' + (data.front_count ?? 0) + '</strong></div>' +
        '<div class="review-stat"><span>Objectives</span><strong>' + ((data.objectives || []).length) + '</strong></div>' +
        '</div><div class="muted" style="font-size:11px;margin-bottom:8px">' + (data.source || 'No Pareto archive artifact') + '</div>' +
        '<div class="review-list">' + rows.map(r =>
          '<div class="review-row"><span style="font-family:Consolas,monospace;color:var(--gold)">' + escapeHtml(r.formula || '-') +
          '</span><br><span class="muted">rank_ic=' + fmt(r.rank_ic, 4) + ' sharpe=' + fmt(r.sharpe, 2) +
          ' turnover=' + fmt(r.turnover, 3) + '</span></div>'
        ).join('') + '</div></div>';
    }

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    }

    function showDetail(idx) {
      const row = (window._factorsCache || [])[idx];
      if (!row) return;
      document.getElementById('modalTitle').innerHTML = 'Factor Detail <span class="muted" style="font-size:13px;font-weight:400">#' + (idx+1) + '</span>';
      const killReasons = row.kill_reasons || [];
      const gates = [];
      if (row.gate_predictive_power !== undefined) gates.push(['Predictive Power', row.gate_predictive_power, 'Rank IC >= 0.01 AND Win Rate >= 0.49', 'rank_ic=' + fmt(row.rank_ic,4) + ' win_rate=' + fmt(row.directional_win_rate,3)]);
      if (row.gate_homogeneity !== undefined) gates.push(['Homogeneity', row.gate_homogeneity, 'max_corr < 0.70', 'max_corr=' + fmt(row.max_corr_to_library,3)]);
      if (row.gate_friction_audit !== undefined) gates.push(['Friction Audit', row.gate_friction_audit, 'cost_sharpe >= 0.30', 'cost_sharpe=' + fmt(row.sharpe,2)]);
      if (row.gate_lifetime !== undefined) gates.push(['Lifespan', row.gate_lifetime, 'val_sharpe >= 0, halflife >= 1', 'val_sharpe=' + fmt(row.validation_sharpe,2) + ' halflife=' + (row.halflife_bars||'-')]);
      document.getElementById('modalBody').innerHTML = `
        <div class="full">
          <div class="muted" style="margin-bottom:4px">Formula</div>
          <div style="font-family:Consolas,monospace;color:var(--gold);font-size:16px;word-break:break-all;margin-bottom:12px">${row.formula}</div>
        </div>
        <div class="full">
          <div class="muted" style="margin-bottom:4px">Rationale</div>
          <div style="line-height:1.7;margin-bottom:12px;font-size:14px">${row.description || '<span class="muted">None</span>'}</div>
        </div>
        <div>
          <div class="muted" style="margin-bottom:4px">Brutal Score</div>
          <div style="font-size:20px;font-weight:700;color:${(row.brutal_score||0) >= 50 ? 'var(--good)' : 'var(--warn)'}">${fmt(row.brutal_score, 2)}</div>
        </div>
        <div>
          <div class="muted" style="margin-bottom:4px">MCTS Score</div>
          <div style="font-size:20px;font-weight:700">${fmt(row.mcts_score, 4)}</div>
        </div>
        ${!row.passed && killReasons.length > 0 ? '<div class="full" style="padding:10px 14px;background:rgba(246,70,93,.1);border:1px solid var(--bad);border-radius:8px;margin-bottom:4px"><span style="color:var(--bad);font-weight:700">KILLED by: ' + killReasons.map(function(r){return ({predictive_power:'Predictive Power',homogeneity:'Homogeneity',friction_audit:'Friction Audit',lifetime:'Lifetime'})[r]||r;}).join(', ') + '</span></div>' : ''}
        <div><span class="muted">Rank IC</span> <strong>${fmt(row.rank_ic, 6)}</strong></div>
        <div><span class="muted">IC</span> <strong>${fmt(row.ic, 6)}</strong></div>
        <div><span class="muted">Sharpe</span> <strong>${fmt(row.sharpe, 2)}</strong></div>
        <div><span class="muted">CAGR</span> <strong>${fmt(row.cagr, 3)}</strong></div>
        <div><span class="muted">Max Drawdown</span> <strong>${fmt(row.max_dd, 3)}</strong></div>
        <div><span class="muted">Win Rate</span> <strong>${fmt(row.directional_win_rate, 3)}</strong></div>
        <div><span class="muted">Turnover</span> <strong>${fmt(row.turnover, 3)}</strong></div>
        <div><span class="muted">Trades</span> <strong>${row.trades ?? '-'}</strong></div>
        <div><span class="muted">Max Corr</span> <strong>${fmt(row.max_corr_to_library, 3)}</strong></div>
        <div><span class="muted">Half-life (bars)</span> <strong>${row.halflife_bars ?? '-'}</strong></div>
        <div><span class="muted">Val Sharpe</span> <strong>${fmt(row.validation_sharpe, 2)}</strong></div>
        <div><span class="muted">Val Rank IC</span> <strong>${fmt(row.validation_rank_ic, 6)}</strong></div>
        <div><span class="muted">Operators</span> <strong>${row.operators ?? '-'}</strong></div>
        <div><span class="muted">Depth</span> <strong>${row.depth ?? '-'}</strong></div>
        <div><span class="muted">Generated</span> <strong>${row.generated_at || '-'}</strong></div>
        <div></div>
        <div class="full" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px">
          ${gates.map(g => '<span style="padding:4px 12px;border-radius:4px;font-size:12px;font-weight:600;' + (g[1] ? 'background:rgba(14,203,129,.15);color:var(--good)' : 'background:rgba(246,70,93,.15);color:var(--bad)') + '">' + (g[1] ? 'PASS' : 'KILL') + ': ' + g[0] + ' <span class="muted" style="font-weight:400">(' + g[2] + ' | ' + g[3] + ')</span></span>').join('')}
          ${gates.length === 0 ? '<span class="muted">Not audited</span>' : ''}
        </div>
        <div class="full" style="font-size:12px;margin-top:4px">
          <span class="muted"><strong>Dimension Scores:</strong>
          effectiveness=${fmt(row.effectiveness,3)} |
          stability=${fmt(row.stability,3)} |
          turnover=${fmt(row.turnover,3)} |
          diversity=${fmt(row.diversity,3)} |
          overfit_risk=${fmt(row.overfit_risk,3)} |
          simplicity=${fmt(row.simplicity,3)}</span>
        </div>
        <div class="full validate-section">
          <button onclick="event.stopPropagation();validateFactor(${idx})" style="border-color:var(--gold);color:var(--gold);font-weight:700">
            Validate (2026 Blind)
          </button>
          <span class="muted" style="margin-left:8px;font-size:12px">Independent backtest on 2026.1.1-2026.5.1 unseen data</span>
          <div id="validateResult${idx}" style="margin-top:12px"></div>
        </div>`;
      document.getElementById('modalOverlay').classList.add('active');
    }

    let _chartInstances = {};

    async function validateFactor(idx) {
      const row = (window._factorsCache || [])[idx];
      if (!row) return;
      const container = document.getElementById('validateResult' + idx);
      container.innerHTML = '<div class="muted" style="padding:8px">Running 2026 blind backtest...</div>';
      try {
        const res = await fetch('/api/validate_factor?formula=' + encodeURIComponent(row.formula));
        const data = await res.json();
        if (data.error) {
          container.innerHTML = '<div style="color:var(--bad);padding:8px">Backtest error: ' + data.error + '</div>';
          return;
        }
        const b = data.blind;
        const isGood = b.sharpe >= 0.5;
        const statusColor = isGood ? 'var(--good)' : (b.sharpe >= 0 ? 'var(--warn)' : 'var(--bad)');
        const statusLabel = isGood ? 'SURVIVED' : (b.sharpe >= 0 ? 'WEAK' : 'DEAD');

        let html = '<div style="margin-top:8px;padding:12px;background:var(--bg);border-radius:8px;border:1px solid ' + statusColor + '">';
        html += '<div style="font-size:18px;font-weight:700;color:' + statusColor + ';margin-bottom:10px">2026 Blind: ' + statusLabel + ' (Sharpe=' + fmt(b.sharpe,3) + ')</div>';
        html += '<div class="metric-grid">';
        html += '<div class="mv"><span>Sharpe</span><strong style="color:' + statusColor + '">' + fmt(b.sharpe,3) + '</strong></div>';
        html += '<div class="mv"><span>CAGR</span><strong>' + fmt(b.cagr,3) + '</strong></div>';
        html += '<div class="mv"><span>Max DD</span><strong>' + fmt(b.max_dd,3) + '</strong></div>';
        html += '<div class="mv"><span>Rank IC</span><strong>' + fmt(b.rank_ic,4) + '</strong></div>';
        html += '<div class="mv"><span>IC</span><strong>' + fmt(b.ic,4) + '</strong></div>';
        html += '<div class="mv"><span>Win Rate</span><strong>' + fmt(b.directional_win_rate,3) + '</strong></div>';
        html += '<div class="mv"><span>Turnover</span><strong>' + fmt(b.turnover,3) + '</strong></div>';
        html += '<div class="mv"><span>Trades</span><strong>' + b.trades + '</strong></div>';
        html += '<div class="mv"><span>Net Return</span><strong>' + fmt(b.net_total,3) + '</strong></div>';
        html += '<div class="mv"><span>Bars</span><strong>' + b.bars + '</strong></div>';
        html += '<div class="mv"><span>Blind Period</span><strong>2026.1-5</strong></div>';
        html += '<div class="mv"><span>BTC Range</span><strong>$62.8k-$97.2k</strong></div>';
        html += '</div>';

        if (data.chart && data.chart.equity && data.chart.equity.length > 0) {
          html += '<div class="chart-row">';
          html += '<div class="chart-box"><h4>Equity Curve</h4><canvas id="equityChart' + idx + '"></canvas></div>';
          html += '<div class="chart-box"><h4>Drawdown</h4><canvas id="ddChart' + idx + '"></canvas></div>';
          html += '</div>';
        }

        if (data.trade_list && data.trade_list.length > 0) {
          html += '<div style="margin-top:12px;font-size:12px;max-height:200px;overflow-y:auto">';
          html += '<table style="width:100%;font-size:11px"><tr><th>Entry</th><th>Exit</th><th>Side</th><th>Entry Price</th><th>Exit Price</th><th>Bars Held</th><th>PnL%</th></tr>';
          data.trade_list.slice(-20).reverse().forEach(function(t) {
            const pnlColor = (t.pnl||0) >= 0 ? 'var(--good)' : 'var(--bad)';
            html += '<tr><td>' + (t.entry_time||'').substring(5,16) + '</td><td>' + (t.exit_time||'').substring(5,16) + '</td><td>' + (t.side||'') + '</td><td>' + fmt(t.entry_price,1) + '</td><td>' + fmt(t.exit_price,1) + '</td><td>' + (t.bars_held||'-') + '</td><td style="color:' + pnlColor + '">' + (t.pnl!=null?(t.pnl>=0?'+':'')+fmt(t.pnl,2)+'%':'') + '</td></tr>';
          });
          html += '</table></div>';
        }

        html += '</div>';
        container.innerHTML = html;

        if (data.chart && data.chart.equity && data.chart.equity.length > 0) {
          const labels = data.chart.timestamps.map(t => t.substring(5,10));
          const step = Math.max(1, Math.floor(labels.length / 12));
          const displayLabels = labels.map((l, i) => i % step === 0 ? l : '');

          const oldEq = _chartInstances['eq' + idx];
          const oldDd = _chartInstances['dd' + idx];
          if (oldEq) oldEq.destroy();
          if (oldDd) oldDd.destroy();

          const eqCtx = document.getElementById('equityChart' + idx);
          const ddCtx = document.getElementById('ddChart' + idx);
          if (eqCtx) {
            _chartInstances['eq' + idx] = new Chart(eqCtx, {
              type: 'line',
              data: {
                labels: displayLabels,
                datasets: [{
                  data: data.chart.equity,
                  borderColor: '#0ecb81',
                  backgroundColor: 'rgba(14,203,129,0.1)',
                  fill: true,
                  pointRadius: 0,
                  borderWidth: 1.5,
                  tension: 0.1,
                }]
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                  x: { ticks: { color: '#848e9c', font: { size: 9 }, maxTicksLimit: 12 } },
                  y: { ticks: { color: '#848e9c', font: { size: 9 } }, grid: { color: '#2b3139' } }
                },
                animation: false,
              }
            });
          }
          if (ddCtx) {
            _chartInstances['dd' + idx] = new Chart(ddCtx, {
              type: 'line',
              data: {
                labels: displayLabels,
                datasets: [{
                  data: data.chart.drawdown,
                  borderColor: '#f6465d',
                  backgroundColor: 'rgba(246,70,93,0.15)',
                  fill: true,
                  pointRadius: 0,
                  borderWidth: 1.5,
                  tension: 0.1,
                }]
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { display: false },
                  tooltip: {
                    callbacks: {
                      label: function(ctx) { return (ctx.raw * 100).toFixed(1) + '%'; }
                    }
                  }
                },
                scales: {
                  x: { ticks: { color: '#848e9c', font: { size: 9 }, maxTicksLimit: 12 } },
                  y: {
                    ticks: {
                      color: '#848e9c', font: { size: 9 },
                      callback: function(v) { return (v * 100).toFixed(0) + '%'; }
                    },
                    grid: { color: '#2b3139' }
                  }
                },
                animation: false,
              }
            });
          }
        }
      } catch(e) {
        container.innerHTML = '<div style="color:var(--bad);padding:8px">Request failed: ' + e.message + '</div>';
      }
    }

    async function testLlm() {
      message.textContent = 'Testing LLM connectivity...';
      try {
        const res = await fetch('/api/test_llm');
        const data = await res.json();
        if (data.ok) {
          message.innerHTML = '<span style="color:var(--good)">LLM OK: ' + data.message + '</span>';
        } else {
          message.innerHTML = '<span style="color:var(--bad)">LLM FAIL: ' + data.message + '</span>';
        }
        refresh();
      } catch(e) {
        message.innerHTML = '<span style="color:var(--bad)">LLM test error: ' + e.message + '</span>';
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


_blind_cache: dict | None = None


def _load_blind_data():
    """Load 2026 blind validation data. Cached at module level for speed."""
    global _blind_cache
    if _blind_cache is not None:
        return _blind_cache["data"], _blind_cache["bar_hours"], _blind_cache["costs"], _blind_cache["execution"]
    base = Path(__file__).resolve().parents[2] / "RandysLab-STRICT4H" / "data"
    ohlcv_path = base / "BTCUSDT_2026_4h.csv"
    funding_path = base / "BTCUSDT_2026_funding.csv"
    if not ohlcv_path.exists():
        ohlcv_path = base / "BTCUSDT_4h.csv"
        funding_path = base / "BTCUSDT_funding.csv"
    ohlcv = read_ohlcv(str(ohlcv_path))
    funding = align_funding_to_ohlcv(ohlcv, read_funding(str(funding_path)))
    data = ohlcv.copy()
    data["funding_rate"] = funding
    costs = CostConfig(taker_bps=4.0, slippage_bps=1.0, funding_multiplier=1.0)
    execution = ExecutionConfig(delay_bars=1, max_exposure_abs=1.0, exposure_threshold=0.15)
    _blind_cache = {"data": data, "bar_hours": 4, "costs": costs, "execution": execution}
    return data, 4, costs, execution


def _run_blind_validate(formula: str) -> dict:
    """Run a single formula backtest on 2026 blind data (cached). Returns chart-ready results."""
    try:
        data, bar_hours, costs, execution = _load_blind_data()
        ledger = run_formula_backtest(data, formula, costs, execution)
        metrics = summarize_ledger(ledger, bar_hours)

        r = ledger["r_net"].fillna(0.0)
        eq = equity_curve(r)
        dd_series = eq / eq.cummax() - 1.0

        # Downsample chart to ~100 points for fast JSON transfer
        step = max(1, len(ledger) // 100)
        idxs = list(range(0, len(ledger), step))
        timestamps = [str(ledger.index[i]) for i in idxs]
        equity_vals = [float(eq.iloc[i]) for i in idxs]
        dd_vals = [float(dd_series.iloc[i]) for i in idxs]

        # Extract trades from exposure changes (vectorized loop over .values for speed)
        exp_arr = ledger["exposure"].values
        close_arr = ledger["close"].values
        ts_arr = ledger.index
        trades = []
        i = 0
        while i < len(exp_arr):
            if exp_arr[i] != 0:
                start = i
                side = "long" if exp_arr[i] > 0 else "short"
                while i < len(exp_arr) and exp_arr[i] != 0:
                    i += 1
                end = i - 1
                pnl = (float(close_arr[end]) / float(close_arr[start]) - 1)
                if side == "short":
                    pnl = -pnl
                trades.append({
                    "entry_time": str(ts_arr[start]),
                    "entry_price": float(close_arr[start]),
                    "exit_time": str(ts_arr[end]),
                    "exit_price": float(close_arr[end]),
                    "side": side,
                    "bars_held": end - start,
                    "pnl": round(pnl * 100, 2),
                })
            else:
                i += 1

        return {
            "formula": formula,
            "error": None,
            "blind": {
                "bars": metrics["bars"],
                "sharpe": round(metrics["sharpe"], 4),
                "cagr": round(metrics["cagr"], 4),
                "max_dd": round(metrics["max_dd"], 4),
                "ic": round(metrics["ic"], 6),
                "rank_ic": round(metrics["rank_ic"], 6),
                "directional_win_rate": round(metrics["directional_win_rate"], 4),
                "turnover": round(metrics["turnover"], 4),
                "trades": int(metrics["trades"]),
                "net_total": round(metrics["net_total"], 4),
            },
            "chart": {
                "timestamps": timestamps,
                "equity": equity_vals,
                "drawdown": dd_vals,
            },
            "trade_list": trades[-40:],
        }
    except Exception as exc:
        return {"formula": formula, "error": str(exc), "blind": None, "chart": None, "trade_list": []}


def build_research_review_payload(output_dir: str | Path) -> dict:
    out = Path(output_dir)
    if not out.is_absolute():
        out = Path(__file__).resolve().parents[1] / out
    reports_root = out.parent

    data_readiness = _data_readiness_payload(
        _latest_artifact(reports_root, "data*", "data_readiness.csv")
    )
    universe = _universe_payload(_latest_artifact(reports_root, "universe*", "universe_summary.csv"))
    portfolio_universe = _portfolio_universe_payload(
        _latest_artifact(reports_root, "portfolio_universe*", "portfolio_universe_summary.csv")
    )
    selector_pipeline = _selector_pipeline_review_payload(
        _latest_artifact(reports_root, "selector_rewrite_pipeline*/review", "selector_pipeline_review.csv")
    )
    selector_evidence = _selector_pipeline_evidence_payload(
        _latest_artifact(reports_root, "selector_pipeline_evidence*", "selector_pipeline_evidence_summary.csv")
    )
    admission = _admission_payload(_latest_artifact(reports_root, "admission*", "admission_decisions.csv"))
    failure = _failure_payload(
        _latest_artifact(reports_root, "failure_memory*", "failure_memory.csv"),
        _latest_artifact(reports_root, "failure_memory*", "failure_clusters.csv"),
    )
    portfolio = _portfolio_wf_payload(
        _latest_artifact(reports_root, "portfolio_walk_forward*", "portfolio_walk_forward_summary.csv")
    )
    pareto = _pareto_payload(_latest_artifact(reports_root, "*", "pareto_archive.json"))
    sections = (
        data_readiness,
        universe,
        portfolio_universe,
        selector_evidence,
        selector_pipeline,
        admission,
        failure,
        portfolio,
        pareto,
    )
    available = any(section.get("available") for section in sections)
    return {
        "available": available,
        "data_readiness": data_readiness,
        "universe_robustness": universe,
        "portfolio_universe": portfolio_universe,
        "selector_pipeline_evidence": selector_evidence,
        "selector_pipeline_review": selector_pipeline,
        "admission": admission,
        "failure_memory": failure,
        "portfolio_walk_forward": portfolio,
        "pareto_archive": pareto,
    }


def _latest_artifact(root: Path, directory_glob: str, filename: str) -> Path | None:
    candidates = [path / filename for path in root.glob(directory_glob) if (path / filename).exists()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _read_optional_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _read_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _data_readiness_payload(path: Path | None) -> dict:
    if path is None:
        return {"available": False}
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        return {"available": False, "source": str(path), "error": str(exc)}
    ready = frame.get("ready", pd.Series(dtype=bool)).fillna(False).astype(bool)
    coverage = [_num(value) for value in frame.get("research_coverage_ratio", pd.Series(dtype=float))]
    missing = [_num(value) for value in frame.get("ohlcv_missing_bars", pd.Series(dtype=float))]
    return {
        "available": True,
        "source": _display_path(path),
        "assets": int(len(frame)),
        "ready": int(ready.sum()),
        "min_research_coverage": min(coverage) if coverage else 0.0,
        "max_missing_bars": int(max(missing)) if missing else 0,
        "rows": [
            {
                "symbol": row.get("symbol") or row.get("expected_symbol", ""),
                "status": row.get("status", ""),
                "research_coverage_ratio": _num(row.get("research_coverage_ratio")),
                "funding_alignment_coverage": _num(row.get("funding_alignment_coverage")),
                "funding_max_staleness_hours": _num(row.get("funding_max_staleness_hours")),
            }
            for row in frame.head(6).to_dict(orient="records")
        ],
    }


def _universe_payload(path: Path | None) -> dict:
    if path is None:
        return {"available": False}
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        return {"available": False, "source": str(path), "error": str(exc)}
    if "robustness_score" in frame.columns:
        frame = frame.sort_values(
            ["robustness_score", "pass_rate", "mean_sharpe", "median_rank_ic"],
            ascending=[False, False, False, False],
        )
    best = frame.iloc[0].to_dict() if not frame.empty else {}
    return {
        "available": True,
        "source": _display_path(path),
        "formulas": int(len(frame)),
        "assets": int(_num(best.get("asset_count"))),
        "best_pass_rate": _num(best.get("pass_rate")),
        "max_pass_rate": _max_num(frame, "pass_rate"),
        "best_robustness_score": _num(best.get("robustness_score")),
        "top": [
            {
                "factor_id": row.get("factor_id", ""),
                "formula": row.get("formula", ""),
                "pass_rate": _num(row.get("pass_rate")),
                "mean_sharpe": _num(row.get("mean_sharpe")),
                "median_rank_ic": _num(row.get("median_rank_ic")),
                "robustness_score": _num(row.get("robustness_score")),
            }
            for row in frame.head(5).to_dict(orient="records")
        ],
    }


def _portfolio_universe_payload(path: Path | None) -> dict:
    if path is None:
        return {"available": False}
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        return {"available": False, "source": str(path), "error": str(exc)}
    if "robustness_score" in frame.columns:
        frame = frame.sort_values(
            ["robustness_score", "pass_rate", "mean_sharpe", "median_rank_ic"],
            ascending=[False, False, False, False],
        )
    best = frame.iloc[0].to_dict() if not frame.empty else {}
    return {
        "available": True,
        "source": _display_path(path),
        "portfolios": int(len(frame)),
        "assets": int(_num(best.get("asset_count"))),
        "best_pass_rate": _num(best.get("pass_rate")),
        "max_pass_rate": _max_num(frame, "pass_rate"),
        "best_robustness_score": _num(best.get("robustness_score")),
        "top": [
            {
                "portfolio_id": row.get("portfolio_id", ""),
                "pass_rate": _num(row.get("pass_rate")),
                "mean_sharpe": _num(row.get("mean_sharpe")),
                "median_rank_ic": _num(row.get("median_rank_ic")),
                "robustness_score": _num(row.get("robustness_score")),
            }
            for row in frame.head(5).to_dict(orient="records")
        ],
    }


def _selector_pipeline_review_payload(path: Path | None) -> dict:
    if path is None:
        return {"available": False}
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        return {"available": False, "source": str(path), "error": str(exc)}
    candidate_frame = _read_optional_csv(path.with_name("selector_pipeline_candidate_review.csv"))
    highlight_frame = _read_optional_csv(path.with_name("selector_pipeline_candidate_highlights.csv"))
    pipeline_manifest = _read_optional_json(path.parents[1] / "selector_rewrite_pipeline_manifest.json")
    rewrite_manifest = pipeline_manifest.get("rewrite", {}) if isinstance(pipeline_manifest, dict) else {}
    verdicts = frame.get("review_verdict", pd.Series(dtype=str)).fillna("")
    candidate_verdicts = candidate_frame.get("candidate_review_verdict", pd.Series(dtype=str)).fillna("")
    highlight_types = highlight_frame.get("highlight_type", pd.Series(dtype=str)).fillna("")
    top = frame.copy()
    if not top.empty:
        for column in ("pass_rate_delta", "mean_sharpe_delta"):
            if column not in top.columns:
                top[column] = 0.0
        if "review_verdict_rank" not in top.columns:
            top["review_verdict_rank"] = verdicts.map(
                {
                    "improved": 4,
                    "mixed": 3,
                    "coverage_only": 2,
                    "not_improved": 1,
                    "needs_evaluation": 0,
                }
            ).fillna(0)
        top = top.sort_values(
            ["review_verdict_rank", "pass_rate_delta", "mean_sharpe_delta"],
            ascending=[False, False, False],
        )
    candidate_top = candidate_frame.copy()
    if not candidate_top.empty:
        for column in ("pass_rate_delta", "mean_sharpe_delta"):
            if column not in candidate_top.columns:
                candidate_top[column] = 0.0
        if "candidate_verdict_rank" not in candidate_top.columns:
            candidate_top["candidate_verdict_rank"] = candidate_verdicts.map(
                {
                    "improved": 4,
                    "mixed": 3,
                    "coverage_only": 2,
                    "not_improved": 1,
                    "needs_evaluation": 0,
                }
            ).fillna(0)
        candidate_top = candidate_top.sort_values(
            ["candidate_verdict_rank", "pass_rate_delta", "mean_sharpe_delta"],
            ascending=[False, False, False],
        )
    highlight_top = highlight_frame.copy()
    if not highlight_top.empty:
        for column in ("highlight_rank", "pass_rate_delta", "mean_sharpe_delta", "candidate_mean_sharpe"):
            if column not in highlight_top.columns:
                highlight_top[column] = 0.0
        highlight_top = highlight_top.sort_values(
            ["highlight_rank", "pass_rate_delta", "mean_sharpe_delta", "candidate_mean_sharpe"],
            ascending=[False, False, False, False],
        )
    return {
        "available": True,
        "source": _display_path(path),
        "parents": int(len(frame)),
        "candidates": int(sum(_num(value) for value in frame.get("candidate_count", pd.Series(dtype=float)))),
        "evaluated_candidates": int(
            sum(_num(value) for value in frame.get("evaluated_candidate_count", pd.Series(dtype=float)))
        ),
        "improved": int((verdicts == "improved").sum()),
        "coverage_only": int((verdicts == "coverage_only").sum()),
        "mixed": int((verdicts == "mixed").sum()),
        "not_improved": int((verdicts == "not_improved").sum()),
        "needs_evaluation": int((verdicts == "needs_evaluation").sum()),
        "candidate_review_available": not candidate_frame.empty,
        "candidate_improved": int((candidate_verdicts == "improved").sum()),
        "candidate_coverage_only": int((candidate_verdicts == "coverage_only").sum()),
        "candidate_mixed": int((candidate_verdicts == "mixed").sum()),
        "candidate_not_improved": int((candidate_verdicts == "not_improved").sum()),
        "candidate_needs_evaluation": int((candidate_verdicts == "needs_evaluation").sum()),
        "candidate_highlights_available": not highlight_frame.empty,
        "candidate_true_improved": int((highlight_types == "true_improved").sum()),
        "candidate_coverage_traps": int((highlight_types == "coverage_only_trap").sum()),
        "candidate_sharpe_improved_no_pass_lift": int(
            (highlight_types == "sharpe_improved_no_pass_lift").sum()
        ),
        "llm_requested": bool(rewrite_manifest.get("use_llm_requested", False)),
        "llm_rewrite_accepted": int(_num(rewrite_manifest.get("llm_rewrite_accepted"))),
        "fallback_rewrite_accepted": int(_num(rewrite_manifest.get("fallback_rewrite_accepted"))),
        "is_llm_policy_evidence": bool(rewrite_manifest.get("is_llm_policy_evidence", False)),
        "top": [
            {
                "parent_factor_id": row.get("parent_factor_id", ""),
                "verdict": row.get("review_verdict", ""),
                "pass_rate_delta": _num(row.get("pass_rate_delta")),
                "mean_sharpe_delta": _num(row.get("mean_sharpe_delta")),
                "best_candidate_factor_id": row.get("best_candidate_factor_id", ""),
                "best_candidate_formula": row.get("best_candidate_formula", ""),
                "best_candidate_generation_source": row.get("best_candidate_generation_source", ""),
                "best_candidate_pass_rate": _num(row.get("best_candidate_pass_rate")),
                "best_candidate_mean_sharpe": _num(row.get("best_candidate_mean_sharpe")),
                "best_candidate_failed_assets": row.get("best_candidate_failed_assets", ""),
                "candidate_verdict_counts": row.get("candidate_verdict_counts", ""),
                "best_candidate_rank_reason": row.get("best_candidate_rank_reason", ""),
            }
            for row in top.head(5).to_dict(orient="records")
        ],
        "candidate_top": [
            {
                "parent_factor_id": row.get("parent_factor_id", ""),
                "factor_id": row.get("factor_id", ""),
                "rewrite_generation_source": row.get("rewrite_generation_source", ""),
                "formula": row.get("formula", ""),
                "verdict": row.get("candidate_review_verdict", ""),
                "pass_rate_delta": _num(row.get("pass_rate_delta")),
                "mean_sharpe_delta": _num(row.get("mean_sharpe_delta")),
                "candidate_pass_rate": _num(row.get("candidate_pass_rate")),
                "candidate_mean_sharpe": _num(row.get("candidate_mean_sharpe")),
                "candidate_failed_assets": row.get("candidate_failed_assets", ""),
                "candidate_rank_reason": row.get("candidate_rank_reason", ""),
            }
            for row in candidate_top.head(5).to_dict(orient="records")
        ],
        "candidate_highlights": [
            {
                "highlight_type": row.get("highlight_type", ""),
                "parent_factor_id": row.get("parent_factor_id", ""),
                "factor_id": row.get("factor_id", ""),
                "rewrite_generation_source": row.get("rewrite_generation_source", ""),
                "formula": row.get("formula", ""),
                "verdict": row.get("candidate_review_verdict", ""),
                "pass_rate_delta": _num(row.get("pass_rate_delta")),
                "mean_sharpe_delta": _num(row.get("mean_sharpe_delta")),
                "candidate_pass_rate": _num(row.get("candidate_pass_rate")),
                "candidate_mean_sharpe": _num(row.get("candidate_mean_sharpe")),
                "candidate_failed_assets": row.get("candidate_failed_assets", ""),
                "candidate_rank_reason": row.get("candidate_rank_reason", ""),
            }
            for row in highlight_top.head(5).to_dict(orient="records")
        ],
    }


def _selector_pipeline_evidence_payload(path: Path | None) -> dict:
    if path is None:
        return {"available": False}
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        return {"available": False, "source": str(path), "error": str(exc)}
    manifest = _read_optional_json(path.with_name("selector_pipeline_evidence_manifest.json"))
    if not frame.empty:
        for column in ("is_llm_true_improvement_evidence", "is_llm_policy_evidence"):
            if column not in frame.columns:
                frame[column] = False
            frame[column] = frame[column].map(_bool)
        for column in ("llm_true_improved_count", "coverage_only_trap_count"):
            if column not in frame.columns:
                frame[column] = 0
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
        frame = frame.sort_values(
            ["is_llm_true_improvement_evidence", "is_llm_policy_evidence", "llm_true_improved_count"],
            ascending=[False, False, False],
        )
    return {
        "available": True,
        "source": _display_path(path),
        "runs": int(manifest.get("run_count", len(frame))),
        "llm_policy_evidence_runs": int(
            manifest.get("llm_policy_evidence_runs", _bool_count(frame, "is_llm_policy_evidence"))
        ),
        "llm_true_improvement_evidence_runs": int(
            manifest.get(
                "llm_true_improvement_evidence_runs",
                _bool_count(frame, "is_llm_true_improvement_evidence"),
            )
        ),
        "coverage_only_trap_runs": int(
            manifest.get("coverage_only_trap_runs", _positive_count(frame, "coverage_only_trap_count"))
        ),
        "top": [
            {
                "run_id": _text(row.get("run_id", "")),
                "is_llm_policy_evidence": _bool(row.get("is_llm_policy_evidence")),
                "is_llm_true_improvement_evidence": _bool(row.get("is_llm_true_improvement_evidence")),
                "llm_true_improved_count": int(_num(row.get("llm_true_improved_count"))),
                "coverage_only_trap_count": int(_num(row.get("coverage_only_trap_count"))),
                "candidate_source_mix": _text(row.get("candidate_source_mix", "")),
                "candidate_highlight_source_mix": _text(row.get("candidate_highlight_source_mix", "")),
                "best_llm_true_improved_factor_id": _text(row.get("best_llm_true_improved_factor_id", "")),
                "best_llm_true_improved_formula": _text(row.get("best_llm_true_improved_formula", "")),
            }
            for row in frame.head(5).to_dict(orient="records")
        ],
    }


def _admission_payload(path: Path | None) -> dict:
    if path is None:
        return {"available": False}
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        return {"available": False, "source": str(path), "error": str(exc)}
    statuses = frame.get("admission_status", pd.Series(dtype=str)).fillna("")
    top = frame.sort_values("admission_score", ascending=False).head(5) if "admission_score" in frame.columns else frame.head(5)
    return {
        "available": True,
        "source": _display_path(path),
        "approved": int((statuses == "approve").sum()),
        "review": int((statuses == "review").sum()),
        "rejected": int((statuses == "reject").sum()),
        "top": [
            {
                "factor_id": row.get("factor_id", ""),
                "status": row.get("admission_status", ""),
                "score": _num(row.get("admission_score")),
                "failed_rules": row.get("failed_rules", ""),
            }
            for row in top.to_dict(orient="records")
        ],
    }


def _failure_payload(memory_path: Path | None, cluster_path: Path | None) -> dict:
    if memory_path is None and cluster_path is None:
        return {"available": False}
    try:
        memory = pd.read_csv(memory_path) if memory_path else pd.DataFrame()
        clusters = pd.read_csv(cluster_path) if cluster_path else pd.DataFrame()
    except Exception as exc:
        return {"available": False, "source": str(memory_path or cluster_path), "error": str(exc)}
    if not clusters.empty and "count" in clusters.columns:
        clusters = clusters.sort_values("count", ascending=False)
    return {
        "available": True,
        "source": _display_path(memory_path or cluster_path),
        "failures": int(len(memory)),
        "cluster_count": int(len(clusters)),
        "clusters": [
            {
                "subtree": row.get("subtree", ""),
                "count": _num(row.get("count")),
                "failed_gates": row.get("failed_gates", ""),
            }
            for row in clusters.head(5).to_dict(orient="records")
        ],
    }


def _portfolio_wf_payload(path: Path | None) -> dict:
    if path is None:
        return {"available": False}
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        return {"available": False, "source": str(path), "error": str(exc)}
    if "survival_rate" in frame.columns:
        frame = frame.sort_values(["survival_rate", "test_sharpe_median"], ascending=[False, False])
    best = frame.iloc[0].to_dict() if not frame.empty else {}
    return {
        "available": True,
        "source": _display_path(path),
        "portfolios": int(len(frame)),
        "best_survival": _num(best.get("survival_rate")),
        "best_windows": _num(best.get("windows")),
        "top": [
            {
                "portfolio_id": row.get("portfolio_id", ""),
                "survival_rate": _num(row.get("survival_rate")),
                "test_sharpe_median": _num(row.get("test_sharpe_median")),
                "test_rank_ic_median": _num(row.get("test_rank_ic_median")),
            }
            for row in frame.head(5).to_dict(orient="records")
        ],
    }


def _pareto_payload(path: Path | None) -> dict:
    if path is None:
        return {"available": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"available": False, "source": str(path), "error": str(exc)}
    front = payload.get("front") or []
    return {
        "available": True,
        "source": _display_path(path),
        "alpha_count": int(_num(payload.get("alpha_count"))),
        "front_count": int(_num(payload.get("front_count"))),
        "objectives": payload.get("objectives") or [],
        "front": [
            {
                "formula": row.get("formula", ""),
                "rank_ic": _num(row.get("rank_ic")),
                "sharpe": _num(row.get("sharpe")),
                "turnover": _num(row.get("turnover")),
            }
            for row in front[:5]
        ],
    }


def _display_path(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.relative_to(Path(__file__).resolve().parents[1]))
    except ValueError:
        return str(path)


def _num(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if pd.notna(number) else 0.0


def _text(value: object) -> str:
    if value is None or not pd.notna(value):
        return ""
    return str(value)


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n", "", "nan", "none"}:
        return False
    return bool(value)


def _bool_count(frame: pd.DataFrame, column: str) -> int:
    if frame.empty or column not in frame.columns:
        return 0
    return sum(1 for value in frame[column].tolist() if _bool(value))


def _positive_count(frame: pd.DataFrame, column: str) -> int:
    if frame.empty or column not in frame.columns:
        return 0
    return sum(1 for value in frame[column].tolist() if _num(value) > 0)


def _max_num(frame: pd.DataFrame, column: str) -> float:
    if column not in frame.columns or frame.empty:
        return 0.0
    return max(_num(value) for value in frame[column])


def run_dashboard(config: str, out: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    import errno
    import socket
    import sys

    session = ResearchSession(config, out)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
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
            elif parsed.path == "/api/research_review":
                self._json(build_research_review_payload(session.output_dir))
            elif parsed.path in {"/api/test_llm", "/api/test_deepseek"}:
                self._json(session.test_llm())
            elif parsed.path == "/api/validate_factor":
                formula = params.get("formula", [None])[0]
                if not formula:
                    self._json({"error": "missing formula"})
                    return
                result = _run_blind_validate(formula)
                self._json(result)
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
