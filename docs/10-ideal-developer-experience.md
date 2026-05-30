# Ideal Evaluation-Driven Design State

This document describes the ideal state for **edd-agent-lab** and **eval-driven-design-platform**: a two-repo workflow for designing, evaluating, improving, and operating AI agents through an evidence-driven loop.

This is not a description of the current implementation. It is the target product model.

The central idea is:

> Start by defining what good agent behavior means.  
> Turn that definition into rules, evals, information requirements, tool requirements, graph design, trace-backed evidence, failure packets, bounded fixes, and version decisions.

Evaluation is not a final report.

Evaluation is part of the design process.

---

## 1. One-Line Vision

The EDD stack helps teams build better AI agents by connecting intent, evaluation, tools, traces, failures, fixes, and promotion decisions into one disciplined design loop.

```text
target → rules → eval contract → information requirements → tool requirements
  → tool feasibility → graph design → v0 → trace evidence → failure packets
  → bounded fix → v1 → comparison → gates → promotion → operation
```

The product should make this loop visible, inspectable, and repeatable.

---

## 2. What the EDD Stack Is

This is not just an eval dashboard.

It is an agent design system spanning the lab (implementation) and the platform (workflow registry).

It helps a developer answer:

- What is this agent supposed to do?
- What does good behavior mean?
- What information does the agent need?
- What tools are required to get that information?
- Do those tools actually exist?
- How should the graph be shaped by the rules?
- How did the agent behave?
- Where did it fail?
- What evidence proves the failure?
- What should change?
- Did the new version improve?
- Is the version safe to promote?
- Can this version be used operationally?

The goal is to reduce “vibe-based agent iteration” and replace it with traceable, evidence-backed design decisions.

---

## 3. Product Roles

The ideal system has three major parts.

### eval-driven-design-platform

Owns design intent and workflow state:

- agent targets
- behavior rules
- eval contracts
- information requirements
- tool requirements
- tool feasibility
- quality gates
- version registry
- run registry
- failure packets
- fix plans
- comparisons
- promotion decisions
- operational readiness

### edd-agent-lab

Owns concrete agent implementation:

- LangGraph code
- prompts
- local tools
- mock tools
- live tool bindings
- local runs
- generated artifacts
- side-by-side development console
- versioned implementation folders

### Langfuse

Owns trace evidence:

- traces, spans, generations
- model inputs and outputs
- tool calls, latency, cost, token usage
- scores, datasets, experiments, annotations

The platform owns the meaning.

The lab owns the implementation.

Langfuse owns the evidence.

---

## 4. Core Principle

The strongest version of evaluation-driven design is not:

```text
Build an agent → run evals afterward → look at the score → make changes
```

The stronger version is:

```text
Define target behavior → derive evaluable rules → identify required information
→ identify required tools → check tool feasibility → design the graph
→ run the agent → capture traces → diagnose failures → make bounded fixes
→ verify improvement → promote only with evidence
```

This distinction is essential.

The platform and lab should ensure the agent is not merely scored after the fact. The agent should be shaped by the target, the rules, and the available evidence.

---

## 5. Ideal Workflow

The ideal workflow begins before an agent exists.

```text
Create Agent Target
        ↓
Generate Behavior Rules
        ↓
Generate Eval Contract
        ↓
Generate Information Requirements
        ↓
Generate Tool Requirements
        ↓
Review Tool Feasibility
        ↓
Create Tool Bindings
        ↓
Generate Graph Design
        ↓
Create v0 Implementation
        ↓
Run v0 → Collect Trace Evidence → Evaluate Against Contract
        ↓
Generate Failure Packets → Generate Bounded Fix Plan
        ↓
Create v1 → Compare v0 and v1 → Apply Gates
        ↓
Promote, Reject, or Accept with Risk → Operate Promoted Agent
```

The workflow should support both:

- **Design-time:** Is the agent built correctly?
- **Run-time:** Is the promoted agent useful and safe to use today?

---

## 6. Step 1: Create the Agent Target

The first user input should be a short description of the agent’s purpose.

The user should not need to manually write every downstream artifact.

The user should define intent.

**Example user input:**

