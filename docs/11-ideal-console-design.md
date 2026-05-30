# Ideal Platform Console Design

This document describes the ideal console experience for **eval-driven-design-platform**.

**Canonical platform spec:** [HLD-011: Console information architecture](../eval-driven-design-platform/docs/hld/HLD-011-console-information-architecture.md) in the platform repo. This doc expands narrative and UX detail; implement against HLD-011 for screen structure and MVP scope.

The EDD stack is a workspace for evaluation-driven agent design. The platform console should help developers move from a rough agent idea to a validated, traceable, versioned, and eventually operational agent.

The console is not just an eval dashboard.

It is the control surface for the full design loop:

```text
agent idea → target → rules → eval contract → information requirements
  → tool requirements → tool feasibility → graph design → v0 → traces
  → failure packets → bounded fix → v1 → comparison → gates → promotion → live operation
```

---

## 1. Console Design Goal

The console should help a developer answer these questions:

- What is this agent supposed to do?
- What rules define good behavior?
- What information does it need?
- What tools would provide that information?
- Do those tools actually exist?
- How should the graph be shaped by the rules and tools?
- How did v0 behave?
- Where did it fail?
- What evidence proves the failure?
- What changed in v1?
- Did v1 improve for the right reasons?
- Is this version safe to promote?
- Can this version be used operationally?

The console should make agent development feel less like prompt tinkering and more like disciplined system design.

---

## 2. Product Framing

The console should be organized around four major modes:

| Mode | Purpose |
|---|---|
| **Design** | Define what the agent should do. |
| **Build** | Shape the graph, prompts, tools, and implementation. |
| **Evaluate** | Run versions, inspect traces, diagnose failures, and compare improvements. |
| **Operate** | Use promoted agents in real workflows while preserving evidence and readiness context. |

Recommended top-level navigation:

```text
Overview

Design
  Target
  Rules
  Eval Contract
  Information Requirements
  Tool Requirements
  Tool Feasibility

Build
  Graph Design
  Prompts
  Tool Bindings
  Versions

Evaluate
  Runs
  Traces
  Failure Packets
  Fix Plans
  Compare Versions
  Gates

Operate
  Live Run
  Action Queue
  Run History
  Promotion

Artifacts
Settings
```

This organization matters because the platform is not merely scoring outputs. It is connecting design intent to implementation, evidence, and operation.

---

## 3. Overall Layout

The ideal console should use a persistent three-region layout.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Top Context Bar                                                             │
│ Agent | Target | Eval Contract | Version | Tool Mode | Gate Status          │
├─────────────────────┬───────────────────────────────────────────────────────┤
│ Left Navigation     │ Main Workspace                                        │
│                     │                                                       │
│ Overview            │ Workspace-specific content                            │
│ Design              │                                                       │
│ Build               │                                                       │
│ Evaluate            │                                                       │
│ Operate             │                                                       │
│ Artifacts           │                                                       │
│ Settings            │                                                       │
└─────────────────────┴───────────────────────────────────────────────────────┘
```

The top context bar should always show:

```text
Agent: Customer Escalation Triage Agent
Target: customer-escalation-triage-target-v1
Eval Contract: escalation-triage-eval-contract-v1
Version: v1-evidence-triage-graph
Tool Mode: mixed / mock / live
Gate: PASS FOR DEMO, BLOCKED FOR PRODUCTION
```

The user should never wonder which target, version, or tool mode they are looking at.

---

## 4. Global Status Model

The console should distinguish behavior readiness from operational readiness.

Example:

```text
Behavior Gate:        PASS
Tool Readiness:       MOCK ONLY
Production Readiness: BLOCKED
Promotion Status:     PROMOTED FOR DEMO
```

This distinction is critical. An agent can pass behavior evals while still being unfit for production because required tools are missing or mock-only.

Recommended global badges:

```text
DRAFT
EVALUATING
FAILED
PASS
PASS WITH WARNING
PROMOTED FOR DEMO
PROMOTED FOR INTERNAL USE
PRODUCTION BLOCKED
PRODUCTION READY
REJECTED
DEPRECATED
```

---

## 5. Overview Workspace

The Overview workspace should summarize the current agent lifecycle state.

### Primary Cards

- **Agent Target** — Purpose, users, goals, non-goals.
- **Active Version** — Current implementation, graph summary, source version.
- **Behavior Gate** — Pass/fail/warning.
- **Tool Readiness** — Missing, mock, local, read-only live, approval-gated, automated.
- **Latest Run** — Score, failure count, trace count, token/cost/latency summary.
- **Current Recommendation** — Promote, reject, continue fixing, or resolve tool blockers.

### Example Layout

```text
┌───────────────────────────────┬───────────────────────────────┐
│ Agent Target                  │ Active Version                │
│ Customer Escalation Triage    │ v1-evidence-triage-graph      │
│ Evidence-first escalation     │ Adds evidence normalization   │
│ diagnosis and action planning │ and facts/hypotheses split    │
└───────────────────────────────┴───────────────────────────────┘

