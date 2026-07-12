import { Link, useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getRevision, type RevisionWorkspace } from "@/api/client";
import { Badge, Card, EmptyState, PageHeader, Table, Td, Th } from "@/components/ui";

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
        description={`${revision.project.name} / ${revision.label}${revision.framework ? ` / ${revision.framework}` : ""}`}
        actions={
          <Link to={`/app/projects/${revision.project.slug}`} className="text-sm text-muted-foreground hover:text-foreground">
            Back to project
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
              <tr key={module.id} className="transition-colors hover:bg-muted/50">
                <Td className="font-medium">{module.name || `Module ${module.id}`}</Td>
                <Td>{module.tier ? <Badge>{module.tier}</Badge> : "—"}</Td>
                <Td className="min-w-[420px] whitespace-normal text-muted-foreground">{module.objective || "—"}</Td>
                <Td className="text-right font-mono tabular-nums">{module.minutes ?? "—"}</Td>
                <Td className="text-right font-mono tabular-nums">{module.techniqueCount}</Td>
                <Td className="text-right font-mono tabular-nums">{module.evidenceCount}</Td>
                <Td className="text-right font-mono tabular-nums">{module.commentCount}</Td>
                <Td className="text-right font-mono tabular-nums">{module.decisionCount}</Td>
              </tr>
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
            <tr key={technique.id} className="transition-colors hover:bg-muted/50">
              <Td className="font-mono font-medium">{technique.id}</Td>
              <Td className="font-medium">{technique.name}</Td>
              <Td>{technique.module || "—"}</Td>
              <Td className="max-w-[280px] whitespace-normal text-muted-foreground">
                {technique.tactics.length ? technique.tactics.join(", ") : "—"}
              </Td>
              <Td className="font-mono text-muted-foreground">{technique.evidence || "—"}</Td>
              <Td className="min-w-[420px] whitespace-normal text-muted-foreground">
                {technique.plannedAction || "—"}
              </Td>
              <Td className="text-right font-mono tabular-nums">{technique.commentCount}</Td>
              <Td className="text-right font-mono tabular-nums">{technique.decisionCount}</Td>
            </tr>
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
            <tr key={item.id} className="transition-colors hover:bg-muted/50">
              <Td className="font-mono font-medium">{item.id}</Td>
              <Td className="min-w-[420px] whitespace-normal text-muted-foreground">{item.description || "—"}</Td>
              <Td className="text-right font-mono tabular-nums">{item.techniqueCount}</Td>
              <Td className="text-right font-mono tabular-nums">{item.commentCount}</Td>
              <Td className="text-right font-mono tabular-nums">{item.decisionCount}</Td>
            </tr>
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
            {revision.comments.map((comment) => (
              <tr key={comment.id} className="transition-colors hover:bg-muted/50">
                <Td className="font-mono">{comment.objectType}:{comment.objectId}</Td>
                <Td className="min-w-[460px] whitespace-pre-wrap text-muted-foreground">
                  {comment.body}
                  {comment.edited ? <span className="ml-2 text-xs">(edited)</span> : null}
                </Td>
                <Td>{comment.author}</Td>
                <Td className="text-muted-foreground">{formatDate(comment.createdAt)}</Td>
              </tr>
            ))}
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
            {revision.decisions.map((decision) => (
              <tr key={decision.id} className="transition-colors hover:bg-muted/50">
                <Td className="font-mono">{decision.objectType}:{decision.objectId}</Td>
                <Td>
                  <Badge>{decision.decision}</Badge>
                </Td>
                <Td className="min-w-[420px] whitespace-normal text-muted-foreground">{decision.rationale || "—"}</Td>
                <Td>{decision.author}</Td>
                <Td className="text-muted-foreground">{formatDate(decision.createdAt)}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
