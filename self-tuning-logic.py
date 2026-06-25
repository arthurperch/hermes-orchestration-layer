"""
self-tuning-logic.py  —  Tier-0 Architect loop (BLUEPRINT / PSEUDOCODE)

How the orchestration improves itself. The Architect reads the benchmark log,
finds where routing was wrong, proposes concrete rule/threshold changes, and
sandbox-tests them on a HELD-OUT task set before anything is promoted to prod.

This is a blueprint, not production code. The `call_model(...)`, `load_log(...)`,
and `run_strategy(...)` calls are placeholders for your real implementations
(Hermes API client, log store, lab harness).

Core principle: optimize quality_per_dollar SUBJECT TO a quality_pass_rate floor.
Never promote a change that saves money by dropping below the floor.
"""

from dataclasses import dataclass
from statistics import mean

# ----------------------------------------------------------------------------
# Config — these mirror the defaults in rules-and-gates.md
# ----------------------------------------------------------------------------
QUALITY_FLOOR = 0.95          # min quality_pass_rate a strategy must hold
MIN_SAMPLES_PER_BUCKET = 20   # don't tune on thin data
COMPLEXITY_ERROR_TRIGGER = 1.5  # avg |predicted-actual| above this → recalibrate Gate B
OVERSPEND_TRIGGER = 0.30      # >30% of tasks in a bucket over-routed → consider routing down
UNDERSHOOT_TRIGGER = 0.20     # >20% needed escalation → consider routing up

ARCHITECT_MODEL = "claude-opus-4-8"


# ----------------------------------------------------------------------------
# 1. INGEST — pull the benchmark records (schema: benchmark-schema.json)
# ----------------------------------------------------------------------------
def ingest():
    records = load_log()  # -> list[BenchmarkRecord]
    # split into the set we tune on vs a held-out set we validate on.
    # NEVER validate on the data you tuned on.
    tune_set, holdout_set = split(records, ratio=0.7, seed=42)
    return tune_set, holdout_set


# ----------------------------------------------------------------------------
# 2. DIAGNOSE — find where routing is wrong, per (task_type, complexity bucket)
# ----------------------------------------------------------------------------
@dataclass
class Finding:
    task_type: str
    bucket: str           # "simple" | "medium" | "hard"
    issue: str            # human-readable problem
    evidence: dict        # the numbers behind it
    hypothesis: str       # proposed direction


def diagnose(records):
    findings = []
    for (task_type, bucket), rows in group_by_type_and_bucket(records):
        if len(rows) < MIN_SAMPLES_PER_BUCKET:
            continue  # insufficient data, skip

        pass_rate   = fraction(rows, lambda r: r.quality_thresholds_met)
        escal_rate  = fraction(rows, lambda r: len(r.escalations) > 0)
        cmplx_error = mean(abs(r.complexity_predicted - r.complexity_actual) for r in rows)
        qpd         = mean(r.quality_score for r in rows) / max(mean(r.cost_usd for r in rows), 1e-9)

        # (a) Planner mis-scoring complexity → recalibrate Gate B
        if cmplx_error > COMPLEXITY_ERROR_TRIGGER:
            direction = "up" if avg_signed_error(rows) > 0 else "down"
            findings.append(Finding(
                task_type, bucket,
                issue=f"complexity systematically {('under' if direction=='up' else 'over')}-predicted",
                evidence={"avg_abs_error": cmplx_error, "n": len(rows)},
                hypothesis=f"shift default complexity for '{task_type}' {direction} ~1 point",
            ))

        # (b) Too many escalations → the default tier is too weak → route up
        if escal_rate > UNDERSHOOT_TRIGGER and pass_rate < 1.0:
            findings.append(Finding(
                task_type, bucket,
                issue="default tier under-powered; frequent escalation",
                evidence={"escalation_rate": escal_rate, "pass_rate": pass_rate},
                hypothesis=f"promote '{task_type}' default from {bucket} to next tier up",
            ))

        # (c) Cheap model passing easily AND rarely escalating → maybe over-routed → route down
        if bucket != "simple" and pass_rate >= QUALITY_FLOOR and escal_rate < 0.05:
            findings.append(Finding(
                task_type, bucket,
                issue="high pass-rate with near-zero escalation; possibly over-provisioned",
                evidence={"pass_rate": pass_rate, "escalation_rate": escal_rate, "qpd": qpd},
                hypothesis=f"trial routing '{task_type}' one tier DOWN to cut cost",
            ))

        # (d) Looping / per-task cost blowup on a 'cheap' model (Gate F territory)
        if bucket == "simple" and median_cost(rows) > expected_cost(bucket) * 2:
            findings.append(Finding(
                task_type, bucket,
                issue="cheap-model per-task cost inflated (looping / retries)",
                evidence={"median_cost": median_cost(rows)},
                hypothesis="tighten Gate F output-sanity bound or swap cheap model for this task_type",
            ))

    return findings