┌───────────────┬───────────────┬───────────────┬────────────────┐
│ Behavior Gate │ Tool Mode     │ Prod Status   │ Latest Score   │
│ PASS          │ MOCK/LOCAL    │ BLOCKED       │ 4.4 / 5        │
└───────────────┴───────────────┴───────────────┴────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ Recommendation                                                  │
│ v1 can be promoted for demo use. Production readiness is blocked│
│ until trace, recent-change, and tool-health connectors are live.│
└────────────────────────────────────────────────────────────────┘
```

The overview should immediately tell the product story.

---

## 6. Target Workspace

The Target workspace is where the user defines what the agent should do.

This is the beginning of the EDD workflow.

### Input Style

The user should be able to start with plain language:

```text
I want an agent that helps FDEs triage customer escalations for AI deployments.
It should look at traces, eval results, recent changes, tool failures, and customer reports.
It should identify likely causes, recommend safe next actions, and help draft a customer update.
It must not invent root causes.
```

The console then generates a structured target.

### Target Fields

- Agent name
- Purpose
- Intended users
- Primary goals
- Non-goals
- Allowed tool categories
- Risk tolerance
- Expected output format
- Example scenarios

### Generated Target Example

```yaml
agent_target:
  id: customer-escalation-triage-target-v1
  name: Customer Escalation Triage Agent
  purpose: >
    Help Forward Deployed Engineers triage customer escalations in AI deployments
    by synthesizing customer reports, traces, eval results, recent changes,
    and tool health into a grounded diagnosis and action plan.
  primary_goals:
    - Summarize the customer-reported problem.
    - Identify relevant evidence.
    - Separate confirmed facts from hypotheses.
    - Recommend safe next actions.
    - Draft a customer-safe update.
  non_goals:
    - Do not claim a confirmed root cause without evidence.
    - Do not expose sensitive trace details to the customer.
    - Do not suggest destructive production changes without approval.
```

### Actions

- Generate target from description
- Edit target
- Save target version
- Mark target active
- Generate behavior rules
- Compare target versions

The target should be versioned. Changing the target should be treated as a meaningful design change.

---

## 7. Rules Workspace

The Rules workspace turns agent intent into explicit behavioral expectations.

### Rule Card

Each rule should be shown as a card.

```text
Rule: Separate facts from hypotheses
Severity: Critical
Status: Active

Used by metrics:
  - diagnostic_grounding

Recent failures:
  - v0-baseline / escalation-latency-quality-regression-001

Graph impact:
  - separate_facts_hypotheses_unknowns node
```

### Rule Categories

- Discovery
- Grounding
- Evidence use
- Tool use
- Planning
- Safety
- Customer communication
- Production readiness
- Action approval

### Actions

- Generate rules from target
- Add rule
- Edit rule
- Disable rule
- View eval metrics using this rule
- View graph nodes supporting this rule
- View failures tied to this rule
- View traces where this rule failed

Rules should feel alive. They should connect to metrics, graph nodes, traces, and failures.

---

## 8. Eval Contract Workspace

The Eval Contract workspace shows how rules become measurable checks.

### Main Sections

- Metrics
- Rubrics
- Scoring scales
- Hard gates
- Warning gates
- Scenario sets
- Regression checks
- Overfitting checks

### Metric Card Example

```text
Metric: diagnostic_grounding
Scale: 0–5

Rules:
  - evidence_first_diagnosis
  - separate_facts_from_hypotheses

Current version:
  v0-baseline: 2 / 5
  v1-evidence-triage-graph: 5 / 5

