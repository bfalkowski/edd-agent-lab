# Functional Application Plan

This plan tracks the remaining work to make `edd-agent-lab` a functional local
application for creating, running, evaluating, comparing, and publishing agents.

## Goal

Make the local builder support the complete draft-agent loop:

1. Create a new agent from scratch.
2. Define target behavior.
3. Generate and review rules, evals, requirements, tools, and graph design.
4. Add scenarios.
5. Run v0.
6. Evaluate v0.
7. Generate a bounded fix plan.
8. Create and run v1.
9. Compare v0 and v1.
10. Publish evidence to the platform.

## Phase 1: Local Draft Workflow

- [x] Create local agent draft from name and description.
- [x] Save `agent-target.yaml`.
- [x] Generate draft rules, eval contract, requirements, tools, and graph design.
- [x] Add a first local scenario.
- [x] Run deterministic `v0-baseline`.
- [x] Evaluate v0 locally.
- [x] Generate local failure packet.
- [x] Generate fix plan, v1 graph, v1 run, v1 eval, and comparison.
- [x] Delete draft projects from the local project list.
- [x] Delete non-target artifacts so a step can be regenerated.

## Phase 2: Review And Editing

- [x] Review generated artifact YAML in the builder.
- [x] Save edited artifact YAML.
- [x] Keep activity status local to the step that produced it.
- [ ] Add structured editors for target, rules, eval contract, requirements, and graph.
- [ ] Add YAML/schema validation errors in the review drawer.
- [ ] Add artifact diff view before saving edits.
- [ ] Add rename/archive for draft projects.

## Phase 3: Runtime Feedback

- [ ] Add streaming step activity from the API.
- [ ] Emit the same event shape in deterministic mock mode and live mode.
- [ ] Show model/tool progress inline on the active step.
- [ ] Show written artifacts as they are created.
- [ ] Preserve failures with retry context on the owning step.

## Phase 4: Better Agent Execution

- [ ] Replace deterministic v0 text with a generic runnable LangGraph template.
- [ ] Generate a minimal agent package or folder for draft agents.
- [ ] Add mock tool binding generation.
- [ ] Run draft agents through the same runner/eval artifact format as existing agents.
- [ ] Support optional live generation when provider credentials exist.
- [ ] Keep CI and local tests deterministic by default.

## Phase 5: Evaluation Maturity

- [ ] Convert draft eval contracts into runnable eval suites.
- [ ] Add deterministic structure and keyword checks from generated rules.
- [ ] Add optional LLM judge path.
- [ ] Add failure packet generation per failed rule.
- [ ] Add overfitting or variant scenario generation.
- [ ] Add regression comparison across multiple scenarios.
- [ ] Show rule-level pass/fail, not only an aggregate score.

## Phase 6: Platform Publish Loop

- [ ] Publish draft run records through the existing publish integration.
- [ ] Include target, rule, eval, graph, and comparison identifiers in the publish envelope.
- [ ] Show publish result and platform run ID in the builder.
- [ ] Link to relevant platform records.
- [ ] Handle queued/offline publish clearly.
- [ ] Add retry publish for queued runs.
- [ ] Add platform health and auth diagnostics in the UI.

## Phase 7: Product Hardening

- [ ] Add end-to-end tests for the React builder flow.
- [ ] Add API tests for draft create, action, artifact edit, artifact delete, and project delete.
- [ ] Add schema tests for generated YAML artifacts.
- [ ] Add import/export of draft workspaces.
- [ ] Add better error handling for missing or corrupt artifacts.
- [ ] Add screenshots once the UI stabilizes.

## Near-Term Build Order

1. Add API streaming for workflow actions.
2. Add schema validation in artifact review.
3. Add structured editors for the highest-value artifacts.
4. Publish draft evidence to the platform.
5. Generate runnable draft agent packages.
