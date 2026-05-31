export type DraftSummary = {
  agent_key: string;
  name: string;
  updated_at: string;
  target_path: string;
};

export type WorkflowStep = {
  id: string;
  step: string;
  complete: boolean;
  next_action: string;
};

export type DraftDetail = {
  agent_key: string;
  target: {
    agent_target: {
      id: string;
      name: string;
      purpose: string;
      risk_tolerance: string;
      expected_output_format: string;
      status: string;
    };
  };
  artifacts: Record<string, unknown>;
  artifact_sources: Record<string, string>;
  artifact_validations: Record<string, { valid: boolean; errors: string[] }>;
  status: {
    completed: number;
    total: number;
    percent: number;
    next_action: string;
    steps: WorkflowStep[];
  };
  artifact_cards: Array<{
    id: string;
    artifact: string;
    group: string;
    status: string;
    action: string;
    file: string;
  }>;
  comparison_view: Record<string, unknown>;
};

export type WorkflowEvent = {
  step_id: string;
  phase: "starting" | "running" | "artifact" | "completed" | "failed";
  message: string;
  artifact_id?: string;
  file?: string;
  retry_action?: string;
  retryable?: boolean;
  draft?: DraftDetail;
};

export type GenerationMode = "auto" | "mock" | "live";

export type RuntimeConfig = {
  generation: {
    default_mode: GenerationMode;
    resolved_mode: "mock" | "live";
    live_available: boolean;
    model: string;
  };
};

export async function loadRuntimeConfig(): Promise<RuntimeConfig> {
  const response = await fetch("/api/runtime");
  await assertOk(response);
  return response.json();
}

export async function listDrafts(): Promise<DraftSummary[]> {
  const response = await fetch("/api/drafts");
  await assertOk(response);
  const payload = await response.json();
  return payload.drafts;
}

export async function createDraft(name: string, description: string): Promise<DraftDetail> {
  const response = await fetch("/api/drafts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  await assertOk(response);
  return response.json();
}

export async function loadDraft(agentKey: string): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}`);
  await assertOk(response);
  return response.json();
}

export async function deleteDraft(agentKey: string): Promise<DraftSummary[]> {
  const response = await fetch(`/api/drafts/${agentKey}`, { method: "DELETE" });
  await assertOk(response);
  const payload = await response.json();
  return payload.drafts;
}

export async function renameDraft(agentKey: string, name: string): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/rename`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  await assertOk(response);
  return response.json();
}

export async function archiveDraft(agentKey: string): Promise<DraftSummary[]> {
  const response = await fetch(`/api/drafts/${agentKey}/archive`, { method: "POST" });
  await assertOk(response);
  const payload = await response.json();
  return payload.drafts;
}

export async function runDraftAction(agentKey: string, action: string): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/${action}`, { method: "POST" });
  await assertOk(response);
  return response.json();
}

export async function streamDraftAction(
  agentKey: string,
  action: string,
  onEvent: (event: WorkflowEvent) => void,
  generationMode?: GenerationMode,
): Promise<DraftDetail> {
  const params = new URLSearchParams();
  if (generationMode) params.set("generation_mode", generationMode);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`/api/drafts/${agentKey}/actions/${action}/stream${suffix}`, {
    method: "POST",
  });
  await assertOk(response);
  if (!response.body) {
    throw new Error("Streaming response was empty.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalDraft: DraftDetail | null = null;
  let failedEvent: WorkflowEvent | null = null;

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line) as WorkflowEvent;
      onEvent(event);
      if (event.draft) finalDraft = event.draft;
      if (event.phase === "failed") failedEvent = event;
    }
    if (done) break;
  }

  if (buffer.trim()) {
    const event = JSON.parse(buffer) as WorkflowEvent;
    onEvent(event);
    if (event.draft) finalDraft = event.draft;
    if (event.phase === "failed") failedEvent = event;
  }

  if (failedEvent) {
    throw new Error(failedEvent.message);
  }
  if (!finalDraft) {
    throw new Error("Workflow action did not return a draft.");
  }
  return finalDraft;
}

export async function saveScenario(agentKey: string, problem: string): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/scenario`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ problem }),
  });
  await assertOk(response);
  return response.json();
}

export type TargetUpdate = {
  name: string;
  purpose: string;
  risk_tolerance: string;
  expected_output_format: string;
};

export type BehaviorRule = {
  id: string;
  severity: string;
  description: string;
  target_id?: string;
  status: string;
};

export type EvalMetric = {
  id: string;
  scale: string;
  rules: string[];
};

export type EvalGate = {
  id: string;
  type: string;
  condition: string;
};

export type EvalContractUpdate = {
  metrics: EvalMetric[];
  gates: EvalGate[];
  status: string;
};

export type InformationRequirement = {
  id: string;
  description: string;
  required_for_rules: string[];
  status: string;
};

export type ToolRequirement = {
  id: string;
  suggested_tool_name: string;
  information_requirements: string[];
  implementation_status: string;
  production_blocker: boolean;
  status: string;
};

export type GraphNode = {
  id: string;
  purpose: string;
  supports_rules: string[];
};

export type GraphEdge = {
  from: string;
  to: string;
};

export type GraphDesignUpdate = {
  artifact_key: "graph_design" | "graph_design_v1";
  version: string;
  status: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export async function saveTarget(agentKey: string, target: TargetUpdate): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/target`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(target),
  });
  await assertOk(response);
  return response.json();
}

export async function saveBehaviorRules(
  agentKey: string,
  rules: BehaviorRule[],
): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/rules`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rules }),
  });
  await assertOk(response);
  return response.json();
}

export async function saveEvalContract(
  agentKey: string,
  contract: EvalContractUpdate,
): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/eval-contract`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(contract),
  });
  await assertOk(response);
  return response.json();
}

export async function saveInformationRequirements(
  agentKey: string,
  requirements: InformationRequirement[],
): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/information-requirements`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ requirements }),
  });
  await assertOk(response);
  return response.json();
}

export async function saveToolRequirements(
  agentKey: string,
  tools: ToolRequirement[],
): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/tool-requirements`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tools }),
  });
  await assertOk(response);
  return response.json();
}

export async function saveGraphDesign(
  agentKey: string,
  graph: GraphDesignUpdate,
): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/graph-design`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(graph),
  });
  await assertOk(response);
  return response.json();
}

export async function saveArtifactSource(
  agentKey: string,
  artifactKey: string,
  source: string,
): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/artifacts/${artifactKey}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source }),
  });
  await assertOk(response);
  return response.json();
}

export async function deleteArtifact(agentKey: string, artifactKey: string): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/artifacts/${artifactKey}`, {
    method: "DELETE",
  });
  await assertOk(response);
  return response.json();
}

async function assertOk(response: Response): Promise<void> {
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") {
        message = payload.detail;
      }
    } catch {
      // Keep the status-only message when the response body is not JSON.
    }
    throw new Error(message);
  }
}