```text
I want an agent that helps Forward Deployed Engineers triage customer escalations
for AI deployments. It should look at traces, eval results, recent changes, tool
failures, and customer reports. It should identify likely causes, recommend safe
next actions, and help draft a customer update. It must not invent root causes or
blame systems without evidence.
```

From this, the platform generates an agent target:

```yaml
agent_target:
  id: customer-escalation-triage-target-v1
  name: Customer Escalation Triage Agent
  purpose: >
    Help Forward Deployed Engineers triage customer escalations in AI deployments
    by synthesizing customer reports, traces, eval results, recent changes, and
    tool health into a grounded diagnosis and action plan.
  intended_users:
    - Forward Deployed Engineers
    - Platform Engineers
    - Customer deployment leads
    - AI support engineers
  primary_goals:
    - Summarize the customer-reported problem.
    - Identify relevant evidence from traces, evals, tool status, and recent changes.
    - Separate confirmed facts from hypotheses.
    - Identify likely root-cause candidates without overclaiming.
    - Recommend immediate mitigation steps.
    - Recommend follow-up investigation steps.
    - Draft a customer-safe status update.
  non_goals:
    - Do not claim a confirmed root cause without evidence.
    - Do not blame the customer, model provider, or internal team prematurely.
    - Do not expose sensitive trace details in a customer-facing message.
    - Do not suggest destructive production changes without explicit approval.
```

The target becomes the root design artifact. Everything downstream should trace back to it.

---

## 7. Step 2: Generate Behavior Rules

Behavior rules convert intent into explicit expectations.

```yaml
behavior_rules:
  - id: evidence_first_diagnosis
    severity: critical
    description: >
      The agent must base diagnosis on available evidence from traces, evals,
      recent changes, customer reports, and tool health.
  - id: separate_facts_from_hypotheses
    severity: critical
    description: >
      The agent must distinguish confirmed facts from likely causes and unknowns.
  - id: identify_recent_changes
    severity: high
    description: >
      The agent must check whether recent prompts, model settings, tools, configs,
      deployments, or data changes correlate with the issue.
  - id: assess_customer_impact
    severity: high
    description: >
      The agent must describe customer impact, affected workflows, severity,
      and urgency where evidence is available.
  - id: recommend_safe_next_actions
    severity: high
    description: >
      The agent must recommend safe, sequenced mitigation and investigation steps.
  - id: draft_customer_safe_update
    severity: medium
    description: >
      The agent should produce a concise customer-facing update that avoids
      speculation and sensitive internal details.
```

Rules should be user-reviewable. The system may generate them, but the user should be able to approve, edit, disable, or add rules.

---

## 8. Step 3: Generate Eval Contract

The eval contract turns rules into measurable checks.

```yaml
eval_contract:
  id: customer-escalation-triage-eval-contract-v1
  target_id: customer-escalation-triage-target-v1
  metrics:
    - id: diagnostic_grounding
      scale: 0-5
      rules:
        - evidence_first_diagnosis
        - separate_facts_from_hypotheses
    - id: change_correlation_quality
      scale: 0-5
      rules:
        - identify_recent_changes
    - id: impact_assessment_quality
      scale: 0-5
      rules:
        - assess_customer_impact
    - id: action_plan_quality
      scale: 0-5
      rules:
        - recommend_safe_next_actions
    - id: customer_communication_quality
      scale: 0-5
      rules:
        - draft_customer_safe_update
  gates:
    - id: no_unsupported_root_cause
      type: hard
      condition: diagnostic_grounding >= 4
    - id: must_separate_facts_and_hypotheses
      type: hard
      condition: diagnostic_grounding >= 4
    - id: must_include_safe_next_actions
      type: hard
      condition: action_plan_quality >= 4
    - id: customer_update_must_be_safe
      type: warning
      condition: customer_communication_quality >= 4
```

The eval contract is not just for scoring. It should influence the graph, information requirements, tool requirements, and acceptance gates.

---

## 9. Step 4: Generate Information Requirements

Before generating tools, the system should identify what information the agent needs to satisfy the rules.

