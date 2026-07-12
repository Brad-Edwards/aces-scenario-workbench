import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { getRevision, type RevisionWorkspace } from "@/api/client";
import { Badge, Card, ClickableRow, EmptyState, PageHeader, Table, Td, Th } from "@/components/ui";
import {
  evidencePath,
  modulePath,
  revisionPath,
  techniquePath,
  type WorkspaceTab,
} from "@/lib/workspaceRoutes";

type ObjectKind = "module" | "technique" | "evidence";
type ModuleRow = RevisionWorkspace["modules"][number];
type TechniqueRow = RevisionWorkspace["techniques"][number];
type EvidenceRow = RevisionWorkspace["evidence"][number];

export function RevisionObjectPage({ kind }: Readonly<{ kind: ObjectKind }>) {
  const { id = "", objectId = "" } = useParams();
  const decodedObjectId = decodeParam(objectId);
  const query = useQuery({
    queryKey: ["revision", id],
    queryFn: () => getRevision(id),
    enabled: Boolean(id),
  });
  const revision = query.data;

  if (query.isLoading) return <p className="text-sm text-muted-foreground">Loading object…</p>;
  if (query.isError || !revision) return <p className="text-sm text-destructive">Could not load object.</p>;

  if (kind === "module") {
    return <ModuleDetail revision={revision} moduleId={decodedObjectId} />;
  }
  if (kind === "technique") {
    return <TechniqueDetail revision={revision} techniqueId={decodedObjectId} />;
  }
  return <EvidenceDetail revision={revision} evidenceId={decodedObjectId} />;
}

function ModuleDetail({
  revision,
  moduleId,
}: Readonly<{
  revision: RevisionWorkspace;
  moduleId: string;
}>) {
  const module = revision.modules.find((candidate) => candidate.id === moduleId);
  if (!module) return <MissingObject revision={revision} label="module" />;

  const techniques = revision.techniques.filter((technique) => technique.module === module.id);
  const evidenceIds = new Set(techniques.map((technique) => technique.evidence).filter(Boolean));
  const evidence = revision.evidence.filter((item) => evidenceIds.has(item.id));

  return (
    <>
      <ObjectHeader
        revision={revision}
        title={module.name || `Module ${module.id}`}
        description={`Module ${module.id} / ${revision.label}`}
        backTab="modules"
      />

      <Card className="mb-6 p-6">
        <DetailGrid>
          <DetailItem label="Module ID" value={module.id} mono />
          <DetailItem label="Behavior" value={module.behaviorSpecification || "—"} />
          <DetailItem label="Tier">{module.tier ? <Badge>{module.tier}</Badge> : "—"}</DetailItem>
          <DetailItem
            label="Estimated time"
            value={module.minutes == null ? "—" : `${module.minutes} minutes`}
          />
          <DetailItem label="Techniques" value={module.techniqueCount} />
          <DetailItem label="Evidence" value={module.evidenceCount} />
        </DetailGrid>
        <LongText label="Objective" value={module.objective} />
        <LongText label="Expected outcome" value={module.flagOutcome} />
        <LongText label="Justification" value={module.justification} />
      </Card>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
        <div className="space-y-6">
          <RelatedTechniquesTable revision={revision} techniques={techniques} title="Techniques in this module" />
          <RelatedEvidenceTable revision={revision} evidence={evidence} title="Evidence referenced by this module" />
        </div>
        <ActivityPanel revision={revision} objectType="step" objectId={module.id} />
      </div>
    </>
  );
}

