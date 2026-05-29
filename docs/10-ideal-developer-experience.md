# Ideal Developer Experience (Target DX)

This document describes the **target** agent developer experience when **edd-agent-lab** and **eval-driven-design-platform** work as one system.

For the current gap, see `09-developer-experience-today.md`.

---

## One-line goal

**Build and compare agent versions in the lab; promote evidence to the platform; decide with gates and history — mostly without leaving the console.**

---

## Target architecture

```text
Developer
   │
   ├─ edd-agent-lab console (:8502)     ← primary daily UI
   │     run agents · chat · eval · compare · publish
   │
   ├─ edd-agent-lab CLI                 ← CI, scripting, power users
   │
   v
eval-driven-design-platform (:8501 / :8000)
   run registry · gates · cross-team history · Langfuse orchestration
   │
   v
Langfuse
   traces · scores · datasets · experiments
```

**Rule unchanged:** lab never talks to Langfuse directly.

---

## Ideal day in the life

### Morning: pick up where you left off

1. Open `edd-lab console` → **Sessions** lists recent runs (local + synced platform runs).
2. Resume yesterday’s side-by-side session or start **New comparison** (v0 vs v1, scenario, suite).
3. Sidebar shows: generation mode, eval suite, **last publish status**, platform run link if published.

### Iterate on behavior

4. Send multi-turn messages (discovery script); watch **turn scores** and **session rollup** update live.
5. Toggle **Mock** for fast structural checks, **Live** for realistic language — same session, labeled per turn which mode was used.
6. **Inspect check failures** inline: which rubric item failed, suggested fix hint, link to failure packet.

### Validate before promoting

7. Click **Run suite on this session** (or on scenario) — executes `discovery_quality` + `overfitting` from UI, not only CLI.
8. Console shows suite scorecard: pass/fail per case, overall score, regression vs last published v1.
9. If improved → **Publish to platform** button sends envelope; platform returns **ExperimentRun id** and gate status.

### Decide in platform

10. Switch to platform `:8501` **Results Explorer** — lab-published run appears next to native experiment runs.
11. Compare v0 vs v1 across scenarios and time; drill to Langfuse trace if live run emitted one.
12. Gate passes → tag `v1-discovery-graph` as **accepted** for scenario set; CI uses same gate on PR.

### CI (unchanged principle)

```bash
AGENT_GENERATION_MODE=mock pytest
edd-lab run-evals --version v1 --suite discovery_quality  # fail if score drops
```

---

## Ideal lab console (expanded)

The console becomes the **control room**, not just a chat demo.

### A. Comparison workspace (exists today — extend)

| Feature | Today | Ideal |
|---|---|---|
| Side-by-side chat | ✅ | ✅ |
| Mock / Live toggle | ✅ | ✅ + per-turn mode badge |
| Turn analysis | ✅ latest only | ✅ any turn selectable |
| Session rollup | ✅ | ✅ + trend sparkline |
| Session resume | ✅ local | ✅ + search/filter |

### B. Eval panel (mostly missing)

- **Run eval suite** from UI (suite picker, version pair)
- Suite scorecard with case breakdown
- Diff vs last published run (same suite)
- Link to `failure-packet` with fix hints
- **Hybrid judge** in live mode (structure + LLM rubric)

### C. Promotion panel (missing — needs platform ingest)

- **Publish session** or **Publish eval run** to platform
- Show publish status: `published` | `queued` | `failed`
- Deep link to platform ExperimentRun
- **Gate result** inline (pass / fail / insufficient evidence)

### D. Agent workspace (future)

- View active graph version and policy summary (read-only)
- “Open in IDE” deep link to `graph.py` / prompts
- Optional: trigger **lab run** that writes full brief artifact (not chat-only)

### E. Scenario & script helpers (partial)

- **Send scenario as first message** ✅
- Saved **conversation scripts** (e.g. 4-turn discovery playbook) one-click
- Scenario switch warning if mid-session

### F. Observability bridge (platform-owned)

- “View in Langfuse” on live turns (via platform URL, not direct SDK)
- Trace id on turn artifact when platform records it

---

## Ideal CLI (still required)

Console covers daily work; CLI remains for:

- CI pipelines and quality gates
- Batch eval across all scenarios
- Scripting and MCP automation
- Headless publish after merge

```bash
edd-lab run-evals --version v1 --suite discovery_quality --publish --fail-under 0.75
```

---

## Platform-side work (required for ideal DX)

### 1. Lab ingest API (priority)

```http
POST /v1/integrations/lab/publish
```

Accept lab envelope (`schema_version: "1"`) and:

- Create or update **ExperimentRun** (or LabRun registry entity)
- Store eval summary, failure packet, outputs
- Return `platform_run_id`, gate status
- Optionally create Langfuse trace/score stubs

See `05-platform-integration.md` for envelope fields.

### 2. Run registry UI

- Filter runs by `source=edd-agent-lab`, agent, version, suite
- Compare two published lab runs (same as platform ExperimentRun compare)
- Show link back to lab session id if present in envelope

### 3. Quality gates

- Gate on published lab eval summary (threshold per suite)
- Block “accept version” if overfitting suite regresses

### 4. MCP (optional)

- Platform exposes `edd.compare_runs`, `edd.get_gate_status` for external agents
- Lab MCP delegates to platform when `EDD_MCP_SERVER_URL` set

---

## Agent-lab work (console-first DX)

| Item | Repo | Priority |
|---|---|---|
| Platform lab ingest endpoint | platform | **P0** |
| E2E publish verification | lab + platform | **P0** |
| Console: Run eval suite | lab | P1 |
| Console: Publish + gate status | lab | P1 |
| Hybrid turn eval (live mode) | lab | P1 |
| Console: per-turn history picker | lab | P2 |
| Console: conversation scripts | lab | P2 |
| Publish console session envelope | lab | P2 |
| Per-node LLM traces in live graph | lab | P3 |

---

## Success criteria (“we nailed DX”)

1. Developer can complete **v0 → v1 compare → suite pass → publish → gate green** without reading JSON in `lab-runs/`.
2. Platform shows lab runs alongside native experiment runs with comparable UI.
3. Mock stays default in CI; live is one toggle away with clear labeling.
4. Side-by-side console is the default demo and daily driver; CLI is for automation.
5. Langfuse traces for live runs are reachable from platform, not configured in lab.

---

## Phased rollout

### Phase A — Close the platform gap

- Implement `POST /v1/integrations/lab/publish`
- Lab `edd-lab publish-run` succeeds against local platform stack
- Platform Results Explorer shows ingested run

### Phase B — Console eval + publish

- Run suite from console
- Publish button + status + platform link
- Session rollup + suite score on same page

### Phase C — Polish + team readiness

- Conversation scripts, turn history, hybrid judge
- Gate enforcement in CI referencing platform run ids
- Docs + demo script updated (`06-demo-script.md`)

---

## Related docs

| Doc | Topic |
|---|---|
| `09-developer-experience-today.md` | Current DX |
| `05-platform-integration.md` | Publish contract |
| `07-final-milestone-side-by-side-console.md` | Console milestone spec |
| `eval-driven-design-platform/EVAL_DRIVEN_DESIGN_PLAN.md` | Platform phases |