```yaml
information_requirements:
  - id: customer_report
    required_for_rules:
      - evidence_first_diagnosis
      - assess_customer_impact
    description: >
      The customer-provided report of the problem, including affected workflows,
      reported symptoms, timing, and urgency.
  - id: trace_evidence
    required_for_rules:
      - evidence_first_diagnosis
      - separate_facts_from_hypotheses
    description: >
      Recent traces for the affected workflow, including model calls, tool calls,
      latency, failed spans, and error patterns.
  - id: eval_history
    required_for_rules:
      - evidence_first_diagnosis
      - identify_recent_changes
    description: >
      Recent eval results and score trends for the affected workflow, scenario,
      model, prompt, or deployment version.
  - id: recent_changes
    required_for_rules:
      - identify_recent_changes
    description: >
      Recent prompt, model, tool, config, deployment, code, or dataset changes
      that could correlate with the reported issue.
  - id: tool_health
    required_for_rules:
      - evidence_first_diagnosis
      - recommend_safe_next_actions
    description: >
      Health, timeout, failure, or latency status for tools used by the deployed agent.
  - id: customer_context
    required_for_rules:
      - assess_customer_impact
      - draft_customer_safe_update
    description: >
      Customer metadata, affected environment, deployment stage, business impact,
      and communication constraints.
```

This step prevents inventing tools before clarifying what information is actually needed.

---

## 10. Step 5: Generate Tool Requirements

Tool requirements are derived from information requirements.

The system should not assume these tools exist. It should say: given the rules, the agent needs information; these are the kinds of tools that could provide that information.

```yaml
tool_requirements:
  - id: customer_report_source
    information_requirement_id: customer_report
    suggested_tool_name: fetch_customer_report
    access_mode: read_only
    purpose: Retrieve the customer-reported issue, symptoms, timeline, and impact.
  - id: trace_evidence_source
    information_requirement_id: trace_evidence
    suggested_tool_name: fetch_trace_summary
    access_mode: read_only
    purpose: Retrieve trace-level evidence for the affected customer, workflow, and time period.
  - id: eval_history_source
    information_requirement_id: eval_history
    suggested_tool_name: fetch_eval_results
    access_mode: read_only
    purpose: Retrieve recent eval score trends and failures for the affected workflow.
  - id: recent_changes_source
    information_requirement_id: recent_changes
    suggested_tool_name: fetch_recent_changes
    access_mode: read_only
    purpose: Retrieve recent prompt, model, tool, config, deployment, or code changes.
  - id: tool_health_source
    information_requirement_id: tool_health
    suggested_tool_name: fetch_tool_health
    access_mode: read_only
    purpose: Retrieve recent tool failures, timeout rates, and latency trends.
  - id: customer_context_source
    information_requirement_id: customer_context
    suggested_tool_name: fetch_customer_context
    access_mode: read_only
    purpose: Retrieve customer deployment context and communication constraints.
```

This is a requirements inventory, not yet an implementation.

---

## 11. Step 6: Review Tool Feasibility

Tool feasibility is first-class. The system must distinguish:

| Question | Meaning |
|----------|---------|
| Required information | What information is needed? |
| Suggested tool | What kind of tool could provide it? |
| Available implementation | Does that tool exist today? |
| Production feasibility | Can we use it safely and reliably? |

```yaml
tool_feasibility:
  - requirement_id: trace_evidence_source
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
  - requirement_id: eval_history_source
    suggested_tool_name: fetch_eval_results
    implementation_status: available_local
    mvp_strategy: local_eval_summary_json
    production_strategy: platform_run_database
    feasibility_status: feasible
  - requirement_id: recent_changes_source
    suggested_tool_name: fetch_recent_changes
    implementation_status: not_implemented
    mvp_strategy: mock_changelog_json
    production_strategy: github_or_gitlab_api
    feasibility_status: needs_review
  - requirement_id: tool_health_source
    suggested_tool_name: fetch_tool_health
    implementation_status: not_implemented
    mvp_strategy: mock_tool_health_json
    production_strategy: metrics_or_logs_api
    feasibility_status: needs_review
```

The platform should never pretend an agent is production-ready because a graph contains imaginary tools.

---

## 12. Step 7: Create Tool Bindings

A tool requirement can have multiple implementations.

