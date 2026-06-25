"""
mcp-test.py — smoke tests for the Hermes MCP Orchestration Server.

Validates the tool contract against a mock backend (no real models called).
CI runs this on every push; a failure blocks the deploy.

Run:  python mcp-test.py
"""
import asyncio
import sys

# Tests hit the tool functions directly with a stubbed backend so they run
# offline. They check the I/O shape, not real orchestration behavior.

import hermes_mcp_orchestration as srv


# --- stub the backend so no network/models are needed ---
async def fake_backend(method, path, payload=None):
    if path == "/v1/plan":
        return {
            "complexity_score": 6,
            "planner_model": "glm-5.2",
            "executor_tier": "medium",
            "executor_models": ["claude-sonnet-4-6", "glm-5.2"],
            "gates_firing": ["A", "B", "D"],
            "estimated_cost_usd": 0.18,
            "reasoning": "multi-file refactor, moderate blast radius",
        }
    if path == "/v1/execute":
        return {"outcome": "success", "cost_usd": 0.21, "quality_score": 0.94,
                "models_used": ["glm-5.2", "claude-sonnet-4-6"], "escalations": [], "output": "..."}
    if path == "/v1/benchmark":
        return {"logged": True, "id": "tsk_test_001"}
    if path == "/v1/profile":
        return {"active_profile": payload["active_profile"], "applied": True}
    if path == "/v1/status":
        return {"healthy": True, "active_profile": "orchestration", "failover": False}
    raise AssertionError(f"unexpected path {path}")


srv._backend = fake_backend  # type: ignore  # noqa: SLF001

PASS, FAIL = 0, 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[\u2713] {name}")
    else:
        FAIL += 1
        print(f"[\u2717] {name}")


async def run():
    plan = await srv.orchestrate_plan("refactor handler into modules")
    check("orchestrate_plan returns a complexity score 0-10",
          isinstance(plan.get("complexity_score"), int) and 0 <= plan["complexity_score"] <= 10)
    check("orchestrate_plan routes to a tier", plan.get("executor_tier") in {"simple", "medium", "hard"})

    pending = await srv.orchestrate_execute(plan, "refactor", confirm=False)
    check("execute without confirm waits", pending.get("status") == "awaiting_confirmation")

    done = await srv.orchestrate_execute(plan, "refactor", confirm=True)
    check("execute with confirm returns an outcome", done.get("outcome") == "success")

    logged = await srv.benchmark_log({"task_id": "tsk_test_001", "outcome": "success"})
    check("benchmark_log logs the record", logged.get("logged") is True)

    sw = await srv.profile_switch("orchestration")
    check("profile_switch accepts a valid profile", sw.get("applied") is True)

    bad = await srv.profile_switch("nonsense")
    check("profile_switch rejects an invalid profile", "error" in bad)

    st = await srv.orchestration_status()
    check("status reports healthy", st.get("healthy") is True)


if __name__ == "__main__":
    asyncio.run(run())
    print(f"\n{PASS} passed, {FAIL} failed.")
    sys.exit(1 if FAIL else 0)
