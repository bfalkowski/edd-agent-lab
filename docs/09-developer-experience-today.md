# Developer Experience Today

This document describes how an agent developer actually works with **edd-agent-lab** and **eval-driven-design-platform** **right now** — not the target state.

For integration boundaries, see `05-platform-integration.md`. For live vs mock generation, see `08-live-agent-generation.md`.

---

## Mental model

You are running two related but mostly **separate** tools:

| Tool | Port | Role today |
|---|---|---|
| **edd-agent-lab** | `:8502` (console), CLI | Build agents, run local evals, compare versions in chat |
| **eval-driven-design-platform** | `:8501` (console), `:8000` (API) | EvalSpec / EvalCase / ExperimentRun workflow, Langfuse adapter |

The intended direction is `lab → platform → Langfuse`. **The lab publish seam exists; platform ingest does not yet.**

---

## Day-one setup

```bash
cd edd-agent-lab
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,agent,ui]"
cp .env.example .env
# Optional: OPENAI_API_KEY for live generation
```

Platform (separate repo):

```bash
cd eval-driven-design-platform
# Follow README / scripts/local_e2e.sh for API + console on :8000 / :8501
```

There is **no single command** that starts both stacks and wires them together.

---

## Primary workflow: CLI-first

Most engineering work happens in the terminal.

### 1. Run an agent version

```bash
edd-lab run-agent \
  --agent customer-solution \
  --version v1 \
  --scenario healthcare_documentation \
  --generation-mode mock   # or live with OPENAI_API_KEY
```

Writes artifacts under `lab-runs/customer_solution_agent/v1-discovery-graph/`.

### 2. Score with an eval suite

```bash
edd-lab run-evals \
  --agent customer-solution \
  --version v1 \
  --suite discovery_quality
```

Produces `eval-summary-*.json` and optionally `failure-packet-*.json`.

### 3. Compare versions (CLI)

```bash
edd-lab compare-turn \
  --scenario healthcare_documentation \
  --before v0 --after v1
```

### 4. Check overfitting

```bash
edd-lab run-evals --version v1 --suite overfitting
```

### 5. Publish (seam only)

```bash
edd-lab publish-run --agent customer-solution --version v1
# or: edd-lab run-evals ... --publish
```

**Today:** if the platform API is not running or ingest is missing, envelopes land in `lab-runs/_platform_publish_queue/` — not in the platform UI.

---

## Secondary workflow: side-by-side console

```bash
edd-lab console   # http://localhost:8502
```

**Good for:**

- Same prompt → two agent versions → scored replies
- Multi-turn discovery conversations
- Turn-level analysis (latest turn)
- Session score rollup (average across turns)
- Session resume (`?session_id=` or sidebar picker)
- **Mock / Live toggle** in sidebar

**Not good for (yet):**

- Editing agent code or graph
- Running full eval suites from the UI
- Publishing to platform
- Viewing Langfuse traces
- Team-wide run history (sessions are local files)

Console artifacts: `lab-runs/customer_solution_agent/console-sessions/<session_id>/`.

---

## Generation modes

| Mode | Where set | Behavior |
|---|---|---|
| **Mock** | Console toggle or `--generation-mode mock` | Deterministic LangGraph templates + chat formatter |
| **Live** | Console toggle or `--generation-mode live` | OpenAI structured discovery + chat (needs API key) |
| **Auto** | `AGENT_GENERATION_MODE=auto` in env | Live if key present, else mock (CLI default when unset) |

CI / pytest always forces mock via `tests/conftest.py`.

---

## What “evidence” looks like on disk

```text
lab-runs/customer_solution_agent/
  v0-baseline/
    run-record.json
    eval-summary-discovery_quality.json
    failure-packet-*.json
    agent-output.json
  console-sessions/
    <session_id>/
      session.json              # chat + turn summaries
      turns/<turn_id>/
        turn-evaluation.json
        turn-comparison.json
  _platform_publish_queue/      # when publish cannot reach platform
```

You inspect JSON manually or via CLI output. There is no unified “run explorer” in the lab.

---

## Platform workflow today (parallel path)

On **eval-driven-design-platform** `:8501`:

1. Define **EvalSpec** (what good means)
2. Add **EvalCases** (manual or Langfuse import)
3. Run **ExperimentRun** against a candidate version
4. Review results in Results Explorer
5. Quality gates — planned, not fully enforced

This workflow uses the **platform’s own scaffold/evaluator**, not lab LangGraph agents. Lab run records do **not** automatically appear here.

---

## MCP seam (lab)

```bash
edd-lab invoke-mcp --tool edd.run_eval_suite --args '{"suite":"discovery_quality"}'
edd-lab invoke-mcp --tool edd.publish_run --args '{"run_record":"..."}'
```

Local shims today; remote MCP server optional via `EDD_MCP_SERVER_URL`.

---

## Friction points (honest)

1. **Two consoles, two mental models** — `:8502` chat comparison vs `:8501` experiment workflow.
2. **Auth wiring for publish** — `local_e2e.sh` enables platform auth; lab publish needs `EDD_API_KEY` unless the smoke script auto-mints a JWT.
3. **Console vs CLI for promotion** — lab console has eval suite + publish panel, but durable registry and gates live on platform `:8501`.
4. **Mock vs live confusion** — easy to demo in mock and think behavior is “real.”
5. **Turn eval is heuristic** — pattern checks unless LLM judge is wired for that path.
6. **No in-console agent editing** — code changes still happen in IDE + terminal rerun.
7. **Console sessions are local** — not shared via platform or team dashboard.

---

## What works well today

- Clear **v0 / v1 / v3** graph story and local eval suites
- **Deterministic CI** with mock generation
- **Side-by-side chat** with session persistence and rollup scores
- **Publish envelope contract** and live HTTP ingest to platform (`POST /v1/integrations/runs/publish`)
- **Overfitting suite** to catch brittle “fixes”

---

## Related docs

| Doc | Topic |
|---|---|
| `03-evaluation-driven-design.md` | EDD principles |
| `05-platform-integration.md` | Ownership + publish envelope |
| `07-final-milestone-side-by-side-console.md` | Console spec |
| `08-live-agent-generation.md` | Mock / live / auto |
| `10-ideal-developer-experience.md` | Target DX |