```yaml
tool_implementations:
  - implementation_id: fetch_trace_summary_mock
    requirement_id: trace_evidence_source
    mode: mock
    status: available
    backing_source: data/mock/escalations/apex_health/langfuse_trace_summary.json
  - implementation_id: fetch_trace_summary_live
    requirement_id: trace_evidence_source
    mode: live
    status: not_implemented
    backing_source: Langfuse API
  - implementation_id: fetch_eval_results_local
    requirement_id: eval_history_source
    mode: local
    status: available
    backing_source: outputs/eval-summary.json

tool_bindings:
  - graph_node: collect_trace_evidence
    requirement_id: trace_evidence_source
    active_implementation: fetch_trace_summary_mock
    environment: local_demo
  - graph_node: collect_eval_history
    requirement_id: eval_history_source
    active_implementation: fetch_eval_results_local
    environment: local_demo
```

This enables an honest path:

- Use mocks for design/eval.
- Use read-only live tools for realistic operation.
- Use approval-gated write tools later.

The graph can remain stable while tool implementations mature.

---

## 13. Step 8: Generate Graph Design

Only after rules, information requirements, and tool feasibility are known should the system generate graph design.

```text
start
  ↓ parse_escalation_report
  ↓ collect_evidence
      ├── fetch_customer_report
      ├── fetch_trace_summary
      ├── fetch_eval_results
      ├── fetch_recent_changes
      ├── fetch_tool_health
      └── fetch_customer_context
  ↓ normalize_evidence
  ↓ identify_correlations
  ↓ separate_facts_hypotheses_unknowns
  ↓ assess_customer_impact
  ↓ recommend_mitigation_plan
  ↓ draft_customer_update
  ↓ customer_safe_update_review
  ↓ final_response
```

The graph is shaped by the rules.

| Rule | Required behavior | Graph impact |
|------|-------------------|--------------|
| evidence_first_diagnosis | Gather and normalize evidence | collect_evidence, normalize_evidence |
| identify_recent_changes | Check prompt/config/deploy changes | fetch_recent_changes |
| separate_facts_from_hypotheses | Prevent overclaiming | separate_facts_hypotheses_unknowns |
| assess_customer_impact | Describe affected workflows and severity | assess_customer_impact |
| draft_customer_safe_update | Avoid speculation in customer language | customer_safe_update_review |

This is where the EDD stack proves it is doing design, not just evaluation.

---

## 14. Step 9: Generate v0

v0 is a baseline implementation tied to a target and eval contract.

v0 should be intentionally simple enough to expose gaps.

```yaml
agent_version:
  id: v0-baseline
  target_id: customer-escalation-triage-target-v1
  eval_contract_id: customer-escalation-triage-eval-contract-v1
  implementation_summary: >
    Single-pass prompt agent. No explicit evidence collection. No tool bindings.
    No facts/hypotheses separation. No customer-safe update review.
  expected_failure_modes:
    - May overclaim root cause.
    - May ignore recent changes or tool health.
    - May produce vague next steps.
    - May draft customer updates with too much speculation.
```

v0 is valuable because it creates a baseline and demonstrates why the rules matter.

---

## 15. Step 10: Run v0

The lab runs v0 against scenarios.

```yaml
scenario:
  id: escalation-latency-quality-regression-001
  name: Latency and Quality Regression After Prompt Change
  user_prompt: >
    Customer Apex Health says their AI assistant started giving inconsistent answers
    this week. They say latency is worse and their reviewers are losing confidence.
    We changed the summarization prompt two days ago. Langfuse shows latency is up,
    eval scores dropped for scanned PDF cases, and the eligibility-check tool has
    intermittent timeouts. Help me triage and draft an update.
  expected_behavior:
    - Summarize the customer issue.
    - Identify known facts.
    - Identify hypotheses without claiming certainty.
    - Consider prompt change, scanned PDF eval drop, latency, and tool timeouts.
    - Recommend safe immediate actions.
    - Recommend investigation steps.
    - Draft a customer-safe update.
```

**Possible v0 response (useful failure):**

```text
The likely cause is the summarization prompt change from two days ago. I recommend
rolling it back and telling the customer we found the issue. The latency increase
is probably related to the bad prompt causing longer generations.
```

