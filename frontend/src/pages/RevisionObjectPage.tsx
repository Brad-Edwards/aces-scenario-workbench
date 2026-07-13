import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import {
  getRevision,
  postObjectComment,
  postObjectDecision,
  type DecisionValue,
  type RevisionWorkspace,
} from "@/api/client";
import { Badge, Button, Card, ClickableRow, EmptyState, PageHeader, Table, Td, Th } from "@/components/ui";
import {
  challengePath,
  evidencePath,
  modulePath,
  revisionPath,
  techniquePath,
  type WorkspaceTab,
} from "@/lib/workspaceRoutes";

type ObjectKind = "challenge" | "module" | "technique" | "evidence";
type ChallengeRow = RevisionWorkspace["challenges"][number];
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

  if (kind === "challenge") {
    return <ChallengeDetail revision={revision} challengeId={decodedObjectId} />;
  }
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
  const challenges = revision.challenges.filter((challenge) => challenge.module === module.id);

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
          <RelatedChallengesTable revision={revision} challenges={challenges} title="Challenges in this module" />
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
  const challenges = revision.challenges.filter((challenge) => challenge.techniqueIds.includes(technique.id));

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
          <RelatedChallengesTable revision={revision} challenges={challenges} title="Related challenges" />
        </div>
        <ActivityPanel
          revision={revision}
          objectType="technique"
          objectId={technique.id}
          allowCommentForm
          showDecisions={false}
        />
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
  const challenges = revision.challenges.filter((challenge) =>
    challenge.evidenceRequirements.some((requirement) => requirement.evidenceId === evidence.id),
  );

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
          <RelatedChallengesTable revision={revision} challenges={challenges} title="Challenges requiring this evidence" />
          <RelatedTechniquesTable revision={revision} techniques={techniques} title="Techniques using this evidence" />
        </div>
        <ActivityPanel revision={revision} objectType="evidence" objectId={evidence.id} />
      </div>
    </>
  );
}

