# Lab Console Design: Side-by-Side Agent Workbench

## Status

Draft

## Purpose

This document defines the UI design for the `edd-agent-lab` console.

The lab console is a local developer workbench for running, comparing, inspecting, and publishing agent versions.

It is **not** the platform console.

The platform console owns the canonical evaluation-driven design workflow:

```text
AgentTarget
BehaviorRule
EvalContract
InformationRequirement
ToolRequirement
ToolFeasibilityReview
GraphDesign
FailurePacket
FixPlan
Comparison
GateResult
PromotionRecord
ReadinessStatus
```

The lab console owns the local development loop:

```text
select agent
select scenario
run v0
run v1
compare outputs
inspect graph/tool differences
view local eval summary
publish results to platform
```

The lab console should feel like a focused developer workbench, not a generic dashboard and not a full observability wall.

**Implement the reference workbench (`edd-lab console`, :8502) against this doc.** Platform console IA remains [HLD-011](../eval-driven-design-platform/docs/hld/HLD-011-console-information-architecture.md). The older side-by-side **chat** spec is [07-final-milestone-side-by-side-console.md](07-final-milestone-side-by-side-console.md) (`customer-solution` agent).

---

## Core Design Goal

The default screen should answer three questions in under ten seconds:

```text
What did v0 do?

What did v1 do differently?

Why is v1 better but still not production-ready?
```

For the Customer Escalation Triage reference scenario, the core story is:

```text
v0 guessed.
v1 checked evidence.

v0 overclaimed root cause.
v1 separated facts, hypotheses, and unknowns.

v0 failed separate_facts_from_hypotheses.
v1 passed behavior gates.

v1 is demo-ready.
v1 is not production-ready because required tools are mock/local.
```

The UI should make that story obvious without requiring users to open raw YAML files.

---

## Non-Goals

Do not build the full platform console in the lab repo.

The lab console should not own:

```text
target authoring
rule authoring
eval contract authoring
canonical gate decisions
canonical promotion workflow
production readiness ownership
approval-gated write actions
operational run workflows
full graph editor
Langfuse replacement views
```

Those belong to `eval-driven-design-platform`.

The lab console may display related artifacts for local inspection, but it should not become the canonical product database.

---

## Relationship to Platform Console

### Platform Console

The platform console answers:

```text
What is this agent supposed to do?
Which rules define good behavior?
What information does it need?
Which tools are required?
Do the tools exist?
Which gates passed?
Can the version be promoted?
Is it production-ready?
```

### Lab Console

The lab console answers:

```text
How do v0 and v1 behave locally?
What did each version output?
Which version failed?
Which rule failed?
What graph/tool changes explain the improvement?
Which artifacts were produced?
Can I publish this run to the platform?
```

The lab console should use platform concepts, but it should present them from a local developer workflow perspective.

---

## Primary UX Principle

The previous dense dashboard-style mockup showed too much at once.

The revised lab console should be simpler:

```text
Top:
  Context bar and run actions

Main:
  v0 output | v1 output

Bottom:
  EDD verdict

Details:
  Graph, tools, scores, traces, artifacts, publish controls
  hidden behind tabs, accordions, or a right-side drawer
```

The default view should not try to show every score, every trace, every graph node, every tool, every artifact, and every publish detail at once.

---

## Recommended Layout

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Header / Context Bar                                                       │
│ Agent | Scenario | Version A | Version B | Tool Mode | Platform Status      │
│ Run v0 | Run v1 | Compare | Publish                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Scenario Summary                                                            │
│ Short problem statement + expected behavior summary                         │
├───────────────────────────────────┬─────────────────────────────────────────┤
│ v0-baseline                       │ v1-evidence-triage-graph               │
│ Score / Gate                      │ Score / Gate / Readiness               │
│ Agent response                    │ Agent response                         │
│ Failure callout                   │ Improvement callout                    │
├───────────────────────────────────┴─────────────────────────────────────────┤
│ EDD Verdict                                                                 │
│ What failed in v0, what changed in v1, what is still blocked                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Details Tabs / Accordions                                                   │
│ Graph Diff | Tools | Scores | Traces | Artifacts | Publish                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# Screen 1: Main Workbench

The main workbench is the default page.

It should show only the most important information.

## Header / Context Bar

### Purpose

Show the current local development context and primary actions.

### Required Fields

```text
Agent
Scenario
Version A
Version B
Tool mode
Platform connection status
Run mode
```

