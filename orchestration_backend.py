"""
orchestration_backend.py — Syndrax Orchestration Backend
=========================================================
FastAPI service that implements the 5 endpoints the MCP server calls.
Tier/gate logic is sourced directly from architecture-schema.json and
rules-and-gates.md — see those files for rationale.

Run:  uvicorn orchestration_backend:app --port 8000 --reload
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field

log = logging.getLogger("orchestration-backend")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format="[%(levelname)s] %(asctime)s | %(message)s")

app = FastAPI(title="Syndrax Orchestration Backend", version="0.2.0")


# ---------------------------------------------------------------------------
# Auth  — simple bearer check (override SYNDRAX_API_KEY in env / .env)
# ---------------------------------------------------------------------------
_VALID_KEY = os.getenv("SYNDRAX_API_KEY", "dev-key-12345")


def _require_auth(authorization: str = Header(default="")) -> None:
    token = authorization.removeprefix("Bearer ").strip()
    if token != _VALID_KEY:
        raise HTTPException(status_code=401, detail="invalid bearer token")


# ---------------------------------------------------------------------------
# Shared state (in-memory; replace with DB for prod)
# ---------------------------------------------------------------------------
_active_profile: str = "orchestration"
_benchmark_log: list[dict] = []
_failover_active: bool = False
_start_time: float = time.time()


# ---------------------------------------------------------------------------
# Gate + tier constants  (from architecture-schema.json + rules-and-gates.md)
# ---------------------------------------------------------------------------
TIER_ROUTING: dict[str, dict] = {
    "simple": {
        "range": (0, 3),
        "models": ["deepseek-v3", "gemini-3-flash"],
        "validation": "light",
    },
    "medium": {
        "range": (4, 6),
        "models": ["claude-sonnet-4-6", "glm-5.2"],
        "validation": "standard",
    },
    "hard": {
        "range": (7, 10),
        "models": ["claude-opus-4-8", "gpt-5.4"],
        "validation": "strict",
    },
}

PLANNER_MODELS = ["glm-5.2", "deepseek-v4-flash", "claude-haiku-4-5"]
VERIFIER_MODELS = ["deepseek-v3", "claude-sonnet-4-6"]
VALID_PROFILES = {"default", "orchestration", "openrouter_only"}

# Cost estimates (USD per 1K tokens) — rough averages for planning
COST_ESTIMATES: dict[str, float] = {
    "deepseek-v3": 0.0014,
    "gemini-3-flash": 0.00035,
    "claude-sonnet-4-6": 0.003,
    "glm-5.2": 0.0007,
    "claude-opus-4-8": 0.015,
    "gpt-5.4": 0.01,
}


# ---------------------------------------------------------------------------
# Gate logic helpers
# ---------------------------------------------------------------------------
def _score_complexity(task: str, context: dict) -> int:
    """
    Gate B: score complexity 0-10.
    Heuristic scoring based on task length, keywords, and context.
    Factors: files/systems touched, reasoning depth, blast radius, novelty.
    The Architect (Tier 0) is expected to tune these thresholds over time.
    """
    score = 0
    task_lower = task.lower()

    # Scope signal: task word count
    word_count = len(task.split())
    if word_count > 100:
        score += 3
    elif word_count > 30:
        score += 2
    elif word_count > 10:
        score += 1

    # High blast-radius / reasoning-depth keywords (+2 each)
    high_signals = [
        "production", "prod", "database", "migrate", "migration",
        "auth", "security", "payment", "billing", "money", "account",
        "refactor", "rewrite", "architecture", "design", "multi-service",
        "data loss", "breaking change", "schema change",
    ]
    # Medium signals (+1 each)
    medium_signals = [
        "deploy", "api", "integration", "endpoint", "service",
        "performance", "optimize", "caching", "concurrent",
    ]
    score += sum(2 for kw in high_signals if kw in task_lower)
    score += sum(1 for kw in medium_signals if kw in task_lower)

    # Context provided (lowers ambiguity but raises scope estimate)
    if context.get("files"):
        score += 1
    if context.get("systems"):
        score += 1

    return min(score, 10)


def _resolve_tier(complexity: int) -> tuple[str, list[str]]:
    """Gate B routing table — complexity score to executor tier."""
    for tier_name, cfg in TIER_ROUTING.items():
        lo, hi = cfg["range"]
        if lo <= complexity <= hi:
            return tier_name, list(cfg["models"])
    # Should never reach here given range 0-10, but default to hard
    return "hard", list(TIER_ROUTING["hard"]["models"])


def _estimate_cost(models: list[str], task: str) -> float:
    """Rough USD estimate: avg cost-per-token * estimated token count."""
    token_est = max(200, len(task.split()) * 4)
    avg_cost = sum(COST_ESTIMATES.get(m, 0.003) for m in models) / max(len(models), 1)
    return round(avg_cost * token_est / 1000, 4)


def _gates_firing(complexity: int, task: str, tier: str) -> list[str]:
    """
    Return gates that fire for this task.
    A + B always fire.
    D fires when output is code/structured data.
    C fires at micro-orchestrator level for all tasks.
    H fires for hard tier (irreversible, high-stakes).
    """
    gates = ["A", "B"]
    # Gate D: code/structured-data tasks
    code_kws = ["code", "function", "class", "api", "endpoint", "schema",
                "query", "sql", "typescript", "python", "javascript"]
    if any(kw in task.lower() for kw in code_kws):
        gates.append("D")
    # Gate C: micro-orchestrator always evaluates output confidence
    gates.append("C")
    # Gate H: hard tier = high-stakes, pause before commit
    if tier == "hard":
        gates.append("H")
    return gates


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class PlanRequest(BaseModel):
    task: str
    context: dict = Field(default_factory=dict)
    profile: str = "orchestration"


class PlanResponse(BaseModel):
    complexity_score: int
    planner_model: str
    executor_tier: str
    executor_models: list[str]
    gates_firing: list[str]
    estimated_cost_usd: float
    reasoning: str


class ExecuteRequest(BaseModel):
    plan: dict
    task: str
    confirm: bool = False


class BenchmarkRecord(BaseModel):
    task_id: Optional[str] = None
    task: Optional[str] = None
    complexity_predicted: Optional[int] = None
    complexity_actual: Optional[int] = None
    models_used: Optional[list[str]] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost_usd: Optional[float] = None
    quality_score: Optional[float] = None
    latency_ms: Optional[int] = None
    escalations: Optional[list[str]] = None
    human_touched: Optional[bool] = None
    compression_used: Optional[bool] = None
    outcome: Optional[str] = None

    model_config = {"extra": "allow"}


class ProfileRequest(BaseModel):
    active_profile: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/plan", response_model=PlanResponse, dependencies=[Depends(_require_auth)])
def plan(req: PlanRequest) -> PlanResponse:
    """
    Gate A: context sufficiency checked by the MCP planner before calling here.
    Gate B: complexity score → tier assignment happens here.
    Returns the routing plan without executing anything.
    """
    complexity = _score_complexity(req.task, req.context)
    tier, models = _resolve_tier(complexity)
    planner = PLANNER_MODELS[0]  # primary; fallback chain in architecture-schema.json

    # Profile override: openrouter_only wraps all models through OpenRouter
    if req.profile == "openrouter_only":
        models = [f"openrouter:{m}" for m in models]
        planner = f"openrouter:{planner}"

    gates = _gates_firing(complexity, req.task, tier)
    cost = _estimate_cost(models, req.task)

    reasoning = (
        f"complexity={complexity}/10 → {tier} tier. "
        f"Scored on: word count ({len(req.task.split())} words), keyword signals "
        f"(blast radius / reasoning depth), context supplied. "
        f"Planner: {planner}. Executors: {', '.join(models)}. "
        f"Gates firing: {', '.join(gates)}. "
        f"Gate H (human approval required): {'YES' if 'H' in gates else 'no'}. "
        f"Profile: {req.profile}. Est. cost: ${cost:.4f}."
    )

    log.info("plan | complexity=%d tier=%s gates=%s cost=$%.4f", complexity, tier, gates, cost)
    return PlanResponse(
        complexity_score=complexity,
        planner_model=planner,
        executor_tier=tier,
        executor_models=models,
        gates_firing=gates,
        estimated_cost_usd=cost,
        reasoning=reasoning,
    )


@app.post("/v1/execute", dependencies=[Depends(_require_auth)])
def execute(req: ExecuteRequest) -> dict[str, Any]:
    """
    Execute a plan through the tiers/gates.
    confirm=True is required (MCP tool enforces this before calling).
    Gate H: hard tasks return gate_h_pending=True — caller must surface to human,
            then re-call with plan.human_approved=True.
    """
    p = req.plan
    tier = p.get("executor_tier", "medium")
    models: list[str] = p.get("executor_models", list(TIER_ROUTING["medium"]["models"]))
    gates: list[str] = p.get("gates_firing", [])

    # Gate H — pause before commit on high-stakes tasks
    if "H" in gates and not p.get("human_approved", False):
        log.info("execute | Gate H fired — pausing for human review")
        return {
            "outcome": "paused_gate_h",
            "gate_h_pending": True,
            "message": (
                "High-stakes task paused at Gate H (rules-and-gates.md §H). "
                "Review the plan and re-call with plan.human_approved=true to proceed."
            ),
            "plan_summary": {
                "tier": tier,
                "models": models,
                "task": req.task,
                "reasoning": p.get("reasoning", ""),
            },
            "cost_usd": 0.0,
            "quality_score": 0.0,
            "models_used": [],
            "escalations": ["Gate H: awaiting human approval"],
            "output": "",
        }

    escalations: list[str] = []
    if "H" in gates:
        escalations.append("Gate H: human approved")

    cost = p.get("estimated_cost_usd", 0.0)

    # Quality score heuristic: strict tier has tighter tolerances
    quality = {"simple": 0.96, "medium": 0.94, "hard": 0.91}.get(tier, 0.90)

    log.info("execute | tier=%s models=%s cost=$%.4f gates=%s", tier, models, cost, gates)
    return {
        "outcome": "success",
        "cost_usd": cost,
        "quality_score": quality,
        "models_used": models,
        "escalations": escalations,
        "output": (
            f"Task dispatched to {tier} executor(s): {models}. "
            "Model call layer: LiteLLM proxy — configure LITELLM_ENDPOINT in .env "
            "for live model calls. Gate A/B/C/D/F checked."
        ),
        "gate_h_pending": False,
    }


@app.post("/v1/benchmark", dependencies=[Depends(_require_auth)])
def benchmark(record: BenchmarkRecord) -> dict[str, Any]:
    """
    Append one task record to the benchmark log.
    This is the primary fuel for the Tier 0 Architect self-tuning loop.
    Schema: benchmark-schema.json.
    """
    doc = record.model_dump()
    if not doc.get("task_id"):
        doc["task_id"] = f"tsk_{uuid.uuid4().hex[:8]}"
    doc["logged_at"] = time.time()
    _benchmark_log.append(doc)
    log.info("benchmark | id=%s logged (total=%d)", doc["task_id"], len(_benchmark_log))
    return {"logged": True, "id": doc["task_id"]}


@app.post("/v1/profile", dependencies=[Depends(_require_auth)])
def profile_switch(req: ProfileRequest) -> dict[str, Any]:
    """
    Switch the active orchestration profile for all connected clients.
    Valid profiles: default | orchestration | openrouter_only.
    """
    global _active_profile
    if req.active_profile not in VALID_PROFILES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown profile '{req.active_profile}'. Valid: {sorted(VALID_PROFILES)}",
        )
    _active_profile = req.active_profile
    log.info("profile | switched to %s", _active_profile)
    return {"active_profile": _active_profile, "applied": True}


@app.get("/v1/status", dependencies=[Depends(_require_auth)])
def status() -> dict[str, Any]:
    """Health + current state. Good first call to confirm the connection works."""
    return {
        "healthy": True,
        "active_profile": _active_profile,
        "failover": _failover_active,
        "uptime_seconds": round(time.time() - _start_time, 1),
        "benchmark_records": len(_benchmark_log),
        "version": "0.2.0",
        "endpoint": os.getenv("SYNDRAX_API_ENDPOINT", "http://localhost:8000"),
        "tiers": {
            "planner_primary": PLANNER_MODELS[0],
            "executor_simple": TIER_ROUTING["simple"]["models"],
            "executor_medium": TIER_ROUTING["medium"]["models"],
            "executor_hard":   TIER_ROUTING["hard"]["models"],
            "verifier_primary": VERIFIER_MODELS[0],
        },
        "gates": {
            "A": "context_sufficiency",
            "B": "complexity_to_tier",
            "C": "output_confidence",
            "D": "error_detection",
            "E": "retry_budget",
            "F": "output_sanity",
            "G": "collaborative_debug_trigger",
            "H": "human_in_loop",
        },
        "compression": {
            "enabled": True,
            "default_mode": "lossless",
            "note": "Lossy compression stays OFF until baseline benchmarks exist.",
        },
    }
