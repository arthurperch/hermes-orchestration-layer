# Controlplane Dashboard — Product Spec

The shared cockpit on **syndrax.app**: where you and Danish log in, talk to the
orchestrator, watch it execute live, confirm/modify plans before they run, manage
profiles + repos, and edit live templates. Dark, glassy, modern, sound-aware.

> This is the spec to **read and react to** — not built yet. It's the Stage 6
> deliverable, expanded. Design tokens + sound map live in `DESIGN_SYSTEM.md`; the
> look is previewed in `dashboard-preview.html`.

---

## What it is in one line

A self-hosted, two-person Claude/GPT-style workspace wrapped around the Hermes
orchestration layer — chat in, watch the tiers route, approve the plan, ship to repo.

---

## Page map

| Page | Purpose |
|------|---------|
| **Login** | Secure gate. Cloudflare Access (same Zero-Trust policy as Syndrax Sync) — only your two identities. |
| **Home / Cockpit** | Split-view: glassy chat (left) + live orchestration feed and the **Plan Console** (right). The default screen. |
| **Plan Console** | The orchestrator proposes a plan; you see it visualized (tier flow, color-animated) and **confirm / modify / run** before anything executes. |
| **Profiles** | Create multiple custom profiles from the default template, customize, version, and push updates. Each has its own memory. |
| **Connections / Repos** | Card grid of connected repos + platforms (GitHub, Vercel, Railway). Add/remove, push, deploy — visually. |
| **Live Canvas** | Host HTML/image templates, live-edit, and **click any element to send its DOM reference to the AI** as context. |
| **Sessions** | Manage multiple parallel chat sessions; each tied to a profile + its memory. |
| **Benchmark** | Live table of runs: complexity predicted vs actual, cost, quality, escalations (reads the benchmark log). |
| **Architecture** | Renders `orchestration-flowchart.md` Mermaid diagrams + the gates, for reference. |
| **Settings** | Sound on/off + volume, theme accent, model/collab defaults, provider key health. |

---

## Core features

### 1. Glassy chat (Home)
- Transparent glass panel, **bold white** text for normal messages.
- **Multi-font / multi-color / collapsible code view:** code blocks are
  syntax-highlighted, language-labeled, collapsible, copy-on-click.
- Streaming responses; per-message cost + model badge (which tier/model answered).
- A compact **plan strip** that can expand into the full Plan Console.

### 2. Plan Console — confirm before run
- The orchestrator emits a plan; the UI shows it **visually**: the tier path
  (Planner → which executor → verifier), complexity score, estimated cost, and any
  gates that will fire — with color + motion.
- You **Confirm**, **Modify** (drag/swap a tier, change a model, add a human gate),
  or **Cancel**. Nothing executes until you approve.
- **Optional quick collaboration:** one toggle to pull a smarter model in to
  pressure-test the plan or a stuck step (user-configurable which model, off by default).
- A **Dry-run** switch: produce the plan and cost estimate without executing.

### 3. Profiles with per-profile memory
- All profiles derive from a **default template** you author once.
- Clone → customize (tier chains, models, gates, compression toggles, accent color)
  → save as a new profile → **push the update** (commits `profiles.json`).
- **Each profile has its own memory section** — its own context store, so a
  "refactor" profile and a "research" profile don't bleed into each other.
- Export/import a profile as JSON to share between you and Danish.

### 4. Connections / Repos (card workflow)
- Card grid of connected repos and platforms.
- **Direct connect to Vercel / Railway / GitHub** via OAuth.
- Per card: push updates, trigger a deploy, view status, **add or remove** a repo.
- Drag a card into a profile to scope which repos that profile can touch.

### 5. Live Canvas + Element Inspector
- Host an HTML template or image; render it live in a pane.
- **Click any element → its DOM path/snippet is captured and handed to the AI** as
  context ("make this button match the others", "this card is misaligned").
- Live-edit the template; changes re-render instantly; "Ready to commit" pushes to repo.

### 6. Live orchestration feed
- Real-time stream of decisions: `PLANNER scored 6/10`, `EXECUTOR escalated via Gate G`,
  color-coded by tier. Both logged-in users see the same feed (WebSocket).

---

## Extra features worth adding (my additions)

- **Spend HUD** — live token + dollar meter per session, ties to the benchmark log; warns near a budget cap (mirrors `OVERSPEND_TRIGGER`).
- **Diff viewer** — AI file edits shown as diffs with per-hunk approve/reject before commit.
- **Provider health panel** — which keys are live, which are rate-limited, current failover state (is OpenRouter carrying load right now?).
- **Command palette (⌘K)** — jump to any page, switch profile, start a session, run a saved task.
- **Run timeline** — scrub past runs; replay the decision trace for any task.
- **Side-by-side model compare** — same prompt, two models, diff the outputs (great for deciding tier assignments).
- **Notifications** — ping when a long run finishes or hits a human gate (in-app + optional desktop).
- **Audit trail** — every plan, approval, override, and commit is logged and queryable (pairs with the git history).
- **Accent-per-profile** — each profile carries its own accent color so you always know which one is active at a glance.

---

## How it ties to the orchestration layer

- Chat → **Planner (Tier 1)** scores + emits plan → **Plan Console** shows it → you approve.
- On run, the tiers/gates from `rules-and-gates.md` drive execution; the feed shows each gate.
- Profile switches edit `profiles.json` (the same toggle from Stage 1); both Hermes agents pull it.
- The Architect loop (`self-tuning-logic.py`) and self-teaching planner run in the background; their proposals surface as PRs you can review in the Repos page.

---

## Build note

Ship in layers (see Stage 6 in `roadmap.html`): backend + live feed first, then the
glassy chat, then Plan Console, then Profiles/Repos/Canvas. The visual polish
(hexagons, sounds, glass) layers on top of a working core — don't front-load it.
Optionally bootstrap the agent runtime from an open-source agent SDK (e.g. Cline's
open SDK) rather than building the loop from scratch; confirm the exact base before
committing.