### Example

```text
Agent: Customer Escalation Triage
Scenario: Apex Health — Latency & Quality Regression
Compare: v0-baseline vs v1-evidence-triage-graph
Tool Mode: mock_local
Model Mode: fixture
Platform: connected
```

### Required Actions

```text
Run v0
Run v1
Compare
Publish to Platform
Refresh Artifacts
```

### Notes

Use `--platform-api-url` terminology when the lab needs an API URL.

Avoid ambiguous `--platform-url`, because platform console and platform API may be on different ports.

---

## Scenario Summary Panel

### Purpose

Show the scenario in a compact form.

The user should not need to read a full YAML file to understand what is being tested.

### Required Content

```text
Scenario name
Customer/problem summary
Key signals
Expected behavior
```

### Example

```text
Scenario:
Apex Health reports inconsistent answers, higher latency, a recent summarization
prompt change, scanned-PDF eval score drops, and eligibility-check tool timeouts.

Expected behavior:
- Do not overclaim root cause
- Separate facts, hypotheses, and unknowns
- Use evidence and tools
- Recommend safe next actions
- Draft a customer-safe update
```

### UI Guidance

Keep this panel short.

Do not show all mock data here. Put detailed mock data in the Details section.

---

## Side-by-Side Version Panels

The heart of the lab console is the side-by-side comparison.

```text
┌───────────────────────────────────┬─────────────────────────────────────────┐
│ v0-baseline                       │ v1-evidence-triage-graph               │
├───────────────────────────────────┼─────────────────────────────────────────┤
│ Score: 2.4 / 5                    │ Score: 4.4 / 5                         │
│ Gate: FAIL                        │ Gate: PASS FOR DEMO                    │
│ Graph: single_pass_response       │ Graph: evidence_triage_v1              │
│ Tool Mode: none / fixture         │ Tool Mode: mock_local                  │
├───────────────────────────────────┼─────────────────────────────────────────┤
│ Agent response                    │ Agent response                         │
└───────────────────────────────────┴─────────────────────────────────────────┘
```

---

## v0 Panel

### Purpose

Show the weak baseline clearly.

### Required Fields

```text
Version ID
Graph summary
Score
Gate status
Tool mode
Agent output
Failure callout
Trace/run ID if available
```

### Example

```text
v0-baseline
Score: 2.4 / 5
Gate: FAIL
Graph: single_pass_response

Agent Response:
"The likely cause is the summarization prompt change. We should roll back the
change and tell the customer we found the issue."

Failure:
Failed separate_facts_from_hypotheses.
The agent overclaimed root cause without enough evidence.
```

### Visual Treatment

Use restrained styling.

The failure should be obvious, but do not overdo warning colors everywhere.

Recommended:

```text
small red FAIL badge
one failure callout at bottom of panel
```

---

## v1 Panel

### Purpose

Show the improved candidate clearly.

### Required Fields

```text
Version ID
Graph summary
Score
Gate status
Tool mode
Production readiness
Agent output
Improvement callout
Trace/run ID if available
```

### Example

```text
v1-evidence-triage-graph
Score: 4.4 / 5
Gate: PASS FOR DEMO
Production: BLOCKED
Graph: evidence_triage_v1
Tool Mode: mock_local

Agent Response:
Confirmed facts:
- Latency increased.
- Eval scores dropped for scanned PDF cases.
- Eligibility-check tool has intermittent timeouts.

Hypotheses:
- Recent summarization prompt change may contribute.
- Scanned-PDF extraction may be a factor.
- Tool timeouts may contribute to latency or incomplete answers.

Unknowns:
- Whether the prompt change directly caused the issue.
- Whether non-scanned PDF workflows are unaffected.

Recommended next actions:
- Compare pre/post-change eval results.
- Inspect high-latency traces.
- Check timeout correlation.
- Prepare customer-safe update.
```

### Visual Treatment

Use restrained positive styling.

Recommended:

```text
green PASS FOR DEMO badge
amber BLOCKED production badge
```

Do not make the whole panel glow green. It passed behavior gates, but it is not production-ready.

---

## EDD Verdict Panel

### Purpose

This is the most important explanation panel.

It should summarize the design improvement in plain language.

### Required Content

```text
v0 failure
v1 fix
resolved failure
remaining blocker
promotion recommendation
```

### Example

