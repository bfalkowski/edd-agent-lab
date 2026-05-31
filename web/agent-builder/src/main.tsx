import {
  ArrowRight,
  Check,
  Clock3,
  FileText,
  Folder,
  Loader2,
  PanelRight,
  PencilLine,
  Play,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  createDraft,
  deleteDraft,
  deleteArtifact,
  BehaviorRule,
  DraftDetail,
  DraftSummary,
  GenerationMode,
  listDrafts,
  loadRuntimeConfig,
  loadDraft,
  RuntimeConfig,
  saveArtifactSource,
  saveBehaviorRules,
  saveScenario,
  saveTarget,
  TargetUpdate,
  streamDraftAction,
} from "./api";
import "./styles.css";

const actions = [
  { id: "design", label: "Generate design", icon: Sparkles },
  { id: "run-v0", label: "Run v0", icon: Play },
  { id: "evaluate-v0", label: "Evaluate v0", icon: FileText },
  { id: "fix-plan", label: "Create fix plan", icon: Sparkles },
  { id: "v1-graph", label: "Generate v1 graph", icon: Sparkles },
  { id: "run-v1", label: "Run v1", icon: Play },
  { id: "evaluate-v1", label: "Evaluate v1", icon: FileText },
  { id: "compare", label: "Compare", icon: ArrowRight },
  { id: "publish", label: "Publish", icon: ArrowRight },
];

const stepActions: Record<string, string> = {
  behavior_rules: "design",
  scenario: "scenario",
  v0_run: "run-v0",
  eval_summary: "evaluate-v0",
  fix_plan: "fix-plan",
  graph_design_v1: "v1-graph",
  v1_run: "run-v1",
  eval_summary_v1: "evaluate-v1",
  comparison: "compare",
  publish_result: "publish",
};

const actionLabelById = Object.fromEntries(actions.map((action) => [action.id, action.label]));
const generationModeStorageKey = "edd-agent-lab:generation-mode";

type ArtifactCards = DraftDetail["artifact_cards"];

const stepOutputs: Record<string, string[]> = {
  target: ["target"],
  behavior_rules: [
    "behavior_rules",
    "eval_contract",
    "eval_suite",
    "information_requirements",
    "tool_requirements",
    "graph_design",
  ],
  scenario: ["scenario"],
  v0_run: ["v0_run"],
  eval_summary: ["eval_summary", "failure_packet"],
  fix_plan: ["fix_plan"],
  graph_design_v1: ["graph_design_v1"],
  v1_run: ["v1_run"],
  eval_summary_v1: ["eval_summary_v1"],
  comparison: ["comparison"],
  publish_result: ["publish_result"],
};

const outputToStep = Object.fromEntries(
  Object.entries(stepOutputs).flatMap(([stepId, outputIds]) =>
    outputIds.map((outputId) => [outputId, stepId]),
  ),
);

function actionStepId(actionId: string): string {
  return Object.entries(stepActions).find(([, action]) => action === actionId)?.[0] ?? "target";
}

function artifactStepId(artifactId: string): string {
  return outputToStep[artifactId] ?? "target";
}

function targetUpdateFromDraft(draft: DraftDetail): TargetUpdate {
  const target = draft.target.agent_target;
  return {
    name: target.name ?? "",
    purpose: target.purpose ?? "",
    risk_tolerance: target.risk_tolerance ?? "needs_review",
    expected_output_format: target.expected_output_format ?? "needs_review",
  };
}

function behaviorRulesFromDraft(draft: DraftDetail): BehaviorRule[] {
  const artifact = draft.artifacts.behavior_rules as
    | { behavior_rules?: BehaviorRule[] }
    | undefined;
  return (artifact?.behavior_rules ?? []).map((rule) => ({
    id: rule.id ?? "",
    severity: rule.severity ?? "medium",
    description: rule.description ?? "",
    target_id: rule.target_id ?? draft.target.agent_target.id,
    status: rule.status ?? "draft",
  }));
}

type DiffLine = {
  key: string;
  prefix: string;
  text: string;
  type: "same" | "added" | "removed";
};