Gate:
  Must be >= 4
```

### Gate Card Example

```text
Gate: no_unsupported_root_cause
Type: Hard
Condition: diagnostic_grounding >= 4
Latest result: PASS
Previous result: FAIL
Resolved by: v1-evidence-triage-graph
```

### Actions

- Generate eval contract from rules
- Edit rubric text
- Preview evaluator prompt
- Attach scenario set
- Run contract validation
- View score history
- View gates affected by a rule change

The eval contract should be inspectable. Developers should understand what the evaluator is checking.

---

## 9. Information Requirements Workspace

This is a key workspace in the ideal console.

Before the system recommends tools, it should identify what information the agent needs.

### Purpose

This screen answers:

> What information must this agent have to satisfy the rules?

### Example Requirements

**Customer report**

- Needed for: `evidence_first_diagnosis`, `assess_customer_impact`
- Description: Customer-reported symptoms, timing, affected workflows, and urgency.

**Trace evidence**

- Needed for: `evidence_first_diagnosis`, `separate_facts_from_hypotheses`
- Description: Recent traces, model calls, tool calls, latency, failed spans, and errors.

**Recent changes**

- Needed for: `identify_recent_changes`
- Description: Recent prompt, model, config, code, deployment, or dataset changes.

### UI Pattern

Use a table:

| Information Requirement | Required By Rules | Available Source? | Status |
|---|---|---:|---|
| Customer report | Evidence, impact | Scenario input | Available |
| Trace evidence | Evidence, grounding | Mock Langfuse summary | Mock only |
| Eval history | Evidence, change correlation | Local eval summary | Available |
| Recent changes | Change correlation | Mock changelog | Mock only |
| Tool health | Evidence, safe actions | Mock status file | Mock only |

### Actions

- Generate information requirements
- Edit requirement
- Map requirement to tool
- Mark requirement optional/required
- View rules depending on requirement
- View tool feasibility

This screen prevents premature fantasy-tool design.

---

## 10. Tool Requirements Workspace

The Tool Requirements workspace translates information needs into tool needs.

The console should be explicit that suggested tools are requirements, not confirmed implementations.

### Tool Requirement Card

```text
Tool Requirement: Trace evidence source
Suggested tool: fetch_trace_summary
Access mode: Read-only

Information needed:
  - recent traces
  - latency trends
  - failed spans
  - model inputs/outputs
  - tool call failures

Required by rules:
  - evidence_first_diagnosis
  - separate_facts_from_hypotheses

Possible implementations:
  - mock JSON fixture
  - Langfuse API
  - platform trace summary endpoint
```

### Statuses

- Missing
- Mock only
- Local artifact
- Read-only live
- Approval-gated action
- Automated action

### Actions

- Generate tool requirements
- Create mock implementation
- Bind existing implementation
- Mark as production blocker
- View graph nodes requiring this tool
- View gates affected by this tool

The key UI message:

> This is what the agent needs. This does not mean the tool already exists.

---

## 11. Tool Feasibility Workspace

The Tool Feasibility workspace answers:

> Can this agent actually get the information it needs?

This should be one of the most important screens.

### Feasibility Table

| Requirement | Suggested Tool | Current Implementation | Demo Ready | Production Ready | Risk |
|---|---|---|---:|---:|---|
| Customer report | fetch_customer_report | Scenario input | Yes | Partial | Manual input |
| Trace evidence | fetch_trace_summary | Mock JSON | Yes | No | Needs Langfuse API |
| Eval history | fetch_eval_results | Local eval summary | Yes | Partial | Needs platform DB |
| Recent changes | fetch_recent_changes | Mock JSON | Yes | No | Needs GitHub/GitLab |
| Tool health | fetch_tool_health | Mock JSON | Yes | No | Needs metrics/logs |

### Feasibility Detail

```yaml
tool_feasibility:
  requirement_id: trace_evidence_source
  suggested_tool_name: fetch_trace_summary
  implementation_status: mock_only
  mvp_strategy: mock_json_fixture
  production_strategy: langfuse_api_connector
  feasibility_status: needs_review
  risks:
    - API permissions
    - sensitive trace contents
    - trace volume
    - summarization latency