```text
EDD Verdict

v0 failed because it overclaimed root cause.
Failed rule: separate_facts_from_hypotheses.

v1 fixed the failure by adding:
- evidence collection
- evidence normalization
- facts/hypotheses/unknowns separation
- customer-safe update review

Resolved:
- unsupported root-cause claim

No new critical failures.

Readiness:
- Behavior readiness: PASS
- Tool readiness: MOCK_LOCAL
- Production readiness: BLOCKED
- Promotion: PROMOTED_FOR_DEMO
```

### UI Guidance

This should be short and readable.

If the user reads only one section, this should be it.

---

# Details Area

The details area should be below the main workbench or available as a right-side drawer.

Recommended implementation for Streamlit:

```text
st.tabs([
  "Graph Diff",
  "Tools",
  "Scores",
  "Traces",
  "Artifacts",
  "Publish"
])
```

Or use expanders if tabs are easier.

The details area should not dominate the default view.

---

## Details Tab: Graph Diff

### Purpose

Show why v1's graph is different from v0's graph.

### Required Content

```text
v0 graph summary
v1 graph summary
added nodes
reason each node exists
rules supported
failure packets addressed
```

### Example

```text
v0 graph:
start → single_pass_response → final_response

v1 graph:
start
→ parse_escalation_report
→ collect_evidence
→ normalize_evidence
→ identify_correlations
→ separate_facts_hypotheses_unknowns
→ assess_customer_impact
→ recommend_mitigation_plan
→ draft_customer_update
→ customer_safe_update_review
→ final_response
```

### Node Diff Table

| Added Node | Why It Exists | Rule Supported | Failure Addressed |
|---|---|---|---|
| collect_evidence | Gather evidence before diagnosis | evidence_first_diagnosis | fp-v0-unsupported-root-cause |
| normalize_evidence | Normalize traces/evals/tools/changes | evidence_first_diagnosis | fp-v0-unsupported-root-cause |
| separate_facts_hypotheses_unknowns | Prevent unsupported causality | separate_facts_from_hypotheses | fp-v0-unsupported-root-cause |
| customer_safe_update_review | Avoid speculative external update | draft_customer_safe_update | fp-v0-unsupported-root-cause |

### Important

The graph diff should not just show that v1 has more nodes.

It must explain why those nodes were added.

---

## Details Tab: Tools

### Purpose

Show active tool bindings and readiness.

### Required Content

```text
Tool requirement
Implementation
Mode
Read/write
Production blocker
```

### Example Table

| Graph Node | Requirement | Implementation | Mode | Production Blocker |
|---|---|---|---|---|
| collect_trace_evidence | trace_evidence_source | fetch_trace_summary_mock | mock | Yes |
| collect_eval_history | eval_history_source | fetch_eval_results_local | local | Yes |
| collect_recent_changes | recent_changes_source | fetch_recent_changes_mock | mock | Yes |
| collect_tool_health | tool_health_source | fetch_tool_health_mock | mock | Yes |
| collect_customer_context | customer_context_source | fetch_customer_context_from_scenario | local | Yes |

### Required Warning

```text
Production readiness is blocked because required tools are mock/local.
This run is suitable for demo and offline evaluation only.
```

### Important

Do not hide tool mode.

Tool mode is part of the product honesty story.

---

## Details Tab: Scores

### Purpose

Show score dimensions without cluttering the main view.

### Required Content

```text
Metric
v0 score
v1 score
delta
rule mapping
```

### Example Table

| Metric | v0 | v1 | Delta | Rules |
|---|---:|---:|---:|---|
| diagnostic_grounding | 2 | 5 | +3 | evidence_first_diagnosis, separate_facts_from_hypotheses |
| change_correlation_quality | 3 | 4 | +1 | identify_recent_changes |
| impact_assessment_quality | 2 | 4 | +2 | assess_customer_impact |
| action_plan_quality | 3 | 4 | +1 | recommend_safe_next_actions |
| customer_communication_quality | 2 | 5 | +3 | draft_customer_safe_update |

### Summary

```text
Overall:
v1 improved because it stopped overclaiming root cause and separated facts,
hypotheses, and unknowns.
```

---

## Details Tab: Traces

### Purpose

Show trace links or placeholder trace IDs.

### Required Content

```text
Run ID
Trace provider
Trace ID
Tool mode
Environment
Open trace link if available
```

### Example Table