It sounds plausible, but it overclaims.

---

## 16. Step 11: Capture Trace Evidence

The run should be registered by the platform and linked to Langfuse.

Every trace should include platform metadata.

```json
{
  "platform_run_id": "run_v0_001",
  "platform_agent_id": "customer-escalation-triage-agent",
  "platform_agent_version": "v0-baseline",
  "platform_target_id": "customer-escalation-triage-target-v1",
  "platform_eval_contract_id": "customer-escalation-triage-eval-contract-v1",
  "scenario_id": "escalation-latency-quality-regression-001",
  "environment": "local_demo"
}
```

**Langfuse provides:** exact model input/output, graph path, tool calls, latency, cost, tokens, scores, span-level evidence, annotations.

**The platform provides:** target meaning, rule meaning, version meaning, gate result, failure packet, fix plan, promotion decision.

---

## 17. Step 12: Evaluate v0

```yaml
eval_summary:
  version: v0-baseline
  scenario_id: escalation-latency-quality-regression-001
  scores:
    diagnostic_grounding: 2
    change_correlation_quality: 3
    impact_assessment_quality: 2
    action_plan_quality: 3
    customer_communication_quality: 2
  gate_status: fail
  failed_gates:
    - no_unsupported_root_cause
    - must_separate_facts_and_hypotheses
    - customer_update_must_be_safe
```

The failure should be rule-specific — not just “Bad answer,” but:

```text
Failed critical rule: separate_facts_from_hypotheses
```

---

## 18. Step 13: Generate Failure Packets

Failure packets connect eval failure to design change.

```yaml
failure_packet:
  id: fp-v0-unsupported-root-cause
  version: v0-baseline
  scenario_id: escalation-latency-quality-regression-001
  failed_rule: separate_facts_from_hypotheses
  severity: critical
  observed_behavior: >
    The agent stated that the summarization prompt change was the likely cause
    and recommended telling the customer the issue had been found.
  expected_behavior: >
    The agent should have separated confirmed facts from hypotheses. It should
    have treated the prompt change, scanned PDF eval drop, latency increase, and
    tool timeouts as candidate contributing factors requiring investigation.
  suspected_cause: >
    v0 has no explicit evidence normalization or facts/hypotheses/unknowns step.
  trace_evidence:
    langfuse_trace_id: trace_v0_abc123
    platform_run_id: run_v0_001
  recommended_fix: >
    Add normalize_evidence and separate_facts_hypotheses_unknowns nodes before
    mitigation planning or customer communication.
```

This prevents vague improvement instructions.

---

## 19. Step 14: Generate Bounded Fix Plan

```yaml
fix_plan:
  id: fix-v1-evidence-first-triage
  source_version: v0-baseline
  target_version: v1-evidence-triage-graph
  failed_rules_addressed:
    - evidence_first_diagnosis
    - separate_facts_from_hypotheses
    - recommend_safe_next_actions
    - draft_customer_safe_update
  graph_changes:
    - Add collect_evidence node.
    - Add normalize_evidence node.
    - Add identify_correlations node.
    - Add separate_facts_hypotheses_unknowns node.
    - Add customer_safe_update_review node.
  tool_changes:
    - Add mock trace summary tool.
    - Add mock eval results tool.
    - Add mock recent changes tool.
    - Add mock tool health tool.
  prompt_changes:
    - Require output sections for Facts, Hypotheses, Unknowns, Immediate Actions,
      Investigation Plan, and Customer Update.
    - Forbid confirmed-root-cause language unless evidence threshold is met.
    - Require customer-facing update to avoid internal trace details and speculation.
  non_goals:
    - Do not automatically roll back production.
    - Do not contact the customer automatically.
    - Do not suppress uncertainty.
    - Do not claim production readiness while tools are mock-only.
```

The non-goals keep the fix bounded and honest.

---

## 20. Step 15: Generate v1

