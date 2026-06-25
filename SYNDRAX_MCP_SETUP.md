# Syndrax MCP Setup — Bidirectional

The goal: type in **Hermes Desktop** OR on the **syndrax.app** site, and either way you
hit your own orchestration rules, gates, and multi-tier agents. Same backend, same
state, both directions. You and Danish both connect to it.

```
   Hermes Desktop (you)  ┐
   Hermes Desktop (Danish)├──(MCP, stdio)──┐
                          ┘                 │
                                            ▼
                            ┌──────────────────────────────┐
                            │  MCP Server                   │
                            │  hermes_mcp_orchestration.py  │
                            └──────────────────────────────┘
                                            │ HTTP (bearer key)
                                            ▼
                            ┌──────────────────────────────┐
                            │  Orchestration Backend        │
                            │  api.syndrax.app (Railway)     │
                            │  tiers · gates · benchmark log │
                            └──────────────────────────────┘
                                            ▲
            syndrax.app dashboard ───(MCP, SSE)──┘
            (browser chat + repo/container cards + live preview)
```

Both entry points (desktop + browser) call the **same five tools** →
`orchestrate_plan`, `orchestrate_execute`, `benchmark_log`, `profile_switch`,
`orchestration_status`. One source of truth.

---

## A. Connect Hermes Desktop (stdio)

Add to Hermes' `config.yaml` (Windows: `%LOCALAPPDATA%\hermes\config.yaml`,
Linux/Mac: `~/.config/hermes/config.yaml` or `~/.hermes/config.yaml`):

```yaml
mcp_servers:
  syndrax_orchestration:
    command: "python"
    args: ["-m", "hermes_mcp_orchestration"]
    env:
      SYNDRAX_ENV: "prod"                       # or "dev" for local testing
      SYNDRAX_API_ENDPOINT: "https://api.syndrax.app"
      SYNDRAX_API_KEY: ""                        # from AWS Secrets Manager / .env
      LOG_LEVEL: "INFO"
    timeout: 30
```

Restart Hermes Desktop. Type `@syndrax` to see the tools, or just:

```
> use syndrax to plan: refactor the handler into modules
   (Hermes calls orchestrate_plan → shows the plan)
> looks good, run it
   (Hermes calls orchestrate_execute with confirm=true)
```

Both you and Danish paste the **same block** → both hit the same backend.

---

## B. Connect the syndrax.app dashboard (SSE/HTTP)

The dashboard backend runs the MCP server in SSE mode (`TRANSPORT=sse`, port 3000) and
calls the same tools, so the browser chat and Hermes Desktop stay in lockstep. The
dashboard also gives you the visual layer: repo/container cards, click-to-open a live
local preview, build/test/push status. (Full UI in `DASHBOARD_SPEC.md`.)

---

## C. AWS cost guardrails (only if you use AWS — Railway is the cheaper default)

You said: don't let it vertically scale or run up a bill. If any piece runs on AWS,
set these and mark them so they're visible:

- **No unbounded autoscale.** Set a hard **max** on instances/concurrency. Never leave
  scaling open-ended.
  - Lambda → set **reserved concurrency** (caps parallel invocations, stops runaway cost).
  - ECS/EC2 → set a max task/instance count and **fixed** CPU/memory; do **not** enable
    vertical auto-scaling.
- **API Gateway** → enable request **throttling** (rate + burst caps).
- **CloudWatch Logs** → set **retention** (7 days) and keep level at INFO, not DEBUG
  (verbose logs are a silent cost driver).
- **Avoid NAT Gateway** where you can (per-GB charge); prefer VPC endpoints or a public
  subnet for the small service.
- **Budget alarm** → an AWS Budgets alert (e.g. $20/mo) that emails you before a surprise.
- **Secrets Manager** → negligible (~$0.40/secret/mo); fine to use.

**Recommendation:** keep the backend on **Railway** (flat monthly, you set CPU/memory
once — no autoscale surprises). The container caps in `docker-compose.yml` already
bound local runs. Treat AWS as optional/standby, not the default path.

---

## D. Quick verify (both directions)

1. `orchestration_status` from Hermes Desktop → `{ healthy: true }`.
2. `orchestrate_plan` → a plan with a complexity score + gates.
3. Open syndrax.app, send the same task in the browser chat → same plan.
4. Change the profile once (either side) → both reflect it next call.

If all four pass, the loop is closed: desktop and browser, one brain.
