# Milestone 10: Live Agent Generation

## Goal

Replace template-only agent behavior with **OpenAI-backed generation** while keeping deterministic mock mode for CI and offline development.

```text
same scenario + user message
  -> resolve generation mode (mock | live | auto)
  -> mock: existing LangGraph template nodes
  -> live: structured discovery draft + chat/brief response
  -> evals score the final response either way
```

## Generation Modes

| Mode | When | Behavior |
|---|---|---|
| `mock` | CI, offline dev | Existing LangGraph nodes + template chat formatter |
| `live` | Explicit production runs | OpenAI structured discovery + LLM chat/brief |
| `auto` | Default | `live` if `OPENAI_API_KEY` is set, else `mock` |

Environment variables:

```bash
OPENAI_API_KEY=sk-...
AGENT_GENERATION_MODE=auto   # mock | live | auto
AGENT_MODEL=gpt-4o-mini      # optional
```

## Architecture

### Mock path (unchanged)

- LangGraph topology demonstrates v0 / v1 / v3 policy differences
- Deterministic node templates fill `CustomerSolutionState`
- Console chat uses template formatter in mock mode

### Live path (new)

1. **Structured discovery draft** — one LLM call with version-specific policy prompt
2. **State materialization** — draft mapped into `CustomerSolutionState`
3. **Response generation**
   - `brief` mode: render markdown brief from state
   - `chat` mode: second LLM call grounded in state + conversation history

Version behavior is enforced through policy prompts in `prompts.py`, not separate template strings.

## Key Files

| File | Role |
|---|---|
| `src/edd_agent_lab/agents/generation.py` | Mode resolution + model factory |
| `src/edd_agent_lab/agents/customer_solution_agent/live_generation.py` | Live draft + chat generation |
| `src/edd_agent_lab/agents/customer_solution_agent/prompts.py` | Version policy prompts |
| `src/edd_agent_lab/agents/customer_solution_agent/runner.py` | Mock vs live orchestration |
| `tests/conftest.py` | Forces `AGENT_GENERATION_MODE=mock` in pytest |

## Usage

```bash
pip install -e ".[dev,agent,ui]"

# Deterministic (no API key)
AGENT_GENERATION_MODE=mock edd-lab run-agent \
  --agent customer-solution --version v1 --scenario healthcare_documentation

# Live generation
export OPENAI_API_KEY=sk-...
edd-lab run-agent \
  --agent customer-solution --version v1 --scenario healthcare_documentation \
  --generation-mode live

# Console: auto uses live when key is present
edd-lab console
```

## Testing Strategy

- All existing tests run in **mock** mode via `tests/conftest.py`
- `tests/test_live_generation.py` patches live generators to avoid network calls
- Eval suites continue to score whichever response path produced the output

## What Is Still Not Live

- Turn eval checks remain heuristic/pattern-based by default (LLM judge optional)
- Platform publish endpoint on eval-driven-design-platform is still a seam
- LangGraph nodes are not individually LLM-backed in live mode (single structured draft call instead)

## Next Steps (Phase 11+)

1. Per-node LLM calls inside LangGraph for trace granularity
2. ~~Session persistence outside Streamlit `session_state`~~ (see session resume in console)
3. Hybrid turn eval (structure checks + LLM judge by default in live mode)
4. Platform ingest verification end-to-end

Console sessions persist under `lab-runs/customer_solution_agent/console-sessions/<session_id>/session.json` with full chat transcripts and turn summaries. Resume via sidebar or `?session_id=` query param.