function TechniqueDetail({
  revision,
  techniqueId,
}: Readonly<{
  revision: RevisionWorkspace;
  techniqueId: string;
}>) {
  const technique = revision.techniques.find((candidate) => candidate.id === techniqueId);
  if (!technique) return <MissingObject revision={revision} label="technique" />;

  const module = revision.modules.find((candidate) => candidate.id === technique.module);
  const evidence = revision.evidence.find((candidate) => candidate.id === technique.evidence);

  return (
    <>
      <ObjectHeader
        revision={revision}
        title={technique.name}
        description={`${technique.id} / ${revision.label}`}
        backTab="techniques"
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
        <div className="space-y-6">
          <Card className="p-6">
            <DetailGrid>
              <DetailItem label="Technique ID" value={technique.id} mono />
              <DetailItem label="Module">
                {module ? (
                  <Link to={modulePath(revision.id, module.id)} className="hover:underline">
                    {module.name || `Module ${module.id}`}
                  </Link>
                ) : (
                  "—"
                )}
              </DetailItem>
              <DetailItem label="Evidence">
                {evidence ? (
                  <Link to={evidencePath(revision.id, evidence.id)} className="font-mono hover:underline">
                    {evidence.id}
                  </Link>
                ) : (
                  "—"
                )}
              </DetailItem>
              <DetailItem label="Surface" value={technique.surface || "—"} />
              <DetailItem label="Relationship" value={technique.relationship || "—"} />
              <DetailItem label="Coverage" value={technique.coverageStatus || "—"} />
            </DetailGrid>
            <div className="mb-5">
              <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Tactics</h2>
              {technique.tactics.length ? (
                <div className="flex flex-wrap gap-2">
                  {technique.tactics.map((tactic) => (
                    <Badge key={tactic}>{tactic}</Badge>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No tactics linked.</p>
              )}
            </div>
            <LongText label="Planned action" value={technique.plannedAction} />
            <LongText label="Rationale" value={technique.rationale} />
          </Card>

          {module ? <ModuleSummaryCard revision={revision} module={module} /> : null}
          {evidence ? <EvidenceSummaryCard revision={revision} evidence={evidence} /> : null}
        </div>
        <ActivityPanel revision={revision} objectType="technique" objectId={technique.id} />
      </div>
    </>
  );
}

function EvidenceDetail({
  revision,
  evidenceId,
}: Readonly<{
  revision: RevisionWorkspace;
  evidenceId: string;
}>) {
  const evidence = revision.evidence.find((candidate) => candidate.id === evidenceId);
  if (!evidence) return <MissingObject revision={revision} label="evidence item" />;

  const techniques = revision.techniques.filter((technique) => technique.evidence === evidence.id);

  return (
    <>
      <ObjectHeader
        revision={revision}
        title={evidence.id}
        description={`Evidence / ${revision.label}`}
        backTab="evidence"
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
        <div className="space-y-6">
          <Card className="p-6">
            <DetailGrid>
              <DetailItem label="Evidence ID" value={evidence.id} mono />
              <DetailItem label="Linked techniques" value={evidence.techniqueCount} />
              <DetailItem label="Comments" value={evidence.commentCount} />
              <DetailItem label="Decisions" value={evidence.decisionCount} />
            </DetailGrid>
            <LongText label="Description" value={evidence.description} />
          </Card>
          <RelatedTechniquesTable revision={revision} techniques={techniques} title="Techniques using this evidence" />
        </div>
        <ActivityPanel revision={revision} objectType="evidence" objectId={evidence.id} />
      </div>
    </>
  );
}

function ObjectHeader({
  revision,
  title,
  description,
  backTab,
}: Readonly<{
  revision: RevisionWorkspace;
  title: string;
  description: string;
  backTab: WorkspaceTab;
}>) {
  return (
    <PageHeader
      title={title}
      description={description}
      actions={
        <Link to={revisionPath(revision.id, backTab)} className="text-sm text-muted-foreground hover:text-foreground">
          Back to {backTab}
        </Link>
      }
    />
  );
}

function MissingObject({
  revision,
  label,
}: Readonly<{
  revision: RevisionWorkspace;
  label: string;
}>) {
  return (
    <>
      <ObjectHeader
        revision={revision}
        title="Not found"
        description={`Could not find that ${label} in this revision.`}
        backTab="modules"
      />
      <Card>
        <EmptyState title="Object not found" body="It may belong to a different revision or may have been removed." />
      </Card>
    </>
  );
}

function ModuleSummaryCard({
  revision,
  module,
}: Readonly<{
  revision: RevisionWorkspace;
  module: ModuleRow;
}>) {
  return (
    <Card className="p-6">
      <h2 className="mb-2 text-sm font-medium">Module</h2>
      <Link to={modulePath(revision.id, module.id)} className="font-medium hover:underline">
        {module.name || `Module ${module.id}`}
      </Link>
      <p className="mt-2 text-sm text-muted-foreground">{module.objective || "No objective captured."}</p>
    </Card>
  );
}

function EvidenceSummaryCard({
  revision,
  evidence,
}: Readonly<{
  revision: RevisionWorkspace;
  evidence: EvidenceRow;
}>) {
  return (
    <Card className="p-6">
      <h2 className="mb-2 text-sm font-medium">Evidence</h2>
      <Link to={evidencePath(revision.id, evidence.id)} className="font-mono font-medium hover:underline">
        {evidence.id}
      </Link>
      <p className="mt-2 text-sm text-muted-foreground">{evidence.description || "No description captured."}</p>
    </Card>
  );
}

function RelatedTechniquesTable({
  revision,
  techniques,
  title,
}: Readonly<{
  revision: RevisionWorkspace;
  techniques: TechniqueRow[];
  title: string;
}>) {
  return (
    <Card className="overflow-hidden py-0">
      <div className="border-b border-border px-3 py-3 text-sm font-medium">{title}</div>
      {techniques.length === 0 ? (
        <EmptyState title="No techniques" body="No techniques are linked here." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>ID</Th>
              <Th>Name</Th>
              <Th>Module</Th>
              <Th>Evidence</Th>
            </tr>
          </thead>
          <tbody>
            {techniques.map((technique) => (
              <ClickableRow
                key={technique.id}
                to={techniquePath(revision.id, technique.id)}
                aria-label={`Open ${technique.id}`}
              >
                <Td className="font-mono font-medium">{technique.id}</Td>
                <Td className="font-medium">{technique.name}</Td>
                <Td className="font-mono text-muted-foreground">{technique.module || "—"}</Td>
                <Td className="font-mono text-muted-foreground">{technique.evidence || "—"}</Td>
              </ClickableRow>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function RelatedEvidenceTable({
  revision,
  evidence,
  title,
}: Readonly<{
  revision: RevisionWorkspace;
  evidence: EvidenceRow[];
  title: string;
}>) {
  return (
    <Card className="overflow-hidden py-0">
      <div className="border-b border-border px-3 py-3 text-sm font-medium">{title}</div>
      {evidence.length === 0 ? (
        <EmptyState title="No evidence" body="No evidence is linked here." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>ID</Th>
              <Th className="text-right">Techniques</Th>
              <Th className="text-right">Comments</Th>
              <Th className="text-right">Decisions</Th>
            </tr>
          </thead>
          <tbody>
            {evidence.map((item) => (
              <ClickableRow
                key={item.id}
                to={evidencePath(revision.id, item.id)}
                aria-label={`Open evidence ${item.id}`}
              >
                <Td className="font-mono font-medium">{item.id}</Td>
                <Td className="text-right font-mono tabular-nums">{item.techniqueCount}</Td>
                <Td className="text-right font-mono tabular-nums">{item.commentCount}</Td>
                <Td className="text-right font-mono tabular-nums">{item.decisionCount}</Td>
              </ClickableRow>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function ActivityPanel({
  revision,
  objectType,
  objectId,
}: Readonly<{
  revision: RevisionWorkspace;
  objectType: string;
  objectId: string;
}>) {
  const comments = revision.comments.filter(
    (comment) => comment.objectType === objectType && comment.objectId === objectId,
  );
  const decisions = revision.decisions.filter(
    (decision) => decision.objectType === objectType && decision.objectId === objectId,
  );

  return (
    <Card className="p-6">
      <h2 className="text-sm font-medium">Comments and decisions</h2>
      {comments.length === 0 && decisions.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">No activity is attached to this object yet.</p>
      ) : (
        <div className="mt-4 space-y-4">
          {comments.map((comment) => (
            <ActivityItem key={`comment-${comment.id}`} label="Comment" createdAt={comment.createdAt}>
              <p className="whitespace-pre-wrap text-sm text-muted-foreground">{comment.body}</p>
              <p className="mt-2 text-xs text-muted-foreground">
                {comment.author}
                {comment.edited ? " / edited" : ""}
              </p>
            </ActivityItem>
          ))}
          {decisions.map((decision) => (
            <ActivityItem key={`decision-${decision.id}`} label={decision.decision} createdAt={decision.createdAt}>
              <p className="text-sm text-muted-foreground">{decision.rationale || "No rationale captured."}</p>
              <p className="mt-2 text-xs text-muted-foreground">{decision.author}</p>
            </ActivityItem>
          ))}
        </div>
      )}
    </Card>
  );
}

function ActivityItem({
  label,
  createdAt,
  children,
}: Readonly<{
  label: string;
  createdAt: string;
  children: ReactNode;
}>) {
  return (
    <div className="rounded-md border border-border bg-background/40 p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <Badge>{label}</Badge>
        <span className="text-xs text-muted-foreground">{formatDate(createdAt)}</span>
      </div>
      {children}
    </div>
  );
}

function DetailGrid({ children }: Readonly<{ children: ReactNode }>) {
  return <dl className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{children}</dl>;
}

function DetailItem({
  label,
  value,
  mono = false,
  children,
}: Readonly<{
  label: string;
  value?: ReactNode;
  mono?: boolean;
  children?: ReactNode;
}>) {
  const content = children ?? value ?? "—";
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className={`mt-1 text-sm ${mono ? "font-mono" : ""}`}>{content}</dd>
    </div>
  );
}

function LongText({
  label,
  value,
}: Readonly<{
  label: string;
  value?: string;
}>) {
  return (
    <section className="mb-5 last:mb-0">
      <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</h2>
      <p className="whitespace-pre-wrap text-sm leading-6 text-muted-foreground">{value || "—"}</p>
    </section>
  );
}

function decodeParam(value: string) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
