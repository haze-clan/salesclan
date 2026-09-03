"""
Sales XP engine — Night City edition.

Converts a day's sales activity into XP, tracks streaks, levels, rank
titles, and achievement unlocks. Pure stdlib, no dependencies.

State lives in data/xp_state.json. Nothing here talks to the network or
touches anything outside that one file.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "data" / "xp_state.json"

# ---------------------------------------------------------------------------
# XP weights
# ---------------------------------------------------------------------------

STAT_WEIGHTS: dict[str, int] = {
    "calls": 4,
    "emails": 2,
    "follow_ups": 6,
    "meetings_booked": 25,
    "demos": 40,
    "proposals_sent": 30,
    "referrals": 60,
    "deals_closed": 250,
}

STAT_LABELS: dict[str, str] = {
    "calls": "Calls",
    "emails": "Emails",
    "follow_ups": "Follow-ups",
    "meetings_booked": "Meetings Booked",
    "demos": "Demos Run",
    "proposals_sent": "Proposals Sent",
    "referrals": "Referrals",
    "deals_closed": "Deals Closed",
    "revenue": "Revenue ($)",
}

REVENUE_XP_RATE = 1 / 20  # 1 XP per $20 of revenue closed that day
BIG_DEAL_THRESHOLD = 10_000
BIG_DEAL_BONUS = 500
WHALE_THRESHOLD = 50_000
WHALE_BONUS = 1_500

STREAK_CAP_DAYS = 30
STREAK_BONUS_PER_DAY = 0.01  # +1% per streak day, capped at +30%

# ---------------------------------------------------------------------------
# Leveling curve
# ---------------------------------------------------------------------------


def xp_to_next(level: int) -> int:
    """XP required to go from `level` to `level + 1`."""
    return round(100 * (level**1.5) / 10) * 10


def level_from_total_xp(total_xp: int) -> tuple[int, int, int]:
    """Return (level, xp_into_level, xp_needed_for_level)."""
    level = 1
    remaining = total_xp
    while remaining >= xp_to_next(level):
        remaining -= xp_to_next(level)
        level += 1
    return level, remaining, xp_to_next(level)


# ---------------------------------------------------------------------------
# Ranks — Night City career ladder
# ---------------------------------------------------------------------------

RANKS: list[tuple[int, str, str]] = [
    (1, "Street Kid", "Basic Comms Implant — cold outreach no longer makes you flinch."),
    (2, "Edgerunner Recruit", "Kiroshi Optics Mk.1 — you spot buying signals across the room."),
    (4, "Fixer's Runner", "Gorilla Arms — objections don't move you anymore."),
    (7, "Solo-in-Training", "Sandevistan Mk.1 — inbound leads get answered before they cool."),
    (10, "Netrunner", "ICEbreaker — gatekeepers stop being a wall."),
    (13, "Corpo Associate", "Synaptic Accelerator — follow-ups never slip again."),
    (17, "Nomad Trader", "Reflex Tuner — objection handling is pure muscle memory."),
    (21, "Techie", "Cyberdeck Mk.2 — the busywork runs itself."),
    (26, "Edgerunner", "Mantis Blades — you close hard and you close fast."),
    (31, "Silverhand's Protege", "Berserk — a hot streak turns into a revenue rush."),
    (37, "Night City Solo", "Sandevistan Mk.3 — full pipeline, zero drag."),
    (44, "Arasaka Rainmaker", "Legendary Cyberdeck — every account in the territory, mapped."),
    (51, "Militech Closer", "Smart Weapons — every pitch finds its target."),
    (61, "Chrome Legend", "Full-Body Conversion — there's barely a human bottleneck left."),
    (76, "Night City Legend", "Relic-bound — they tell rookies stories about you now."),
]


def rank_for_level(level: int) -> tuple[str, str]:
    title, perk = RANKS[0][1], RANKS[0][2]
    for min_level, t, p in RANKS:
        if level >= min_level:
            title, perk = t, p
        else:
            break
    return title, perk


def next_rank_at(level: int) -> tuple[int, str] | None:
    for min_level, title, _ in RANKS:
        if min_level > level:
            return min_level, title
    return None


# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------


@dataclass
class Achievement:
    id: str
    name: str
    desc: str
    check: "callable"  # (state, day_stats, day_xp) -> bool


def _totals(state: dict) -> dict:
    return state["totals"]


# Cumulative career-revenue milestones — deliberately small early rungs so
# there's something to unlock well before the single-day bonuses hit.
REVENUE_MILESTONES: list[tuple[str, str, int]] = [
    ("first_5k", "First 5K", 5_000),
    ("first_10k", "First 10K", 10_000),
    ("25k_club", "25K Club", 25_000),
    ("six_figures", "Six Figures", 100_000),
]

ACHIEVEMENTS: list[Achievement] = [
    # --- onboarding: small, close, one per early action ---
    Achievement(
        "jacked_in",
        "Jacked In",
        "Log your first day.",
        lambda s, d, xp: s.get("last_log_date") is not None,
    ),
    Achievement(
        "first_contact",
        "First Contact",
        "Book your first meeting.",
        lambda s, d, xp: _totals(s).get("meetings_booked", 0) >= 1,
    ),
    Achievement(
        "first_client",
        "First Client",
        "Close your first deal.",
        lambda s, d, xp: _totals(s).get("deals_closed", 0) >= 1,
    ),
    # --- career revenue ladder ---
    *[
        Achievement(
            mid,
            name,
            f"${threshold:,}+ in total career revenue.",
            lambda s, d, xp, _t=threshold: s.get("totals_revenue", 0) >= _t,
        )
        for mid, name, threshold in REVENUE_MILESTONES
    ],
    # --- volume / single-day feats ---
    Achievement(
        "referral_network",
        "Referral Network",
        "5+ career referrals.",
        lambda s, d, xp: _totals(s).get("referrals", 0) >= 5,
    ),
    Achievement(
        "cold_call_cyborg",
        "Cold Call Cyborg",
        "50+ calls in a single day.",
        lambda s, d, xp: d.get("calls", 0) >= 50,
    ),
    Achievement(
        "big_score",
        "Big Score",
        f"Close ${BIG_DEAL_THRESHOLD:,}+ in a single day.",
        lambda s, d, xp: d.get("revenue", 0) >= BIG_DEAL_THRESHOLD,
    ),
    Achievement(
        "whale_hunter",
        "Whale Hunter",
        f"Close ${WHALE_THRESHOLD:,}+ in a single day.",
        lambda s, d, xp: d.get("revenue", 0) >= WHALE_THRESHOLD,
    ),
    # --- streaks & endgame ---
    Achievement(
        "combo_breaker",
        "Combo Breaker",
        "Hit a 7-day logging streak.",
        lambda s, d, xp: s.get("streak", 0) >= 7,
    ),
    Achievement(
        "chrome_veteran",
        "Chrome Veteran",
        "Hit a 30-day logging streak.",
        lambda s, d, xp: s.get("streak", 0) >= 30,
    ),
    Achievement(
        "legend_of_night_city",
        "Legend of Night City",
        "Reach the top rank.",
        lambda s, d, xp: s.get("level", 1) >= RANKS[-1][0],
    ),
]

# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------

EMPTY_STATE = {
    "total_xp": 0,
    "level": 1,
    "streak": 0,
    "last_log_date": None,
    "totals": {k: 0 for k in STAT_WEIGHTS},
    "totals_revenue": 0,
    "achievements": [],
    "history": [],
}


def load_state() -> dict:
    if not STATE_PATH.exists():
        return json.loads(json.dumps(EMPTY_STATE))
    return json.loads(STATE_PATH.read_text())


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Core: log a day
# ---------------------------------------------------------------------------


def log_day(state: dict, stats: dict, log_date: date | None = None) -> dict:
    """Apply one day's stats to `state` in place. Returns a report dict."""
    log_date = log_date or date.today()
    date_str = log_date.isoformat()

    stats = {k: stats.get(k, 0) for k in list(STAT_WEIGHTS) + ["revenue"]}

    # --- streak ---
    old_streak = state.get("streak", 0)
    last = state.get("last_log_date")
    if last is None:
        streak = 1
    else:
        delta = (log_date - date.fromisoformat(last)).days
        if delta == 0:
            streak = old_streak or 1
        elif delta == 1:
            streak = old_streak + 1
        else:
            streak = 1
    streak_broken = last is not None and (log_date - date.fromisoformat(last)).days > 1

    # --- XP math ---
    base_xp = sum(stats[k] * w for k, w in STAT_WEIGHTS.items())
    revenue_xp = round(stats["revenue"] * REVENUE_XP_RATE)
    bonus_xp = 0
    bonuses_hit = []
    if stats["revenue"] >= WHALE_THRESHOLD:
        bonus_xp += WHALE_BONUS
        bonuses_hit.append(("Whale Contract", WHALE_BONUS))
    elif stats["revenue"] >= BIG_DEAL_THRESHOLD:
        bonus_xp += BIG_DEAL_BONUS
        bonuses_hit.append(("Legendary Contract", BIG_DEAL_BONUS))

    pre_multiplier_xp = base_xp + revenue_xp + bonus_xp
    multiplier = 1 + min(max(streak - 1, 0), STREAK_CAP_DAYS) * STREAK_BONUS_PER_DAY
    day_xp = round(pre_multiplier_xp * multiplier)

    # --- apply ---
    old_level, _, _ = level_from_total_xp(state["total_xp"])
    state["total_xp"] += day_xp
    new_level, xp_into, xp_needed = level_from_total_xp(state["total_xp"])
    state["level"] = new_level
    state["streak"] = streak
    state["last_log_date"] = date_str

    for k in STAT_WEIGHTS:
        state["totals"][k] = state["totals"].get(k, 0) + stats[k]
    state["totals_revenue"] = state.get("totals_revenue", 0) + stats["revenue"]

    levels_gained = list(range(old_level + 1, new_level + 1))

    newly_unlocked = []
    for ach in ACHIEVEMENTS:
        if ach.id in state["achievements"]:
            continue
        if ach.check(state, stats, day_xp):
            state["achievements"].append(ach.id)
            newly_unlocked.append(ach)

    entry = {
        "date": date_str,
        "stats": stats,
        "xp_gained": day_xp,
        "streak": streak,
        "level_after": new_level,
    }
    state["history"].append(entry)
    state["history"] = state["history"][-90:]  # keep it bounded

    old_title, _ = rank_for_level(old_level)
    new_title, new_perk = rank_for_level(new_level)

    return {
        "date": date_str,
        "stats": stats,
        "base_xp": base_xp,
        "revenue_xp": revenue_xp,
        "bonuses_hit": bonuses_hit,
        "streak": streak,
        "streak_broken": streak_broken,
        "multiplier": multiplier,
        "day_xp": day_xp,
        "total_xp": state["total_xp"],
        "old_level": old_level,
        "new_level": new_level,
        "levels_gained": levels_gained,
        "xp_into_level": xp_into,
        "xp_needed_for_level": xp_needed,
        "old_title": old_title,
        "new_title": new_title,
        "new_perk": new_perk,
        "newly_unlocked": newly_unlocked,
    }
