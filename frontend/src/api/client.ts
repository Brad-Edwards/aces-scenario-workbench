export type Principal = {
  email: string;
  displayName: string;
  isStaff: boolean;
};

export type ProjectRow = {
  slug: string;
  name: string;
  description: string;
  role: string;
  scenarioCount: number;
  revisionCount: number;
  updatedAt: string;
};

export type ProjectDetail = {
  project: ProjectRow;
  scenarios: Array<{
    slug: string;
    name: string;
    description: string;
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
  }>;
};

export type RevisionWorkspace = {
  id: number;
  label: string;
  project: { slug: string; name: string };
  scenario: { slug: string; name: string; description: string };
  framework: string;
  createdAt: string;
  modules: Array<{
    id: string;
    name: string;
    tier: string;
    objective: string;
    minutes: number | null;
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
    plannedAction: string;
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

export function getProjects() {
  return getJson<{ projects: ProjectRow[] }>("/api/app/projects");
}

export function getProject(slug: string) {
  return getJson<ProjectDetail>(`/api/app/projects/${encodeURIComponent(slug)}`);
}

export function getRevision(id: string) {
  return getJson<RevisionWorkspace>(`/api/app/revisions/${encodeURIComponent(id)}`);
}
