# Secrets Setup

The one job you (Oleg) do by hand before Hermes can run. Get the keys, paste them
into a local `.env`, confirm git can't see them, then hand off to Hermes.

> **Why this is manual:** API keys are the one thing that must never touch the repo.
> Everything else Hermes can do itself. This file is the bridge.

---

## The flow (start to finish)

```
get keys  →  paste into .env  →  verify gitignored  →  start LiteLLM  →  tell Hermes go
 (you)          (you)              (you, 1 cmd)         (you/Hermes)       (you, chat)
```

---

## Step 1 — Get the keys

Open each console, create an API key, copy it. You can start with **just OpenRouter**
and add the rest later (everything falls through to OpenRouter until a direct key
exists — see `API_KEY_HIERARCHY.md`).

| Order | Key | Where | Notes |
|-------|-----|-------|-------|
| 1 (start here) | `OPENROUTER_API_KEY` | https://openrouter.ai/keys | unlocks every model with one key; fund ~$20–50 for testing |
| 2 | `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys | Claude tiers |
| 3 | `DEEPSEEK_API_KEY` | https://platform.deepseek.com → API Keys | cheapest workhorse |
| 4 | `ZAI_API_KEY` | https://z.ai (or open.bigmodel.cn) → API | GLM-5.2 planner |
| 5 | `OPENAI_API_KEY` | https://platform.openai.com → API Keys | GPT-5.4 |
| 6 | `GOOGLE_API_KEY` | https://aistudio.google.com → Get API Key | Gemini |

Also invent a `LITELLM_MASTER_KEY` — any random string (e.g. `sk-hermes-` + random).
It's the password Hermes uses to talk to your proxy.

---

## Step 2 — Paste into `.env`

From the repo root:

```bash
cp .env.template .env
```

Open `.env` in your editor and paste each real key after its `=`. Example (fake
values shown):

```
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
LITELLM_MASTER_KEY=sk-hermes-9f3a...
```

Leave any key you don't have yet **blank** — that model just falls through to
OpenRouter until you fill it in.

---

## Step 3 — Verify git can't see it

This is the safety check. Run:

```bash
git check-ignore .env
```

It must print `.env`. If it prints nothing, **stop** — the `.gitignore` isn't
protecting it and you risk committing secrets. (It's already in `.gitignore`, so this
should just work.)

Double-check nothing secret is staged:

```bash
git status        # .env must NOT appear in the list
```

---

## Step 4 — Start the LiteLLM proxy

```bash
pip install 'litellm[proxy]'
litellm --config litellm-config.yaml
```

It loads keys from your environment. Load the `.env` first if your shell doesn't
auto-load it:

```bash
set -a; source .env; set +a
litellm --config litellm-config.yaml
```

Proxy comes up on `http://127.0.0.1:4000` (or whatever `LITELLM_PROXY_URL` says).

---

## Step 5 — Hand off to Hermes

Keys are in place. Now Hermes does the rest. In your Hermes chat:

> "Read `litellm-config.yaml` and `profiles.json`. Use the `orchestration` profile
> (or `openrouter_only` if I've only set the OpenRouter key so far). Confirm you can
> reach the proxy, then start the planner."

That's it. You never touch keys again unless one rotates.

---

## Where keys live (and don't)

| Location | Holds real keys? | Why |
|----------|------------------|-----|
| `.env.template` (in repo) | ❌ names only | the public shape |
| `.env` (local, gitignored) | ✅ | your machine + Danish's machine, never pushed |
| AWS Secrets Manager (prod) | ✅ | when the controlplane goes live on syndrax.app — see `DEPLOYMENT.md` |
| anywhere in git history | ❌ never | the whole point of the gitignore |

---

## Optional: keys encrypted *inside* the repo (advanced)

If you specifically want the keys versioned in the repo but unreadable (instead of a
local-only `.env`), use **git-crypt** or **SOPS**:

- `git-crypt` — transparently encrypts chosen files (e.g. `secrets/keys.env`) with a
  GPG key. Both you and Danish hold the key; anyone else sees ciphertext. Setup:
  `git-crypt init`, add `secrets/** filter=git-crypt diff=git-crypt` to
  `.gitattributes`, share the symmetric key out-of-band.
- `SOPS` (Mozilla) — encrypts values with AWS KMS / age; pairs naturally with your
  AWS account.

For your two-person setup the **local `.env` is simpler and safer** (keys never leave
your machines at all). Only reach for git-crypt/SOPS if you truly need the keys to
travel with the repo. Either way: never commit plaintext keys.
