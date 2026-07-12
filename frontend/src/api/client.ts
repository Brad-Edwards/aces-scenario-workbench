export type Principal = {
  email: string;
  displayName: string;
  isStaff: boolean;
};

export type ScenarioRow = {
  slug: string;
  name: string;
  description: string;
  role: string;
  revisionCount: number;
  updatedAt: string;
};

export type ScenarioDetail = {
  scenario: ScenarioRow;
  revisions: Array<{
    id: number;
    label: string;
    packVersion: string;
    framework: string;
    createdAt: string;
    updatedAt: string;
    moduleCount: number;
    techniqueCount: number;
    evidenceCount: number;
    commentCount: number;
    decisionCount: number;
  }>;
};

export type RevisionWorkspace = {
  id: number;
  label: string;
  scenario: { slug: string; name: string; description: string };
  framework: string;
  createdAt: string;
  modules: Array<{
    id: string;
    name: string;
    behaviorSpecification: string;
    tier: string;
    objective: string;
    minutes: number | null;
    flagOutcome: string;
    justification: string;
    techniqueCount: number;
    evidenceCount: number;
    commentCount: number;
    decisionCount: number;
  }>;
  techniques: Array<{
    id: string;
    name: string;
    module: string;
    tactics: string[];
    evidence: string;
    surface: string;
    relationship: string;
    coverageStatus: string;
    plannedAction: string;
    rationale: string;
    commentCount: number;
    decisionCount: number;
  }>;
  evidence: Array<{
    id: string;
    description: string;
    techniqueCount: number;
    commentCount: number;
    decisionCount: number;
  }>;
  decisions: Array<{
    id: number;
    objectType: string;
    objectId: string;
    decision: string;
    rationale: string;
    author: string;
    createdAt: string;
  }>;
  comments: Array<{
    id: number;
    objectType: string;
    objectId: string;
    body: string;
    author: string;
    createdAt: string;
    updatedAt: string;
    edited: boolean;
  }>;
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function getPrincipal() {
  return getJson<Principal>("/api/app/me");
}

export function getScenarios() {
  return getJson<{ scenarios: ScenarioRow[] }>("/api/app/scenarios");
}

export function getScenario(slug: string) {
  return getJson<ScenarioDetail>(`/api/app/scenarios/${encodeURIComponent(slug)}`);
}

export function getRevision(id: string) {
  return getJson<RevisionWorkspace>(`/api/app/revisions/${encodeURIComponent(id)}`);
}
