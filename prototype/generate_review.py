#!/usr/bin/env python3
"""Generate, validate, or serve the original KeplerOps review prototype."""

from __future__ import annotations

import argparse
import html
import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPO_ROOT / "fixtures" / "keplerops-ai" / "atlas-technique-projection.yaml"
OUTPUT_DIR = REPO_ROOT / "prototype"
OUTPUT_PATH = OUTPUT_DIR / "index.html"


def load_projection(path: Path = SOURCE_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected YAML object")
    return value


def _json_for_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).replace(
        "</", "<\\/"
    )


def render_site(data: dict[str, Any]) -> str:
    framework = data.get("framework", {})
    experience = data.get("experience_contract", {})
    title = f"KeplerOps ATLAS {framework.get('release', '')} review"
    payload = {
        "framework": framework,
        "experience": experience,
        "steps": data.get("steps", []),
        "tactics": data.get("tactic_modules", []),
        "techniques": data.get("technique_catalog", []),
    }
    template = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>$title</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #182026;
      --muted: #59636b;
      --line: #ccd2d6;
      --line-strong: #9da7ad;
      --paper: #f7f8f8;
      --surface: #ffffff;
      --nav: #20272c;
      --blue: #1769aa;
      --green: #1f7a4d;
      --amber: #a25d08;
      --red: #a33a33;
      --focus: #0b6fc2;
      --quick: #1f7a4d;
      --intermediate: #1769aa;
      --advanced: #8a3f75;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body { margin: 0; color: var(--ink); background: var(--paper); }
    button, input, select { font: inherit; letter-spacing: 0; }
    button:focus-visible, input:focus-visible, select:focus-visible {
      outline: 3px solid color-mix(in srgb, var(--focus) 35%, transparent);
      outline-offset: 1px;
    }
    .topbar {
      min-height: 64px; display: flex; align-items: center; gap: 20px;
      padding: 10px 24px; background: var(--nav); color: white;
      border-bottom: 3px solid #44a06d;
    }
    .brand { min-width: 250px; }
    .brand strong { display: block; font-size: 17px; font-weight: 700; }
    .brand span { color: #c9d0d4; font-size: 12px; }
    .top-metrics { display: flex; gap: 22px; margin-left: auto; }
    .top-metric { min-width: 68px; }
    .top-metric b { display: block; font-size: 16px; }
    .top-metric span { color: #c9d0d4; font-size: 11px; text-transform: uppercase; }
    .status {
      padding: 5px 8px; border: 1px solid #d69a47; color: #ffd798;
      font-size: 12px; font-weight: 700; text-transform: uppercase;
    }
    .tabs {
      display: flex; gap: 2px; padding: 0 24px; background: var(--surface);
      border-bottom: 1px solid var(--line);
    }
    .tab {
      border: 0; border-bottom: 3px solid transparent; background: transparent;
      padding: 13px 15px 11px; color: var(--muted); cursor: pointer;
      font-weight: 650;
    }
    .tab[aria-selected="true"] { color: var(--ink); border-color: var(--blue); }
    main { max-width: 1540px; margin: 0 auto; padding: 22px 24px 40px; }
    .view[hidden] { display: none; }
    h1, h2, h3 { letter-spacing: 0; }
    h1 { margin: 0; font-size: 24px; }
    h2 { margin: 0 0 14px; font-size: 17px; }
    h3 { margin: 0; font-size: 14px; }
    .subhead { margin: 5px 0 20px; color: var(--muted); font-size: 13px; }
    .summary-grid {
      display: grid; grid-template-columns: repeat(4, minmax(150px, 1fr));
      border: 1px solid var(--line); background: var(--surface); margin-bottom: 22px;
    }
    .summary-item { padding: 16px; border-right: 1px solid var(--line); }
    .summary-item:last-child { border-right: 0; }
    .summary-item b { display: block; font-size: 25px; margin-bottom: 2px; }
    .summary-item span { color: var(--muted); font-size: 12px; }
    .split { display: grid; grid-template-columns: minmax(480px, 1fr) minmax(420px, .8fr); gap: 24px; }
    .panel { background: var(--surface); border: 1px solid var(--line); padding: 18px; }
    .bars { display: grid; gap: 7px; }
    .bar-row { display: grid; grid-template-columns: minmax(145px, 220px) 1fr 38px; gap: 10px; align-items: center; }
    .bar-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
    .bar-track { height: 10px; background: #e7eaec; border-left: 1px solid var(--line-strong); }
    .bar-fill { height: 100%; background: var(--blue); }
    .bar-count { text-align: right; font-variant-numeric: tabular-nums; font-size: 12px; }
    .progression { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
    .progress-step { min-width: 0; border-left: 5px solid var(--line-strong); padding: 5px 9px; }
    .progress-step[data-tier="quick"] { border-color: var(--quick); }
    .progress-step[data-tier="intermediate"] { border-color: var(--intermediate); }
    .progress-step[data-tier="advanced"] { border-color: var(--advanced); }
    .progress-step b { display: block; font-size: 12px; }
    .progress-step span { display: block; color: var(--muted); font-size: 10px; margin-top: 2px; }
    .integrity { margin: 18px 0 0; display: grid; gap: 8px; }
    .integrity-row { display: grid; grid-template-columns: 150px 1fr; gap: 12px; font-size: 11px; }
    .integrity-row code { overflow-wrap: anywhere; }
    .toolbar {
      display: grid; grid-template-columns: minmax(240px, 1.7fr) repeat(3, minmax(150px, .7fr)) auto;
      gap: 10px; align-items: end; margin-bottom: 14px;
    }
    .field label { display: block; margin-bottom: 5px; color: var(--muted); font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .field input, .field select {
      width: 100%; min-height: 38px; border: 1px solid var(--line-strong);
      border-radius: 2px; padding: 7px 9px; background: var(--surface); color: var(--ink);
    }
    .clear {
      width: 38px; height: 38px; border: 1px solid var(--line-strong);
      border-radius: 2px; background: var(--surface); cursor: pointer; font-weight: 800;
    }
    .result-line { display: flex; justify-content: space-between; color: var(--muted); font-size: 12px; margin-bottom: 8px; }
    .table-wrap { overflow: auto; border: 1px solid var(--line); background: var(--surface); max-height: calc(100vh - 260px); }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th {
      position: sticky; top: 0; z-index: 1; text-align: left; padding: 9px 10px;
      background: #edf0f1; border-bottom: 1px solid var(--line-strong); color: #39434a;
      font-size: 10px; text-transform: uppercase;
    }
    td { padding: 9px 10px; border-bottom: 1px solid #e1e5e7; vertical-align: top; }
    tbody tr:hover { background: #f2f7fa; }
    .tech-id { white-space: nowrap; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-weight: 700; color: var(--blue); }
    .planned { min-width: 360px; line-height: 1.42; }
    .evidence { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px; }
    .tag { display: inline-block; margin: 0 4px 3px 0; padding: 2px 5px; border: 1px solid var(--line); background: #f5f6f6; white-space: nowrap; }
    .tier { font-weight: 750; }
    .tier[data-tier="quick"] { color: var(--quick); }
    .tier[data-tier="intermediate"] { color: var(--intermediate); }
    .tier[data-tier="advanced"] { color: var(--advanced); }
    .module-grid { display: grid; grid-template-columns: repeat(2, minmax(360px, 1fr)); gap: 14px; }
    .module {
      background: var(--surface); border: 1px solid var(--line);
      border-left: 5px solid var(--line-strong); padding: 16px;
    }
    .module[data-tier="quick"] { border-left-color: var(--quick); }
    .module[data-tier="intermediate"] { border-left-color: var(--intermediate); }
    .module[data-tier="advanced"] { border-left-color: var(--advanced); }
    .module-head { display: flex; gap: 12px; justify-content: space-between; align-items: start; }
    .module-number { color: var(--muted); font-size: 11px; text-transform: uppercase; }
    .module-objective { margin: 8px 0 12px; font-size: 13px; line-height: 1.4; }
    .facts { display: grid; grid-template-columns: 130px 1fr; gap: 6px 10px; font-size: 11px; }
    .facts dt { color: var(--muted); }
    .facts dd { margin: 0; overflow-wrap: anywhere; }
    .module-techniques { margin-top: 13px; padding-top: 11px; border-top: 1px solid var(--line); color: var(--muted); font-size: 11px; }
    .empty { padding: 30px; text-align: center; color: var(--muted); }
    @media (max-width: 900px) {
      .topbar { align-items: flex-start; flex-wrap: wrap; padding: 12px 16px; }
      .top-metrics { order: 3; width: 100%; margin: 0; justify-content: space-between; }
      .tabs { padding: 0 10px; }
      main { padding: 16px 12px 30px; }
      .summary-grid { grid-template-columns: repeat(2, 1fr); }
      .summary-item:nth-child(2) { border-right: 0; }
      .summary-item:nth-child(-n+2) { border-bottom: 1px solid var(--line); }
      .split, .module-grid { grid-template-columns: 1fr; }
      .toolbar { grid-template-columns: 1fr 1fr; }
      .field-search { grid-column: 1 / -1; }
      .progression { grid-template-columns: 1fr; }
      .planned { min-width: 280px; }
    }
    @media print {
      .topbar, .tabs, .toolbar { display: none; }
      main { max-width: none; padding: 0; }
      .view[hidden] { display: block; }
      .table-wrap { max-height: none; overflow: visible; }
      th { position: static; }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="brand"><strong>KeplerOps ATLAS review</strong><span id="release-label"></span></div>
    <div class="status">Draft plan</div>
    <div class="top-metrics">
      <div class="top-metric"><b id="top-techniques">0</b><span>Techniques</span></div>
      <div class="top-metric"><b id="top-tactics">0</b><span>Tactics</span></div>
      <div class="top-metric"><b id="top-modules">0</b><span>Modules</span></div>
      <div class="top-metric"><b id="top-quick">0</b><span>Quick starts</span></div>
    </div>
  </header>
  <nav class="tabs" aria-label="Review views">
    <button class="tab" data-view="overview" aria-selected="true">Overview</button>
    <button class="tab" data-view="techniques" aria-selected="false">Techniques</button>
    <button class="tab" data-view="modules" aria-selected="false">Modules</button>
  </nav>
  <main>
    <section class="view" id="view-overview">
      <h1>Coverage overview</h1>
      <p class="subhead">Pinned catalog, planned module assignment, and ACES tactic reconciliation.</p>
      <div class="summary-grid" id="summary-grid"></div>
      <div class="split">
        <section class="panel"><h2>Technique relationships by tactic</h2><div class="bars" id="tactic-bars"></div></section>
        <section class="panel">
          <h2>Challenge progression</h2><div class="progression" id="progression"></div>
          <div class="integrity" id="integrity"></div>
        </section>
      </div>
    </section>
    <section class="view" id="view-techniques" hidden>
      <h1>Technique projection</h1>
      <p class="subhead">Exact ATLAS relationships, KeplerOps assignments, evidence boundaries, and planned in-world variants.</p>
      <div class="toolbar">
        <div class="field field-search"><label for="search">Search</label><input id="search" type="search" placeholder="ID, name, action, evidence"></div>
        <div class="field"><label for="module-filter">Module</label><select id="module-filter"><option value="">All modules</option></select></div>
        <div class="field"><label for="tactic-filter">Tactic</label><select id="tactic-filter"><option value="">All tactics</option></select></div>
        <div class="field"><label for="tier-filter">Level</label><select id="tier-filter"><option value="">All levels</option><option value="quick">Quick</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></div>
        <button class="clear" id="clear-filters" type="button" title="Clear filters" aria-label="Clear filters">x</button>
      </div>
      <div class="result-line"><span id="result-count"></span><span id="assignment-state"></span></div>
      <div class="table-wrap"><table>
        <thead><tr><th>ID</th><th>Technique</th><th>Tactics</th><th>Module</th><th>Evidence</th><th>Planned in-world variant</th></tr></thead>
        <tbody id="technique-body"></tbody>
      </table></div>
    </section>
    <section class="view" id="view-modules" hidden>
      <h1>Challenge modules</h1>
      <p class="subhead">Progression, ACES behavior joins, evidence, outcomes, and technique allocation.</p>
      <div class="module-grid" id="module-grid"></div>
    </section>
  </main>
  <script id="projection-data" type="application/json">$payload</script>
  <script>
    const data = JSON.parse(document.getElementById('projection-data').textContent);
    const steps = [...data.steps].sort((a,b) => Number(a.path_step) - Number(b.path_step));
    const stepById = Object.fromEntries(steps.map(step => [String(step.path_step), step]));
    const tacticById = Object.fromEntries(data.tactics.map(tactic => [tactic.tactic_id, tactic]));
    const techniques = [...data.techniques].sort((a,b) => a.id.localeCompare(b.id, undefined, {numeric:true}));
    const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const tacticNames = ids => ids.map(id => tacticById[id]?.name || id);
    const techniquesForStep = id => techniques.filter(row => String(row.challenge_step) === String(id));

    document.getElementById('release-label').textContent = `MITRE ATLAS ${data.framework.release} / ${data.framework.name}`;
    document.getElementById('top-techniques').textContent = techniques.length;
    document.getElementById('top-tactics').textContent = data.tactics.length;
    document.getElementById('top-modules').textContent = steps.length;
    document.getElementById('top-quick').textContent = steps.filter(step => step.tier === 'quick').length;

    const summary = [
      [techniques.length, 'Pinned ATLAS techniques'],
      [data.tactics.length, 'Governed ATLAS tactics'],
      [steps.length, 'Selectable and progressive modules'],
      [`${data.experience.shortest_flag_minutes} min`, 'Shortest planned outcome']
    ];
    document.getElementById('summary-grid').innerHTML = summary.map(([value,label]) => `<div class="summary-item"><b>${escapeHtml(value)}</b><span>${escapeHtml(label)}</span></div>`).join('');

    const tacticCounts = data.tactics.map(tactic => ({...tactic, count: techniques.filter(row => row.tactics.includes(tactic.tactic_id)).length}));
    const maxTactic = Math.max(...tacticCounts.map(row => row.count));
    document.getElementById('tactic-bars').innerHTML = tacticCounts.map(row => `<div class="bar-row" title="${escapeHtml(row.tactic_id)}"><div class="bar-label">${escapeHtml(row.name)}</div><div class="bar-track"><div class="bar-fill" style="width:${(row.count/maxTactic)*100}%"></div></div><div class="bar-count">${row.count}</div></div>`).join('');

    document.getElementById('progression').innerHTML = steps.map(step => `<div class="progress-step" data-tier="${escapeHtml(step.tier)}"><b>${escapeHtml(step.path_step)}. ${escapeHtml(step.surface)}</b><span>${escapeHtml(step.estimated_minutes)} min / ${techniquesForStep(step.path_step).length} techniques</span></div>`).join('');
    const integrityFields = [['Catalog digest','catalog_digest'],['Relationship digest','relationship_digest'],['Assignment digest','assignment_digest']];
    document.getElementById('integrity').innerHTML = integrityFields.map(([label,key]) => `<div class="integrity-row"><span>${label}</span><code>${escapeHtml(data.experience[key])}</code></div>`).join('');

    const moduleFilter = document.getElementById('module-filter');
    moduleFilter.insertAdjacentHTML('beforeend', steps.map(step => `<option value="${escapeHtml(step.path_step)}">${escapeHtml(step.path_step)}. ${escapeHtml(step.surface)}</option>`).join(''));
    const tacticFilter = document.getElementById('tactic-filter');
    tacticFilter.insertAdjacentHTML('beforeend', data.tactics.map(tactic => `<option value="${escapeHtml(tactic.tactic_id)}">${escapeHtml(tactic.name)}</option>`).join(''));

    function renderTechniques() {
      const query = document.getElementById('search').value.trim().toLowerCase();
      const moduleValue = moduleFilter.value;
      const tacticValue = tacticFilter.value;
      const tierValue = document.getElementById('tier-filter').value;
      const filtered = techniques.filter(row => {
        const step = stepById[String(row.challenge_step)] || {};
        const haystack = [row.id,row.name,row.planned_action,row.evidence,row.surface,...tacticNames(row.tactics)].join(' ').toLowerCase();
        return (!query || haystack.includes(query)) &&
          (!moduleValue || String(row.challenge_step) === moduleValue) &&
          (!tacticValue || row.tactics.includes(tacticValue)) &&
          (!tierValue || step.tier === tierValue);
      });
      document.getElementById('result-count').textContent = `${filtered.length} of ${techniques.length} techniques`;
      document.getElementById('assignment-state').textContent = `${steps.length} modules / ${data.tactics.length} tactics`;
      const body = document.getElementById('technique-body');
      if (!filtered.length) { body.innerHTML = '<tr><td class="empty" colspan="6">No matching techniques</td></tr>'; return; }
      body.innerHTML = filtered.map(row => {
        const step = stepById[String(row.challenge_step)] || {};
        const tags = tacticNames(row.tactics).map(name => `<span class="tag">${escapeHtml(name)}</span>`).join('');
        return `<tr><td class="tech-id">${escapeHtml(row.id)}</td><td><strong>${escapeHtml(row.name)}</strong></td><td>${tags}</td><td><span class="tier" data-tier="${escapeHtml(step.tier)}">${escapeHtml(row.challenge_step)}. ${escapeHtml(step.surface)}</span></td><td class="evidence">${escapeHtml(row.evidence)}</td><td class="planned">${escapeHtml(row.planned_action)}</td></tr>`;
      }).join('');
    }
    ['search','module-filter','tactic-filter','tier-filter'].forEach(id => document.getElementById(id).addEventListener('input', renderTechniques));
    document.getElementById('clear-filters').addEventListener('click', () => {
      ['search','module-filter','tactic-filter','tier-filter'].forEach(id => document.getElementById(id).value = '');
      renderTechniques();
    });
    renderTechniques();

    document.getElementById('module-grid').innerHTML = steps.map(step => {
      const assigned = techniquesForStep(step.path_step);
      const tactics = data.tactics.filter(tactic => tactic.challenge_steps.includes(String(step.path_step))).map(tactic => tactic.name);
      return `<article class="module" data-tier="${escapeHtml(step.tier)}"><div class="module-head"><div><div class="module-number">Module ${escapeHtml(step.path_step)}</div><h3>${escapeHtml(step.surface)}</h3></div><span class="tier" data-tier="${escapeHtml(step.tier)}">${escapeHtml(step.tier)}</span></div><p class="module-objective">${escapeHtml(step.objective)}</p><dl class="facts"><dt>ACES behavior</dt><dd><code>${escapeHtml(step.aces_behavior_specification)}</code></dd><dt>Target</dt><dd>${escapeHtml(step.estimated_minutes)} minutes</dd><dt>Outcome</dt><dd><code>${escapeHtml(step.flag_outcome)}</code></dd><dt>Evidence</dt><dd>${step.evidence.map(item => `<code>${escapeHtml(item)}</code>`).join(', ')}</dd><dt>ATLAS tactics</dt><dd>${tactics.map(name => `<span class="tag">${escapeHtml(name)}</span>`).join('')}</dd></dl><div class="module-techniques">${assigned.length} technique-specific variants</div></article>`;
    }).join('');

    const viewNames = new Set(['overview', 'techniques', 'modules']);
    function selectView(name) {
      const selected = viewNames.has(name) ? name : 'overview';
      document.querySelectorAll('.tab').forEach(tab => tab.setAttribute('aria-selected', String(tab.dataset.view === selected)));
      document.querySelectorAll('.view').forEach(view => view.hidden = view.id !== `view-${selected}`);
    }
    document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => {
      history.replaceState(null, '', `#${button.dataset.view}`);
      selectView(button.dataset.view);
    }));
    window.addEventListener('hashchange', () => selectView(location.hash.slice(1)));
    selectView(location.hash.slice(1));
  </script>
</body>
</html>
'''
    return template.replace("$title", html.escape(title)).replace(
        "$payload", _json_for_script(payload)
    )


def generate(source: Path = SOURCE_PATH, output: Path = OUTPUT_PATH) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_site(load_projection(source)), encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def validate(source: Path = SOURCE_PATH, output: Path = OUTPUT_PATH) -> list[str]:
    try:
        expected = render_site(load_projection(source))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"{_display_path(source)}: {exc}"]
    try:
        actual = output.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{_display_path(output)}: cannot read generated site: {exc}"]
    if actual != expected:
        return [
            f"{_display_path(output)}: generated review site is stale; "
            "run `python3 prototype/generate_review.py generate`"
        ]
    return []


def serve(bind: str, port: int) -> None:
    generate()
    handler = partial(SimpleHTTPRequestHandler, directory=str(OUTPUT_DIR))
    server = ThreadingHTTPServer((bind, port), handler)
    print(f"Serving ACES Scenario Workbench prototype on http://{bind}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("generate")
    subparsers.add_parser("validate")
    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--bind", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8008)
    args = parser.parse_args(argv)
    if args.command == "generate":
        generate()
        print(f"[ok] generated {OUTPUT_PATH.relative_to(REPO_ROOT)}")
        return 0
    if args.command == "validate":
        failures = validate()
        if failures:
            for failure in failures:
                print(f"ERROR: {failure}", file=sys.stderr)
            return 1
        print(f"[ok] {OUTPUT_PATH.relative_to(REPO_ROOT)}")
        return 0
    serve(args.bind, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
