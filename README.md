# Chrome Ledger

A Cyberpunk 2077-flavored XP system for daily sales grinding. Report your
numbers, watch the XP land, level up through Night City's career ladder,
and unlock "cyberware" perks and achievements along the way.

**Live dashboard:** https://claude.ai/code/artifact/b51f595a-c293-4984-bba7-f45778f5f40b

## How it works

Every day (or whenever you feel like it), tell Claude your stats for the
day — calls, meetings booked, demos, proposals sent, deals closed, revenue,
referrals, follow-ups. Claude runs the numbers through `scripts/xp_engine.py`,
updates `data/xp_state.json`, regenerates the dashboard, and republishes it.
You get a report right in chat (XP gained, level-ups, achievements) plus a
persistent link you can check anytime.

You can also run it yourself from the terminal:

```bash
python3 scripts/log_day.py --calls 20 --meetings-booked 3 --demos 1 \
    --deals-closed 2 --revenue 4500

python3 scripts/render_dashboard.py   # regenerate dashboard/index.html
```

Run `log_day.py` with no flags to see current status without logging
anything.

## XP formula

| Action | XP |
|---|---|
| Call | 4 |
| Email | 2 |
| Follow-up | 6 |
| Meeting booked | 25 |
| Demo | 40 |
| Proposal sent | 30 |
| Referral | 60 |
| Deal closed | 250 |
| Revenue | 1 XP per $20 |

Bonuses:
- **Legendary Contract** — close $10k+ in a single day: +500 XP
- **Whale Contract** — close $50k+ in a single day: +1,500 XP

**Streaks:** logging stats on consecutive days builds a streak. Each streak
day adds +1% to that day's total XP, capped at +30% at a 30-day streak
("combat stims maxed"). Miss a day and the streak resets to 1.

**Base salary:** a $35k/yr base ($95.89/day) accrues into career revenue
every time a day is logged, based on calendar days since the last log (so
it doesn't double-count a same-day relog and doesn't skip days that go
unlogged). It only affects the cumulative Career Revenue figure and the
revenue-milestone achievements below — it earns no XP and doesn't count
toward the single-day $10k/$50k bonuses, which stay tied to actual deals
closed. The dashboard breaks out how much of Career Revenue is base salary
vs. sales.

**Leveling curve:** XP to go from level `n` to `n+1` is
`round(100 * n^1.5 / 10) * 10` — early levels come fast, later ones take a
real grind, same shape as most RPG curves.

## Rank ladder

| Level | Rank | Cyberware / Perk |
|---|---|---|
| 1 | Street Kid | Basic Comms Implant |
| 2 | Edgerunner Recruit | Kiroshi Optics Mk.1 |
| 4 | Fixer's Runner | Gorilla Arms |
| 7 | Solo-in-Training | Sandevistan Mk.1 |
| 10 | Netrunner | ICEbreaker |
| 13 | Corpo Associate | Synaptic Accelerator |
| 17 | Nomad Trader | Reflex Tuner |
| 21 | Techie | Cyberdeck Mk.2 |
| 26 | Edgerunner | Mantis Blades |
| 31 | Silverhand's Protege | Berserk |
| 37 | Night City Solo | Sandevistan Mk.3 |
| 44 | Arasaka Rainmaker | Legendary Cyberdeck |
| 51 | Militech Closer | Smart Weapons |
| 61 | Chrome Legend | Full-Body Conversion |
| 76 | Night City Legend | Relic-bound |

Full text (titles + perk flavor) lives in `RANKS` in `scripts/xp_engine.py`.

## Achievements

**Onboarding** — Jacked In (log your first day), First Contact (first
meeting booked), First Client (first deal closed).

**Career revenue ladder** (cumulative, not single-day) — First 5K, First
10K, 25K Club, Six Figures.

**Volume / single-day feats** — Referral Network (5+ career referrals),
Cold Call Cyborg (50+ calls/day), Big Score ($10k+ in a single day), Whale
Hunter ($50k+ in a single day).

**Streaks & endgame** — Combo Breaker (7-day streak), Chrome Veteran
(30-day streak), Legend of Night City (max rank).

14 total. See `ACHIEVEMENTS` in `scripts/xp_engine.py`.

## Files

- `scripts/xp_engine.py` — XP math, leveling curve, ranks, achievements.
- `scripts/log_day.py` — CLI to log a day and print a report.
- `scripts/render_dashboard.py` — regenerates `dashboard/index.html` from
  `data/xp_state.json`.
- `data/xp_state.json` — the save file. Total XP, level, streak, career
  totals, unlocked achievements, and a rolling 90-entry history.

## Ideas for expansion

- **Clan leaderboard** — since this repo's called `salesclan`: track
  multiple reps in the same state file and rank them against each other,
  or split into a weekly "gig board" with a shared bounty.
- **Weekly gigs** — a rotating side-quest ("close 3 deals this week",
  "50 cold calls by Friday") with its own bonus XP on completion, on top
  of the daily grind.
- **Street Cred vs XP** — a second track (like the game's actual system)
  that goes up specifically from *quality* actions (deals, referrals)
  rather than volume, and gates cosmetic-only unlocks separately from
  level.
- **Streak grace day** — one "reroll" a week so a single missed day
  doesn't nuke a long streak.
- **Districts** — reskin the level ladder as unlocking Night City
  districts (Watson → Westbrook → City Center → Arasaka Tower) instead of
  a flat number, with a small map that fills in.
- **Boss fights** — a big prospect/account framed as a boss battle with
  its own HP bar (e.g., total deal value) that drains as you log
  activity against it.
- **Self-serve logging** — give the dashboard a form and its own database
  so you can log a day directly on the page instead of going through
  chat, with Claude just reading/reporting on it.