function buildLineDiff(before: string, after: string): DiffLine[] {
  const beforeLines = before.split("\n");
  const afterLines = after.split("\n");
  const maxLines = Math.max(beforeLines.length, afterLines.length);
  const lines: DiffLine[] = [];

  for (let index = 0; index < maxLines; index += 1) {
    const beforeLine = beforeLines[index];
    const afterLine = afterLines[index];
    if (beforeLine === afterLine) {
      lines.push({
        key: `same-${index}`,
        prefix: " ",
        text: beforeLine ?? "",
        type: "same",
      });
      continue;
    }
    if (beforeLine !== undefined) {
      lines.push({
        key: `removed-${index}`,
        prefix: "-",
        text: beforeLine,
        type: "removed",
      });
    }
    if (afterLine !== undefined) {
      lines.push({
        key: `added-${index}`,
        prefix: "+",
        text: afterLine,
        type: "added",
      });
    }
  }
  return lines;
}

function App() {
  const [drafts, setDrafts] = useState<DraftSummary[]>([]);
  const [activeDraft, setActiveDraft] = useState<DraftDetail | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [scenario, setScenario] = useState("");
  const [selectedArtifact, setSelectedArtifact] = useState("");
  const [artifactDraft, setArtifactDraft] = useState("");
  const [targetDraft, setTargetDraft] = useState<TargetUpdate>({
    name: "",
    purpose: "",
    risk_tolerance: "",
    expected_output_format: "",
  });
  const [rulesDraft, setRulesDraft] = useState<BehaviorRule[]>([]);
  const [reviewMode, setReviewMode] = useState<"edit" | "diff">("edit");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isReviewPanelOpen, setIsReviewPanelOpen] = useState(false);
  const [runtimeConfig, setRuntimeConfig] = useState<RuntimeConfig | null>(null);
  const [generationMode, setGenerationMode] = useState<GenerationMode>(() => {
    const stored = window.localStorage.getItem(generationModeStorageKey);
    return stored === "mock" || stored === "live" || stored === "auto" ? stored : "auto";
  });
  const [activityByStep, setActivityByStep] = useState<Record<string, string[]>>({});
  const [lastCurrentStep, setLastCurrentStep] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void refreshDrafts();
    void refreshRuntimeConfig();
  }, []);

  useEffect(() => {
    window.localStorage.setItem(generationModeStorageKey, generationMode);
  }, [generationMode]);

  async function refreshRuntimeConfig() {
    try {
      setRuntimeConfig(await loadRuntimeConfig());
    } catch {
      setRuntimeConfig(null);
    }
  }

  async function refreshDrafts() {
    setError("");
    const nextDrafts = await listDrafts();
    setDrafts(nextDrafts);
    if (!activeDraft && nextDrafts[0]) {
      setActiveDraft(await loadDraft(nextDrafts[0].agent_key));
    }
  }

  async function handleCreateDraft() {
    if (!name.trim() || !description.trim()) {
      setError("Agent name and idea are required.");
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      const draft = await createDraft(name.trim(), description.trim());
      setActiveDraft(draft);
      closeReviewPanel();
      setIsCreating(false);
      setName("");
      setDescription("");
      setDrafts(await listDrafts());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not create draft.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSelectDraft(agentKey: string) {
    setIsLoading(true);
    setError("");
    try {
      setActiveDraft(await loadDraft(agentKey));
      closeReviewPanel();
      setIsCreating(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load draft.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDeleteDraft(agentKey: string, draftName: string) {
    if (!window.confirm(`Delete "${draftName}" and its local draft artifacts?`)) return;
    setIsLoading(true);
    setError("");
    try {
      const nextDrafts = await deleteDraft(agentKey);
      setDrafts(nextDrafts);
      if (activeDraft?.agent_key === agentKey) {
        setActiveDraft(nextDrafts[0] ? await loadDraft(nextDrafts[0].agent_key) : null);
        closeReviewPanel();
        setIsCreating(nextDrafts.length === 0);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete project.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAction(action: string) {
    if (!activeDraft) return;
    setIsLoading(true);
    setError("");
    const label = actionLabelById[action] ?? action;
    const stepId = actionStepId(action);
    let sawStreamFailure = false;
    try {
      const draft = await streamDraftAction(
        activeDraft.agent_key,
        action,
        (event) => {
          appendStepActivity(event.step_id || stepId, event.message);
          if (event.phase === "failed") sawStreamFailure = true;
        },
        action === "run-v0" || action === "run-v1" ? generationMode : undefined,
      );
      setActiveDraft(draft);
      setDrafts(await listDrafts());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Action failed.");
      if (!sawStreamFailure) {
        appendStepActivity(stepId, `${label} failed.`);
      }
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSaveScenario() {
    if (!activeDraft) return;
    const problem = scenario.trim() || target?.purpose || "Test the draft agent behavior.";
    setIsLoading(true);
    setError("");
    appendStepActivity("scenario", "Saving scenario.");
    try {
      setActiveDraft(await saveScenario(activeDraft.agent_key, problem));
      setScenario("");
      setDrafts(await listDrafts());
      appendStepActivity("scenario", "Scenario saved; workflow refreshed.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save scenario.");
      appendStepActivity("scenario", "Scenario save failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSaveArtifact() {
    if (!activeDraft || !selectedArtifact) return;
    if (selectedArtifact === "target") {
      await handleSaveTarget();
      return;
    }
    if (selectedArtifact === "behavior_rules") {
      await handleSaveRules();
      return;
    }
    setIsLoading(true);
    setError("");
    appendStepActivity(artifactStepId(selectedArtifact), `Saving ${selectedArtifact}.`);
    try {
      const draft = await saveArtifactSource(
        activeDraft.agent_key,
        selectedArtifact,
        artifactDraft,
      );
      setActiveDraft(draft);
      setArtifactDraft(draft.artifact_sources[selectedArtifact] ?? "");
      setReviewMode("edit");
      setDrafts(await listDrafts());
      appendStepActivity(artifactStepId(selectedArtifact), `Saved ${selectedArtifact}.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save artifact.");
      appendStepActivity(artifactStepId(selectedArtifact), `Save failed for ${selectedArtifact}.`);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSaveRules() {
    if (!activeDraft) return;
    setIsLoading(true);
    setError("");
    appendStepActivity("behavior_rules", "Saving behavior rules.");
    try {
      const draft = await saveBehaviorRules(activeDraft.agent_key, rulesDraft);
      setActiveDraft(draft);
      setArtifactDraft(draft.artifact_sources.behavior_rules ?? "");
      setRulesDraft(behaviorRulesFromDraft(draft));
      setReviewMode("edit");
      setDrafts(await listDrafts());
      appendStepActivity("behavior_rules", "Saved behavior rules.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save behavior rules.");
      appendStepActivity("behavior_rules", "Behavior rule save failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSaveTarget() {
    if (!activeDraft) return;
    setIsLoading(true);
    setError("");
    appendStepActivity("target", "Saving target.");
    try {
      const draft = await saveTarget(activeDraft.agent_key, targetDraft);
      setActiveDraft(draft);
      setArtifactDraft(draft.artifact_sources.target ?? "");
      setTargetDraft(targetUpdateFromDraft(draft));
      setReviewMode("edit");
      setDrafts(await listDrafts());
      appendStepActivity("target", "Saved target.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save target.");
      appendStepActivity("target", "Target save failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDeleteArtifact() {
    if (!activeDraft || !selectedArtifact || selectedArtifact === "target") return;
    setIsLoading(true);
    setError("");
    appendStepActivity(artifactStepId(selectedArtifact), `Deleting ${selectedArtifact}.`);
    try {
      const draft = await deleteArtifact(activeDraft.agent_key, selectedArtifact);
      setActiveDraft(draft);
      closeReviewPanel();
      setDrafts(await listDrafts());
      appendStepActivity(artifactStepId(selectedArtifact), `Deleted ${selectedArtifact}.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete artifact.");
      appendStepActivity(artifactStepId(selectedArtifact), `Delete failed for ${selectedArtifact}.`);
    } finally {
      setIsLoading(false);
    }
  }

  function reviewArtifact(artifactKey: string) {
    if (!activeDraft) return;
    setSelectedArtifact(artifactKey);
    setArtifactDraft(activeDraft.artifact_sources[artifactKey] ?? "");
    if (artifactKey === "target") {
      setTargetDraft(targetUpdateFromDraft(activeDraft));
    }
    if (artifactKey === "behavior_rules") {
      setRulesDraft(behaviorRulesFromDraft(activeDraft));
    }
    setReviewMode("edit");
    setIsReviewPanelOpen(true);
  }

  function closeReviewPanel() {
    setSelectedArtifact("");
    setArtifactDraft("");
    setReviewMode("edit");
    setIsReviewPanelOpen(false);
  }

  function appendStepActivity(stepId: string, message: string) {
    setActivityByStep((current) => ({
      ...current,
      [stepId]: [message, ...(current[stepId] ?? [])].slice(0, 3),
    }));
  }

  const target = activeDraft?.target.agent_target;
  const nextAction = activeDraft?.status.next_action ?? "Create a draft target.";
  const shouldShowComposer = isCreating || !activeDraft || !target;
  const activeStep = activeDraft?.status.steps.find((step) => !step.complete);
  const workflowDone = Boolean(activeDraft && !activeStep);
  const showReviewPanel = Boolean(selectedArtifact && isReviewPanelOpen);
  const selectedValidation = selectedArtifact
    ? activeDraft?.artifact_validations[selectedArtifact]
    : undefined;
  const savedArtifactSource = selectedArtifact
    ? activeDraft?.artifact_sources[selectedArtifact] ?? ""
    : "";
  const hasArtifactChanges = artifactDraft !== savedArtifactSource;
  const savedTargetDraft = activeDraft ? targetUpdateFromDraft(activeDraft) : targetDraft;
  const hasTargetChanges =
    selectedArtifact === "target" &&
    (targetDraft.name !== savedTargetDraft.name ||
      targetDraft.purpose !== savedTargetDraft.purpose ||
      targetDraft.risk_tolerance !== savedTargetDraft.risk_tolerance ||
      targetDraft.expected_output_format !== savedTargetDraft.expected_output_format);
  const savedRulesDraft = activeDraft ? behaviorRulesFromDraft(activeDraft) : rulesDraft;
  const hasRulesChanges =
    selectedArtifact === "behavior_rules" &&
    JSON.stringify(rulesDraft) !== JSON.stringify(savedRulesDraft);
  const hasReviewChanges =
    selectedArtifact === "target"
      ? hasTargetChanges
      : selectedArtifact === "behavior_rules"
        ? hasRulesChanges
        : hasArtifactChanges;
  const artifactDiff = useMemo(
    () => buildLineDiff(savedArtifactSource, artifactDraft),
    [artifactDraft, savedArtifactSource],
  );
  const artifactsByStep = useMemo(() => {
    const byStep: Record<string, ArtifactCards> = {};
    if (!activeDraft) return byStep;
    for (const step of activeDraft.status.steps) {
      const outputIds = stepOutputs[step.id] ?? [];
      byStep[step.id] = activeDraft.artifact_cards.filter((artifact) =>
        outputIds.includes(artifact.id),
      );
    }
    return byStep;
  }, [activeDraft]);
  const resolvedGenerationMode =
    generationMode === "auto" ? runtimeConfig?.generation.resolved_mode ?? "mock" : generationMode;
  const generationStatus =
    generationMode === "auto"
      ? `Auto: ${resolvedGenerationMode}`
      : generationMode === "live"
        ? runtimeConfig?.generation.live_available
          ? `Live: ${runtimeConfig.generation.model}`
          : "Live unavailable"
        : "Mock: deterministic";

  useEffect(() => {
    const currentStepId = activeStep?.id ?? "";
    if (!lastCurrentStep) {
      setLastCurrentStep(currentStepId);
      return;
    }
    if (currentStepId !== lastCurrentStep) {
      setActivityByStep((current) => {
        const next = { ...current };
        delete next[lastCurrentStep];
        return next;
      });
      setLastCurrentStep(currentStepId);
    }
  }, [activeStep?.id, lastCurrentStep]);

  return (
    <main
      className={[
        "app-shell",
        isSidebarOpen ? "" : "sidebar-collapsed",
        showReviewPanel ? "review-open" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <aside className="sidebar">
        <div className="sidebar-window-bar">
          <div className="traffic-lights" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <button
            className="sidebar-toggle"
            onClick={() => setIsSidebarOpen(false)}
            title="Hide project panel"
          >
            <PanelRight className="flip-horizontal" size={18} />
          </button>
        </div>

        <nav className="primary-nav" aria-label="Primary">
          <button
            className={shouldShowComposer ? "nav-command active" : "nav-command"}
            onClick={() => {
              setIsCreating(true);
              setError("");
            }}
          >
            <PencilLine size={20} />
            <span>New agent</span>
          </button>
          <button className="nav-command" disabled>
            <Search size={20} />
            <span>Search</span>
          </button>
          <button className="nav-command" disabled>
            <Clock3 size={20} />
            <span>Runs</span>
          </button>
        </nav>

        <section className="project-list">
          <p>Projects</p>
          <div className="project-heading">
            <Folder size={19} />
            <span>edd-agent-lab</span>
          </div>
          <div className="draft-list">
            {drafts.map((draft) => (
              <div
                className={draft.agent_key === activeDraft?.agent_key ? "draft-row active" : "draft-row"}
                key={draft.agent_key}
              >
                <button className="draft-open" onClick={() => void handleSelectDraft(draft.agent_key)}>
                  <strong>{draft.name}</strong>
                </button>
                <span className="draft-actions">
                  <kbd>⌘{drafts.indexOf(draft) + 1}</kbd>
                  <button
                    aria-label={`Delete ${draft.name}`}
                    className="delete-draft"
                    onClick={(event) => {
                      event.stopPropagation();
                      void handleDeleteDraft(draft.agent_key, draft.name);
                    }}
                    title="Delete project"
                  >
                    <Trash2 size={14} />
                  </button>
                </span>
              </div>
            ))}
            {drafts.length === 0 ? <span className="muted">No agents yet</span> : null}
          </div>
        </section>

        <section className="chat-list">
          <p>Chats</p>
          <span className="muted">No chats</span>
        </section>
      </aside>

      <aside className="collapsed-sidebar-rail">
        <button
          className="sidebar-toggle"
          onClick={() => setIsSidebarOpen(true)}
          title="Show project panel"
        >
          <PanelRight className="flip-horizontal" size={18} />
        </button>
      </aside>

      <section className="main-pane">
        <header className="topbar">
          <div>
            <strong>{shouldShowComposer ? "New agent" : target?.name}</strong>
            <span>{shouldShowComposer ? "Describe the target" : nextAction}</span>
          </div>
          <div className="topbar-actions">
            <div className="generation-control" aria-label="Generation mode">
              {(["auto", "mock", "live"] as GenerationMode[]).map((mode) => (
                <button
                  className={generationMode === mode ? "active" : ""}
                  disabled={mode === "live" && runtimeConfig?.generation.live_available === false}
                  key={mode}
                  onClick={() => setGenerationMode(mode)}
                  title={
                    mode === "live" && runtimeConfig?.generation.live_available === false
                      ? "Set OPENAI_API_KEY to enable live generation"
                      : `Use ${mode} generation`
                  }
                >
                  {mode}
                </button>
              ))}
              <span>{generationStatus}</span>
            </div>
            {!shouldShowComposer && !showReviewPanel ? (
              <button
                className="topbar-button"
                onClick={() => setIsReviewPanelOpen(true)}
                disabled={!selectedArtifact}
                title={selectedArtifact ? "Toggle review panel" : "Select an artifact to review"}
              >
                <PanelRight size={17} />
                Review
              </button>
            ) : null}
            {isLoading ? <Loader2 className="spin" size={18} /> : null}
          </div>
        </header>

        {shouldShowComposer ? (
          <section className="composer">
            <p className="eyebrow">Start from intent</p>
            <h1>What agent are we building?</h1>
            <p className="intro">
              Give it a name and describe what it should do. The draft appears in the project
              list as soon as it is created.
            </p>
            <div className="composer-card">
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Agent name"
              />
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Describe the agent purpose, users, constraints, and safe behavior."
              />
              <div className="composer-actions">
                {error ? <span className="error">{error}</span> : <span />}
                <button onClick={handleCreateDraft} disabled={isLoading}>
                  Create draft
                </button>
              </div>
            </div>
          </section>
        ) : (
        <section className="workspace">
          <div className="workspace-header">
            <div>
              <p className="eyebrow">Local draft</p>
              <h2>{target.name}</h2>
              <p>{target.purpose}</p>
            </div>
            <div className="progress-card">
              <strong>
                {activeDraft.status.completed}/{activeDraft.status.total}
              </strong>
              <span>steps</span>
            </div>
          </div>

          <div className="workflow-panel">
            <div className="workflow-current">
              <div>
                <span>{workflowDone ? "Complete" : "Current step"}</span>
                <strong>{workflowDone ? "Ready for publish review" : activeStep?.step}</strong>
                <p>{nextAction}</p>
              </div>
            </div>

            <div className="step-list">
              {activeDraft.status.steps.map((step) => (
                <div
                  className={[
                    "step-item",
                    step.complete ? "complete" : "",
                    step.id === activeStep?.id ? "current" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  key={step.id}
                >
                  <span>{step.complete ? <Check size={14} /> : null}</span>
                  <strong>{step.step}</strong>
                </div>
              ))}
            </div>
          </div>
          <div className="workflow-board">
            {activeDraft.status.steps.map((step) => {
              const action = stepActions[step.id];
              const actionMeta = actions.find((candidate) => candidate.id === action);
              const Icon = actionMeta?.icon;
              const stepArtifacts = artifactsByStep[step.id] ?? [];
              const isCurrent = step.id === activeStep?.id;
              const stepActivity = activityByStep[step.id] ?? [];
              const latestActivity = stepActivity[0];
              const runArtifact = stepArtifacts.find(
                (artifact) => artifact.id === "v0_run" || artifact.id === "v1_run",
              );
              const runMode =
                runArtifact?.id && activeDraft.artifacts[runArtifact.id]
                  ? (
                      activeDraft.artifacts[runArtifact.id] as {
                        run?: { generation_mode?: string };
                      }
                    ).run?.generation_mode
                  : undefined;

              return (
                <section
                  className={[
                    "workflow-card",
                    step.complete ? "complete" : "",
                    isCurrent ? "current" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  key={step.id}
                >
                  <div className="workflow-card-main">
                    <span>{step.complete ? <Check size={14} /> : null}</span>
                    <div>
                      <strong>{step.step}</strong>
                      <p>{step.complete ? "Done" : step.next_action}</p>
                      {runMode ? <small>Generated with {runMode}</small> : null}
                      {latestActivity ? <em>{latestActivity}</em> : null}
                    </div>
                  </div>

                  {isCurrent && step.id === "scenario" ? (
                    <div className="scenario-editor">
                      <textarea
                        value={scenario}
                        onChange={(event) => setScenario(event.target.value)}
                        placeholder="Describe the local test scenario to run against this agent."
                      />
                      <button onClick={() => void handleSaveScenario()} disabled={isLoading}>
                        Save scenario
                        <ArrowRight size={17} />
                      </button>
                    </div>
                  ) : null}

                  {isCurrent && action && action !== "scenario" ? (
                    <button
                      className="step-action"
                      onClick={() => void handleAction(action)}
                      disabled={isLoading}
                    >
                      {Icon ? <Icon size={17} /> : null}
                      {actionLabelById[action]}
                    </button>
                  ) : null}

                  <div className="step-outputs">
                    <span>Outputs</span>
                    {stepArtifacts.length > 0 ? (
                      stepArtifacts.map((artifact) => (
                        <div className="output-row" key={artifact.id}>
                          <code className={artifact.status === "ready" ? "ready" : ""}>
                            {artifact.file}
                          </code>
                          {artifact.status === "ready" ? (
                            <button
                              className={selectedArtifact === artifact.id ? "active" : ""}
                              onClick={() => reviewArtifact(artifact.id)}
                            >
                              Review
                            </button>
                          ) : null}
                        </div>
                      ))
                    ) : (
                      <em>Created by this step</em>
                    )}
                  </div>
                </section>
              );
            })}
          </div>
          {error ? <p className="error workspace-error">{error}</p> : null}

        </section>
        )}
      </section>

      {showReviewPanel ? (
        <aside className="artifact-review">
          <div className="review-title">
            <div>
              <span>Review artifact</span>
              <strong>{selectedArtifact}</strong>
            </div>
            <div>
              <button className="secondary" onClick={closeReviewPanel}>
                <PanelRight size={16} />
                Close
              </button>
              <button
                className={reviewMode === "edit" ? "secondary active" : "secondary"}
                onClick={() => setReviewMode("edit")}
              >
                Edit
              </button>
              <button
                className={reviewMode === "diff" ? "secondary active" : "secondary"}
                onClick={() => setReviewMode("diff")}
                disabled={
                  !hasReviewChanges ||
                  selectedArtifact === "target" ||
                  selectedArtifact === "behavior_rules"
                }
                title={
                  selectedArtifact === "target" || selectedArtifact === "behavior_rules"
                    ? "YAML diff is available for raw artifacts."
                    : hasArtifactChanges
                      ? "Review unsaved changes"
                      : "No unsaved changes"
                }
              >
                Diff
              </button>
              <button onClick={() => void handleSaveArtifact()} disabled={isLoading}>
                Save edits
              </button>
              <button
                className="danger"
                onClick={() => void handleDeleteArtifact()}
                disabled={isLoading || selectedArtifact === "target"}
                title={
                  selectedArtifact === "target"
                    ? "The draft target anchors the workspace."
                    : "Delete artifact"
                }
              >
                <Trash2 size={16} />
                Delete
              </button>
            </div>
          </div>
          {reviewMode === "diff" ? (
            <div className="artifact-diff">
              {artifactDiff.map((line) => (
                <div className={`diff-line ${line.type}`} key={line.key}>
                  <span>{line.prefix}</span>
                  <code>{line.text || " "}</code>
                </div>
              ))}
            </div>
          ) : selectedArtifact === "target" ? (
            <div className="target-editor">
              <label>
                Name
                <input
                  value={targetDraft.name}
                  onChange={(event) =>
                    setTargetDraft({ ...targetDraft, name: event.target.value })
                  }
                />
              </label>
              <label>
                Purpose
                <textarea
                  value={targetDraft.purpose}
                  onChange={(event) =>
                    setTargetDraft({ ...targetDraft, purpose: event.target.value })
                  }
                />
              </label>
              <label>
                Risk tolerance
                <input
                  value={targetDraft.risk_tolerance}
                  onChange={(event) =>
                    setTargetDraft({ ...targetDraft, risk_tolerance: event.target.value })
                  }
                />
              </label>
              <label>
                Expected output
                <input
                  value={targetDraft.expected_output_format}
                  onChange={(event) =>
                    setTargetDraft({
                      ...targetDraft,
                      expected_output_format: event.target.value,
                    })
                  }
                />
              </label>
            </div>
          ) : selectedArtifact === "behavior_rules" ? (
            <div className="rules-editor">
              {rulesDraft.map((rule, index) => (
                <section className="rule-editor-card" key={`${rule.id}-${index}`}>
                  <label>
                    Rule id
                    <input
                      value={rule.id}
                      onChange={(event) => {
                        const nextRules = [...rulesDraft];
                        nextRules[index] = { ...rule, id: event.target.value };
                        setRulesDraft(nextRules);
                      }}
                    />
                  </label>
                  <label>
                    Severity
                    <select
                      value={rule.severity}
                      onChange={(event) => {
                        const nextRules = [...rulesDraft];
                        nextRules[index] = { ...rule, severity: event.target.value };
                        setRulesDraft(nextRules);
                      }}
                    >
                      <option value="low">low</option>
                      <option value="medium">medium</option>
                      <option value="high">high</option>
                    </select>
                  </label>
                  <label>
                    Description
                    <textarea
                      value={rule.description}
                      onChange={(event) => {
                        const nextRules = [...rulesDraft];
                        nextRules[index] = { ...rule, description: event.target.value };
                        setRulesDraft(nextRules);
                      }}
                    />
                  </label>
                  <label>
                    Status
                    <input
                      value={rule.status}
                      onChange={(event) => {
                        const nextRules = [...rulesDraft];
                        nextRules[index] = { ...rule, status: event.target.value };
                        setRulesDraft(nextRules);
                      }}
                    />
                  </label>
                </section>
              ))}
            </div>
          ) : (
            <textarea
              value={artifactDraft}
              onChange={(event) => setArtifactDraft(event.target.value)}
              spellCheck={false}
            />
          )}
          <div
            className={
              selectedValidation?.valid === false
                ? "validation-panel invalid"
                : "validation-panel valid"
            }
          >
            {selectedValidation?.valid === false ? (
              <>
                <strong>Validation issues</strong>
                {selectedValidation.errors.map((item) => (
                  <span key={item}>{item}</span>
                ))}
              </>
            ) : (
              <span>Artifact shape looks valid.</span>
            )}
          </div>
        </aside>
      ) : null}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
