import { Link, useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getRevision, type RevisionWorkspace } from "@/api/client";
import { Badge, Card, ClickableRow, EmptyState, PageHeader, Table, Td, Th } from "@/components/ui";
import { evidencePath, modulePath, objectPath, techniquePath } from "@/lib/workspaceRoutes";

type TabKey = "modules" | "techniques" | "evidence" | "comments" | "decisions";

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: "modules", label: "Modules" },
  { key: "techniques", label: "Techniques" },
  { key: "evidence", label: "Evidence" },
  { key: "comments", label: "Comments" },
  { key: "decisions", label: "Decisions" },
];

export function RevisionPage() {
  const { id = "" } = useParams();
  const location = useLocation();
  const query = useQuery({ queryKey: ["revision", id], queryFn: () => getRevision(id), enabled: Boolean(id) });
  const revision = query.data;
  const active = tabFromHash(location.hash);

  if (query.isLoading) return <p className="text-sm text-muted-foreground">Loading workspace…</p>;
  if (query.isError || !revision) return <p className="text-sm text-destructive">Could not load workspace.</p>;

  return (
    <>
      <PageHeader
        title={revision.scenario.name}
        description={`${revision.label}${revision.framework ? ` / ${revision.framework}` : ""}`}
        actions={
          <Link to={`/app/scenarios/${revision.scenario.slug}`} className="text-sm text-muted-foreground hover:text-foreground">
            Back to scenario
          </Link>
        }
      />

      <div className="mb-4 flex flex-wrap gap-2" aria-label="Workspace views">
        {TABS.map((tab) => (
          <a
            key={tab.key}
            href={`#${tab.key}`}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              active === tab.key
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
            }`}
          >
            {tab.label}
          </a>
        ))}
      </div>

      {active === "modules" ? <ModulesTable revision={revision} /> : null}
      {active === "techniques" ? <TechniquesTable revision={revision} /> : null}
      {active === "evidence" ? <EvidenceTable revision={revision} /> : null}
      {active === "comments" ? <CommentsTable revision={revision} /> : null}
      {active === "decisions" ? <DecisionsTable revision={revision} /> : null}
    </>
  );
}

function tabFromHash(hash: string): TabKey {
  const value = hash.replace("#", "");
  return TABS.some((tab) => tab.key === value) ? (value as TabKey) : "modules";
}

function ModulesTable({ revision }: Readonly<{ revision: RevisionWorkspace }>) {
  return (
    <Card className="overflow-hidden py-0">
      {revision.modules.length === 0 ? (
        <EmptyState title="No modules" body="This revision does not include challenge modules." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>Module</Th>
              <Th>Tier</Th>
              <Th>Objective</Th>
              <Th className="text-right">Minutes</Th>
              <Th className="text-right">Techniques</Th>
              <Th className="text-right">Evidence</Th>
              <Th className="text-right">Comments</Th>
              <Th className="text-right">Decisions</Th>
            </tr>
          </thead>
          <tbody>
            {revision.modules.map((module) => (
              <ClickableRow
                key={module.id}
                to={modulePath(revision.id, module.id)}
                aria-label={`Open module ${module.id}`}
              >
                <Td className="font-medium">
                  <Link to={modulePath(revision.id, module.id)} className="hover:underline">
                    {module.name || `Module ${module.id}`}
                  </Link>
                </Td>
                <Td>{module.tier ? <Badge>{module.tier}</Badge> : "—"}</Td>
                <Td className="min-w-[420px] whitespace-normal text-muted-foreground">{module.objective || "—"}</Td>
                <Td className="text-right font-mono tabular-nums">{module.minutes ?? "—"}</Td>
                <Td className="text-right font-mono tabular-nums">{module.techniqueCount}</Td>
                <Td className="text-right font-mono tabular-nums">{module.evidenceCount}</Td>
                <Td className="text-right font-mono tabular-nums">{module.commentCount}</Td>
                <Td className="text-right font-mono tabular-nums">{module.decisionCount}</Td>
              </ClickableRow>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function TechniquesTable({ revision }: Readonly<{ revision: RevisionWorkspace }>) {
  return (
    <Card className="overflow-hidden py-0">
      <Table>
        <thead>
          <tr className="border-b border-border">
            <Th>ID</Th>
            <Th>Name</Th>
            <Th>Module</Th>
            <Th>Tactics</Th>
            <Th>Evidence</Th>
            <Th>Planned action</Th>
            <Th className="text-right">Comments</Th>
            <Th className="text-right">Decisions</Th>
          </tr>
        </thead>
        <tbody>
          {revision.techniques.map((technique) => (
            <ClickableRow
              key={technique.id}
              to={techniquePath(revision.id, technique.id)}
              aria-label={`Open ${technique.id}`}
            >
              <Td className="font-mono font-medium">
                <Link to={techniquePath(revision.id, technique.id)} className="hover:underline">
                  {technique.id}
                </Link>
              </Td>
              <Td className="font-medium">{technique.name}</Td>
              <Td>
                {technique.module ? (
                  <Link to={modulePath(revision.id, technique.module)} className="font-mono hover:underline">
                    {technique.module}
                  </Link>
                ) : (
                  "—"
                )}
              </Td>
              <Td className="max-w-[280px] whitespace-normal text-muted-foreground">
                {technique.tactics.length ? technique.tactics.join(", ") : "—"}
              </Td>
              <Td className="font-mono text-muted-foreground">
                {technique.evidence ? (
                  <Link to={evidencePath(revision.id, technique.evidence)} className="hover:underline">
                    {technique.evidence}
                  </Link>
                ) : (
                  "—"
                )}
              </Td>
              <Td className="min-w-[420px] whitespace-normal text-muted-foreground">
                {technique.plannedAction || "—"}
              </Td>
              <Td className="text-right font-mono tabular-nums">{technique.commentCount}</Td>
              <Td className="text-right font-mono tabular-nums">{technique.decisionCount}</Td>
            </ClickableRow>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}

function EvidenceTable({ revision }: Readonly<{ revision: RevisionWorkspace }>) {
  return (
    <Card className="overflow-hidden py-0">
      <Table>
        <thead>
          <tr className="border-b border-border">
            <Th>ID</Th>
            <Th>Description</Th>
            <Th className="text-right">Techniques</Th>
            <Th className="text-right">Comments</Th>
            <Th className="text-right">Decisions</Th>
          </tr>
        </thead>
        <tbody>
          {revision.evidence.map((item) => (
            <ClickableRow
              key={item.id}
              to={evidencePath(revision.id, item.id)}
              aria-label={`Open evidence ${item.id}`}
            >
              <Td className="font-mono font-medium">
                <Link to={evidencePath(revision.id, item.id)} className="hover:underline">
                  {item.id}
                </Link>
              </Td>
              <Td className="min-w-[420px] whitespace-normal text-muted-foreground">{item.description || "—"}</Td>
              <Td className="text-right font-mono tabular-nums">{item.techniqueCount}</Td>
              <Td className="text-right font-mono tabular-nums">{item.commentCount}</Td>
              <Td className="text-right font-mono tabular-nums">{item.decisionCount}</Td>
            </ClickableRow>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}

function CommentsTable({ revision }: Readonly<{ revision: RevisionWorkspace }>) {
  return (
    <Card className="overflow-hidden py-0">
      {revision.comments.length === 0 ? (
        <EmptyState title="No comments" body="Comments will appear here as scenario collaborators discuss objects." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>Object</Th>
              <Th>Comment</Th>
              <Th>Author</Th>
              <Th>Created</Th>
            </tr>
          </thead>
          <tbody>
            {revision.comments.map((comment) => {
              const target = objectPath(revision.id, comment.objectType, comment.objectId);
              return (
                <ClickableRow
                  key={comment.id}
                  to={target}
                  aria-label={`Open ${objectLabel(comment.objectType)} ${comment.objectId}`}
                >
                  <Td className="font-mono">
                    <Link to={target} className="hover:underline">
                      {comment.objectType}:{comment.objectId}
                    </Link>
                  </Td>
                  <Td className="min-w-[460px] whitespace-pre-wrap text-muted-foreground">
                    {comment.body}
                    {comment.edited ? <span className="ml-2 text-xs">(edited)</span> : null}
                  </Td>
                  <Td>{comment.author}</Td>
                  <Td className="text-muted-foreground">{formatDate(comment.createdAt)}</Td>
                </ClickableRow>
              );
            })}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function DecisionsTable({ revision }: Readonly<{ revision: RevisionWorkspace }>) {
  return (
    <Card className="overflow-hidden py-0">
      {revision.decisions.length === 0 ? (
        <EmptyState title="No decisions" body="Decisions are currently append-only review records, not votes." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>Object</Th>
              <Th>Decision</Th>
              <Th>Rationale</Th>
              <Th>Author</Th>
              <Th>Created</Th>
            </tr>
          </thead>
          <tbody>
            {revision.decisions.map((decision) => {
              const target = objectPath(revision.id, decision.objectType, decision.objectId);
              return (
                <ClickableRow
                  key={decision.id}
                  to={target}
                  aria-label={`Open ${objectLabel(decision.objectType)} ${decision.objectId}`}
                >
                  <Td className="font-mono">
                    <Link to={target} className="hover:underline">
                      {decision.objectType}:{decision.objectId}
                    </Link>
                  </Td>
                  <Td>
                    <Badge>{decision.decision}</Badge>
                  </Td>
                  <Td className="min-w-[420px] whitespace-normal text-muted-foreground">
                    {decision.rationale || "—"}
                  </Td>
                  <Td>{decision.author}</Td>
                  <Td className="text-muted-foreground">{formatDate(decision.createdAt)}</Td>
                </ClickableRow>
              );
            })}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function objectLabel(objectType: string) {
  if (objectType === "step") return "module";
  return objectType;
}
