#!/usr/bin/env python3
"""
Render dashboard/index.html from the current data/xp_state.json.

Run this after logging a day (log_day.py does NOT call it automatically,
so the flow is: log_day.py -> render_dashboard.py -> publish the artifact).
"""
from __future__ import annotations

import json
from pathlib import Path
from string import Template

import xp_engine as xp

OUT_PATH = xp.REPO_ROOT / "dashboard" / "index.html"
MANIFEST_PATH = xp.REPO_ROOT / "dashboard" / "manifest.webmanifest"
ICON_B64_PATH = xp.REPO_ROOT / "dashboard" / "icons" / "apple-touch-icon-180.b64.txt"

STAT_ORDER = [
    "calls",
    "emails",
    "follow_ups",
    "meetings_booked",
    "demos",
    "proposals_sent",
    "referrals",
    "deals_closed",
]

PAGE_TEMPLATE = Template(r"""<title>Chrome Ledger</title>
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Chrome Ledger">
<meta name="theme-color" content="#0d0d10">
<link rel="apple-touch-icon" href="data:image/png;base64,$icon_b64">
<link rel="manifest" href="manifest.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Share+Tech+Mono&family=Barlow:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --void: #0d0d10;
    --panel: #17171b;
    --panel-edge: #2a2a30;
    --signal: #fcee0a;
    --signal-dim: #7a730a;
    --ice: #00e5ff;
    --redline: #ff2c54;
    --text-hi: #f0efe9;
    --text-dim: #87878f;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--void);
    color: var(--text-hi);
    font-family: "Barlow", system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .scanlines {
    position: fixed; inset: 0; pointer-events: none; z-index: 5;
    background: repeating-linear-gradient(
      to bottom, rgba(255,255,255,0.025) 0px, rgba(255,255,255,0.025) 1px,
      transparent 1px, transparent 3px
    );
    mix-blend-mode: overlay;
  }
  .page {
    max-width: 880px;
    margin: 0 auto;
    padding: 28px 20px 60px;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }
  .mono { font-family: "Share Tech Mono", ui-monospace, monospace; font-variant-numeric: tabular-nums; }
  h1, h2, .display { font-family: "Rajdhani", system-ui, sans-serif; text-wrap: balance; }
  .panel-cut {
    background: var(--panel);
    border: 1px solid var(--panel-edge);
    clip-path: polygon(18px 0, 100% 0, 100% calc(100% - 18px), calc(100% - 18px) 100%, 0 100%, 0 18px);
    padding: 20px 24px;
    position: relative;
  }
  .panel-label {
    display: block;
    font-family: "Share Tech Mono", monospace;
    font-size: 11px;
    letter-spacing: 0.14em;
    color: var(--ice);
    text-transform: uppercase;
    margin-bottom: 12px;
  }
  /* header */
  .hud-header { border-color: var(--signal-dim); }
  .eyebrow {
    font-family: "Share Tech Mono", monospace;
    font-size: 11px;
    letter-spacing: 0.18em;
    color: var(--text-dim);
    margin-bottom: 6px;
  }
  .header-row { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  h1 {
    margin: 0;
    font-size: clamp(28px, 5vw, 40px);
    font-weight: 700;
    color: var(--signal);
    letter-spacing: 0.01em;
    text-shadow: 0 0 18px rgba(252,238,10,0.25);
  }
  .level-badge {
    font-family: "Share Tech Mono", monospace;
    font-size: 15px;
    color: var(--void);
    background: var(--signal);
    padding: 4px 12px;
    letter-spacing: 0.08em;
    white-space: nowrap;
  }
  .level-badge span { font-size: 20px; font-weight: 700; margin-left: 4px; }
  .callsign { margin-top: 10px; color: var(--text-dim); font-size: 14px; }
  /* hero */
  .hero-top, .hero-bottom { display: flex; justify-content: space-between; align-items: baseline; font-size: 13px; }
  .hero-label { color: var(--text-dim); letter-spacing: 0.1em; font-size: 11px; }
  .hero-xp { color: var(--text-hi); font-size: 15px; }
  .xp-bar {
    margin: 10px 0 12px;
    height: 14px;
    background: #000;
    border: 1px solid var(--panel-edge);
    position: relative;
    overflow: hidden;
  }
  .xp-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--signal-dim), var(--signal));
    box-shadow: 0 0 12px rgba(252,238,10,0.55);
  }
  .hero-bottom { color: var(--text-dim); margin-top: 4px; }
  .hero-bottom .mono { color: var(--ice); }
  .perk {
    margin: 14px 0 0;
    padding-top: 12px;
    border-top: 1px dashed var(--panel-edge);
    color: var(--text-hi);
    font-size: 14.5px;
    line-height: 1.5;
  }
  .perk::before { content: "PERK :: "; color: var(--signal); font-family: "Share Tech Mono", monospace; font-size: 12px; }
  /* mid grid */
  .mid-grid { display: grid; grid-template-columns: 220px 1fr; gap: 18px; }
  @media (max-width: 620px) { .mid-grid { grid-template-columns: 1fr; } }
  .streak-panel { display: flex; flex-direction: column; }
  .streak-value { font-size: 44px; font-weight: 700; color: var(--signal); line-height: 1; }
  .streak-value small { font-size: 18px; color: var(--text-dim); margin-left: 4px; }
  .streak-note { margin-top: 10px; color: var(--text-dim); font-size: 13px; line-height: 1.4; }
  .stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  @media (max-width: 480px) { .stat-grid { grid-template-columns: repeat(2, 1fr); } }
  .stat-cell { display: flex; flex-direction: column; gap: 2px; }
  .stat-cell .v { font-family: "Share Tech Mono", monospace; font-size: 20px; color: var(--text-hi); }
  .stat-cell .k { font-size: 11px; letter-spacing: 0.06em; color: var(--text-dim); text-transform: uppercase; }
  .stat-cell.revenue .v { color: var(--signal); }
  /* achievements */
  .ach-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
  .ach-chip {
    border: 1px solid var(--panel-edge);
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .ach-chip.unlocked { border-color: var(--signal-dim); background: rgba(252,238,10,0.05); }
  .ach-chip .name { font-family: "Rajdhani", sans-serif; font-weight: 600; font-size: 15px; }
  .ach-chip.unlocked .name { color: var(--signal); }
  .ach-chip.locked .name { color: var(--text-dim); }
  .ach-chip .desc { font-size: 12px; color: var(--text-dim); line-height: 1.35; }
  .ach-chip.locked { opacity: 0.65; }
  .ach-chip .status { font-family: "Share Tech Mono", monospace; font-size: 10px; letter-spacing: 0.1em; }
  .ach-chip.unlocked .status { color: var(--ice); }
  .ach-chip.locked .status { color: var(--redline); }
  /* transmissions */
  .log-list { display: flex; flex-direction: column; gap: 8px; font-family: "Share Tech Mono", monospace; font-size: 12.5px; }
  .log-row { display: flex; justify-content: space-between; gap: 12px; color: var(--text-dim); border-bottom: 1px solid var(--panel-edge); padding-bottom: 6px; }
  .log-row .d { color: var(--text-hi); }
  .log-row .x { color: var(--signal); }
  .log-empty { color: var(--text-dim); font-family: "Share Tech Mono", monospace; font-size: 13px; }
  footer { color: var(--text-dim); font-size: 12.5px; text-align: center; line-height: 1.6; padding: 6px 8px 0; }
  footer .signal { color: var(--ice); }
</style>

<div class="scanlines"></div>
<div class="page">
  <header class="hud-header panel-cut">
    <div class="eyebrow">AGENT STATUS // NIGHT CITY NETWATCH</div>
    <div class="header-row">
      <h1>$rank_title</h1>
      <div class="level-badge">LVL<span>$level</span></div>
    </div>
    <div class="callsign">$callsign_line</div>
  </header>

  <section class="hero panel-cut">
    <div class="hero-top">
      <span class="hero-label">EXPERIENCE</span>
      <span class="hero-xp mono">$xp_into / $xp_needed XP</span>
    </div>
    <div class="xp-bar"><div class="xp-fill" style="width:${pct}%"></div></div>
    <div class="hero-bottom">
      <span class="mono">TOTAL $total_xp XP</span>
      <span class="mono">NEXT :: $next_rank_line</span>
    </div>
    <p class="perk">$perk_text</p>
  </section>

  <div class="mid-grid">
    <section class="panel-cut streak-panel">
      <span class="panel-label">Streak</span>
      <div class="streak-value mono">$streak<small>day$streak_plural</small></div>
      <div class="streak-note">$streak_note</div>
    </section>
    <section class="panel-cut">
      <span class="panel-label">Career Log</span>
      <div class="stat-grid">
        $stat_cells
      </div>
    </section>
  </div>

  <section class="panel-cut">
    <span class="panel-label">Cyberware // Achievements</span>
    <div class="ach-grid">
      $ach_chips
    </div>
  </section>

  <section class="panel-cut">
    <span class="panel-label">Transmission Log</span>
    <div class="log-list">
      $log_rows
    </div>
  </section>

  <footer>
    Report today's numbers to Claude in chat to log a new transmission.<br>
    <span class="signal">SIGNAL LAST SYNCED :: $last_sync</span>
  </footer>
</div>
""")