# ----------------------------------------------------------------------------
# 3. PROPOSE — let the Architect model turn findings into concrete rule edits
# ----------------------------------------------------------------------------
def propose_changes(findings, current_rules):
    """
    The Architect model reads the diagnosis + current rules and emits a STRUCTURED
    diff (not prose) so changes are reviewable and reversible.
    """
    prompt = f"""
You are the Build Architect for the Hermes orchestration layer.
Objective: maximize quality_per_dollar subject to quality_pass_rate >= {QUALITY_FLOOR}.

Here are the current routing rules:
{serialize(current_rules)}

Here are data-backed findings from the benchmark log:
{serialize(findings)}

Propose specific, minimal changes as a JSON list of edits. Each edit:
  {{ "target": "<rule path e.g. task_type_routing.code_refactor.default_role>",
     "from": "<current value>",
     "to": "<proposed value>",
     "rationale": "<one line tied to the evidence>",
     "risk": "<what could regress>" }}
Only propose changes supported by the evidence. Prefer one-step moves.
Return ONLY the JSON list, no preamble.
"""
    raw = call_model(ARCHITECT_MODEL, prompt)
    return parse_json(raw)  # -> list[edit]


# ----------------------------------------------------------------------------
# 4. SANDBOX-TEST — validate proposed edits on the HELD-OUT set before promoting
# ----------------------------------------------------------------------------
def sandbox_test(edits, holdout_set, current_rules):
    candidate_rules = apply_edits(clone(current_rules), edits)

    baseline = run_strategy(current_rules,   tasks=holdout_set)  # re-run same tasks
    candidate = run_strategy(candidate_rules, tasks=holdout_set)

    return {
        "edits": edits,
        "baseline":  summarize(baseline),
        "candidate": summarize(candidate),
        "verdict": decide(baseline, candidate),
    }


def decide(baseline, candidate):
    # HARD GATE: never accept a drop below the quality floor, no matter the savings.
    if candidate["quality_pass_rate"] < QUALITY_FLOOR:
        return "REJECT — quality_pass_rate below floor"
    # Accept only a real quality_per_dollar improvement that doesn't regress quality.
    improved_qpd     = candidate["quality_per_dollar"] > baseline["quality_per_dollar"] * 1.02
    quality_held     = candidate["avg_quality_score"]  >= baseline["avg_quality_score"] - 0.01
    latency_sane     = candidate["avg_latency"]        <= baseline["avg_latency"] * 1.25
    if improved_qpd and quality_held and latency_sane:
        return "PROMOTE"
    return "HOLD — insufficient improvement or latency regression"


# ----------------------------------------------------------------------------
# 5. PROMOTE — open a PR against the rule files; humans review high-impact changes
# ----------------------------------------------------------------------------
def promote(result):
    if result["verdict"] == "PROMOTE":
        # md_files_are_plans_not_contracts: the Architect edits the source files
        # and opens a PR. Low-risk edits can auto-merge; high-risk wait for human.
        open_pull_request(
            files=["rules-and-gates.md", "skill-definitions.json", "architecture-schema.json"],
            edits=result["edits"],
            evidence=result,
            auto_merge=is_low_risk(result["edits"]),
        )
    else:
        log_rejected(result)  # keep rejected proposals — they're signal too


