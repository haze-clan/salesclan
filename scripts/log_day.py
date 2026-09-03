#!/usr/bin/env python3
"""
Log a day's sales stats and print a Night City-flavored report.

Usage:
    python3 scripts/log_day.py --calls 20 --meetings-booked 3 --demos 1 \\
        --deals-closed 2 --revenue 4500

Run with no arguments to see current status without logging anything new.
"""
from __future__ import annotations

import argparse
from datetime import date

import xp_engine as xp


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--calls", type=int, default=0)
    p.add_argument("--emails", type=int, default=0)
    p.add_argument("--follow-ups", type=int, default=0, dest="follow_ups")
    p.add_argument("--meetings-booked", type=int, default=0, dest="meetings_booked")
    p.add_argument("--demos", type=int, default=0)
    p.add_argument("--proposals-sent", type=int, default=0, dest="proposals_sent")
    p.add_argument("--referrals", type=int, default=0)
    p.add_argument("--deals-closed", type=int, default=0, dest="deals_closed")
    p.add_argument("--revenue", type=float, default=0)
    p.add_argument("--date", type=str, default=None, help="YYYY-MM-DD, defaults to today")
    p.add_argument("--status-only", action="store_true", help="print status, log nothing")
    return p


def bar(pct: float, width: int = 30) -> str:
    filled = int(width * pct)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {pct * 100:5.1f}%"


def print_status(state: dict) -> None:
    level, xp_into, xp_needed = xp.level_from_total_xp(state["total_xp"])
    title, perk = xp.rank_for_level(level)
    print(f"\n== NIGHT CITY STATUS :: {title} (Lvl {level}) ==")
    print(f"XP {xp_into}/{xp_needed}  " + bar(xp_into / xp_needed if xp_needed else 1))
    print(f"Total XP: {state['total_xp']}   Streak: {state['streak']}d   Career revenue: ${state['totals_revenue']:,.0f}")
    print(f"Perk: {perk}\n")


def main() -> None:
    args = build_parser().parse_args()
    state = xp.load_state()

    if args.status_only or not any(
        [args.calls, args.emails, args.follow_ups, args.meetings_booked, args.demos, args.proposals_sent, args.referrals, args.deals_closed, args.revenue]
    ):
        print_status(state)
        return

    log_date = date.fromisoformat(args.date) if args.date else date.today()
    stats = {
        "calls": args.calls,
        "emails": args.emails,
        "follow_ups": args.follow_ups,
        "meetings_booked": args.meetings_booked,
        "demos": args.demos,
        "proposals_sent": args.proposals_sent,
        "referrals": args.referrals,
        "deals_closed": args.deals_closed,
        "revenue": args.revenue,
    }
    report = xp.log_day(state, stats, log_date)
    xp.save_state(state)

    print(f"\n>> TRANSMISSION LOGGED :: {report['date']}")
    for k, v in report["stats"].items():
        if v:
            label = xp.STAT_LABELS.get(k, k)
            print(f"   {label:<18} {v}")
    print(f"   Base XP: {report['base_xp']}  Revenue XP: {report['revenue_xp']}", end="")
    if report["bonuses_hit"]:
        for name, amt in report["bonuses_hit"]:
            print(f"  +{amt} [{name}]", end="")
    print()
    print(f"   Streak x{report['multiplier']:.2f} ({report['streak']}d)" + ("  [STREAK BROKEN, RESET]" if report["streak_broken"] else ""))
    print(f"   >>> +{report['day_xp']} XP <<<")

    if report["levels_gained"]:
        print(f"\n*** LEVEL UP: {report['old_level']} -> {report['new_level']} ***")
        print(f"    New rank: {report['new_title']}")
        print(f"    {report['new_perk']}")

    if report["newly_unlocked"]:
        print("\n*** ACHIEVEMENT UNLOCKED ***")
        for ach in report["newly_unlocked"]:
            print(f"    [{ach.name}] {ach.desc}")

    print_status(state)


if __name__ == "__main__":
    main()
