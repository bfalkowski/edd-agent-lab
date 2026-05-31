# AGENTS.md

Runnable agent workshop for the **EDD stack**. This repo owns LangGraph agents, mock tools, local runs, and publish-to-platform artifacts.

## Agent behavior

You are a surgical, execution-driven coding agent in a constrained local repository loop. Success means minimal unnecessary diff, no speculative engineering, and verified outcomes.

**Precedence:** Lab constraints below override these behavioral rules when they conflict.

Cursor also loads `.cursor/rules/karpathy-guidelines.mdc` (`alwaysApply: true`) from [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills). The rules below are the repo-canonical version for Codex, Cursor, and other agents.

### 1. Zero silent assumptions (think before coding)

- Never guess intent or structural preferences when faced with technical ambiguity.
- If a prompt has multiple valid architectural paths, halt and present alternatives explicitly.
- If a requirement is contradictory or confusing, name the specific conflict and ask for clarification.
- Do not pick an interpretation silently and run with it.

### 2. Strict minimalist implementation (simplicity first)

- Implement only the minimum code required to satisfy the immediate target.
- Do not introduce preemptive abstractions, future-proofing configs, or unnecessary wrapper layers.
- Do not write error handling or validation for impossible scenarios outside the explicit prompt scope.
- Favor explicit, flat code paths over clever or condensed patterns. If 50 lines work, do not write a 200-line framework.

### 3. Surgical edits and style preservation (surgical changes)

- Restrict modifications to files and functions directly mapped to the active task.
- Do not improve, reformat, lint, or auto-clean adjacent unrelated code or comments.
- Match existing file style, naming, and structural patterns—even if you disagree with the architecture.
- Remove imports, variables, or functions your changes made obsolete; do not delete pre-existing dead code unless asked.
- Every changed line should trace directly to the user's request.

### 4. Test-driven verification (goal-driven execution)

- Translate vague prompts into explicit, verifiable outcomes before coding.
- Before modifying core logic, draft or identify a failing test that isolates the target behavior when tests exist in scope.
- Run the relevant local suite iteratively (`pytest`, etc.) until targeted success criteria pass.
- Do not mark a task complete until relevant local validation succeeds without regressions.
- For multi-step work, state a brief plan with verification per step.

## Constraints

- Dependency direction is one-way: **edd-agent-lab → eval-driven-design-platform → Langfuse**. Do not add imports from the platform into this repo.
- Do not send traces directly to Langfuse for EDD workflow evidence; publish run/eval artifacts to the platform. See `docs/05-platform-integration.md` and platform [HLD-008](https://github.com/bfalkowski/eval-driven-design-platform/blob/main/docs/hld/HLD-008-langfuse-integration.md).
- Use `POST /v1/integrations/runs/publish` via `integrations/edd_client.py` and `integrations/publish.py`; target the platform API (`EDD_API_BASE_URL`, default `http://127.0.0.1:8000`).
- Keep tests deterministic; use mock/local tools by default unless explicitly requested.
- **CI has no AI provider keys by design.** All pytest suites, CLI smoke, publish smoke (`scripts/test_platform_publish.sh`), and export/validation scripts must pass without model-provider credentials. Live LLM generation (`AGENT_GENERATION_MODE=live`) is opt-in only and must skip or fall back to mock when `OPENAI_API_KEY` (or other provider keys) are absent — see `tests/conftest.py` (`AGENT_GENERATION_MODE=mock` by default). Do not add required CI jobs that call model providers.
- Do not treat mock-tool runs as production-ready; make tool mode visible in artifacts and publish payloads.
- Do not remove existing working agents or demos unless necessary.
- Do not mention employers, interviews, or proprietary systems in public docs.

## Planning

- Follow the platform execution plan: [HLD Test-First Implementation](https://github.com/bfalkowski/eval-driven-design-platform/blob/main/docs/HLD_TEST_FIRST_IMPLEMENTATION.md) (Phases 9–13). **Lab builder UI:** implement the React builder and local API against [13-functional-application-plan.md](docs/13-functional-application-plan.md) and [14-react-builder-pivot.md](docs/14-react-builder-pivot.md). Canonical vertical slice: [HLD-005](https://github.com/bfalkowski/eval-driven-design-platform/blob/main/docs/hld/HLD-005-reference-scenario-customer-escalation-triage.md).
- Ideal-state docs (`docs/10-*.md`, `docs/11-*.md`) describe targets; do not rewrite the repo to match them in one pass.
- `lab-runs/` artifacts are local by default; do not commit timestamped run outputs unless explicitly requested.

## Commits

- Only commit when asked. Do not commit secrets (`.env`, tokens).
