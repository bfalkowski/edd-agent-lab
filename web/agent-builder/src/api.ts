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
      status: string;
    };
  };
  artifacts: Record<string, unknown>;
  artifact_sources: Record<string, string>;
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

export async function listDrafts(): Promise<DraftSummary[]> {
  const response = await fetch("/api/drafts");
  assertOk(response);
  const payload = await response.json();
  return payload.drafts;
}

export async function createDraft(name: string, description: string): Promise<DraftDetail> {
  const response = await fetch("/api/drafts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  assertOk(response);
  return response.json();
}

export async function loadDraft(agentKey: string): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}`);
  assertOk(response);
  return response.json();
}

export async function deleteDraft(agentKey: string): Promise<DraftSummary[]> {
  const response = await fetch(`/api/drafts/${agentKey}`, { method: "DELETE" });
  assertOk(response);
  const payload = await response.json();
  return payload.drafts;
}

export async function runDraftAction(agentKey: string, action: string): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/${action}`, { method: "POST" });
  assertOk(response);
  return response.json();
}

export async function saveScenario(agentKey: string, problem: string): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/scenario`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ problem }),
  });
  assertOk(response);
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
  assertOk(response);
  return response.json();
}

export async function deleteArtifact(agentKey: string, artifactKey: string): Promise<DraftDetail> {
  const response = await fetch(`/api/drafts/${agentKey}/artifacts/${artifactKey}`, {
    method: "DELETE",
  });
  assertOk(response);
  return response.json();
}

function assertOk(response: Response): void {
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
}