function ChallengeDetail({
  revision,
  challengeId,
}: Readonly<{
  revision: RevisionWorkspace;
  challengeId: string;
}>) {
  const challenge = revision.challenges.find((candidate) => candidate.id === challengeId);
  if (!challenge) return <MissingObject revision={revision} label="challenge" />;

  const module = revision.modules.find((candidate) => candidate.id === challenge.module);
  const techniques = revision.techniques.filter((technique) => challenge.techniqueIds.includes(technique.id));
  const evidence = revision.evidence.filter((item) =>
    challenge.evidenceRequirements.some((requirement) => requirement.evidenceId === item.id),
  );

  return (
    <>
      <ObjectHeader
        revision={revision}
        title={challenge.title}
        description={`${challenge.flagId} / ${revision.label}`}
        backTab="challenges"
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
        <div className="space-y-6">
          <Card className="p-6">
            <DetailGrid>
              <DetailItem label="Flag ID" value={challenge.flagId} mono />
              <DetailItem label="Outcome" value={challenge.outcome} mono />
              <DetailItem label="Status">
                <Badge className={challenge.implemented ? "" : "bg-muted text-muted-foreground"}>
                  {challenge.status}
                </Badge>
              </DetailItem>
              <DetailItem label="Category" value={challenge.category || "—"} />
              <DetailItem label="Difficulty">
                {challenge.difficulty ? <Badge>{challenge.difficulty}</Badge> : "—"}
              </DetailItem>
              <DetailItem label="Points" value={challenge.points ?? "—"} />
              <DetailItem label="Scoring points" value={challenge.scoring.points ?? "—"} />
              <DetailItem label="Runtime">
                {challenge.implemented ? <Badge>Implemented</Badge> : <Badge>Planned</Badge>}
              </DetailItem>
              <DetailItem label="Entrypoint" value={challenge.runtimeEntrypoint || "—"} mono />
              <DetailItem
                label="Canonical steps"
                value={challenge.canonicalSteps.length ? challenge.canonicalSteps.join(", ") : "—"}
                mono
              />
              <DetailItem label="Module">
                {module ? (
                  <Link to={modulePath(revision.id, module.id)} className="hover:underline">
                    {module.name || `Module ${module.id}`}
                  </Link>
                ) : (
                  "—"
                )}
              </DetailItem>
              <DetailItem label="Attack path" value={challenge.sourcePath || "—"} />
            </DetailGrid>
            <LongText label="Question" value={challenge.question} />
            <ReadinessChecklist readiness={challenge.readiness} />
            <LongText label="Delivery" value={formatKeyValueMap(challenge.delivery)} />
            <section className="mb-5 last:mb-0">
              <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Hints</h2>
              {challenge.hints.length ? (
                <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                  {challenge.hints.map((hint) => (
                    <li key={hint}>{hint}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">—</p>
              )}
            </section>
          </Card>

          <EvidenceRequirementsTable revision={revision} challenge={challenge} />
          <RelatedTechniquesTable revision={revision} techniques={techniques} title="Related TTPs" />
          <RelatedEvidenceTable revision={revision} evidence={evidence} title="Required evidence objects" />
        </div>
        <ActivityPanel
          revision={revision}
          objectType="challenge"
          objectId={challenge.id}
          allowCommentForm
          allowDecisionForm
        />
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

function RelatedChallengesTable({
  revision,
  challenges,
  title,
}: Readonly<{
  revision: RevisionWorkspace;
  challenges: ChallengeRow[];
  title: string;
}>) {
  return (
    <Card className="overflow-hidden py-0">
      <div className="border-b border-border px-3 py-3 text-sm font-medium">{title}</div>
      {challenges.length === 0 ? (
        <EmptyState title="No challenges" body="No implemented challenges are linked here." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>Challenge</Th>
              <Th>Outcome</Th>
              <Th className="text-right">Evidence</Th>
              <Th className="text-right">TTPs</Th>
            </tr>
          </thead>
          <tbody>
            {challenges.map((challenge) => (
              <ClickableRow
                key={challenge.id}
                to={challengePath(revision.id, challenge.id)}
                aria-label={`Open challenge ${challenge.title}`}
              >
                <Td className="font-medium">{challenge.title}</Td>
                <Td className="font-mono text-muted-foreground">{challenge.outcome}</Td>
                <Td className="text-right font-mono tabular-nums">{challenge.evidenceRequirements.length}</Td>
                <Td className="text-right font-mono tabular-nums">{challenge.techniqueIds.length}</Td>
              </ClickableRow>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function EvidenceRequirementsTable({
  revision,
  challenge,
}: Readonly<{
  revision: RevisionWorkspace;
  challenge: ChallengeRow;
}>) {
  return (
    <Card className="overflow-hidden py-0">
      <div className="border-b border-border px-3 py-3 text-sm font-medium">Evidence requirements</div>
      {challenge.evidenceRequirements.length === 0 ? (
        <EmptyState title="No evidence requirements" body="No evidence contract is linked to this challenge." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>Evidence</Th>
              <Th>Event</Th>
              <Th>Source</Th>
              <Th>Proof fields</Th>
              <Th className="text-right">Freshness</Th>
            </tr>
          </thead>
          <tbody>
            {challenge.evidenceRequirements.map((requirement) => (
              <ClickableRow
                key={requirement.evidenceId}
                to={evidencePath(revision.id, requirement.evidenceId)}
                aria-label={`Open evidence ${requirement.evidenceId}`}
              >
                <Td className="font-mono font-medium">{requirement.evidenceId}</Td>
                <Td>
                  <div className="font-mono">{requirement.eventKind || "—"}</div>
                  {requirement.predicate ? (
                    <div className="mt-1 max-w-xl whitespace-normal text-sm text-muted-foreground">
                      {requirement.predicate}
                    </div>
                  ) : null}
                </Td>
                <Td className="text-muted-foreground">
                  <div>{requirement.sourceService || "—"}</div>
                  <div className="font-mono text-xs">{requirement.sourceAsset || ""}</div>
                  <div className="mt-1 font-mono text-xs">{requirement.sourcePath || ""}</div>
                </Td>
                <Td className="max-w-[280px] whitespace-normal font-mono text-xs text-muted-foreground">
                  {requirement.proofFields.length ? requirement.proofFields.join(", ") : "—"}
                </Td>
                <Td className="text-right font-mono tabular-nums">
                  {requirement.freshnessSeconds == null ? "—" : `${requirement.freshnessSeconds}s`}
                </Td>
              </ClickableRow>
            ))}
          </tbody>
        </Table>
      )}
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
  allowCommentForm = false,
  allowDecisionForm = false,
  showDecisions = true,
}: Readonly<{
  revision: RevisionWorkspace;
  objectType: string;
  objectId: string;
  allowCommentForm?: boolean;
  allowDecisionForm?: boolean;
  showDecisions?: boolean;
}>) {
  const queryClient = useQueryClient();
  const [commentBody, setCommentBody] = useState("");
  const [decisionValue, setDecisionValue] = useState<DecisionValue>("accept");
  const [decisionRationale, setDecisionRationale] = useState("");
  const comments = revision.comments.filter(
    (comment) => comment.objectType === objectType && comment.objectId === objectId,
  );
  const decisions = showDecisions
    ? revision.decisions.filter(
        (decision) => decision.objectType === objectType && decision.objectId === objectId,
      )
    : [];
  const title = showDecisions ? "Comments and decisions" : "Comments";

  const commentMutation = useMutation({
    mutationFn: () => postObjectComment(revision.id, objectType, objectId, commentBody),
    onSuccess: async () => {
      setCommentBody("");
      await queryClient.invalidateQueries({ queryKey: ["revision", String(revision.id)] });
    },
  });

  const decisionMutation = useMutation({
    mutationFn: () =>
      postObjectDecision(revision.id, objectType, objectId, decisionValue, decisionRationale),
    onSuccess: async () => {
      setDecisionValue("accept");
      setDecisionRationale("");
      await queryClient.invalidateQueries({ queryKey: ["revision", String(revision.id)] });
    },
  });

  function submitComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!commentBody.trim() || commentMutation.isPending) return;
    commentMutation.mutate();
  }

  function submitDecision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (decisionMutation.isPending) return;
    decisionMutation.mutate();
  }

  return (
    <Card className="space-y-5 p-6">
      <h2 className="text-sm font-medium">{title}</h2>
      {allowCommentForm ? (
        <form onSubmit={submitComment} className="space-y-3">
          <label className="block text-xs font-medium uppercase tracking-wide text-muted-foreground" htmlFor="comment">
            Add comment
          </label>
          <textarea
            id="comment"
            value={commentBody}
            onChange={(event) => setCommentBody(event.target.value)}
            rows={4}
            placeholder="Add a note for this item…"
            className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
          />
          {commentMutation.isError ? (
            <p className="text-sm text-destructive">{commentMutation.error.message}</p>
          ) : null}
          <Button type="submit" disabled={!commentBody.trim() || commentMutation.isPending}>
            {commentMutation.isPending ? "Saving…" : "Add comment"}
          </Button>
        </form>
      ) : null}
      {allowDecisionForm ? (
        <form onSubmit={submitDecision} className="space-y-3 border-t border-border pt-5">
          <div>
            <label
              className="mb-2 block text-xs font-medium uppercase tracking-wide text-muted-foreground"
              htmlFor="decision"
            >
              Vote / decision
            </label>
            <select
              id="decision"
              value={decisionValue}
              onChange={(event) => setDecisionValue(event.target.value as DecisionValue)}
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/30"
            >
              <option value="accept">Accept</option>
              <option value="needs-change">Needs change</option>
              <option value="resolve">Resolve</option>
              <option value="reopen">Reopen</option>
            </select>
          </div>
          <div>
            <label
              className="mb-2 block text-xs font-medium uppercase tracking-wide text-muted-foreground"
              htmlFor="decision-rationale"
            >
              Rationale
            </label>
            <textarea
              id="decision-rationale"
              value={decisionRationale}
              onChange={(event) => setDecisionRationale(event.target.value)}
              rows={3}
              placeholder="Optional context for the decision…"
              className="min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
            />
          </div>
          {decisionMutation.isError ? (
            <p className="text-sm text-destructive">{decisionMutation.error.message}</p>
          ) : null}
          <Button type="submit" disabled={decisionMutation.isPending}>
            {decisionMutation.isPending ? "Recording…" : "Record decision"}
          </Button>
        </form>
      ) : null}
      {comments.length === 0 && decisions.length === 0 ? (
        <p className="text-sm text-muted-foreground">No activity is attached to this object yet.</p>
      ) : (
        <div className="space-y-4 border-t border-border pt-5">
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

function ReadinessChecklist({ readiness }: Readonly<{ readiness: Record<string, boolean> }>) {
  const entries = Object.entries(readiness);
  if (entries.length === 0) return null;
  return (
    <section className="mb-5 last:mb-0">
      <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Readiness</h2>
      <div className="flex flex-wrap gap-2">
        {entries.map(([key, ready]) => (
          <Badge key={key} className={ready ? "" : "bg-muted text-muted-foreground"}>
            {readinessLabel(key)}: {ready ? "yes" : "no"}
          </Badge>
        ))}
      </div>
    </section>
  );
}

function readinessLabel(value: string) {
  return value.replaceAll("_", " ");
}

function formatKeyValueMap(value: Record<string, string>) {
  const entries = Object.entries(value).filter(([, entry]) => entry);
  if (entries.length === 0) return "";
  return entries.map(([key, entry]) => `${readinessLabel(key)}: ${entry}`).join("\n");
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