```

### Actions

- Create mock fixture
- Create connector task
- Mark production blocker
- Approve read-only live use
- Require human approval
- View affected gates

This screen should make tool gaps visible instead of hidden.

---

## 12. Graph Design Workspace

The Graph Design workspace shows how target rules, information requirements, and tool feasibility shape the LangGraph design.

This screen proves the platform is doing design, not just eval reporting.

### Main View

```text
Rule → Required Information → Tool Requirement → Graph Node
```

Example:

```text
Rule:
  separate_facts_from_hypotheses

Information required:
  trace evidence
  eval history
  recent changes
  tool health

Graph impact:
  collect_evidence
  normalize_evidence
  separate_facts_hypotheses_unknowns
```

### Graph Diagram

```text
start
  ↓
parse_escalation_report
  ↓
collect_evidence
  ├── fetch_customer_report
  ├── fetch_trace_summary
  ├── fetch_eval_results
  ├── fetch_recent_changes
  ├── fetch_tool_health
  └── fetch_customer_context
  ↓
normalize_evidence
  ↓
identify_correlations
  ↓
separate_facts_hypotheses_unknowns
  ↓
assess_customer_impact
  ↓
recommend_mitigation_plan
  ↓
draft_customer_update
  ↓
customer_safe_update_review
  ↓
final_response
```

### Node Detail Panel

Selecting a node should show:

- Node purpose
- Rules supported
- Information requirements used
- Tool requirements used
- Tool binding status
- Prompt used
- State fields read
- State fields written
- Recent failures involving this node
- Trace examples

### Example Node Detail

```yaml
node:
  id: separate_facts_hypotheses_unknowns
  purpose: >
    Prevent unsupported diagnosis by separating confirmed facts,
    plausible hypotheses, and unknowns before recommending actions.
  supports_rules:
    - separate_facts_from_hypotheses
    - evidence_first_diagnosis
  reads_state:
    - normalized_evidence
    - trace_summary
    - eval_history
    - recent_changes
    - tool_health
  writes_state:
    - confirmed_facts
    - hypotheses
    - unknowns
```

The graph should be explainable from the eval contract.

---

## 13. Prompts Workspace

The Prompts workspace shows prompt artifacts connected to nodes and rules.

### Prompt Card

```text
Prompt: facts_hypotheses_unknowns.md
Used by node:
  separate_facts_hypotheses_unknowns

Supports rules:
  - separate_facts_from_hypotheses
  - evidence_first_diagnosis

Latest failure:
  v0 overclaimed root cause without evidence.

Current instruction:
  Do not claim a confirmed root cause unless the evidence threshold is met.
```

### Actions

- View prompt
- Edit prompt
- Compare prompt versions
- Preview prompt with scenario data
- Run prompt-level eval
- View failures tied to prompt

Prompts should not be floating text files. They should be tied to graph nodes and rules.

---

## 14. Tool Bindings Workspace

The Tool Bindings workspace shows which implementation is active for each requirement.

### Binding Table

| Graph Node | Requirement | Active Implementation | Mode | Status |
|---|---|---|---|---|
| collect_trace_evidence | Trace evidence | fetch_trace_summary_mock | Mock | Available |
| collect_eval_history | Eval history | fetch_eval_results_local | Local | Available |
| collect_recent_changes | Recent changes | fetch_recent_changes_mock | Mock | Available |
| collect_tool_health | Tool health | fetch_tool_health_mock | Mock | Available |

### Actions

- Switch binding
- Test tool
- View sample response
- Create live connector task
- Mark binding unsafe
- Require approval

This screen is especially important for honesty. The user should know whether they are running against mock data or live systems.

---

## 15. Versions Workspace

The Versions workspace shows the evolution of the agent.

### Version Timeline

```text
v0-baseline
  Single-pass prompt agent.
  Gate: FAIL
  Main failure: unsupported root-cause claim.

v1-evidence-triage-graph
  Adds evidence collection and facts/hypotheses split.
  Gate: PASS FOR DEMO
  Production: BLOCKED, mock tools.

v2-live-trace-reader
  Replaces mock trace summary with Langfuse API.
  Gate: PASS FOR INTERNAL USE
  Production: PARTIAL.
