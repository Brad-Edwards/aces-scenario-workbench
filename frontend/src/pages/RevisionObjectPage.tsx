import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppWindow, Server } from "lucide-react";
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
  const hasActivity = hasObjectActivity(revision, "step", module.id);

  return (
    <>
      <ObjectHeader
        revision={revision}
        title={module.name || `Module ${module.id}`}
        description={`Module ${module.id}`}
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
        </DetailGrid>
        <LongText label="Objective" value={module.objective} />
        <LongText label="Expected outcome" value={module.flagOutcome} />
        <LongText label="Justification" value={module.justification} />
      </Card>

      <div className={hasActivity ? "grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]" : ""}>
        <div className="space-y-6">
          <RelatedChallengesTable revision={revision} challenges={challenges} title="Challenges in this module" />
          <RelatedTechniquesTable
            revision={revision}
            techniques={techniques}
            title="Behaviors in this module"
            showModule={false}
          />
          <RelatedEvidenceTable revision={revision} evidence={evidence} title="Evidence referenced by this module" />
        </div>
        {hasActivity ? <ActivityPanel revision={revision} objectType="step" objectId={module.id} /> : null}
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
  if (!technique) return <MissingObject revision={revision} label="behavior" />;

  const module = revision.modules.find((candidate) => candidate.id === technique.module);
  const evidence = revision.evidence.find((candidate) => candidate.id === technique.evidence);
  const challenges = revision.challenges.filter((challenge) => challenge.techniqueIds.includes(technique.id));

  return (
    <>
      <ObjectHeader
        revision={revision}
        title={technique.name}
        description={technique.id}
        backTab="techniques"
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
        <div className="space-y-6">
          <Card className="p-6">
            <DetailGrid>
              <DetailItem label="Behavior ID" value={technique.id} mono />
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
              <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Behavior refs</h2>
              {technique.tactics.length ? (
                <div className="flex flex-wrap gap-2">
                  {technique.tactics.map((tactic) => (
                    <Badge key={tactic}>{tactic}</Badge>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No behavior refs linked.</p>
              )}
            </div>
            <LongText label="Planned action" value={technique.plannedAction} />
            <LongText label="Rationale" value={technique.rationale} />
          </Card>

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
  const hasActivity = hasObjectActivity(revision, "evidence", evidence.id);

  return (
    <>
      <ObjectHeader
        revision={revision}
        title={evidence.id}
        description="Evidence object"
        backTab="evidence"
      />

      <div className={hasActivity ? "grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]" : ""}>
        <div className="space-y-6">
          <Card className="p-6">
            <DetailGrid>
              <DetailItem label="Evidence ID" value={evidence.id} mono />
              <DetailItem label="Linked behaviors" value={evidence.techniqueCount} />
            </DetailGrid>
            <LongText label="Description" value={evidence.description} />
          </Card>
          <RelatedChallengesTable revision={revision} challenges={challenges} title="Challenges requiring this evidence" />
          <RelatedTechniquesTable revision={revision} techniques={techniques} title="Behaviors using this evidence" />
        </div>
        {hasActivity ? <ActivityPanel revision={revision} objectType="evidence" objectId={evidence.id} /> : null}
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

  return (
    <>
      <ObjectHeader
        revision={revision}
        title={challenge.title}
        description={challenge.question || challenge.flagId}
        backTab="challenges"
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="mb-5 text-sm font-medium">Challenge overview</h2>
            <DetailGrid>
              <DetailItem label="Flag ID" value={challenge.flagId} mono />
              <DetailItem label="Outcome" value={challenge.outcome} mono />
              <DetailItem label="Module">
                {module ? (
                  <Link to={modulePath(revision.id, module.id)} className="hover:underline">
                    {module.name || `Module ${module.id}`}
                  </Link>
                ) : (
                  "—"
                )}
              </DetailItem>
              <DetailItem label="Status">
                <Badge className={challenge.implemented ? "" : "bg-muted text-muted-foreground"}>
                  {challenge.status}
                </Badge>
              </DetailItem>
              <DetailItem label="Difficulty">
                {challenge.difficulty ? <Badge>{challenge.difficulty}</Badge> : "—"}
              </DetailItem>
              <DetailItem label="Points" value={challenge.points ?? "—"} />
              {challenge.runtimeEntrypoint ? (
                <DetailItem label="Entrypoint" value={challenge.runtimeEntrypoint} mono />
              ) : null}
            </DetailGrid>
            <LongText label="Participant objective" value={challenge.question} />
            <LongText label="Delivery" value={formatKeyValueMap(challenge.delivery)} />
            <section className="mb-5 last:mb-0">
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Participant hints</h3>
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

          <OrganizerChallengeCard challenge={challenge} />
          <RelatedSystemsCard challenge={challenge} />
          <EvidenceRequirementsTable revision={revision} challenge={challenge} />
          <RelatedTechniquesTable
            revision={revision}
            techniques={techniques}
            title="Related behaviors"
            showModule={false}
          />
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

function OrganizerChallengeCard({ challenge }: Readonly<{ challenge: ChallengeRow }>) {
  const organizer = challenge.organizer;
  const targetWindow = formatMinuteWindow(
    organizer.min_minutes,
    organizer.target_minutes,
    organizer.max_minutes,
  );
  return (
    <Card className="p-6">
      <h2 className="mb-5 text-sm font-medium">Organizer review</h2>
      <DetailGrid>
        <DetailItem label="Challenge ID" value={organizer.challenge_id || challenge.id} mono />
        <DetailItem label="Lifecycle" value={organizer.lifecycle_state || "—"} />
        <DetailItem label="Implementation" value={organizer.implementation_status || challenge.status} />
        <DetailItem label="Time window" value={targetWindow || "—"} />
        <DetailItem label="Reliability" value={organizer.reliability || "—"} />
        <DetailItem label="Telemetry" value={organizer.telemetry_profile || "—"} mono />
        <DetailItem label="Disposition" value={organizer.disposition || "—"} />
        <DetailItem label="Specification" value={organizer.semantic_version || "—"} mono />
        <DetailItem label="Implementation issue" value={organizer.issue ? `#${organizer.issue}` : "—"} />
      </DetailGrid>
      <LongText label="Proof obligation" value={organizer.proof_obligation} />
      <ReviewList label="Prerequisites" values={organizer.prerequisites ?? []} mono />
      <ReviewList label="Behavior categories" values={organizer.behavior_refs ?? []} />
      <ReviewList label="Authority scope" values={organizer.authority_scope_refs ?? []} mono />
      <ReviewList
        label="Hint costs"
        values={(organizer.hint_costs ?? []).map((cost) => `${cost} points`)}
      />
    </Card>
  );
}

function RelatedSystemsCard({ challenge }: Readonly<{ challenge: ChallengeRow }>) {
  return (
    <Card className="p-6">
      <h2 className="text-sm font-medium">Related systems and applications</h2>
      <p className="mt-1 text-sm text-muted-foreground">Systems directly referenced by the challenge scope.</p>
      {challenge.relatedSystems.length ? (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {challenge.relatedSystems.map((system) => (
            <div key={`${system.id}:${system.service}`} className="rounded-lg border border-border bg-background/40 p-4">
              <div className="flex items-start gap-3">
                <span className="rounded-md bg-muted p-2 text-muted-foreground"><Server size={17} /></span>
                <div className="min-w-0">
                  <div className="font-mono text-sm font-medium">{system.id}</div>
                  <p className="mt-1 text-sm leading-5 text-muted-foreground">{system.description || "—"}</p>
                </div>
              </div>
              {system.service ? (
                <div className="mt-3 flex items-start gap-2 rounded-md border border-border bg-card p-2.5">
                  <AppWindow className="mt-0.5 shrink-0 text-muted-foreground" size={15} />
                  <div className="min-w-0">
                    <div className="font-mono text-xs font-medium">
                      {system.service}{system.service_port ? `:${system.service_port}` : ""}
                    </div>
                    {system.service_description ? (
                      <p className="mt-1 text-xs leading-4 text-muted-foreground">{system.service_description}</p>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground">No system references are attached.</p>
      )}
    </Card>
  );
}

function ReviewList({
  label,
  values,
  mono = false,
}: Readonly<{ label: string; values: string[]; mono?: boolean }>) {
  if (!values.length) return null;
  return (
    <section className="mb-5 last:mb-0">
      <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</h3>
      <div className="flex flex-wrap gap-2">
        {values.map((value) => (
          <span key={value} className={`rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground ${mono ? "font-mono" : ""}`}>
            {value}
          </span>
        ))}
      </div>
    </section>
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
          Back to {workspaceTabLabel(backTab)}
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
              <Th className="text-right">Behaviors</Th>
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
  showModule = true,
}: Readonly<{
  revision: RevisionWorkspace;
  techniques: TechniqueRow[];
  title: string;
  showModule?: boolean;
}>) {
  return (
    <Card className="overflow-hidden py-0">
      <div className="border-b border-border px-3 py-3 text-sm font-medium">{title}</div>
      {techniques.length === 0 ? (
        <EmptyState title="No behaviors" body="No behaviors are linked here." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>ID</Th>
              <Th>Name</Th>
              {showModule ? <Th>Module</Th> : null}
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
                {showModule ? (
                  <Td className="font-mono text-muted-foreground">{technique.module || "—"}</Td>
                ) : null}
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
              <Th>Description</Th>
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
                <Td className="min-w-[320px] whitespace-normal text-muted-foreground">
                  {item.description || "—"}
                </Td>
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

function workspaceTabLabel(value: WorkspaceTab) {
  return value === "techniques" ? "behaviors" : value;
}

function formatKeyValueMap(value: Record<string, unknown>) {
  const entries = Object.entries(value).filter(([, entry]) => entry);
  if (entries.length === 0) return "";
  return entries.map(([key, entry]) => `${humanizeKey(key)}: ${formatValue(entry)}`).join("\n");
}

function hasObjectActivity(revision: RevisionWorkspace, objectType: string, objectId: string) {
  return (
    revision.comments.some(
      (comment) => comment.objectType === objectType && comment.objectId === objectId,
    ) ||
    revision.decisions.some(
      (decision) => decision.objectType === objectType && decision.objectId === objectId,
    )
  );
}

function humanizeKey(value: string) {
  return value.replaceAll("_", " ");
}

function formatValue(value: unknown) {
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "boolean") return value ? "yes" : "no";
  return String(value);
}

function formatMinuteWindow(
  minimum?: number | null,
  target?: number | null,
  maximum?: number | null,
) {
  if (minimum == null && target == null && maximum == null) return "";
  const range = minimum != null && maximum != null ? `${minimum}–${maximum} min` : "";
  return target != null ? `${target} min target${range ? ` (${range})` : ""}` : range;
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
