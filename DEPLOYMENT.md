# Deployment

How the controlplane goes live on **syndrax.app**, reusing the existing Syndrax
stack — Namecheap, Cloudflare, Vercel, Railway, AWS — with the **same connection
profiles and security as syndrax.io / Syndrax Sync**. No new vendors, no new accounts.

> Repo already exists (empty): **https://github.com/arthurperch/hermes-orchestration-layer**
> Push the zip contents into it (see `HERMES_SETUP.md`). This doc is the hosting path
> for Stage 6 — build it after the orchestration core works.

---

## The stack (mirror syndrax.io)

```
Namecheap (registrar)  ──DNS──►  Cloudflare (DNS + Access/Zero-Trust)
                                        │
                        ┌───────────────┴───────────────┐
                        ▼                                ▼
                 syndrax.app (frontend)            api.syndrax.app (backend)
                 Vercel project                   Railway service
                 (same Git + env profile          (same account + deploy
                  as the syndrax.io project)        profile as syndrax)
                                        │
                                        ▼
                              AWS Secrets Manager
                              (API keys in prod)
```

| Domain | Registrar | DNS | Frontend | Backend | Secrets |
|--------|-----------|-----|----------|---------|---------|
| syndrax.io | Namecheap | Cloudflare | Vercel | — | — |
| **syndrax.app** | Namecheap | Cloudflare | **Vercel (new project)** | **Railway (new service)** | AWS Secrets Manager |
| syndrax.dev | Namecheap | Cloudflare | (reserved — staging) | (reserved — staging) | — |

> **Domain note:** `syndrax.ai` was never owned — confirmed in the Namecheap dashboard.
> Owned domains are `syndrax.io` (main site), `syndrax.app`, and `syndrax.dev`.
> `.app` was picked for the controlplane since it's literally what it is — a web app,
> not the marketing site. `syndrax.dev` is reserved as the **staging/preview**
> environment (point it at a separate Vercel preview + Railway staging service so you
> can test changes before they hit `syndrax.app`). If you'd rather flip which domain
> is prod vs staging, every reference below is a find-and-replace away.

---

## 1. DNS (Cloudflare) — cleanest setup

In the existing Cloudflare zone (same account as syndrax.io):

- `syndrax.app` → **CNAME → Vercel** (Vercel gives the target on domain add). Proxied (orange cloud).
- `api.syndrax.app` → **CNAME → Railway** (Railway gives the target). Proxied.
- Keep Namecheap nameservers pointed at Cloudflare (same as syndrax.io — likely already set).

CNAME-to-platform is the cleanest because Vercel/Railway manage their own certs and
IPs; you never touch A records. Cloudflare proxy gives you WAF + caching for free.

## 2. Frontend — Vercel (copy the syndrax.io profile)

- New Vercel project from the `hermes-orchestration-layer` repo.
- **Reuse the syndrax.io connection profile:** same GitHub integration, same
  team/scope, same env-var conventions, same custom-domain flow. Add `syndrax.app`
  as the domain → Vercel prints the CNAME for step 1.
- Auto-deploys on push to `main` (same as syndrax.io).

## 3. Backend — Railway (same account/setup as syndrax)

- New Railway service in the same project/account, from the same repo.
- FastAPI + WebSocket (the live feed). Bind `api.syndrax.app`.
- Pull API keys from AWS Secrets Manager (below), not from env files in the repo.
- Same deploy profile/region conventions as your other Syndrax services.

## 4. Security — Cloudflare Access (same as Syndrax Sync)

- Put `syndrax.app` behind **Cloudflare Access** using the **same Zero-Trust policy /
  identity provider as Syndrax Sync**. Mirror that policy exactly.
- Allow only your two identities (you + Danish). No public signup.
- This is the dashboard's secure login — the home screen sits behind Access; the app
  also does GitHub OAuth inside for per-user identity + repo/Vercel connections.

## 5. Secrets — AWS Secrets Manager (prod)

Local dev uses `.env` (`SECRETS_SETUP.md`). Prod keys live in Secrets Manager so they
never sit on Railway in plaintext:

```bash
aws secretsmanager create-secret --name hermes/OPENROUTER_API_KEY --secret-string "sk-or-..."
# repeat: ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, ZAI_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY
```

Give the Railway service IAM `secretsmanager:GetSecretValue` on `hermes/*`. Both
local Hermes agents can also read from Secrets Manager via IAM — one source of truth.

---

## Deploy pipeline (same shape as syndrax.io)

```
push to main
   → Vercel builds + deploys frontend (syndrax.app)
   → Railway builds + deploys backend (api.syndrax.app)
   → profiles.json change → both Hermes agents pick it up next cycle
```

---

## Cost

Near-zero on existing infra: Vercel (likely existing plan), Railway (small service),
Cloudflare (free tier covers DNS + Access for a couple users), Secrets Manager
(~$0.40/secret/mo). Model API spend dwarfs hosting.

---

## Build order (Stage 6)

1. Backend on Railway: FastAPI + WebSocket + GitHub/Vercel OAuth + `profiles.json` read/write.
2. Wire both Hermes agents to push structured events to the WebSocket.
3. Frontend on Vercel: the pages in `DASHBOARD_SPEC.md`, styled per `DESIGN_SYSTEM.md`.
4. Cloudflare Access (mirror Syndrax Sync) → lock to two identities.
5. Point `syndrax.app` + `api.syndrax.app` via Cloudflare CNAMEs.
6. Optional: stand up `syndrax.dev` as a staging mirror first, validate there, then
   point `syndrax.app` at the same build once it's confirmed.
7. Ship; iterate on the visual polish (hexagons, sounds, glass) on top of the working core.

> Open question to confirm before building: do you want to **fork an open-source agent
> dashboard** as the base, or build the frontend custom? If forking, point this repo's
> deploy at that base and we adapt it; if custom, the spec above is self-contained.
