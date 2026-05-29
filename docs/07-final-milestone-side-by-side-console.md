# Final Milestone: Side-by-Side Agent Comparison Console

## Goal

Build a full local UI in `edd-agent-lab` that lets a user interact with two agent versions side by side and see turn-level EDD analysis after each message.

This is the final lab milestone and should make the full EDD story visible:

```text
same user message
  -> v0 responds
  -> v1 responds
  -> each response is scored
  -> UI explains score differences and regressions
  -> turn/session artifacts are written for future platform ingestion
```

## Product Boundary

This is a local lab console, not the durable platform console.

```text
edd-agent-lab
  owns:
    local side-by-side chat
    local agent execution
    turn-level EDD analysis
    local artifacts

eval-driven-design-platform
  owns:
    reusable run registry
    durable comparison history
    quality gates
    Langfuse integration
    MCP tools
    long-term decision history

Langfuse
  owns:
    traces
    scores
    datasets
    experiments
    prompt/run observability
```

Important:

- Do not add direct Langfuse integration to `edd-agent-lab`.
- Do not require `eval-driven-design-platform` to be running.
- Do not implement MCP in this milestone.

## Roadmap Update Target

```markdown
| Milestone | Status |
|---|---|
| 1 — Repo skeleton, CLI, loaders, tests | Complete |
| 2 — v0 LangGraph agent + `run-agent` | Complete |
| 3 — Eval runner + `run-evals` | Complete |
| 4 — v1 discovery graph | Complete |
| 5 — Overfitting eval | Complete |
| 6 — Competency model | Complete |
| 7 — EDD platform client | Complete |
| 8 — MCP integration | Complete |
| 9 — Side-by-side agent comparison console | Final milestone |
```

Add README section title:

`## Side-by-Side Agent Comparison Console`

## Preferred UI Stack

Use Streamlit.

Add optional dependency group:

```toml
[project.optional-dependencies]
ui = [
  "streamlit>=1.0.0"
]
```

UI entrypoint:

`src/edd_agent_lab/ui/app.py`

CLI command:

`edd-lab console`

Acceptable behavior:

- launch Streamlit directly, or
- print:
  `streamlit run src/edd_agent_lab/ui/app.py`

## Console Layout

### Region 1 — Control Bar

Controls:

- Agent (initially customer-solution)
- Scenario (load from `scenarios/customer_solution_agent/*.yml`)
- Eval suite (load from `evals/customer_solution_agent/*.yml`)
- Left version (v0-baseline, v1-discovery-graph, future versions)
- Right version (same)
- Message input
- Buttons:
  - Send to Both
  - Use Scenario Problem
  - Clear Session
  - Save Session (optional)

### Region 2 — Side-by-Side Chats

Two aligned columns:

- left version transcript
- right version transcript

Each panel should show:

- version name
- full transcript
- latest response
- turn score + pass/fail
- top strengths
- top gaps
- expandable check details

### Region 3 — Turn-Level EDD Analysis

Show for latest turn:

- v0 score
- v1 score
- delta
- decision
- improved checks
- regressed checks
- unchanged checks
- short explanation

### Region 4 — Evidence + Artifacts

Show generated files and path:

- `turn-evaluation.json`
- `turn-comparison.json`
- `turn-comparison.md`

Also show raw JSON expanders for latest turn evaluation/comparison.

## Turn-Level Schemas

Create:

`src/edd_agent_lab/evals/turn_schemas.py`

Models to include:

- `TurnCheckResult`
- `TurnVersionResult`
- `TurnEvaluation`
- `TurnComparison`

Normalize scores to `[0.0, 1.0]`.

## Turn Evaluator

Create:

`src/edd_agent_lab/evals/turn_evaluator.py`

Function:

`evaluate_turn(agent, scenario_id, suite_id, user_input, responses_by_version) -> TurnEvaluation`

Responsibilities:

1. Load selected suite.
2. Evaluate each version response.
3. Produce per-version overall score.
4. Produce check-level evidence.
5. Include gaps + fix hints for weak checks.
6. Return `TurnEvaluation`.

