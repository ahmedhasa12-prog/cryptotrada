# CryptoTrada UI/UX Rebuild — Brief for a Dedicated Session

## Who's reading this

A fresh Claude Code session with no memory of the conversation that produced this
document. Read this whole brief before touching anything. This is a standalone
mandate — you don't need to ask permission to begin; the authorization section below
is deliberately broad.

## What this project is

CryptoTrada is a Sudan-based trading intelligence platform: P2P USDT/SDG market making
plus spot XRP/SOL swing trading on Binance. Python/FastAPI backend, SQLAlchemy 2.0 +
SQLite, Vue 3 + Vite + Pinia frontend with Arabic/English i18n and full RTL support.
It runs locally right now (`run.sh`), not on a cloud host — deployment infra was
removed and never replaced.

**Your job is the frontend only.** Do not modify trading logic, the risk supervisor,
or the agent framework. If a view needs data the backend doesn't expose yet, add a
read-only route under `web/routes/` that queries existing tables — never change what
the trading engine decides or does.

## Why this brief exists

The backend just went through a deliberate rebuild (finished 2026-08-23): a fast-cycle
scheduling bug was closed, and XRP swing's auto-trading now runs through a tested,
auditable risk supervisor (`spot/xrp_risk/`) — every proposal to open a trade is
recorded with a full pass/fail breakdown across seven named gates
(`spot/xrp_risk/reasons.py`), whether approved or refused. State that used to live in
a JSON file (`data/xrp_swing_auto.json`) now survives a restart, persisted to the
`xrp_auto_state` table. None of this has a UI surface yet.

Separately, the *frontend* had its own abandoned effort: `UI_REDESIGN_PLAN.md` (dated
2026-08-11) specified a full agent-first redesign in six phases. Phases 1–2 shipped —
design tokens, dark/light theming, the `AppHeader`/`SideNav` shell, the current router
(`/`, `/agents`, `/agents/:type`, `/p2p`, `/intel`, `/journal`, `/settings`, with
`/bot` and `/xrp` redirecting into the new structure — this *is* the live app, not a
parallel one). **Phase 3 — the reusable component library — was never built.** Check
`frontend/src/components/ui/`: only `ActivityFeed.vue` and `ToastContainer.vue` exist.
Every view (`DashboardView`, `AgentDetailView`, `P2PView`, `IntelView`, `JournalView`,
`SettingsView`) was built directly against raw markup instead, which almost certainly
means duplicated card/table/badge/button styling scattered across all six.

Read `UI_REDESIGN_PLAN.md` for its design-token detail and RTL/accessibility
groundwork — that part is good and still current. Do **not** treat its component list,
phase timeline, or page mockups as binding; verify against the actual code before
building anything, and feel free to diverge where the plan and reality disagree.

The older flat components (`AlertFeed.vue`, `Analytics.vue`, `P2PSnapshot.vue`,
`TodayStats.vue`, `StatusCard.vue`, `LogTradeModal.vue`, `SessionsStrip.vue`,
`AgentControlButton.vue`, everything under `components/trading/` and
`components/timing/`) are not dead — they're likely still used *inside* the new views
as content. Trace each one before assuming it's legacy cruft to delete.

## What needs a UI surface that didn't exist when the Aug 11 plan was written

- **The risk decision audit trail.** Every auto-open XRP swing considered — approved
  or vetoed — is now a row in `xrp_risk_decisions`, with the gate name, pass/fail, and
  a human-readable reason for each of the seven checks (`spot/xrp_risk/reasons.py`
  has the full explain text). This is the single best thing to design well: it's the
  concrete proof that the bot isn't a black box. Show what it considered and why it
  said no, not just what it did.
- **Auto-bot state that now survives a restart.** `xrp_auto_state` (enabled,
  cooldown_until, staging progress) used to be a JSON file; it's a real table now.
  Worth a small, honest "this persists" signal somewhere rather than a bigger feature —
  don't over-build this one.
- Nothing else backend-side changed shape. P2P, macro, watchlist, scoring — all as
  `UI_REDESIGN_PLAN.md` described.

## Hard constraints

- **Reuse the existing stack.** Vue 3 + Vite + Pinia + vue-router + vue-i18n. Do not
  introduce React, a different build tool, or a component framework (no Vuetify/
  PrimeVue/etc.) — build the primitive library in-house, matching what
  `UI_REDESIGN_PLAN.md` §4 and §13 scoped (`Button`, `Card`, `MetricCard`, `DataTable`,
  `Tabs`, `Badge`, `Modal`, and friends under `components/ui/`).
- **Keep dark/light theming and full RTL support.** Both are already wired
  (`useTheme.ts`, `[dir="rtl"]` logical properties in `App.vue`, `ar.js`/`en.js`) and
  are non-negotiable — this platform's primary user is Arabic-speaking.
- **Extend `tokens.css`, don't replace it.** The token system in
  `UI_REDESIGN_PLAN.md` §3 is solid; build on it.
- **No backend/trading logic changes.** Read-only API additions only, and only when a
  view genuinely needs data no endpoint currently exposes.
- Test visually in a real browser before calling anything done — start the dev server
  (`cd frontend && npm run dev`, proxied to the FastAPI backend on :8000 per
  `vite.config.js`) and actually look at it, both themes, both languages, at least one
  mobile width.

## Authorization

Full design authority. Don't bring the user minor choices — button corner radius,
which shade of a color, whether a table paginates or infinite-scrolls, spacing scale
decisions. Decide, build it, explain briefly why in plain language if it's a judgment
call worth surfacing. This mirrors how this project is already run: the user does not
want to be asked to choose between technical alternatives — they want the reasoning
and the result.

Do check in before: dropping RTL or theming support, adding a new major dependency,
restructuring the route map in a way that breaks the existing `/bot` and `/xrp`
redirects, or any change that would touch backend trading logic.

## Suggested first steps

1. Read `UI_REDESIGN_PLAN.md` in full for the token/RTL/accessibility groundwork.
2. Trace what's actually live: open each of the six views and find every component
   they import, distinguishing genuinely dead code from content still in active use.
3. Check `git status` — the frontend has substantial uncommitted work already (this is
   normal for this repo; commit checkpoints as you go rather than accumulating a huge
   diff, but only when you've verified things actually work).
4. Look at `spot/xrp_risk/reasons.py` and the `xrp_risk_decisions` /
   `xrp_auto_state` tables in `data/models.py` directly — that's the real shape of the
   new data you're designing for, not a paraphrase.
5. Build the `components/ui/` primitive library first (this is what Phase 3 of the old
   plan never did) — everything else should be built on top of it, not before it.
6. If you want a visual mockup pass before wiring real Vue components, the `design`
   skill (Claude Design canvas) is available in this environment and is a reasonable
   way to explore layout before committing to code.
