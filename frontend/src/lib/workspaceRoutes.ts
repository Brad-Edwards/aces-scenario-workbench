export type WorkspaceTab = "modules" | "techniques" | "evidence" | "comments" | "decisions";

export function revisionPath(revisionId: number | string, tab?: WorkspaceTab) {
  const base = `/app/revisions/${encodeURIComponent(String(revisionId))}`;
  return tab ? `${base}#${tab}` : base;
}

export function modulePath(revisionId: number | string, moduleId: string) {
  return `${revisionPath(revisionId)}/modules/${encodeURIComponent(moduleId)}`;
}

export function techniquePath(revisionId: number | string, techniqueId: string) {
  return `${revisionPath(revisionId)}/techniques/${encodeURIComponent(techniqueId)}`;
}

export function evidencePath(revisionId: number | string, evidenceId: string) {
  return `${revisionPath(revisionId)}/evidence/${encodeURIComponent(evidenceId)}`;
}

export function objectPath(revisionId: number | string, objectType: string, objectId: string) {
  switch (objectType) {
    case "step":
      return modulePath(revisionId, objectId);
    case "technique":
      return techniquePath(revisionId, objectId);
    case "evidence":
      return evidencePath(revisionId, objectId);
    case "tactic":
      return revisionPath(revisionId, "techniques");
    default:
      return revisionPath(revisionId, "comments");
  }
}