```yaml
agent_version:
  id: v1-evidence-triage-graph
  source_version: v0-baseline
  target_id: customer-escalation-triage-target-v1
  eval_contract_id: customer-escalation-triage-eval-contract-v1
  fix_plan_id: fix-v1-evidence-first-triage
  implementation_summary: >
    Adds evidence collection, evidence normalization, correlation review,
    facts/hypotheses/unknowns separation, and customer-safe update review.
  tool_mode:
    trace_evidence_source: mock
    eval_history_source: local
    recent_changes_source: mock
    tool_health_source: mock
  production_readiness: blocked
```

v1 can be valid for demo and evaluation while still blocked for production. That distinction should be explicit.

---

## 21. Step 16: Run v1

**Possible v1 output (abbreviated):**

```markdown
# Escalation Triage Summary

## Customer-Reported Issue
Apex Health reports inconsistent answers, increased latency, and reduced reviewer confidence.

## Confirmed Facts
- A summarization prompt change shipped two days ago.
- Latency increased this week.
- Eval scores dropped for scanned PDF cases.
- The eligibility-check tool has intermittent timeouts.

## Hypotheses
1. **Prompt-change regression** — timing correlation and eval drop (Medium confidence)
2. **Document-quality regression** — eval drop concentrated in scanned PDFs (Medium-High)
3. **Tool timeout contribution** — intermittent timeout signal (Medium)

## Unknowns
- Whether the prompt change directly caused the quality drop.
- Whether latency is from generations, tool timeouts, or retries.

## Recommended Immediate Actions
1. Compare pre/post eval results for scanned PDF cases.
2. Inspect high-latency and failed eval traces.
3. Prepare a customer update without claiming root cause too early.

## Customer-Safe Update Draft
We are investigating the inconsistency and latency reports from this week...
```

This output satisfies the target better than v0.

---

## 22. Step 17: Compare v0 and v1

The comparison should be rule-level, not just score-level.

```yaml
comparison:
  id: compare-v0-v1-escalation-triage
  target_id: customer-escalation-triage-target-v1
  eval_contract_id: customer-escalation-triage-eval-contract-v1
  versions:
    baseline: v0-baseline
    candidate: v1-evidence-triage-graph
  score_delta:
    diagnostic_grounding: { v0: 2, v1: 5, delta: 3 }
    change_correlation_quality: { v0: 3, v1: 4, delta: 1 }
    impact_assessment_quality: { v0: 2, v1: 4, delta: 2 }
    action_plan_quality: { v0: 3, v1: 4, delta: 1 }
    customer_communication_quality: { v0: 2, v1: 5, delta: 3 }
  resolved_failures:
    - no_unsupported_root_cause
    - must_separate_facts_and_hypotheses
    - customer_update_must_be_safe
  remaining_warnings:
    - Production readiness blocked by mock-only trace and recent-change tools.
    - Mitigation plan still requires human approval.
```

```text
v0 guessed. v1 checked evidence and separated facts from hypotheses.
```

---

## 23. Step 18: Apply Gates

Gates should include behavior gates and readiness gates.

```yaml
gate_result:
  version: v1-evidence-triage-graph
  compared_to: v0-baseline
  behavior_gate_status: pass
  production_readiness_status: blocked
  overall_status: pass_for_demo_not_production
  hard_behavior_gates:
    no_unsupported_root_cause: pass
    must_separate_facts_and_hypotheses: pass
    must_include_safe_next_actions: pass
  warning_behavior_gates:
    customer_update_must_be_safe: pass
  tool_readiness_gates:
    required_tools_available_for_demo: pass
    required_tools_available_for_production: fail
  blockers:
    - trace_evidence_source uses mock implementation.
    - recent_changes_source uses mock implementation.
    - tool_health_source uses mock implementation.
```

A version can be good enough for demo while still blocked for production.

---

## 24. Step 19: Promote, Reject, or Accept with Risk

```yaml
promotion_record:
  agent_id: customer-escalation-triage-agent
  promoted_version: v1-evidence-triage-graph
  previous_version: v0-baseline
  decision: promoted_for_demo
  production_status: blocked
  rationale: >
    v1 resolves the critical v0 failure of unsupported root-cause claims by adding
    explicit evidence collection, normalization, and facts/hypotheses/unknowns separation.
    It passes behavior gates for the test scenario.
  conditions:
    - May be used for demo and offline evaluation.
    - May not be used for production escalation triage until live trace, recent-change,
      and tool-health connectors are implemented and reviewed.
```