# ----------------------------------------------------------------------------
# MAIN LOOP — run on a cadence (e.g. nightly) or on-demand after a benchmark run
# ----------------------------------------------------------------------------
def architect_cycle():
    tune_set, holdout_set = ingest()
    current_rules = load_rules()
    current_skills = load_skills()

    # (1) tune routing thresholds from metrics
    findings = diagnose(tune_set)
    if findings:
        edits = propose_changes(findings, current_rules)
        for edit_batch in batch(edits, size=1):          # test one change at a time
            result = sandbox_test(edit_batch, holdout_set, current_rules)
            promote(result)
            if result["verdict"] == "PROMOTE":
                current_rules = load_rules()             # re-load after each promotion

    # (2) grow/prune planner skills from upward feedback (self-teaching loop)
    skill_proposals = synthesize_skills(tune_set, current_skills)
    if skill_proposals:
        apply_skill_proposals(skill_proposals)

    if not findings and not skill_proposals:
        log("No data-backed findings this cycle. Orchestration stable.")


def synthesize_skills(records, current_skills):
    """
    SELF-TEACHING PLANNER LOOP.
    Reads the `feedback` field from benchmark records (populated by tiers when they
    hit a bottleneck / missing context / skill gap), clusters recurring gaps, and
    proposes NEW planner skills (e.g. a question to ask up front) — and prunes skills
    that never fire. This is what makes the planner get smarter over time instead of
    just having its routing thresholds nudged.
    """
    # 1. gather only records that reported a skill gap
    gaps = [r.feedback for r in records if getattr(r, "feedback", None) and r.feedback.get("skill_gap")]
    if not gaps:
        return []

    # 2. cluster recurring gaps (same suggestion appearing >= N times = worth adding)
    clustered = cluster_by_suggestion(gaps)  # -> {suggestion: count}
    proposals = []
    for suggestion, count in clustered.items():
        if count >= 3 and suggestion not in current_skills["planner"]["learned_questions"]:
            proposals.append({
                "action": "add_planner_skill",
                "skill": suggestion,
                "evidence_count": count,
                "rationale": f"{count} tasks hit this gap; planner should ask this up front",
            })

    # 3. prune dead skills — learned questions that never changed an outcome
    for skill in current_skills["planner"].get("learned_questions", []):
        if skill_never_useful(skill, records):
            proposals.append({
                "action": "remove_planner_skill",
                "skill": skill,
                "rationale": "added previously but never affected an outcome; removing to keep planner lean",
            })

    # 4. the Architect model turns proposals into a regenerated planner prompt,
    #    sandbox-tested like any other change before promotion.
    return proposals


def apply_skill_proposals(proposals):
    # Update skill-definitions.json -> planner.learned_questions, then regenerate the
    # planner's system prompt from it. Skills are DATA; the prompt is built from data.
    for p in proposals:
        sandbox = sandbox_test_skill(p)          # does adding/removing this skill help?
        if sandbox["verdict"] == "PROMOTE":
            update_skill_file(p)                  # edit skill-definitions.json
            regenerate_planner_prompt()           # rebuild planner system prompt from skills
            open_pull_request(files=["skill-definitions.json"], edits=[p], evidence=sandbox)
        else:
            log_rejected(p)


if __name__ == "__main__":
    architect_cycle()

# ----------------------------------------------------------------------------
# Why it's built this way
# ----------------------------------------------------------------------------
# - Diagnose from DATA, not intuition. Every proposed change cites evidence.
# - One change at a time, validated on a HELD-OUT set → you can attribute the win
#   (or regression) to a specific edit instead of a tangle of simultaneous tweaks.
# - The quality floor is a hard gate in decide(): cost can never buy its way past
#   a quality regression. This is what stops the system optimizing itself into a
#   cheap-but-broken local minimum.
# - Rejected proposals are logged. A pattern of rejections is itself a signal that
#   a task_type needs a human rethink, not an automated nudge.
# - Humans stay in the loop on high-risk edits. The system tunes itself; it does
#   not silently rewrite the rules that govern high-stakes work.
