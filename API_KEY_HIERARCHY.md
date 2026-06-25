# API Key Hierarchy

How models resolve to credentials. One calling layer (self-hosted LiteLLM),
direct provider keys underneath it, and OpenRouter as the universal failover.

> Keys are referenced by **env-var name only** everywhere in this repo. Real values
> live in your local `.env` (gitignored) and AWS Secrets Manager for prod. Setup
> runbook: `SECRETS_SETUP.md`.

---

## The picture

```
                    Hermes / Orchestrator
                            │
                            ▼
              ┌───────────────────────────┐
              │  LiteLLM Proxy (your VPS)  │  ← one endpoint, dumb pipe
              │  routing/fallback OFF      │     (the Gates decide, not LiteLLM)
              └───────────────────────────┘
                            │
        holds these direct provider keys:
                            │
   ┌───────────┬────────────┬────────────┬───────────┬───────────┐
   ▼           ▼            ▼            ▼           ▼
ANTHROPIC_  DEEPSEEK_    ZAI_API_     OPENAI_     GOOGLE_
API_KEY     API_KEY      KEY          API_KEY     API_KEY
   │           │            │            │           │
Claude       DeepSeek     GLM-5.2      GPT-5.4    Gemini 3
Opus/Sonnet  V3/V4/       (planner)               Flash /
/Haiku       Flash/Pro                            Flash-Lite

        if no direct key is set for a model,
        OR a direct call fails / rate-limits:
                            │
                            ▼
              ┌───────────────────────────┐
              │   OPENROUTER_API_KEY       │  ← single failover key
              │   catch-all, any model     │     (also your testing key)
              └───────────────────────────┘
```

---

## Mapped onto the tiers

Each row is a fallback chain, left → right. Last column is the safety net.

| Tier | 1st (direct) | 2nd (direct) | 3rd (direct) | Last resort |
|------|--------------|--------------|--------------|-------------|
| Architect | Opus 4.8 · `ANTHROPIC` | GPT-5.4 · `OPENAI` | DeepSeek V4 Pro · `DEEPSEEK` | OpenRouter |
| Planner | GLM-5.2 · `ZAI` | DeepSeek V4 Flash · `DEEPSEEK` | Haiku 4.5 · `ANTHROPIC` | OpenRouter |
| Exec — simple | DeepSeek V3 · `DEEPSEEK` | Gemini 3 Flash · `GOOGLE` | — | OpenRouter |
| Exec — medium | Sonnet 4.6 · `ANTHROPIC` | GLM-5.2 · `ZAI` | — | OpenRouter |
| Exec — hard | Opus 4.8 · `ANTHROPIC` | GPT-5.4 · `OPENAI` | DeepSeek V4 Pro · `DEEPSEEK` | OpenRouter |
| Micro-orch | Haiku 4.5 · `ANTHROPIC` | GLM-5.2 · `ZAI` | — | OpenRouter |
| Verifier | DeepSeek V3 · `DEEPSEEK` | Sonnet 4.6 · `ANTHROPIC` | — | OpenRouter |

**5 direct keys** cover the whole system. **1 OpenRouter key** sits underneath all of
them as failover (and doubles as your testing key for models you don't have direct
access to yet).

---

## Resolution rule (what happens per call)

1. Hermes asks for a model (e.g. `glm-5.2`) through the LiteLLM proxy.
2. LiteLLM looks up the provider (`glm-5.2` → `zai`) and reads `ZAI_API_KEY` from the
   environment.
3. If `ZAI_API_KEY` is **unset**, or the call **fails / rate-limits**, LiteLLM routes
   the same request through `OPENROUTER_API_KEY`.
4. You never change Hermes code to switch providers — only the `.env` keys and
   `profiles.json` chains.

This is why you can start with **only `OPENROUTER_API_KEY`** set (everything falls
through to it), then add direct keys one at a time to cut cost — no migration step.

---

## The 6 keys, at a glance

| Env var | Provider | Covers | Get it from |
|---------|----------|--------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic | Opus / Sonnet / Haiku | console.anthropic.com |
| `DEEPSEEK_API_KEY` | DeepSeek | V3 / V4 Flash / V4 Pro | platform.deepseek.com |
| `ZAI_API_KEY` | Z.ai | GLM-5.2 | z.ai |
| `OPENAI_API_KEY` | OpenAI | GPT-5.4 | platform.openai.com |
| `GOOGLE_API_KEY` | Google | Gemini 3 Flash / Flash-Lite | aistudio.google.com |
| `OPENROUTER_API_KEY` | OpenRouter | everything (failover + testing) | openrouter.ai/keys |
