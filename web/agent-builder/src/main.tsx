import {
  ArrowRight,
  Archive,
  Check,
  Clock3,
  Download,
  FileText,
  Loader2,
  MoreHorizontal,
  PanelRight,
  PencilLine,
  Play,
  Plus,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  archiveDraft,
  createDraft,
  deleteDraft,
  BehaviorRule,
  DraftDetail,
  DraftSummary,
  EvalContractUpdate,
  EvalGate,
  EvalMetric,
  GenerationMode,
  GraphDesignUpdate,
  InformationRequirement,
  listDrafts,
  loadRuntimeConfig,
  loadDraft,
  renameDraft,
  RuntimeConfig,
  saveArtifactSource,
  saveBehaviorRules,
  saveEvalContract,
  saveGraphDesign,
  saveInformationRequirements,
  saveScenario,
  saveTarget,
  saveToolRequirements,
  TargetUpdate,
  ToolRequirement,
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
  scenario: ["scenario", "scenario_variants"],
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

const artifactDescriptions: Record<string, string> = {
  target: "Intent, users, scope, and output expectations.",
  behavior_rules: "Behavior constraints the agent should satisfy.",
  eval_contract: "Metrics and gates used to judge the agent.",
  eval_suite: "Deterministic checks generated for local evaluation.",
  information_requirements: "Facts the agent must collect before acting.",
  tool_requirements: "Tooling gaps or production blockers.",
  graph_design: "First-pass graph nodes and transitions.",
  scenario: "Local test scenario for exercising the agent.",
  scenario_variants: "Scenario variations for broader coverage.",
  v0_run: "First run evidence and generated response.",
  eval_summary: "Evaluation result for the first run.",
  failure_packet: "Focused explanation of what failed and why.",
  fix_plan: "Bounded changes for improving the draft.",
  graph_design_v1: "Revised graph after the fix plan.",
  v1_run: "Second run evidence after changes.",
  eval_summary_v1: "Evaluation result for the revised run.",
  comparison: "Before and after comparison across versions.",
  publish_result: "Platform publish payload and delivery status.",
};

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

function evalContractFromDraft(draft: DraftDetail): EvalContractUpdate {
  const artifact = draft.artifacts.eval_contract as
    | {
        eval_contract?: {
          metrics?: EvalMetric[];
          gates?: EvalGate[];
          status?: string;
        };
      }
    | undefined;
  const contract = artifact?.eval_contract;
  return {
    metrics: (contract?.metrics ?? []).map((metric) => ({
      id: metric.id ?? "",
      scale: metric.scale ?? "0-5",
      rules: metric.rules ?? [],
    })),
    gates: (contract?.gates ?? []).map((gate) => ({
      id: gate.id ?? "",
      type: gate.type ?? "hard",
      condition: gate.condition ?? "",
    })),
    status: contract?.status ?? "draft",
  };
}

function informationRequirementsFromDraft(draft: DraftDetail): InformationRequirement[] {
  const artifact = draft.artifacts.information_requirements as
    | { information_requirements?: InformationRequirement[] }
    | undefined;
  return (artifact?.information_requirements ?? []).map((requirement) => ({
    id: requirement.id ?? "",
    description: requirement.description ?? "",
    required_for_rules: requirement.required_for_rules ?? [],
    status: requirement.status ?? "draft",
  }));
}

function toolRequirementsFromDraft(draft: DraftDetail): ToolRequirement[] {
  const artifact = draft.artifacts.tool_requirements as
    | { tool_requirements?: ToolRequirement[] }
    | undefined;
  return (artifact?.tool_requirements ?? []).map((tool) => ({
    id: tool.id ?? "",
    suggested_tool_name: tool.suggested_tool_name ?? "",
    information_requirements: tool.information_requirements ?? [],
    implementation_status: tool.implementation_status ?? "missing",
    production_blocker: Boolean(tool.production_blocker),
    status: tool.status ?? "draft",
  }));
}

function graphDesignFromDraft(
  draft: DraftDetail,
  artifactKey: "graph_design" | "graph_design_v1",
): GraphDesignUpdate {
  const artifact = draft.artifacts[artifactKey] as
    | {
        graph_design?: {
          version?: string;
          status?: string;
          nodes?: GraphDesignUpdate["nodes"];
          edges?: GraphDesignUpdate["edges"];
        };
      }
    | undefined;
  const graph = artifact?.graph_design;
  return {
    artifact_key: artifactKey,
    version: graph?.version ?? "draft",
    status: graph?.status ?? "draft",
    nodes: (graph?.nodes ?? []).map((node) => ({
      id: node.id ?? "",
      purpose: node.purpose ?? "",
      supports_rules: node.supports_rules ?? [],
    })),
    edges: (graph?.edges ?? []).map((edge) => ({
      from: edge.from ?? "",
      to: edge.to ?? "",
    })),
  };
}

function newBehaviorRule(): BehaviorRule {
  return {
    id: "new_rule",
    severity: "medium",
    description: "",
    target_id: "",
    status: "draft",
  };
}

function newEvalMetric(): EvalMetric {
  return { id: "new_metric", scale: "0-5", rules: [] };
}

function newEvalGate(): EvalGate {
  return { id: "new_gate", type: "hard", condition: "" };
}

function newInformationRequirement(): InformationRequirement {
  return { id: "new_requirement", description: "", required_for_rules: [], status: "draft" };
}

function newToolRequirement(): ToolRequirement {
  return {
    id: "new_tool",
    suggested_tool_name: "",
    information_requirements: [],
    implementation_status: "missing",
    production_blocker: false,
    status: "draft",
  };
}

function withoutIndex<T>(items: T[], index: number): T[] {
  return items.filter((_, itemIndex) => itemIndex !== index);
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
  const [evalContractDraft, setEvalContractDraft] = useState<EvalContractUpdate>({
    metrics: [],
    gates: [],
    status: "draft",
  });
  const [informationRequirementsDraft, setInformationRequirementsDraft] = useState<
    InformationRequirement[]
  >([]);
  const [toolRequirementsDraft, setToolRequirementsDraft] = useState<ToolRequirement[]>([]);
  const [graphDraft, setGraphDraft] = useState<GraphDesignUpdate>({
    artifact_key: "graph_design",
    version: "draft",
    status: "draft",
    nodes: [],
    edges: [],
  });
  const [highlightedEditorItem, setHighlightedEditorItem] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isReviewPanelOpen, setIsReviewPanelOpen] = useState(false);
  const [runtimeConfig, setRuntimeConfig] = useState<RuntimeConfig | null>(null);
  const [openDraftMenu, setOpenDraftMenu] = useState("");
  const [editingDraftKey, setEditingDraftKey] = useState("");
  const [editingDraftName, setEditingDraftName] = useState("");
  const [deleteDraftTarget, setDeleteDraftTarget] = useState<DraftSummary | null>(null);
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
      const draft = await createDraft(name.trim(), description.trim(), generationMode);
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
    setOpenDraftMenu("");
    setEditingDraftKey("");
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
    setOpenDraftMenu("");
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

  async function handleRenameDraft(agentKey: string) {
    const nextName = editingDraftName.trim();
    const currentName = drafts.find((draft) => draft.agent_key === agentKey)?.name ?? "";
    if (!nextName || nextName === currentName) {
      setEditingDraftKey("");
      setEditingDraftName("");
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      const draft = await renameDraft(agentKey, nextName);
      if (activeDraft?.agent_key === agentKey) {
        setActiveDraft(draft);
      }
      setDrafts(await listDrafts());
      setEditingDraftKey("");
      setEditingDraftName("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not rename project.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleArchiveDraft(agentKey: string, draftName: string) {
    setOpenDraftMenu("");
    if (!window.confirm(`Archive "${draftName}" and hide it from the project list?`)) return;
    setIsLoading(true);
    setError("");
    try {
      const nextDrafts = await archiveDraft(agentKey);
      setDrafts(nextDrafts);
      if (activeDraft?.agent_key === agentKey) {
        setActiveDraft(nextDrafts[0] ? await loadDraft(nextDrafts[0].agent_key) : null);
        closeReviewPanel();
        setIsCreating(nextDrafts.length === 0);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not archive project.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleExportDraft(agentKey: string) {
    setOpenDraftMenu("");
    window.location.href = `/api/drafts/${agentKey}/export`;
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
        action === "design" ||
          action === "fix-plan" ||
          action === "v1-graph" ||
          action === "run-v0" ||
          action === "run-v1"
          ? generationMode
          : undefined,
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
    if (selectedArtifact === "eval_contract") {
      await handleSaveEvalContract();
      return;
    }
    if (selectedArtifact === "information_requirements") {
      await handleSaveInformationRequirements();
      return;
    }
    if (selectedArtifact === "tool_requirements") {
      await handleSaveToolRequirements();
      return;
    }
    if (selectedArtifact === "graph_design" || selectedArtifact === "graph_design_v1") {
      await handleSaveGraphDesign();
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
      setDrafts(await listDrafts());
      appendStepActivity("behavior_rules", "Saved behavior rules.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save behavior rules.");
      appendStepActivity("behavior_rules", "Behavior rule save failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSaveEvalContract() {
    if (!activeDraft) return;
    setIsLoading(true);
    setError("");
    appendStepActivity("behavior_rules", "Saving eval contract.");
    try {
      const draft = await saveEvalContract(activeDraft.agent_key, evalContractDraft);
      setActiveDraft(draft);
      setArtifactDraft(draft.artifact_sources.eval_contract ?? "");
      setEvalContractDraft(evalContractFromDraft(draft));
      setDrafts(await listDrafts());
      appendStepActivity("behavior_rules", "Saved eval contract.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save eval contract.");
      appendStepActivity("behavior_rules", "Eval contract save failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSaveInformationRequirements() {
    if (!activeDraft) return;
    setIsLoading(true);
    setError("");
    appendStepActivity("behavior_rules", "Saving information requirements.");
    try {
      const draft = await saveInformationRequirements(
        activeDraft.agent_key,
        informationRequirementsDraft,
      );
      setActiveDraft(draft);
      setArtifactDraft(draft.artifact_sources.information_requirements ?? "");
      setInformationRequirementsDraft(informationRequirementsFromDraft(draft));
      setDrafts(await listDrafts());
      appendStepActivity("behavior_rules", "Saved information requirements.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not save information requirements.",
      );
      appendStepActivity("behavior_rules", "Information requirement save failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSaveToolRequirements() {
    if (!activeDraft) return;
    setIsLoading(true);
    setError("");
    appendStepActivity("behavior_rules", "Saving tool requirements.");
    try {
      const draft = await saveToolRequirements(activeDraft.agent_key, toolRequirementsDraft);
      setActiveDraft(draft);
      setArtifactDraft(draft.artifact_sources.tool_requirements ?? "");
      setToolRequirementsDraft(toolRequirementsFromDraft(draft));
      setDrafts(await listDrafts());
      appendStepActivity("behavior_rules", "Saved tool requirements.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save tool requirements.");
      appendStepActivity("behavior_rules", "Tool requirement save failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSaveGraphDesign() {
    if (!activeDraft) return;
    setIsLoading(true);
    setError("");
    appendStepActivity(artifactStepId(graphDraft.artifact_key), "Saving graph design.");
    try {
      const draft = await saveGraphDesign(activeDraft.agent_key, graphDraft);
      setActiveDraft(draft);
      setArtifactDraft(draft.artifact_sources[graphDraft.artifact_key] ?? "");
      setGraphDraft(graphDesignFromDraft(draft, graphDraft.artifact_key));
      setDrafts(await listDrafts());
      appendStepActivity(artifactStepId(graphDraft.artifact_key), "Saved graph design.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save graph design.");
      appendStepActivity(artifactStepId(graphDraft.artifact_key), "Graph design save failed.");
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
      setDrafts(await listDrafts());
      appendStepActivity("target", "Saved target.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save target.");
      appendStepActivity("target", "Target save failed.");
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
    if (artifactKey === "eval_contract") {
      setEvalContractDraft(evalContractFromDraft(activeDraft));
    }
    if (artifactKey === "information_requirements") {
      setInformationRequirementsDraft(informationRequirementsFromDraft(activeDraft));
    }
    if (artifactKey === "tool_requirements") {
      setToolRequirementsDraft(toolRequirementsFromDraft(activeDraft));
    }
    if (artifactKey === "graph_design" || artifactKey === "graph_design_v1") {
      setGraphDraft(graphDesignFromDraft(activeDraft, artifactKey));
    }
    setIsReviewPanelOpen(true);
  }

  function closeReviewPanel() {
    setSelectedArtifact("");
    setArtifactDraft("");
    setIsReviewPanelOpen(false);
  }

  function markEditorItem(itemKey: string) {
    setHighlightedEditorItem(itemKey);
    window.setTimeout(() => {
      setHighlightedEditorItem((current) => (current === itemKey ? "" : current));
    }, 1300);
  }

  function appendStepActivity(stepId: string, message: string) {
    setActivityByStep((current) => ({
      ...current,
      [stepId]: [message, ...(current[stepId] ?? [])].slice(0, 3),
    }));
  }

  const target = activeDraft?.target.agent_target;
  const shouldShowComposer = isCreating || !activeDraft || !target;
  const activeStep = activeDraft?.status.steps.find((step) => !step.complete);
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
  const savedEvalContractDraft = activeDraft
    ? evalContractFromDraft(activeDraft)
    : evalContractDraft;
  const hasEvalContractChanges =
    selectedArtifact === "eval_contract" &&
    JSON.stringify(evalContractDraft) !== JSON.stringify(savedEvalContractDraft);
  const savedInformationRequirementsDraft = activeDraft
    ? informationRequirementsFromDraft(activeDraft)
    : informationRequirementsDraft;
  const hasInformationRequirementsChanges =
    selectedArtifact === "information_requirements" &&
    JSON.stringify(informationRequirementsDraft) !==
      JSON.stringify(savedInformationRequirementsDraft);
  const savedToolRequirementsDraft = activeDraft
    ? toolRequirementsFromDraft(activeDraft)
    : toolRequirementsDraft;
  const hasToolRequirementsChanges =
    selectedArtifact === "tool_requirements" &&
    JSON.stringify(toolRequirementsDraft) !== JSON.stringify(savedToolRequirementsDraft);
  const savedGraphDraft =
    activeDraft && (selectedArtifact === "graph_design" || selectedArtifact === "graph_design_v1")
      ? graphDesignFromDraft(activeDraft, selectedArtifact)
      : graphDraft;
  const hasGraphChanges =
    (selectedArtifact === "graph_design" || selectedArtifact === "graph_design_v1") &&
    JSON.stringify(graphDraft) !== JSON.stringify(savedGraphDraft);
  const hasReviewChanges =
    selectedArtifact === "target"
      ? hasTargetChanges
      : selectedArtifact === "behavior_rules"
        ? hasRulesChanges
        : selectedArtifact === "eval_contract"
          ? hasEvalContractChanges
          : selectedArtifact === "information_requirements"
            ? hasInformationRequirementsChanges
            : selectedArtifact === "tool_requirements"
              ? hasToolRequirementsChanges
              : selectedArtifact === "graph_design" || selectedArtifact === "graph_design_v1"
                ? hasGraphChanges
                : hasArtifactChanges;
  const selectedArtifactCard = activeDraft?.artifact_cards.find(
    (artifact) => artifact.id === selectedArtifact,
  );
  const selectedArtifactTitle = selectedArtifactCard?.artifact ?? selectedArtifact;
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
  const platformConfig = runtimeConfig?.platform;
  const platformStatus = platformConfig?.configured
    ? platformConfig.auth_configured
      ? "Platform: HTTP + auth"
      : "Platform: HTTP"
    : "Platform: local";

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
        <div className="sidebar-brand">
          <div>
            <span className="brand-mark">E</span>
            <strong>EDD Agent Lab</strong>
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
          <p>Agents</p>
          <div className="draft-list">
            {drafts.map((draft) => (
              <div
                className={draft.agent_key === activeDraft?.agent_key ? "draft-row active" : "draft-row"}
                key={draft.agent_key}
              >
                {editingDraftKey === draft.agent_key ? (
                  <input
                    autoFocus
                    className="draft-rename-input"
                    onBlur={() => void handleRenameDraft(draft.agent_key)}
                    onChange={(event) => setEditingDraftName(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.currentTarget.blur();
                      }
                      if (event.key === "Escape") {
                        setEditingDraftKey("");
                        setEditingDraftName("");
                      }
                    }}
                    value={editingDraftName}
                  />
                ) : (
                <button className="draft-open" onClick={() => void handleSelectDraft(draft.agent_key)}>
                    <strong>{draft.name}</strong>
                  </button>
                )}
                <span className="draft-actions">
                  <button
                    aria-label={`Open actions for ${draft.name}`}
                    className="draft-menu-trigger"
                    onClick={(event) => {
                      event.stopPropagation();
                      setOpenDraftMenu(openDraftMenu === draft.agent_key ? "" : draft.agent_key);
                    }}
                    title="Project actions"
                  >
                    <MoreHorizontal size={18} />
                  </button>
                  {openDraftMenu === draft.agent_key ? (
                    <div className="draft-menu">
                      <button
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => {
                          setOpenDraftMenu("");
                          setEditingDraftKey(draft.agent_key);
                          setEditingDraftName(draft.name);
                        }}
                      >
                        <PencilLine size={18} />
                        Rename
                      </button>
                      <button onClick={() => handleExportDraft(draft.agent_key)}>
                        <Download size={18} />
                        Export
                      </button>
                      <button onClick={() => void handleArchiveDraft(draft.agent_key, draft.name)}>
                        <Archive size={18} />
                        Archive
                      </button>
                      <button
                        className="danger"
                        onClick={() => {
                          setOpenDraftMenu("");
                          setDeleteDraftTarget(draft);
                        }}
                      >
                        <Trash2 size={18} />
                        Delete
                      </button>
                    </div>
                  ) : null}
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
        <span className="brand-mark">E</span>
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
            <span>{shouldShowComposer ? "Describe the target" : target?.purpose}</span>
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
            <span className="platform-status" title={platformConfig?.publish_endpoint ?? ""}>
              {platformStatus}
            </span>
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
              const publishRetryable =
                step.id === "publish_result" &&
                Boolean(
                  (
                    activeDraft.artifacts.publish_result as
                      | { publish_result?: { delivery?: { retryable?: boolean } } }
                      | undefined
                  )?.publish_result?.delivery?.retryable,
                );

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

                  {publishRetryable ? (
                    <button
                      className="step-action"
                      onClick={() => void handleAction("publish")}
                      disabled={isLoading}
                    >
                      <ArrowRight size={17} />
                      Retry publish
                    </button>
                  ) : null}

                  <div className="step-outputs">
                    {stepArtifacts.length > 0 ? (
                      stepArtifacts.map((artifact) => (
                        <div className="output-row" key={artifact.id}>
                          <div>
                            <strong>{artifact.artifact}</strong>
                            <span>{artifactDescriptions[artifact.id] ?? artifact.group}</span>
                          </div>
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
            <strong>{selectedArtifactTitle}</strong>
            <div>
              <button
                aria-label="Close review panel"
                className="secondary icon-only"
                onClick={closeReviewPanel}
                title="Close"
              >
                <PanelRight size={16} />
              </button>
              <button onClick={() => void handleSaveArtifact()} disabled={isLoading || !hasReviewChanges}>
                Save
              </button>
            </div>
          </div>
          {selectedArtifact === "target" ? (
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
          ) : selectedArtifact === "eval_contract" ? (
            <div className="eval-contract-editor">
              <label>
                Status
                <input
                  value={evalContractDraft.status}
                  onChange={(event) =>
                    setEvalContractDraft({
                      ...evalContractDraft,
                      status: event.target.value,
                    })
                  }
                />
              </label>
              <section>
                <div className="section-title-row">
                  <strong>Metrics</strong>
                  <button
                    className="small-editor-action"
                    onClick={() => {
                      setEvalContractDraft({
                        ...evalContractDraft,
                        metrics: [newEvalMetric(), ...evalContractDraft.metrics],
                      });
                      markEditorItem("metric-0");
                    }}
                  >
                    <Plus size={14} />
                    Metric
                  </button>
                </div>
                {evalContractDraft.metrics.map((metric, index) => (
                  <div
                    className={[
                      "rule-editor-card",
                      highlightedEditorItem === `metric-${index}` ? "newly-added" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    key={`${metric.id}-${index}`}
                  >
                    <button
                      aria-label={`Remove ${metric.id || "metric"}`}
                      className="card-remove"
                      onClick={() =>
                        setEvalContractDraft({
                          ...evalContractDraft,
                          metrics: withoutIndex(evalContractDraft.metrics, index),
                        })
                      }
                      title="Remove"
                    >
                      <Trash2 size={14} />
                    </button>
                    <label>
                      Metric id
                      <input
                        value={metric.id}
                        onChange={(event) => {
                          const metrics = [...evalContractDraft.metrics];
                          metrics[index] = { ...metric, id: event.target.value };
                          setEvalContractDraft({ ...evalContractDraft, metrics });
                        }}
                      />
                    </label>
                    <label>
                      Scale
                      <input
                        value={metric.scale}
                        onChange={(event) => {
                          const metrics = [...evalContractDraft.metrics];
                          metrics[index] = { ...metric, scale: event.target.value };
                          setEvalContractDraft({ ...evalContractDraft, metrics });
                        }}
                      />
                    </label>
                    <label>
                      Rules
                      <input
                        value={metric.rules.join(", ")}
                        onChange={(event) => {
                          const metrics = [...evalContractDraft.metrics];
                          metrics[index] = {
                            ...metric,
                            rules: event.target.value
                              .split(",")
                              .map((item) => item.trim())
                              .filter(Boolean),
                          };
                          setEvalContractDraft({ ...evalContractDraft, metrics });
                        }}
                      />
                    </label>
                  </div>
                ))}
              </section>
              <section>
                <div className="section-title-row">
                  <strong>Gates</strong>
                  <button
                    className="small-editor-action"
                    onClick={() => {
                      setEvalContractDraft({
                        ...evalContractDraft,
                        gates: [newEvalGate(), ...evalContractDraft.gates],
                      });
                      markEditorItem("gate-0");
                    }}
                  >
                    <Plus size={14} />
                    Gate
                  </button>
                </div>
                {evalContractDraft.gates.map((gate, index) => (
                  <div
                    className={[
                      "rule-editor-card",
                      highlightedEditorItem === `gate-${index}` ? "newly-added" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    key={`${gate.id}-${index}`}
                  >
                    <button
                      aria-label={`Remove ${gate.id || "gate"}`}
                      className="card-remove"
                      onClick={() =>
                        setEvalContractDraft({
                          ...evalContractDraft,
                          gates: withoutIndex(evalContractDraft.gates, index),
                        })
                      }
                      title="Remove"
                    >
                      <Trash2 size={14} />
                    </button>
                    <label>
                      Gate id
                      <input
                        value={gate.id}
                        onChange={(event) => {
                          const gates = [...evalContractDraft.gates];
                          gates[index] = { ...gate, id: event.target.value };
                          setEvalContractDraft({ ...evalContractDraft, gates });
                        }}
                      />
                    </label>
                    <label>
                      Type
                      <input
                        value={gate.type}
                        onChange={(event) => {
                          const gates = [...evalContractDraft.gates];
                          gates[index] = { ...gate, type: event.target.value };
                          setEvalContractDraft({ ...evalContractDraft, gates });
                        }}
                      />
                    </label>
                    <label>
                      Condition
                      <input
                        value={gate.condition}
                        onChange={(event) => {
                          const gates = [...evalContractDraft.gates];
                          gates[index] = { ...gate, condition: event.target.value };
                          setEvalContractDraft({ ...evalContractDraft, gates });
                        }}
                      />
                    </label>
                  </div>
                ))}
              </section>
            </div>
          ) : selectedArtifact === "information_requirements" ? (
            <div className="requirements-editor">
              <div className="section-title-row">
                <strong>Requirements</strong>
                <button
                  className="small-editor-action"
                  onClick={() => {
                    setInformationRequirementsDraft([
                      newInformationRequirement(),
                      ...informationRequirementsDraft,
                    ]);
                    markEditorItem("requirement-0");
                  }}
                >
                  <Plus size={14} />
                  Requirement
                </button>
              </div>
              {informationRequirementsDraft.map((requirement, index) => (
                <section
                  className={[
                    "rule-editor-card",
                    highlightedEditorItem === `requirement-${index}` ? "newly-added" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  key={`${requirement.id}-${index}`}
                >
                  <button
                    aria-label={`Remove ${requirement.id || "requirement"}`}
                    className="card-remove"
                    onClick={() =>
                      setInformationRequirementsDraft(
                        withoutIndex(informationRequirementsDraft, index),
                      )
                    }
                    title="Remove"
                  >
                    <Trash2 size={14} />
                  </button>
                  <label>
                    Requirement id
                    <input
                      value={requirement.id}
                      onChange={(event) => {
                        const requirements = [...informationRequirementsDraft];
                        requirements[index] = { ...requirement, id: event.target.value };
                        setInformationRequirementsDraft(requirements);
                      }}
                    />
                  </label>
                  <label>
                    Description
                    <textarea
                      value={requirement.description}
                      onChange={(event) => {
                        const requirements = [...informationRequirementsDraft];
                        requirements[index] = {
                          ...requirement,
                          description: event.target.value,
                        };
                        setInformationRequirementsDraft(requirements);
                      }}
                    />
                  </label>
                  <label>
                    Required for rules
                    <input
                      value={requirement.required_for_rules.join(", ")}
                      onChange={(event) => {
                        const requirements = [...informationRequirementsDraft];
                        requirements[index] = {
                          ...requirement,
                          required_for_rules: event.target.value
                            .split(",")
                            .map((item) => item.trim())
                            .filter(Boolean),
                        };
                        setInformationRequirementsDraft(requirements);
                      }}
                    />
                  </label>
                  <label>
                    Status
                    <input
                      value={requirement.status}
                      onChange={(event) => {
                        const requirements = [...informationRequirementsDraft];
                        requirements[index] = { ...requirement, status: event.target.value };
                        setInformationRequirementsDraft(requirements);
                      }}
                    />
                  </label>
                </section>
              ))}
            </div>
          ) : selectedArtifact === "tool_requirements" ? (
            <div className="requirements-editor">
              <div className="section-title-row">
                <strong>Tools</strong>
                <button
                  className="small-editor-action"
                  onClick={() => {
                    setToolRequirementsDraft([newToolRequirement(), ...toolRequirementsDraft]);
                    markEditorItem("tool-0");
                  }}
                >
                  <Plus size={14} />
                  Tool
                </button>
              </div>
              {toolRequirementsDraft.map((tool, index) => (
                <section
                  className={[
                    "rule-editor-card",
                    highlightedEditorItem === `tool-${index}` ? "newly-added" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  key={`${tool.id}-${index}`}
                >
                  <button
                    aria-label={`Remove ${tool.id || "tool"}`}
                    className="card-remove"
                    onClick={() => setToolRequirementsDraft(withoutIndex(toolRequirementsDraft, index))}
                    title="Remove"
                  >
                    <Trash2 size={14} />
                  </button>
                  <label>
                    Tool id
                    <input
                      value={tool.id}
                      onChange={(event) => {
                        const tools = [...toolRequirementsDraft];
                        tools[index] = { ...tool, id: event.target.value };
                        setToolRequirementsDraft(tools);
                      }}
                    />
                  </label>
                  <label>
                    Suggested tool name
                    <input
                      value={tool.suggested_tool_name}
                      onChange={(event) => {
                        const tools = [...toolRequirementsDraft];
                        tools[index] = { ...tool, suggested_tool_name: event.target.value };
                        setToolRequirementsDraft(tools);
                      }}
                    />
                  </label>
                  <label>
                    Information requirements
                    <input
                      value={tool.information_requirements.join(", ")}
                      onChange={(event) => {
                        const tools = [...toolRequirementsDraft];
                        tools[index] = {
                          ...tool,
                          information_requirements: event.target.value
                            .split(",")
                            .map((item) => item.trim())
                            .filter(Boolean),
                        };
                        setToolRequirementsDraft(tools);
                      }}
                    />
                  </label>
                  <label>
                    Implementation status
                    <input
                      value={tool.implementation_status}
                      onChange={(event) => {
                        const tools = [...toolRequirementsDraft];
                        tools[index] = { ...tool, implementation_status: event.target.value };
                        setToolRequirementsDraft(tools);
                      }}
                    />
                  </label>
                  <label className="checkbox-row">
                    <input
                      checked={tool.production_blocker}
                      onChange={(event) => {
                        const tools = [...toolRequirementsDraft];
                        tools[index] = { ...tool, production_blocker: event.target.checked };
                        setToolRequirementsDraft(tools);
                      }}
                      type="checkbox"
                    />
                    Production blocker
                  </label>
                  <label>
                    Status
                    <input
                      value={tool.status}
                      onChange={(event) => {
                        const tools = [...toolRequirementsDraft];
                        tools[index] = { ...tool, status: event.target.value };
                        setToolRequirementsDraft(tools);
                      }}
                    />
                  </label>
                </section>
              ))}
            </div>
          ) : selectedArtifact === "graph_design" || selectedArtifact === "graph_design_v1" ? (
            <div className="graph-editor">
              <label>
                Version
                <input
                  value={graphDraft.version}
                  onChange={(event) =>
                    setGraphDraft({ ...graphDraft, version: event.target.value })
                  }
                />
              </label>
              <label>
                Status
                <input
                  value={graphDraft.status}
                  onChange={(event) =>
                    setGraphDraft({ ...graphDraft, status: event.target.value })
                  }
                />
              </label>
              <section>
                <div className="section-title-row">
                  <strong>Nodes</strong>
                  <button
                    className="small-editor-action"
                    onClick={() => {
                      setGraphDraft({
                        ...graphDraft,
                        nodes: [
                          { id: "new_node", purpose: "", supports_rules: [] },
                          ...graphDraft.nodes,
                        ],
                      });
                      markEditorItem("node-0");
                    }}
                  >
                    <Plus size={14} />
                    Node
                  </button>
                </div>
                {graphDraft.nodes.map((node, index) => (
                  <div
                    className={[
                      "rule-editor-card",
                      highlightedEditorItem === `node-${index}` ? "newly-added" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    key={`${node.id}-${index}`}
                  >
                    <button
                      aria-label={`Remove ${node.id || "node"}`}
                      className="card-remove"
                      onClick={() =>
                        setGraphDraft({
                          ...graphDraft,
                          nodes: withoutIndex(graphDraft.nodes, index),
                        })
                      }
                      title="Remove"
                    >
                      <Trash2 size={14} />
                    </button>
                    <label>
                      Node id
                      <input
                        value={node.id}
                        onChange={(event) => {
                          const nodes = [...graphDraft.nodes];
                          nodes[index] = { ...node, id: event.target.value };
                          setGraphDraft({ ...graphDraft, nodes });
                        }}
                      />
                    </label>
                    <label>
                      Purpose
                      <textarea
                        value={node.purpose}
                        onChange={(event) => {
                          const nodes = [...graphDraft.nodes];
                          nodes[index] = { ...node, purpose: event.target.value };
                          setGraphDraft({ ...graphDraft, nodes });
                        }}
                      />
                    </label>
                    <label>
                      Supports rules
                      <input
                        value={node.supports_rules.join(", ")}
                        onChange={(event) => {
                          const nodes = [...graphDraft.nodes];
                          nodes[index] = {
                            ...node,
                            supports_rules: event.target.value
                              .split(",")
                              .map((item) => item.trim())
                              .filter(Boolean),
                          };
                          setGraphDraft({ ...graphDraft, nodes });
                        }}
                      />
                    </label>
                  </div>
                ))}
              </section>
              <section>
                <div className="section-title-row">
                  <strong>Edges</strong>
                  <button
                    className="small-editor-action"
                    onClick={() => {
                      setGraphDraft({
                        ...graphDraft,
                        edges: [{ from: "", to: "" }, ...graphDraft.edges],
                      });
                      markEditorItem("edge-0");
                    }}
                  >
                    <Plus size={14} />
                    Edge
                  </button>
                </div>
                {graphDraft.edges.map((edge, index) => (
                  <div
                    className={[
                      "rule-editor-card",
                      highlightedEditorItem === `edge-${index}` ? "newly-added" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    key={`${edge.from}-${edge.to}-${index}`}
                  >
                    <button
                      aria-label={`Remove edge ${index + 1}`}
                      className="card-remove"
                      onClick={() =>
                        setGraphDraft({
                          ...graphDraft,
                          edges: withoutIndex(graphDraft.edges, index),
                        })
                      }
                      title="Remove"
                    >
                      <Trash2 size={14} />
                    </button>
                    <label>
                      From
                      <input
                        value={edge.from}
                        onChange={(event) => {
                          const edges = [...graphDraft.edges];
                          edges[index] = { ...edge, from: event.target.value };
                          setGraphDraft({ ...graphDraft, edges });
                        }}
                      />
                    </label>
                    <label>
                      To
                      <input
                        value={edge.to}
                        onChange={(event) => {
                          const edges = [...graphDraft.edges];
                          edges[index] = { ...edge, to: event.target.value };
                          setGraphDraft({ ...graphDraft, edges });
                        }}
                      />
                    </label>
                  </div>
                ))}
              </section>
            </div>
          ) : selectedArtifact === "behavior_rules" ? (
            <div className="rules-editor">
              <div className="section-title-row">
                <strong>Rules</strong>
                <button
                  className="small-editor-action"
                  onClick={() => {
                    setRulesDraft([newBehaviorRule(), ...rulesDraft]);
                    markEditorItem("rule-0");
                  }}
                >
                  <Plus size={14} />
                  Rule
                </button>
              </div>
              {rulesDraft.map((rule, index) => (
                <section
                  className={[
                    "rule-editor-card",
                    highlightedEditorItem === `rule-${index}` ? "newly-added" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  key={`${rule.id}-${index}`}
                >
                  <button
                    aria-label={`Remove ${rule.id || "rule"}`}
                    className="card-remove"
                    onClick={() => setRulesDraft(withoutIndex(rulesDraft, index))}
                    title="Remove"
                  >
                    <Trash2 size={14} />
                  </button>
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
          {selectedValidation?.valid === false ? (
            <div className="validation-panel invalid">
              <strong>Validation issues</strong>
              {selectedValidation.errors.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          ) : null}
        </aside>
      ) : null}

      {deleteDraftTarget ? (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-draft-title">
            <h2 id="delete-draft-title">Delete agent?</h2>
            <p>
              This will delete <strong>{deleteDraftTarget.name}</strong>.
            </p>
            <span>The local draft artifacts for this agent will be removed from this workspace.</span>
            <div className="confirm-actions">
              <button className="secondary" onClick={() => setDeleteDraftTarget(null)}>
                Cancel
              </button>
              <button
                className="confirm-delete"
                disabled={isLoading}
                onClick={() => {
                  void handleDeleteDraft(deleteDraftTarget.agent_key, deleteDraftTarget.name);
                  setDeleteDraftTarget(null);
                }}
              >
                Delete
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