def render(state: dict) -> str:
    level, xp_into, xp_needed = xp.level_from_total_xp(state["total_xp"])
    title, perk = xp.rank_for_level(level)
    pct = round((xp_into / xp_needed) * 100, 1) if xp_needed else 100

    nxt = xp.next_rank_at(level)
    next_rank_line = f"{nxt[1]} @ Lvl {nxt[0]}" if nxt else "TOP RANK REACHED"

    streak = state.get("streak", 0)
    multiplier = 1 + min(max(streak - 1, 0), xp.STREAK_CAP_DAYS) * xp.STREAK_BONUS_PER_DAY
    if streak == 0:
        streak_note = "No active streak. Log today's numbers to start one."
    elif streak >= xp.STREAK_CAP_DAYS:
        streak_note = "Combat stims maxed: +30% XP on every log."
    else:
        streak_note = f"+{round((multiplier - 1) * 100)}% XP multiplier active. Keep the streak alive."

    totals = state.get("totals", {})
    stat_cells = []
    for key in STAT_ORDER:
        stat_cells.append(
            f'<div class="stat-cell"><span class="v mono">{totals.get(key, 0)}</span>'
            f'<span class="k">{xp.STAT_LABELS[key]}</span></div>'
        )
    stat_cells.append(
        f'<div class="stat-cell revenue"><span class="v mono">${state.get("totals_revenue", 0):,.0f}</span>'
        f'<span class="k">Career Revenue</span></div>'
    )

    unlocked = set(state.get("achievements", []))
    ach_chips = []
    for ach in xp.ACHIEVEMENTS:
        is_unlocked = ach.id in unlocked
        cls = "unlocked" if is_unlocked else "locked"
        status = "UNLOCKED" if is_unlocked else "LOCKED"
        ach_chips.append(
            f'<div class="ach-chip {cls}"><span class="name">{ach.name}</span>'
            f'<span class="desc">{ach.desc}</span><span class="status">{status}</span></div>'
        )

    history = list(reversed(state.get("history", [])))[:8]
    if history:
        log_rows = []
        for h in history:
            log_rows.append(
                f'<div class="log-row"><span class="d">{h["date"]}</span>'
                f'<span>Lvl {h["level_after"]} · streak {h["streak"]}d</span>'
                f'<span class="x">+{h["xp_gained"]} XP</span></div>'
            )
        log_rows_html = "\n      ".join(log_rows)
    else:
        log_rows_html = '<div class="log-empty">SIGNAL: NONE — no transmissions logged yet. New game, choppa. Tell Claude your first day\'s numbers to boot the terminal.</div>'

    last_sync = state.get("last_log_date") or "NEVER"
    icon_b64 = ICON_B64_PATH.read_text().strip()

    return PAGE_TEMPLATE.substitute(
        icon_b64=icon_b64,
        rank_title=title,
        level=level,
        callsign_line=f"Rank {level} of {xp.RANKS[-1][0]}+ &middot; {len(unlocked)}/{len(xp.ACHIEVEMENTS)} cyberware unlocked",
        xp_into=xp_into,
        xp_needed=xp_needed,
        pct=pct,
        total_xp=state["total_xp"],
        next_rank_line=next_rank_line,
        perk_text=perk,
        streak=streak,
        streak_plural="" if streak == 1 else "s",
        streak_note=streak_note,
        stat_cells="\n        ".join(stat_cells),
        ach_chips="\n      ".join(ach_chips),
        log_rows=log_rows_html,
        last_sync=last_sync,
    )


def render_manifest() -> str:
    icon_b64 = ICON_B64_PATH.read_text().strip()
    manifest = {
        "name": "Chrome Ledger",
        "short_name": "Chrome Ledger",
        "start_url": ".",
        "scope": ".",
        "display": "standalone",
        "background_color": "#0d0d10",
        "theme_color": "#0d0d10",
        "icons": [
            {
                "src": f"data:image/png;base64,{icon_b64}",
                "sizes": "180x180",
                "type": "image/png",
            }
        ],
    }
    return json.dumps(manifest, indent=2)


def main() -> None:
    state = xp.load_state()
    html = render(state)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html)
    print(f"Wrote {OUT_PATH}")

    MANIFEST_PATH.write_text(render_manifest())
    print(f"Wrote {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