| Version | Run ID | Provider | Trace ID | Tool Mode | Environment |
|---|---|---|---|---|---|
| v0 | run_v0_001 | placeholder/langfuse | trace_v0_001 | fixture | local_demo |
| v1 | run_v1_001 | placeholder/langfuse | trace_v1_001 | mock_local | local_demo |

### Important

Langfuse is optional for the lab console MVP.

Placeholder trace IDs are acceptable.

Do not require live Langfuse for local smoke tests.

---

## Details Tab: Artifacts

### Purpose

Show local files produced by the lab.

### Required Content

```text
Artifact type
Path
Version
Status
```

### Example Artifacts

```text
agent-target.yaml
behavior-rules.yaml
eval-contract.yaml
information-requirements.yaml
tool-requirements.yaml
tool-feasibility.yaml
tool-bindings.yaml
graph-design-v0.yaml
graph-design-v1.yaml
failure-packet-v0.yaml
fix-plan-v1.yaml
comparison-v0-v1.yaml
gate-result-v1.yaml
promotion-record-v1.yaml
```

### Actions

```text
Open/view artifact
Copy path
Refresh artifacts
```

Do not overbuild artifact editing in the lab console MVP.

---

## Details Tab: Publish

### Purpose

Publish local lab artifacts to the platform API.

### Required Content

```text
Platform API URL
Selected agent
Selected versions
Selected scenario
Publish v0
Publish v1
Publish comparison
Last publish result
```

### Required Actions

```text
Publish v0 Run
Publish v1 Run
Publish Comparison
Open in Platform Console
```

### Example Publish Result

```text
Published v1 run.

platform_run_id: platform-run-v1-001
behavior_status: pass
tool_status: mock_local
production_status: blocked
overall_status: pass_for_demo_not_production
promotion_status: promoted_for_demo
```

### Important

Use `platform-api-url`, not ambiguous `platform-url`.

The lab publishes to the platform API, not to the Streamlit console.

---

# Visual Design Direction

## Overall Feel

The lab console should feel:

```text
focused
developer-friendly
calm
readable
side-by-side
evidence-driven
not cluttered
```

## Preferred Style

```text
Dark or neutral theme is acceptable.
Use restrained color.
Use badges sparingly.
Use whitespace.
Make v0/v1 comparison the dominant visual.
Move secondary data into tabs or expanders.
Avoid showing every possible object on the default screen.
```

## Suggested Color Semantics

```text
Red:
  actual failure only

Green:
  behavior pass or resolved failure

Amber:
  warning, mock/local, production blocked

Blue/Purple:
  links, actions, neutral metadata
```

Do not make the whole v1 panel green. v1 is better, but production is blocked.

---

# Information Priority

The UI should prioritize information in this order:

```text
1. Scenario and selected versions
2. v0 output
3. v1 output
4. EDD verdict
5. Graph/failure explanation
6. Tool readiness
7. Scores
8. Traces
9. Artifacts
10. Publish details
```

If the screen feels cluttered, hide lower-priority sections behind tabs or expanders.

---

# MVP Implementation Guidance

## Build This First

```text
1. One Streamlit page or current lab console page.
2. Context bar.
3. Scenario summary.
4. Side-by-side v0/v1 output cards.
5. EDD verdict panel.
6. Details tabs:
   - Graph Diff
   - Tools
   - Scores
   - Traces
   - Artifacts
   - Publish
```

## Do Not Build Yet

```text
1. Full lifecycle platform navigation.
2. Target/rule/eval authoring.
3. Graph editor.
4. Live LLM controls.
5. Production operational run UI.
6. Approval-gated action queue.
7. Full Langfuse trace viewer.
```

---

# Expected Data Sources

The lab console should be able to load from local artifacts.

Recommended paths:

```text
lab-runs/customer_escalation_triage/target/
  agent-target.yaml
  behavior-rules.yaml
  eval-contract.yaml
  information-requirements.yaml
  tool-requirements.yaml
  tool-feasibility.yaml
  tool-bindings.yaml
  graph-design-v0.yaml
  graph-design-v1.yaml

lab-runs/customer_escalation_triage/v0-baseline/
  run-output.json
  eval-summary.json
  failure-packets/fp-v0-unsupported-root-cause.yaml

lab-runs/customer_escalation_triage/v1-evidence-triage-graph/
  run-output.json
  eval-summary.json
  fix-plan.yaml
  comparison-against-v0.json
  gate-result.yaml
  promotion-record.yaml
```

The exact paths may differ based on existing repo layout, but the UI should be artifact-driven.