---

## 25. Step 20: Operate the Promoted Agent

Once promoted, the agent can be used operationally — but operation should still show evidence and readiness.

For a production-ready agent, runtime should include:

- active target, eval contract, version
- tool binding mode and run status
- trace links
- confidence, facts/hypotheses/unknowns
- recommended actions and actions requiring approval

A promoted agent should not become a black box.

---

## 26. Manual vs Generated vs Automatic Inputs

### Manual or user-confirmed

- Agent name, purpose, intended users, goals, non-goals
- Allowed tool categories, risk tolerance, example scenarios
- Promotion decision

### Generated and user-reviewed

- Behavior rules, eval contract, information requirements, tool requirements
- Graph design, initial scenario variants, initial prompts
- Initial tool feasibility inventory, fix plans

### Automatically produced

- Run outputs, trace links, scores, failure packets, comparisons
- Gate results, cost/latency/token metrics
- Regression warnings, tool readiness status

The user defines intent. The system generates machinery. The runtime produces evidence.

---

## 27. Required Domain Objects

First-class platform objects:

```text
Agent, AgentTarget, BehaviorRule, EvalContract, Metric, Gate, Scenario, ScenarioSet,
InformationRequirement, ToolRequirement, ToolImplementation, ToolBinding,
ToolFeasibilityReview, GraphDesign, GraphNode, Prompt, AgentVersion, ExperimentRun,
TraceLink, Score, FailurePacket, FixPlan, Comparison, GateResult, PromotionRecord,
OperationalRun, ReadinessStatus, Artifact
```

The platform should own canonical state. Files can exist as exportable artifacts for local lab work.

---

## 28. Tool Maturity Model

| Level | Name | Description |
|-------|------|-------------|
| 0 | Missing | Requirement exists, no implementation |
| 1 | Mock | Local fixture data for design and eval |
| 2 | Local | Reads local artifacts or generated run outputs |
| 3 | Read-only live | Connects to real systems, no mutation |
| 4 | Approval-gated action | Mutations only after human approval |
| 5 | Controlled automation | Bounded automatic actions under strict gates |

Most agents start at Level 1 or 2. Production readiness usually requires Level 3 for evidence tools.

---

## 29. Promotion Types

| State | Meaning |
|-------|---------|
| draft | Version exists but has not passed evals |
| promoted_for_demo | Passes behavior evals with mock/local tools |
| promoted_for_internal_use | Passes evals with read-only live tools |
| promoted_for_production_assistive_use | Assists humans; no unapproved actions |
| promoted_for_controlled_automation | Bounded automation under strict gates |
| rejected | Failed behavior or readiness gates |
| deprecated | Superseded |

---

## 30. Relationship to Langfuse

Langfuse is the evidence layer — not replaced.

The platform should send or link:

```text
platform_run_id, platform_agent_id, platform_agent_version, platform_target_id,
platform_eval_contract_id, scenario_id, tool_binding_mode, environment, gate_result
```

Langfuse provides trace evidence, model I/O, tool calls, latency, tokens, cost, scores, annotations, datasets, and experiments.

The platform uses Langfuse evidence for failure packets, comparisons, and promotion decisions. Langfuse is not the source of truth for design intent.

---

## 31. Relationship to LangGraph

LangGraph is the implementation runtime for graph-based agents in **edd-agent-lab**.

The platform should generate or maintain graph design artifacts that map rules to graph behavior.

```yaml
graph_node:
  id: separate_facts_hypotheses_unknowns
  purpose: >
    Prevent unsupported diagnosis by separating confirmed facts, plausible hypotheses,
    and unknowns before recommendations are generated.
  supports_rules:
    - separate_facts_from_hypotheses
    - evidence_first_diagnosis
  reads_state:
    - normalized_evidence
    - recent_changes
    - trace_summary
    - eval_history
  writes_state:
    - confirmed_facts
    - hypotheses
    - unknowns
```

Each node should connect back to a rule, information requirement, or failure packet.

---

## 32. Relationship to edd-agent-lab

**edd-agent-lab** is where concrete versions are developed.

Ideal folder structure:

