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
    challengeCount: number;
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
  challenges: Array<{
    id: string;
    flagId: string;
    outcome: string;
    title: string;
    question: string;
    category: string;
    difficulty: string;
    points: number | null;
    hints: string[];
    implemented: boolean;
    runtimeEntrypoint: string;
    sourcePath: string;
    module: string;
    moduleName: string;
    techniqueIds: string[];
    evidenceRequirements: Array<{
      evidenceId: string;
      predicate: string;
      sourcePath: string;
      eventId: string;
      eventKind: string;
      sourceService: string;
      sourceAsset: string;
      freshnessSeconds: number | null;
      resetOwner: string;
    }>;
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

export type DecisionValue = "accept" | "needs-change" | "resolve" | "reopen";
export type RevisionComment = RevisionWorkspace["comments"][number];
export type RevisionDecision = RevisionWorkspace["decisions"][number];

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

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const csrfToken = getCookie("csrftoken");
  const response = await fetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the status-only fallback.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

function getCookie(name: string) {
  const match = document.cookie
    .split("; ")
    .find((candidate) => candidate.startsWith(`${encodeURIComponent(name)}=`));
  if (!match) return "";
  return decodeURIComponent(match.split("=").slice(1).join("="));
}

function objectActivityPath(revisionId: string | number, objectType: string, objectId: string, suffix: string) {
  return `/api/app/revisions/${encodeURIComponent(String(revisionId))}/objects/${encodeURIComponent(
    objectType,
  )}/${encodeURIComponent(objectId)}/${suffix}`;
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

export function postObjectComment(
  revisionId: string | number,
  objectType: string,
  objectId: string,
  body: string,
) {
  return postJson<{ comment: RevisionComment }>(
    objectActivityPath(revisionId, objectType, objectId, "comments"),
    { body },
  );
}

export function postObjectDecision(
  revisionId: string | number,
  objectType: string,
  objectId: string,
  decision: DecisionValue,
  rationale: string,
) {
  return postJson<{ decision: RevisionDecision }>(
    objectActivityPath(revisionId, objectType, objectId, "decisions"),
    { decision, rationale },
  );
}
