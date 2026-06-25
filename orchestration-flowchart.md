# Orchestration Flowcharts

Mermaid renders natively on GitHub. To export an image: paste into
[mermaid.live](https://mermaid.live) → download SVG/PNG.

---

## 1. Full request lifecycle

```mermaid
flowchart TD
    U([User task]) --> P{{"TIER 1 — PLANNER<br/>GLM-5.2"}}

    P --> A{"Gate A<br/>enough context?"}
    A -- no --> ASK[Ask user a<br/>clarifying question]
    ASK --> U
    A -- yes --> B["Gate B<br/>score complexity 0-10"]

    B --> S0{complexity?}
    S0 -- "0-3 simple" --> EX1["EXECUTOR<br/>DeepSeek V3 / Gemini Flash"]
    S0 -- "4-6 medium" --> EX2["EXECUTOR<br/>Claude Sonnet 4.6 / GLM-5.2"]
    S0 -- "7-10 hard" --> EX3["EXECUTOR<br/>Opus 4.8 / GPT-5.4 (collab)"]

    EX1 --> MO{{"TIER 2.5<br/>MICRO-ORCHESTRATOR"}}
    EX2 --> MO
    EX3 --> MO

    MO --> D{"Gates C+D+F<br/>confidence ok?<br/>lint/type pass?<br/>output sane?"}
    D -- "fail, local-fixable" --> FIX["one fixer shot<br/>(cheaper sibling)"]
    FIX --> D
    D -- "fail, bigger than expected" --> CB["callback to Planner<br/>'actual N/10'"]
    CB --> B
    D -- pass --> V{{"TIER 3 — VERIFIER"}}

    V --> H{"Gate H<br/>high-stakes?"}
    H -- yes --> HUMAN[Human review gate]
    HUMAN --> DONE([Commit / return])
    H -- no --> DONE

    classDef planner fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef exec fill:#1f4d2e,stroke:#52b788,color:#fff
    classDef micro fill:#5f3a1e,stroke:#d98a4a,color:#fff
    classDef verify fill:#4a2d5f,stroke:#a455d9,color:#fff
    classDef gate fill:#2b2b2b,stroke:#888,color:#fff
    class P planner
    class EX1,EX2,EX3 exec
    class MO,FIX micro
    class V verify
    class A,B,D,H,S0 gate
```

---

## 2. Tier hierarchy + who talks to whom

```mermaid
flowchart TB
    subgraph T0["TIER 0 — runs occasionally, NOT in hot path"]
        ARCH["Build Architect / Manager<br/>Claude Opus 4.8<br/>reads benchmarks → rewrites rules"]
    end

    subgraph HOT["REQUEST HOT PATH"]
        direction TB
        PL["TIER 1 — Planner<br/>GLM-5.2"]
        WK["TIER 2 — Executors<br/>routed by complexity"]
        MI["TIER 2.5 — Micro-Orchestrator<br/>1 reroute or 1 callback"]
        VE["TIER 3 — Verifier"]
        PL --> WK --> MI --> VE
        MI -. callback .-> PL
    end

    subgraph FB["FAILOVER — only on outage"]
        OR["OpenRouter catch-all"]
    end

    LOG[("Benchmark log<br/>task, complexity, cost,<br/>quality, latency, escalations")]

    HOT --> LOG
    LOG --> ARCH
    ARCH -. proposes rule/threshold changes .-> HOT
    HOT -. provider down .-> FB

    classDef arch fill:#5f1e1e,stroke:#d94a4a,color:#fff
    classDef hot fill:#1e3a5f,stroke:#4a90d9,color:#fff
    classDef fb fill:#3a3a1e,stroke:#d9d94a,color:#fff
    classDef log fill:#2b2b2b,stroke:#888,color:#fff
    class ARCH arch
    class PL,WK,MI,VE hot
    class OR fb
    class LOG log
```

---

## 3. Fallback chain (provider bouncing)

What happens when a provider crashes mid-task — chains hop between
**independent providers** so one outage never stalls the pipeline.

```mermaid
flowchart LR
    REQ([planner call]) --> G1{GLM-5.2 up?}
    G1 -- yes --> OK([proceed])
    G1 -- "timeout / 5xx" --> D1{DeepSeek V4 Flash up?}
    D1 -- yes --> OK
    D1 -- "down" --> H1{Claude Haiku up?}
    H1 -- yes --> OK
    H1 -- "down" --> ORF["OpenRouter<br/>(cost penalty accepted)"]
    ORF --> OK

    classDef ok fill:#1f4d2e,stroke:#52b788,color:#fff
    classDef fb fill:#3a3a1e,stroke:#d9d94a,color:#fff
    class OK ok
    class ORF fb
```

---

## 4. Collaborative debug (Gate G) — only when an executor is stuck

```mermaid
sequenceDiagram
    participant E as Executor (Sonnet)
    participant M as Micro-Orchestrator
    participant G as GPT-5.4
    Note over E: writes code, hits a wall
    E->>M: "stuck on edge case X" (confidence low)
    M->>M: Gate G — is this collab-worthy?
    alt high-stakes / hard
        M->>G: here is Sonnet's attempt + the blocker
        G->>E: reasoning on likely cause + fix
        E->>E: revise with GPT's input
        E->>M: revised output
    else simple
        M->>E: one local fixer shot instead
    end
    M->>M: re-run Gates C/D/F
```