Platform reference fixtures also live under `eval-driven-design-platform/examples/customer_escalation_triage/` for read-only design context.

---

# Run Modes

The lab console should support deterministic modes.

```text
fixture:
  Load saved outputs and eval summaries from local artifacts.

mock:
  Run deterministic mock graph/tools/evaluator.

live:
  Optional future mode. Not required for MVP.
```

Default mode:

```text
fixture
```

or:

```text
mock
```

Live LLM calls must not be required for the lab console.

CI and smoke tests should not require AI provider keys.

---

# Platform Publish Behavior

The lab console may call:

```http
POST /v1/integrations/runs/publish
```

The UI should show the platform response but not own canonical promotion logic.

Example response fields to display:

```text
platform_run_id
behavior_status
tool_status
production_status
overall_status
promotion_status
warnings
```

The lab console should treat platform response as authoritative for platform readiness.

Environment variable: `EDD_API_BASE_URL` (platform API, not Streamlit console). Console deep links use `EDD_CONSOLE_BASE_URL` (default `:8501`).

---

# Acceptance Criteria

The lab console is aligned with this design when:

```text
1. The default view is not cluttered.
2. The default view shows scenario, v0 output, v1 output, and EDD verdict.
3. v0 failure is obvious.
4. v1 improvement is obvious.
5. Production blocked status is obvious.
6. Detailed graph/tool/score/trace/artifact/publish data is moved into tabs or expanders.
7. The graph diff explains why v1 added nodes.
8. Tool mode is visible and not hidden.
9. The lab console does not duplicate the platform console's full lifecycle UI.
10. The lab console can publish runs to the platform API.
11. The lab console works with fixture/mock data and does not require live LLM calls.
12. The UI tells the story: v0 guessed, v1 checked evidence.
```

---

# Anti-Patterns

## Anti-pattern: Observability wall

Bad:

```text
Every score, trace, tool, graph node, artifact, and publish status visible at once.
```

Good:

```text
Default view shows the comparison story.
Details are available in tabs.
```

## Anti-pattern: Platform console duplication

Bad:

```text
Lab UI tries to author targets, rules, eval contracts, promotions, and readiness policy.
```

Good:

```text
Lab UI runs and compares local agent versions, then publishes evidence to the platform.
```

## Anti-pattern: Greenwashing v1

Bad:

```text
v1 panel looks fully successful because behavior gates pass.
```

Good:

```text
v1 shows PASS FOR DEMO and PRODUCTION BLOCKED.
```

## Anti-pattern: Hidden mock tools

Bad:

```text
v1 appears evidence-driven but does not show that trace/recent-change/tool-health tools are mock/local.
```

Good:

```text
Tool detail clearly shows mock/local bindings and production blockers.
```

## Anti-pattern: Live LLM required

Bad:

```text
Console fails without OpenAI or Anthropic keys.
```

Good:

```text
Console works from fixtures or deterministic mocks. Live LLM mode is optional.
```

---

# Summary

The lab console should be a side-by-side workbench.

Its job is to make local agent iteration understandable:

```text
Run v0.
Run v1.
Compare outputs.
Explain the failure.
Explain the fix.
Show readiness honestly.
Publish to platform.
```

The default experience should be simple:

```text
v0 output | v1 output
EDD verdict underneath
Details tucked away
```

The key product story remains:

```text
v0 guessed.
v1 checked evidence.

v0 overclaimed root cause.
v1 separated facts, hypotheses, and unknowns.

v1 passed behavior gates.
v1 remained blocked for production because required tools were mock/local.
```

---

## Related Documents

| Document | Repo | Description |
|---|---|---|
| [HLD-005](../eval-driven-design-platform/docs/hld/HLD-005-reference-scenario-customer-escalation-triage.md) | platform | Reference scenario content |
| [HLD-011](../eval-driven-design-platform/docs/hld/HLD-011-console-information-architecture.md) | platform | Platform console IA (not lab) |
| [11-ideal-console-design.md](11-ideal-console-design.md) | lab | Narrative for platform console ideal |
| [07-final-milestone-side-by-side-console.md](07-final-milestone-side-by-side-console.md) | lab | Legacy chat console (`customer-solution`) |
| [HLD Test-First Implementation](../eval-driven-design-platform/docs/HLD_TEST_FIRST_IMPLEMENTATION.md) | platform | PR 13b lab workbench scope |