```

### Version Detail

- Version ID
- Source version
- Target ID
- Eval contract ID
- Fix plan ID
- Graph summary
- Prompt changes
- Tool binding changes
- Run history
- Gate history
- Promotion status

### Actions

- Create baseline version
- Create candidate from fix plan
- Compare with previous
- Run eval suite
- Promote
- Reject
- Deprecate

Versions should tell a design story, not just show commits.

---

## 16. Runs Workspace

The Runs workspace executes agent versions against scenarios.

### Run Configuration

- Agent
- Version
- Target
- Eval contract
- Scenario set
- Tool mode
- Model
- Evaluator
- Trace destination
- Environment

### Run Result Summary

- Run ID
- Started / completed
- Scenario count
- Pass rate
- Average score
- Failed rules
- Hard gate status
- Warning count
- Tool readiness status
- Token usage
- Cost
- Latency
- Trace links

### Actions

- Run selected scenario
- Run full suite
- Run variants
- Run regression suite
- Publish to platform
- Open traces in Langfuse
- Generate failure packets
- Compare to previous version

A run should always be associated with target, contract, version, tool mode, and scenario set.

---

## 17. Traces Workspace

The Traces workspace connects platform decisions to Langfuse evidence.

The platform should not replace Langfuse, but it should summarize trace evidence in platform context.

### Trace Table

| Trace | Scenario | Version | Score | Failed Rules | Cost | Latency | Tool Mode |
|---|---|---|---:|---|---:|---:|---|
| trace_v0_abc123 | escalation-latency | v0 | 2.4 | Root cause overclaim | $0.03 | 4.2s | none |
| trace_v1_def456 | escalation-latency | v1 | 4.4 | none | $0.06 | 6.8s | mock/local |

### Trace Detail

- User input
- Graph path taken
- Tool calls
- Model calls
- Final output
- Evaluator scores
- Failed rules
- Failure packets
- Open in Langfuse

### Actions

- Open in Langfuse
- Create failure packet
- Attach trace to existing failure packet
- Annotate trace
- Compare trace to previous version

The trace view should answer:

- What actually happened?
- Which rule did it satisfy or violate?
- What evidence supports the score?

---

## 18. Failure Packets Workspace

Failure packets are the bridge between eval failure and design change.

### Failure Packet Card

```text
Failure: Unsupported root-cause claim
Rule: separate_facts_from_hypotheses
Severity: Critical
Version: v0-baseline
Scenario: escalation-latency-quality-regression-001
Trace: trace_v0_abc123
Status: Resolved in v1
```

### Failure Packet Detail

```yaml
failure_packet:
  id: fp-v0-unsupported-root-cause
  version: v0-baseline
  failed_rule: separate_facts_from_hypotheses
  observed_behavior: >
    The agent stated that the summarization prompt change was the likely cause
    and recommended telling the customer the issue had been found.
  expected_behavior: >
    The agent should have separated confirmed facts from hypotheses.
  suspected_cause: >
    v0 has no explicit evidence normalization or facts/hypotheses/unknowns step.
  recommended_fix: >
    Add normalize_evidence and separate_facts_hypotheses_unknowns nodes.
```

### Actions

- Create fix plan
- Mark as resolved
- Accept as known risk
- Link to graph node
- Link to prompt
- Open trace
- Compare resolved behavior

The failure packet should make the next design change obvious and bounded.

---

## 19. Fix Plans Workspace

The Fix Plans workspace converts failure packets into bounded changes.

### Fix Plan Sections

- Source version
- Target version
- Failed rules addressed
- Graph changes
- Prompt changes
- Tool changes
- Non-goals
- Regression risks
- Overfitting risks
- Acceptance criteria

### Example

```yaml
fix_plan:
  id: fix-v1-evidence-first-triage
  source_version: v0-baseline
  target_version: v1-evidence-triage-graph
  failed_rules_addressed:
    - evidence_first_diagnosis
    - separate_facts_from_hypotheses
  graph_changes:
    - Add collect_evidence node.
    - Add normalize_evidence node.
    - Add separate_facts_hypotheses_unknowns node.
  tool_changes:
    - Add mock trace summary tool.
    - Add mock recent changes tool.
  non_goals:
    - Do not automatically roll back production.
    - Do not claim production readiness while tools are mock-only.
