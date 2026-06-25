# Stage 6 — Shared Controlplane Dashboard

[← back to roadmap](../ROADMAP.md)

**Goal:** the shared cockpit on **syndrax.app** where you and Danish both log in,
watch Hermes execute live, edit profiles together, and view the architecture — no
Discord, no `.exe`, hosted on your own domain.

**Accent:** 🟦 blue · **Status:** queued (nice-to-have, after orchestration works)

---

## Tasks

- [ ] FastAPI backend + WebSocket `/live` (pushes Hermes events to both users)
- [ ] GitHub read/write of `profiles.json` (edit in UI → commit → both agents pull)
- [ ] React/HTML frontend: split-view — live log (left) + tabs (right)
- [ ] Tabs: Profiles (form editor + toggle), Architecture (render Mermaid), Benchmark (table)
- [ ] GitHub OAuth, locked to two usernames
- [ ] Deploy on syndrax.app (S3 + CloudFront frontend, EC2/Lambda backend) — see `DEPLOYMENT.md`

## Files involved

`profiles.json` · `orchestration-flowchart.md` (rendered in Architecture tab) ·
`benchmark-schema.json` · `DEPLOYMENT.md`

## Done when

- Both of you open syndrax.app, log in with GitHub, and see the same live feed.
- Editing a profile in the UI commits to the repo and both Hermes agents pick it up.
- The architecture diagrams render in a tab; the benchmark table updates as tasks run.

## Notes

Keys come from AWS Secrets Manager in prod, never the repo. Lock OAuth to your two
accounts — no public signup. Ship the FastAPI + plain-HTML version first; wrap in
React/Electron later only if you want.