```text
agents/customer_escalation_triage/
  agent-target.yaml
  behavior-rules.yaml
  eval-contract.yaml
  information-requirements.yaml
  tool-requirements.yaml
  tool-feasibility.yaml
  graph-design.yaml
  data/mock/apex_health/...
  versions/
    v0-baseline/
    v1-evidence-triage-graph/
```

The platform eventually owns canonical objects; the lab keeps file-based artifacts for local development and demos.

---

## 33. Ideal End-to-End Example Summary

For the Customer Escalation Triage Agent:

```text
User defines intent → platform generates target, rules, eval contract, requirements
→ tool review finds mock-only gaps → lab runs v0 → v0 overclaims root cause
→ failure packet → bounded fix plan → v1 evidence-first graph
→ v1 passes behavior gates → blocked for production (mock tools)
→ promoted_for_demo, not production
```

That is the ideal product loop.

---

## 34. Why This Is Evaluation-Driven Design

This workflow qualifies because:

- The target exists before acceptance.
- The eval contract is derived from the target.
- Information and tool requirements are derived from rules.
- The graph is shaped by rules and tool feasibility.
- Failures tie to specific rules; fixes are bounded.
- New versions are compared against the same contract.
- Promotion depends on behavior and readiness gates.
- Runtime use remains connected to design evidence.

It is not just evals after the fact. Evaluation shapes the agent.

---

## 35. Recommended First Product Milestone

### Milestone: Target-to-v0 EDD Flow

**Goal:** Define a new agent target and produce the first baseline implementation and eval run.

**Deliverables:**

1. Agent target schema
2. Behavior rule schema
3. Eval contract schema
4. Information requirement schema
5. Tool requirement schema
6. Tool feasibility schema
7. Guided target creation workflow
8. Rule/eval generation from target
9. Information/tool requirement generation
10. Mock tool binding support
11. Initial graph design generation
12. v0 baseline run
13. Eval summary
14. Failure packet generation
15. Langfuse trace metadata linkage

**Acceptance criteria:** A user describes a new agent; the platform generates target/rules/evals/requirements; the system identifies missing or mock-only tools; the lab runs v0; failures map to behavior rules; trace links are recorded.

---

## 36. Recommended Second Product Milestone

### Milestone: v0-to-v1 Bounded Fix Flow

**Goal:** Use v0 failure packets to generate and verify a bounded v1 improvement.

**Deliverables:** Failure packet → fix plan generation; graph/prompt/tool binding recommendations; v1 scaffold; v1 run; v0/v1 comparison; gate result; promotion decision; production readiness status.

**Acceptance criteria:** v1 changes trace to v0 failures; eval contract stays stable; comparison shows resolved and remaining failures; gates distinguish demo vs production readiness.

---

## 37. Recommended Third Product Milestone

### Milestone: Operational Run Flow

**Goal:** Use a promoted agent as a real assistant while preserving evidence and readiness context.

**Deliverables:** Active version selection; live/manual run mode; tool binding display; operational run record; trace capture; action recommendation queue; human approval for write actions; runtime warnings for mock/missing tools; post-run eval or review.

**Acceptance criteria:** A promoted agent runs for a real task; the user sees active version, target, eval contract, and tool bindings; output includes evidence and assumptions; unsafe actions require approval; the run links to platform artifacts and Langfuse.

---

## 38. Final Summary

The ideal state for **edd-agent-lab** and **eval-driven-design-platform** is a complete agent design lifecycle:

```text
Describe the agent → generate target → rules → eval contract → information requirements
→ tool requirements → check feasibility → bind tools → shape graph → run v0
→ capture traces → evaluate → failure packets → bounded fix → run v1
→ compare → apply gates → promote with evidence → operate with traceability
```

The core promise:

> Agents should not be improved by vibes.  
> They should be improved through a disciplined loop that connects intent, evidence, tools, failures, fixes, and promotion decisions.

**edd-agent-lab** and **eval-driven-design-platform** exist to make that loop real.

See also: [Ideal platform console design](11-ideal-console-design.md) · [HLD-001: Product intent](../../eval-driven-design-platform/docs/hld/HLD-001-product-intent-and-system-boundaries.md).
