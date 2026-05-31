# Functional Application Plan

This plan tracks the work needed to turn `edd-agent-lab` from a local prototype
and reference workshop into a functional application for creating, running,
evaluating, comparing, and publishing agents.

## Goal

Make `edd-agent-lab` a usable local workbench where someone can:

1. Create a new agent from scratch.
2. Define target behavior.
3. Generate and review rules, evals, requirements, tools, and graph design.
4. Run v0.
5. Evaluate v0.
6. Generate a bounded fix plan.
7. Create and run v1.
8. Compare v0 vs v1.
9. Publish evidence to the platform.
10. Eventually persist canonical workflow state in platform/Postgres.

## Phase 1: Make Local Greenfield Flow Complete

- [x] Create local agent draft from name and description.
- [x] Save `agent-target.yaml`.
- [x] Scaffold draft rules/eval/requirements/tools/graph.
- [x] Add first local scenario.
- [x] Run deterministic `v0-baseline`.
- [x] Evaluate v0 locally.
- [x] Generate local failure packet.
- [ ] Add editable forms for target/rules/eval/requirements instead of YAML-only display.
- [ ] Add "Save changes" for edited draft artifacts.
- [ ] Add validation errors for incomplete draft artifacts.
- [ ] Add draft workspace selector/rename/delete/archive.
- [x] Add clear "local only, not platform persisted" status.

## Phase 2: Generate v1 From Failure

- [x] Generate a bounded fix plan from the v0 failure packet.
- [x] Save `fix-plan.yaml`.
- [x] Generate `graph-design-v1.yaml`.
- [x] Generate deterministic `v1` response path.
- [x] Run v1 against same scenario.
- [x] Evaluate v1.
- [x] Compare v0 vs v1.
- [x] Show side-by-side outputs for greenfield agents, not only reference demo.
- [x] Show verdict: what failed, what changed, what remains blocked.

## Phase 3: Make It Feel Like an App

- [ ] Replace giant single Start page with step navigation:
  - Target
  - Rules
  - Eval Contract
  - Requirements
  - Tools
  - Graph
  - Run
  - Evaluate
  - Compare
  - Publish
- [x] Add progress/status indicators for each step.
- [ ] Add compact artifact cards with edit/review states.
- [x] Add "next recommended action" panel.
- [ ] Reduce raw YAML exposure to an advanced/details view.
- [ ] Improve Streamlit styling toward a focused developer workbench.
- [ ] Add empty, loading, success, failure states.

## Phase 4: Real Persistence Boundary

- [ ] Define platform API endpoints needed for greenfield authoring:
  - create agent target
  - create behavior rules
  - create eval contract
  - create information requirements
  - create tool requirements
  - create graph design
  - create failure packet
  - create fix plan
  - create comparison
- [ ] Decide which objects remain local drafts vs platform canonical records.
- [ ] Add `Publish draft to platform`.
- [ ] Save canonical platform IDs back into local draft artifacts.
- [ ] Display platform sync status per artifact.
- [ ] Make Postgres/platform persistence explicit in UI.

## Phase 5: Better Agent Execution

- [ ] Replace deterministic v0 text with a generic runnable LangGraph template.
- [ ] Generate a minimal agent package/folder for draft agents.
- [ ] Add mock tool binding generation.
- [ ] Run v0 through same runner/eval artifact format as existing agents.
- [ ] Support optional live generation when `OPENAI_API_KEY` exists.
- [ ] Keep CI/mock mode deterministic.

## Phase 6: Evaluation Maturity

- [ ] Convert draft eval contract into runnable eval suite.
- [ ] Add deterministic structure/keyword checks from generated rules.
- [ ] Add optional LLM judge path.
- [ ] Add failure packet generation per failed rule.
- [ ] Add overfitting/variant scenario generation.
- [ ] Add regression comparison across multiple scenarios.
- [ ] Show rule-level pass/fail, not only score.

## Phase 7: Publish and Platform Loop

- [ ] Publish greenfield run records through existing publish seam.
- [ ] Include target/rule/eval/graph IDs in publish envelope.
- [ ] Show publish result and platform run ID.
- [ ] Link to platform console pages.
- [ ] Handle queued/offline publish clearly.
- [ ] Add retry publish for queued runs.
- [ ] Add platform health/auth diagnostics in the UI.

## Phase 8: Product Hardening

- [ ] Add end-to-end tests for local draft flow.
- [ ] Add UI smoke tests for `:8502`.
- [ ] Add schema tests for generated YAML artifacts.
- [ ] Add docs for local-only vs platform-persisted flows.
- [ ] Add cleanup/ignore policy for `lab-runs/` generated drafts.
- [ ] Add import/export of draft workspaces.
- [ ] Add better error handling for missing/corrupt artifacts.
- [ ] Add README screenshots or GIF once UI stabilizes.

## Near-Term Build Order

1. Editable artifact review forms.
2. Generate local `fix-plan.yaml` from v0 failure.
3. Generate, run, and evaluate local v1.
4. Greenfield side-by-side compare view.
5. Publish greenfield evidence to platform.
6. Platform persistence API design.