Heuristic scoring is acceptable in this milestone (no live LLM required).

Checks to support:

- `asks_clarifying_questions`
- `identifies_workflow`
- `defines_success_metrics`
- `includes_risks`
- `proposes_eval_plan`

Each check must include human-readable evidence.

## Turn Comparison Logic

Create:

`src/edd_agent_lab/evals/turn_comparison.py`

Function:

`compare_turn_evaluation(evaluation, before_version, after_version) -> TurnComparison`

Decision rules:

- if score missing: `insufficient evidence`
- if delta >= 0.15 and no major regressions: `after version is better for this turn`
- if delta <= -0.10: `after version regressed for this turn`
- if abs(delta) < 0.05: `no meaningful difference`
- else: `mixed result`

Major regression: any applicable check dropping by `>= 0.20`.

## Artifact Writing

Per turn:

`lab-runs/customer_solution_agent/console-sessions/<session_id>/turns/<turn_id>/`

Files:

- `turn-evaluation.json`
- `turn-comparison.json`
- `turn-comparison.md`

Per session:

`lab-runs/customer_solution_agent/console-sessions/<session_id>/session.json`

Include turn summary entries with:

- `turn_id`
- `user_input`
- `artifact_dir`
- `before_score`
- `after_score`
- `score_delta`
- `decision`

## Reusable Execution Path

Do not duplicate runner logic in UI.

Preferred runner signature:

```python
def run_customer_solution_agent(
    scenario_id: str,
    agent_version: str,
    user_message: str | None = None,
    write_artifacts: bool = True,
) -> dict:
    ...
```

Return should include:

- `agent`
- `agent_version`
- `scenario_id`
- `final_response`
- `artifact_path`

## UI Module Structure

Create:

```text
src/edd_agent_lab/ui/
  __init__.py
  app.py
  components.py
```

Suggested helpers:

- `render_control_bar()`
- `render_chat_panel(version, messages, latest_eval_result=None)`
- `render_turn_analysis(comparison, evaluation)`
- `render_artifacts_panel(artifact_dir, evaluation, comparison)`

Use `st.session_state` for:

- `session_id`
- `left_messages`
- `right_messages`
- `turns`
- `latest_evaluation`
- `latest_comparison`

## CLI Additions

1. `edd-lab console`
2. `edd-lab compare-turn --agent ... --scenario ... --suite ... --before ... --after ... [--message ...]`

`compare-turn` responsibilities:

1. load scenario problem if message missing
2. run both versions
3. evaluate both responses
4. compare
5. write same turn artifacts
6. print score summary + decision

## Tests Required

Add:

- `tests/test_turn_schemas.py`
- `tests/test_turn_evaluator.py`
- `tests/test_turn_comparison.py`
- `tests/test_compare_turn_cli.py`
- `tests/test_console_artifacts.py`

Test targets:

1. schema JSON serialization
2. weak checks include `gap` + `fix_hint`
3. strong checks include positive evidence
4. improved/regressed check detection
5. decision rule behavior
6. CLI `compare-turn` writes artifacts
7. session writer creates `session.json` and turn dirs
8. no live LLM requirement for tests

## Acceptance Checklist

```bash
pip install -e ".[dev,agent,ui]"
python -m compileall src tests
pytest
edd-lab compare-turn \
  --agent customer-solution \
  --scenario healthcare_documentation \
  --suite discovery_quality \
  --before v0 \
  --after v1
edd-lab console
```

Console must allow user to:

1. select scenario
2. select suite
3. select left/right versions
4. send same message to both
5. view side-by-side responses
6. view per-version turn score
7. view why each scored that way
8. view improved checks + regressions
9. view decision
10. locate turn/session artifacts

## Out of Scope (Do Not Add Here)

- direct Langfuse integration
- dependency on running EDD platform
- MCP integration
- durable platform-side registry
- auth
- multi-user
- cloud deployment

## Product Intent

A change is not accepted because it *sounds* better.
It is accepted because side-by-side behavior improves under explicit evaluation criteria with written evidence.
