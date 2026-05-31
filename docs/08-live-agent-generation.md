# Live Agent Generation

## Goal

Support provider-backed generation while keeping deterministic mock mode for CI
and offline development.

```text
same scenario + user message
  -> resolve generation mode (mock | live | auto)
  -> mock: existing LangGraph template nodes
  -> live: structured artifacts + runnable response
  -> evals score the final response either way
```

## Generation Modes

| Mode | When | Behavior |
|---|---|---|
| `mock` | CI, offline dev | Deterministic artifacts + template response |
| `live` | Explicit local runs | OpenAI artifact generation + LLM draft response |
| `auto` | Default | `live` if `OPENAI_API_KEY` is set, else `mock` |

Environment variables:

```bash
OPENAI_API_KEY=sk-...
AGENT_GENERATION_MODE=auto   # mock | live | auto
AGENT_MODEL=gpt-4o-mini      # optional
```

## Architecture

### Mock path

- Deterministic design scaffold creates rules, eval contract, requirements,
  tool blockers, graph design, and eval suite.
- Local draft agent runs use deterministic formatters in mock mode.
- CI and local tests stay offline and provider-key-free.

### Live path

1. **Structured artifact generation** — the builder asks the model for an
   expanded target, behavior rules, eval metrics/gates, information
   requirements, tool requirements, graph designs, and bounded fix plans.
2. **Artifact normalization** — the response is parsed as JSON, repaired into
   the expected local artifact shape, and validated before YAML is written.
3. **Draft response generation** — `Run v0` and `Run v1` call the live model for
   the final response when generation mode resolves to `live`.
4. **Evaluation** — evals score the produced response. Hybrid/LLM judging can be
   used when live generation is active.
5. **Progress events** — live builder create/action calls stream
   prompt/model/validation status before the blocking provider call completes,
   then stream written artifacts when YAML is available.

The React builder passes generation mode to `Create draft`, `Generate design`,
`Create fix plan`, `Generate v1 graph`, `Run v0`, and `Run v1`. In `auto`, those
steps use live generation when `OPENAI_API_KEY` is available and fall back to
mock otherwise.

## Key Files

| File | Role |
|---|---|
| `src/edd_agent_lab/agents/generation.py` | Mode resolution + model factory |
| `src/edd_agent_lab/ui/workspace_store.py` | Builder design scaffold, normalization, run artifacts |
| `src/edd_agent_lab/api/builder.py` | Local API and streamed workflow actions |
| `src/edd_agent_lab/agents/customer_solution_agent/live_generation.py` | Live draft + chat generation |
| `src/edd_agent_lab/agents/customer_solution_agent/prompts.py` | Version policy prompts |
| `src/edd_agent_lab/agents/customer_solution_agent/runner.py` | Mock vs live orchestration |
| `tests/conftest.py` | Forces `AGENT_GENERATION_MODE=mock` in pytest |

## Usage

```bash
uv sync --extra dev --extra agent --extra web

# Deterministic (no API key)
AGENT_GENERATION_MODE=mock edd-lab run-agent \
  --agent customer-solution --version v1 --scenario healthcare_documentation

# Live generation
export OPENAI_API_KEY=sk-...
edd-lab run-agent \
  --agent customer-solution --version v1 --scenario healthcare_documentation \
  --generation-mode live
```

Builder usage:

```bash
export OPENAI_API_KEY=sk-...
export AGENT_GENERATION_MODE=auto

uv run --extra web --extra agent \
  uvicorn edd_agent_lab.api.builder:app --host 127.0.0.1 --port 8002

cd web/agent-builder
npm run dev
```

Open `http://localhost:5173`, keep generation mode on `Auto` or select `Live`,
then create a draft and use `Generate design`, `Create fix plan`,
`Generate v1 graph`, `Run v0`, and `Run v1`.

## Testing Strategy

- All existing tests run in **mock** mode via `tests/conftest.py`
- `tests/test_live_generation.py` patches live generators to avoid network calls
- `tests/test_workspace_store.py` patches live builder models and verifies
  normalized target, design, fix-plan, and v1 graph artifacts validate
- Eval suites continue to score whichever response path produced the output

## What Is Still Not Live

- Tool use is not connected to live external systems; draft tool mode remains
  `local_draft`.
- LangGraph nodes are not individually LLM-backed in live mode.
- Platform publish still depends on the configured platform boundary.

## Next Steps

1. Add token streaming for live candidate responses.
2. Add per-node LLM calls inside LangGraph for trace granularity.
3. Verify platform ingest end to end with a live-generated draft.