```

### Actions

- Generate fix plan from failures
- Edit fix plan
- Create candidate version
- Run candidate
- Compare against source version

Fix plans should prevent uncontrolled redesign.

---

## 20. Compare Versions Workspace

This is the core demo screen.

The Compare Versions workspace should make the v0 → v1 improvement obvious.

### Header

```text
Agent: Customer Escalation Triage Agent
Target: customer-escalation-triage-target-v1
Eval Contract: escalation-triage-eval-contract-v1
Compare: v0-baseline vs v1-evidence-triage-graph
Scenario: escalation-latency-quality-regression-001
```

### Side-by-Side Behavior

```text
┌──────────────────────────────────────┬──────────────────────────────────────┐
│ v0-baseline                          │ v1-evidence-triage-graph             │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ Claims prompt change is likely cause │ Separates facts, hypotheses, unknowns│
│ Recommends telling customer issue    │ Says root cause is not confirmed     │
│ was found                            │                                      │
│ Ignores tool timeout uncertainty     │ Considers prompt, scanned PDFs, tool │
│                                      │ timeouts, and latency together       │
│ Gate: FAIL                           │ Gate: PASS FOR DEMO                  │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

### Score Delta

```text
Diagnostic grounding
  v0: 2
  v1: 5
  delta: +3

Customer communication quality
  v0: 2
  v1: 5
  delta: +3

Action plan quality
  v0: 3
  v1: 4
  delta: +1
```

### Comparison Sections

- Resolved failures
- New failures
- Regression warnings
- Tool readiness differences
- Cost delta
- Latency delta
- Trace links
- Gate result
- Promotion recommendation

The comparison should answer:

- Did v1 improve because it satisfied the target better?
- Did it introduce regressions?
- Is the improvement supported by trace evidence?
- Is it ready for demo, internal use, or production?

---

## 21. Gates Workspace

The Gates workspace separates behavior gates from readiness gates.

### Gate Summary

```text
Overall:
  PASS FOR DEMO, BLOCKED FOR PRODUCTION

Behavior gates:
  no_unsupported_root_cause: PASS
  must_separate_facts_and_hypotheses: PASS
  must_include_safe_next_actions: PASS

Tool readiness gates:
  required_tools_available_for_demo: PASS
  required_tools_available_for_production: FAIL

Operational gates:
  no_write_actions_without_approval: PASS
  customer_update_safe_for_external_use: PASS
```

### Gate Detail

Each gate should show:

- Gate name
- Gate type
- Condition
- Result
- Evidence
- Affected scenarios
- Trace links
- Failure packet links
- Recommendation

### Actions

- View failing evidence
- Create fix plan
- Mark accepted risk
- Re-run gate
- Promote with warning
- Block promotion

Gates should drive decisions, not just decorate a scorecard.

---

## 22. Promotion Workspace

The Promotion workspace records the final decision.

### Promotion Options

- Promote for demo
- Promote for internal use
- Promote for production assistive use
- Promote for controlled automation
- Reject version
- Accept with risk
- Deprecate previous version

### Promotion Record

```yaml
promotion_record:
  agent_id: customer-escalation-triage-agent
  promoted_version: v1-evidence-triage-graph
  previous_version: v0-baseline
  decision: promoted_for_demo
  production_status: blocked
  rationale: >
    v1 resolves the critical unsupported-root-cause failure from v0 by adding
    evidence normalization and facts/hypotheses/unknowns separation. It passes
    behavior gates but remains blocked for production because trace, recent-change,
    and tool-health tools are mock-only.
```

### Actions

- Approve promotion
- Reject version
- Request changes
- Accept risk
- Generate promotion summary
- Export decision record

Promotion should be a first-class historical artifact.

---

## 23. Live Run Workspace

The Live Run workspace is for using a promoted agent operationally.

This is important because many agents are not just artifacts to evaluate. They are assistants people use repeatedly.

### Live Run Header

```text
Agent: Customer Escalation Triage Agent
Active Version: v1-evidence-triage-graph
Promotion: PROMOTED FOR DEMO
Production Status: BLOCKED
Tool Mode: MOCK/LOCAL
```

### Runtime Warning

If tool mode is not production-ready, the console should show a clear warning:

```text
This run uses mock/local tools. It is suitable for demo and evaluation only.
Do not use this output as a production escalation diagnosis.
```

