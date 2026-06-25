"""
Hermes MCP Orchestration Server
================================
Exposes the Syndrax orchestration layer as Model Context Protocol (MCP) tools.
Both Hermes Desktop instances (yours + Danish's) AND the syndrax.app dashboard
call these same tools, so everyone shares one source of truth.

This is a SCAFFOLD. The real tier logic (complexity scoring, gate evaluation,
model routing) lives in the orchestration BACKEND that this server calls over
HTTP. This file is the thin MCP <-> backend bridge.

Run modes:
  python hermes_mcp_orchestration.py --dev      # local stdio, mock backend ok
  python -m hermes_mcp_orchestration            # stdio (Hermes Desktop mode)
  TRANSPORT=sse python -m hermes_mcp_orchestration   # SSE/HTTP (dashboard mode)

Config via environment (set in Hermes config.yaml or your .env / Secrets Manager):
  SYNDRAX_ENV            dev | prod
  SYNDRAX_API_ENDPOINT  e.g. https://api.syndrax.app   (the orchestration backend)
  SYNDRAX_API_KEY       bearer token for the backend
  TRANSPORT             stdio (default) | sse
  LOG_LEVEL             INFO | DEBUG
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any, Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: mcp package not found. Install with: pip install -r mcp-requirements.txt", file=sys.stderr)
    sys.exit(1)

import httpx
from pydantic import BaseModel, Field

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
SYNDRAX_ENV = os.getenv("SYNDRAX_ENV", "dev")
SYNDRAX_API_ENDPOINT = os.getenv("SYNDRAX_API_ENDPOINT", "http://localhost:8000")
SYNDRAX_API_KEY = os.getenv("SYNDRAX_API_KEY", "dev-key-12345")
TRANSPORT = os.getenv("TRANSPORT", "stdio")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
REQUEST_TIMEOUT = float(os.getenv("SYNDRAX_TIMEOUT", "30"))

# Write log to /tmp when running non-root in a container (default /app is read-only)
_LOG_FILE = os.getenv("MCP_LOG_FILE", "/tmp/mcp-server.log" if os.getenv("TRANSPORT") == "sse" else "mcp-server.log")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="[%(levelname)s] %(asctime)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler(_LOG_FILE), logging.StreamHandler(sys.stderr)],
)
log = logging.getLogger("hermes-mcp-orchestration")

mcp = FastMCP("syndrax-orchestration")


# ----------------------------------------------------------------------------
# Models (the tool I/O contract)
# ----------------------------------------------------------------------------
class Plan(BaseModel):
    complexity_score: int = Field(ge=0, le=10)
    planner_model: str
    executor_tier: str          # simple | medium | hard
    executor_models: list[str]
    gates_firing: list[str]     # e.g. ["A","B","D","H"]
    estimated_cost_usd: float
    reasoning: str


# ----------------------------------------------------------------------------
# Backend HTTP helper (the orchestration logic lives behind this)
# ----------------------------------------------------------------------------
async def _backend(method: str, path: str, payload: Optional[dict] = None) -> dict[str, Any]:
    url = f"{SYNDRAX_API_ENDPOINT.rstrip('/')}{path}"
    headers = {"Authorization": f"Bearer {SYNDRAX_API_KEY}", "Content-Type": "application/json"}
    log.info("backend %s %s", method, url)
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.request(method, url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


# ============================================================================
# TOOLS — what Hermes Desktop / the dashboard can call
# ============================================================================
@mcp.tool()
async def orchestrate_plan(task: str, context: dict | None = None, profile: str = "orchestration") -> dict:
    """Score a task's complexity and return the routing plan WITHOUT executing it.
    Use this first so the user can confirm or modify before anything runs.

    Args:
        task: what to do, in plain language.
        context: optional extra context (files, constraints, repo info).
        profile: default | orchestration | openrouter_only.
    Returns: a plan {complexity_score, planner_model, executor_tier,
             executor_models, gates_firing, estimated_cost_usd, reasoning}.
    """
    try:
        data = await _backend("POST", "/v1/plan", {"task": task, "context": context or {}, "profile": profile})
        return Plan(**data).model_dump()
    except Exception as e:  # noqa: BLE001
        log.exception("orchestrate_plan failed")
        return {"error": str(e), "hint": "is the backend (SYNDRAX_API_ENDPOINT) reachable?"}


@mcp.tool()
async def orchestrate_execute(plan: dict, task: str, confirm: bool = False) -> dict:
    """Execute a plan through the tiers/gates. Requires confirm=True (Plan Console
    confirm-before-run). High-stakes tasks may still pause at Gate H for a human.

    Returns: {outcome, cost_usd, quality_score, models_used, escalations, output}.
    """
    if not confirm:
        return {"status": "awaiting_confirmation",
                "message": "Re-call with confirm=True to run this plan.",
                "plan": plan}
    try:
        return await _backend("POST", "/v1/execute", {"plan": plan, "task": task, "confirm": True})
    except Exception as e:  # noqa: BLE001
        log.exception("orchestrate_execute failed")
        return {"error": str(e)}


@mcp.tool()
async def benchmark_log(record: dict) -> dict:
    """Append one task record to the shared benchmark log (matches benchmark-schema.json).
    This is the fuel for the Architect self-tuning loop. Returns {logged: bool, id}."""
    try:
        return await _backend("POST", "/v1/benchmark", record)
    except Exception as e:  # noqa: BLE001
        log.exception("benchmark_log failed")
        return {"logged": False, "error": str(e)}


@mcp.tool()
async def profile_switch(active_profile: str) -> dict:
    """Switch the active orchestration profile for everyone.
    Valid: default | orchestration | openrouter_only. Both machines pick it up."""
    if active_profile not in {"default", "orchestration", "openrouter_only"}:
        return {"error": f"unknown profile '{active_profile}'"}
    try:
        return await _backend("POST", "/v1/profile", {"active_profile": active_profile})
    except Exception as e:  # noqa: BLE001
        log.exception("profile_switch failed")
        return {"error": str(e)}


@mcp.tool()
async def orchestration_status() -> dict:
    """Health + current state: active profile, provider key health, failover state,
    recent spend. Good first call to confirm the connection works."""
    try:
        return await _backend("GET", "/v1/status")
    except Exception as e:  # noqa: BLE001
        return {"healthy": False, "error": str(e),
                "endpoint": SYNDRAX_API_ENDPOINT, "env": SYNDRAX_ENV}


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes MCP Orchestration Server")
    parser.add_argument("--dev", action="store_true", help="dev mode (verbose, local backend)")
    args = parser.parse_args()
    if args.dev:
        log.setLevel(logging.DEBUG)
        log.debug("DEV mode | endpoint=%s | transport=%s", SYNDRAX_API_ENDPOINT, TRANSPORT)

    log.info("starting syndrax-orchestration MCP server (env=%s, transport=%s)", SYNDRAX_ENV, TRANSPORT)
    # stdio for Hermes Desktop; sse/http for the dashboard backend.
    if TRANSPORT == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run()  # stdio


if __name__ == "__main__":
    main()