### Live Run Input

```text
Customer: Apex Health

Escalation: AI assistant is giving inconsistent answers this week.
Latency is worse. Reviewer confidence is dropping.

Known signals: Prompt changed two days ago. Eval scores dropped for scanned PDF cases.
Eligibility-check tool has intermittent timeouts.
```

### Live Run Output Sections

- Summary
- Confirmed facts
- Hypotheses
- Unknowns
- Recommended immediate actions
- Investigation plan
- Customer-safe update draft
- Actions requiring approval
- Trace links

### Actions

- Run agent
- Save run
- Create incident note
- Draft customer update
- Create follow-up tasks
- Open trace
- Run post-hoc eval

Write actions should require approval unless the version is explicitly promoted for controlled automation.

---

## 24. Action Queue Workspace

The Action Queue shows recommended actions that require approval.

Example:

```text
Recommended Action: Draft customer update
Status: Awaiting approval
Risk: External communication
Evidence: Based on v1 triage output and customer-safe update review.
Action: Review / Edit / Approve / Reject
```

Other possible actions:

- Create Jira ticket
- Comment on GitHub issue
- Trigger eval rerun
- Open incident
- Create rollback proposal
- Notify owner

The action queue keeps operation safe.

---

## 25. Run History Workspace

Run History shows operational and evaluation runs together.

### Table

| Run | Type | Version | Tool Mode | Gate | Score | Date |
|---|---|---|---|---|---:|---|
| run_v0_001 | Eval | v0 | none | Fail | 2.4 | May 30 |
| run_v1_001 | Eval | v1 | mock/local | Pass demo | 4.4 | May 30 |
| op_run_001 | Live | v1 | mock/local | Demo only | n/a | May 30 |

### Actions

- Open run
- Compare runs
- Open traces
- Create failure packet
- Export run record

This helps prove that live use remains traceable.

---

## 26. Artifacts Workspace

Artifacts are the file-level outputs of the EDD process.

### Artifact Types

```text
agent-target.yaml
behavior-rules.yaml
eval-contract.yaml
information-requirements.yaml
tool-requirements.yaml
tool-feasibility.yaml
tool-bindings.yaml
graph-design.yaml
prompts/
run-output.json
eval-summary.json
failure-packets/
fix-plan.yaml
comparison.json
gate-result.yaml
promotion-record.yaml
trace-links.json
```

### Actions

- View artifact
- Copy artifact
- Download artifact
- Publish to platform
- Open in repo
- Compare artifact versions

Artifacts should be useful for local dev, Cursor handoff, and auditability.

---

## 27. Settings Workspace

Settings should include:

- Model configuration
- Evaluator configuration
- Trace destination
- Langfuse project/environment
- Platform API endpoint
- Tool mode defaults
- Approval policy
- Promotion policy
- Scenario set defaults
- Cost limits
- Latency limits

The settings screen should make it clear when the console is in:

- local demo mode
- platform-connected mode
- live read-only mode
- production assistive mode
- controlled automation mode

---

## 28. Ideal First-Time User Flow

The first-time flow should be guided.

| Step | Action |
|---|---|
| 1 | **Describe agent** — What should it help with? Who will use it? What should it avoid? What data or tools might it need? |
| 2 | **Review generated target** — User reviews and approves the target. |
| 3 | **Review rules and eval contract** — System proposes rules, metrics, and gates. |
| 4 | **Review information and tool requirements** — System explains what information the agent needs and what tools could provide it. |
| 5 | **Review tool feasibility** — System identifies missing, mock-only, local, or live tools. |
| 6 | **Generate graph design** — System proposes the LangGraph structure. |
| 7 | **Create v0** — **edd-agent-lab** creates a baseline version. |
| 8 | **Run v0** — Evaluator scores v0. |
| 9 | **Inspect failure packet** — User sees why v0 failed. |
| 10 | **Generate v1 fix plan** — System proposes bounded changes. |
| 11 | **Run and compare v1** — User sees whether the fix worked. |
| 12 | **Promote** — User promotes for demo, internal use, or production depending on gates and tool readiness. |

---

## 29. Ideal Demo Story

A strong demo should be understandable in one minute.

```text
We created a Customer Escalation Triage Agent.

The platform generated target behavior, rules, evals, information requirements, and tool requirements.
It noticed that the agent needs traces, eval history, recent changes, and tool health.
It also noticed some of those tools are only mock implementations.

v0 was a single-pass prompt agent. It failed because it overclaimed root cause.

The failure packet tied that behavior to the rule: separate facts from hypotheses.

The fix plan added an evidence-first graph:
  collect evidence
  normalize evidence
  separate facts, hypotheses, and unknowns
  review the customer update for safety

v1 passed the behavior gates.

But the console still marks production readiness as blocked because several required tools are mock-only.

So v1 is promoted for demo, not production.
```

That is the product.

---

## 30. Visual Design Direction

The console should feel:

- modern
- technical
- structured
- calm
- evidence-driven
- developer-friendly
- high signal
- not cluttered

Recommended visual patterns:

- Dark or neutral workspace
- Strong top context bar
- Left lifecycle navigation
- Cards for target/rules/gates
- Tables for requirements and feasibility
- Side-by-side panels for version comparison
- Badges for readiness and status
- Trace links near every score
- Inline YAML/code artifact previews
- Graph diagram with node detail drawer

The console should not feel like a generic admin dashboard.

It should feel like a cockpit for designing and operating AI agents.

---

## 31. MVP Console Scope

The first console milestone should avoid building everything.

### MVP Screens

```text
Overview
Target
Rules
Eval Contract
Information Requirements
Tool Requirements
Tool Feasibility
Graph Design
Runs
Failure Packets
Fix Plans
Compare Versions
Gates
Promotion
Artifacts
```

### MVP Capabilities

- Create/load target
- Generate rules
- Generate eval contract
- Generate information requirements
- Generate tool requirements
- Show tool feasibility
- Bind mock tools
- Show graph design
- Run v0
- Show eval summary
- Generate failure packet
- Generate v1 fix plan
- Compare v0 and v1
- Show behavior gates
- Show production readiness gates
- Promote for demo
- Export artifacts

### MVP Non-Goals

- No full live connector marketplace
- No automatic production actions
- No uncontrolled write tools
- No automatic promotion
- No claim of production readiness with mock-only tools

This MVP would prove the real EDD loop.

---

## 32. Second Console Milestone

### Graph-Aware and Trace-Aware Console

Add:

- Interactive graph diagram
- Rule-to-node mapping
- Tool-to-node mapping
- Node-level trace evidence
- Prompt diff view
- Trace comparison between v0 and v1
- Langfuse deep links
- Scenario variant results
- Regression warnings
- Overfitting checks

This milestone makes the LangGraph connection explicit.

---

## 33. Third Console Milestone

### Operational Agent Console

Add:

- Live Run workspace
- Action Queue
- Approval-gated actions
- Operational run history
- Read-only live connectors
- Runtime warnings
- Post-run eval
- Internal-use promotion
- Production-assistive promotion

This milestone turns the EDD stack from a design/eval platform into an operating environment for validated agents.

---

## 34. Summary

The ideal **eval-driven-design-platform** console should make the full agent lifecycle visible:

```text
Define intent.
Generate rules.
Generate evals.
Identify required information.
Identify required tools.
Check whether those tools exist.
Shape the graph.
Run v0.
Capture evidence.
Diagnose failure.
Plan bounded fixes.
Run v1.
Compare behavior.
Apply gates.
Promote with honesty.
Operate with traceability.
```

The most important UX principle is honesty.

The console should never imply that a version is production-ready just because it scored well on mock data.

It should clearly separate:

- Behavior quality
- Tool readiness
- Operational readiness
- Promotion decision

That distinction is what makes the product credible.

The EDD stack should feel like a systematic workspace for turning agent intent, evidence, tools, and evaluation into better agent design.

---

## 35. Relationship to edd-agent-lab

The platform console owns design intent, workflow state, gates, and promotion.

**edd-agent-lab** owns implementation, local runs, graph execution, and side-by-side comparison during development.

The lab publishes run results to the platform via `POST /v1/integrations/runs/publish`. The platform console surfaces those runs alongside platform-native experiment runs.

See also:

- `docs/10-ideal-developer-experience.md` — full EDD lifecycle and artifact model
- `docs/09-developer-experience-today.md` — what exists now
- `docs/05-platform-integration.md` — HTTP publish seam
