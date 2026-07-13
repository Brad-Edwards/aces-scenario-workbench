import { Link, useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { getRevision, type RevisionWorkspace } from "@/api/client";
import { Badge, Card, ClickableRow, EmptyState, PageHeader, Table, Td, Th } from "@/components/ui";
import { challengePath, evidencePath, modulePath, objectPath, techniquePath } from "@/lib/workspaceRoutes";

type TabKey =
  | "challenges"
  | "topology"
  | "schedule"
  | "modules"
  | "techniques"
  | "evidence"
  | "scoring"
  | "environment"
  | "comments"
  | "decisions";

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: "challenges", label: "Challenges" },
  { key: "topology", label: "Topology" },
  { key: "schedule", label: "Schedule" },
  { key: "modules", label: "Modules" },
  { key: "techniques", label: "Techniques" },
  { key: "evidence", label: "Evidence" },
  { key: "scoring", label: "Scoring" },
  { key: "environment", label: "Environment" },
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

      <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="Explicit module time" value={`${revision.summary.totalMinutes} min`} />
        <SummaryCard
          label="Challenges"
          value={`${revision.summary.implementedChallengeCount} implemented / ${revision.summary.plannedChallengeCount} planned`}
        />
        <SummaryCard label="TTPs" value={revision.summary.techniqueCount} />
        <SummaryCard label="Evidence objects" value={revision.summary.evidenceCount} />
      </div>

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

      {active === "challenges" ? <ChallengesTable revision={revision} /> : null}
      {active === "topology" ? <TopologyView revision={revision} /> : null}
      {active === "schedule" ? <ScheduleTable revision={revision} /> : null}
      {active === "modules" ? <ModulesTable revision={revision} /> : null}
      {active === "techniques" ? <TechniquesTable revision={revision} /> : null}
      {active === "evidence" ? <EvidenceTable revision={revision} /> : null}
      {active === "scoring" ? <ScoringView revision={revision} /> : null}
      {active === "environment" ? <EnvironmentView revision={revision} /> : null}
      {active === "comments" ? <CommentsTable revision={revision} /> : null}
      {active === "decisions" ? <DecisionsTable revision={revision} /> : null}
    </>
  );
}

function tabFromHash(hash: string): TabKey {
  const value = hash.replace("#", "");
  return TABS.some((tab) => tab.key === value) ? (value as TabKey) : "challenges";
}

function ChallengesTable({ revision }: Readonly<{ revision: RevisionWorkspace }>) {
  return (
    <Card className="overflow-hidden py-0">
      {revision.challenges.length === 0 ? (
        <EmptyState
          title="No implemented challenges"
          body="This revision does not include implemented challenge contracts."
        />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>Challenge</Th>
              <Th>Status</Th>
              <Th>Module</Th>
              <Th>Difficulty</Th>
              <Th>Evidence</Th>
              <Th className="text-right">Readiness</Th>
              <Th className="text-right">TTPs</Th>
              <Th className="text-right">Points</Th>
              <Th className="text-right">Comments</Th>
              <Th className="text-right">Decisions</Th>
            </tr>
          </thead>
          <tbody>
            {revision.challenges.map((challenge) => (
              <ClickableRow
                key={challenge.id}
                to={challengePath(revision.id, challenge.id)}
                aria-label={`Open challenge ${challenge.title}`}
              >
                <Td className="font-medium">
                  <Link to={challengePath(revision.id, challenge.id)} className="hover:underline">
                    {challenge.title}
                  </Link>
                  <div className="mt-1 font-mono text-xs font-normal text-muted-foreground">{challenge.flagId}</div>
                </Td>
                <Td>
                  <Badge className={challenge.implemented ? "" : "bg-muted text-muted-foreground"}>
                    {challenge.status}
                  </Badge>
                </Td>
                <Td>
                  {challenge.module ? (
                    <Link to={modulePath(revision.id, challenge.module)} className="font-mono hover:underline">
                      {challenge.module}
                    </Link>
                  ) : (
                    "—"
                  )}
                </Td>
                <Td>{challenge.difficulty ? <Badge>{challenge.difficulty}</Badge> : "—"}</Td>
                <Td className="font-mono text-muted-foreground">
                  {challenge.evidenceRequirements.length
                    ? challenge.evidenceRequirements.map((item) => item.evidenceId).join(", ")
                    : "—"}
                </Td>
                <Td className="text-right font-mono tabular-nums">{readinessScore(challenge.readiness)}</Td>
                <Td className="text-right font-mono tabular-nums">{challenge.techniqueIds.length}</Td>
                <Td className="text-right font-mono tabular-nums">{challenge.points ?? "—"}</Td>
                <Td className="text-right font-mono tabular-nums">{challenge.commentCount}</Td>
                <Td className="text-right font-mono tabular-nums">{challenge.decisionCount}</Td>
              </ClickableRow>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function TopologyView({ revision }: Readonly<{ revision: RevisionWorkspace }>) {
  const topology = revision.topology;
  const nodes = topology.nodes ?? [];
  const entities = topology.entities ?? [];
  const agents = topology.agents ?? [];
  const behaviorSpecs = topology.behavior_specs ?? [];
  const networks = topology.networks ?? [];
  const missingAssets = topology.coverage?.contract_assets_missing_from_sdl ?? [];
  const missingServices = topology.coverage?.contract_services_missing_from_sdl ?? [];

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <SummaryCard label="SDL nodes" value={nodes.length} />
        <SummaryCard label="SDL services" value={nodes.reduce((count, node) => count + node.services.length, 0)} />
        <SummaryCard label="Agents" value={agents.length} />
        <SummaryCard label="Entities" value={entities.length} />
        <SummaryCard label="Behavior specs" value={behaviorSpecs.length} />
      </div>

      <Card className="p-6">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-medium">SDL topology map</h2>
            <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
              SDL is treated as the source of truth for range-visible nodes, actors, and behavior surfaces.
            </p>
          </div>
          <Badge>{topology.source || "sdl"}</Badge>
        </div>
        {nodes.length === 0 && agents.length === 0 && behaviorSpecs.length === 0 ? (
          <EmptyState title="No SDL topology" body="This revision does not include SDL topology data." />
        ) : (
          <div className="grid gap-4 xl:grid-cols-[minmax(160px,0.8fr)_minmax(180px,0.9fr)_minmax(260px,1.25fr)_minmax(280px,1.4fr)]">
            <TopologyColumn title="Entities">
              {entities.length ? (
                entities.map((entity) => (
                  <TopologyCard key={entity.id} title={entity.id} subtitle={entity.role} body={entity.description} />
                ))
              ) : (
                <TopologyEmpty label="No entities" />
              )}
            </TopologyColumn>
            <TopologyColumn title="Agents">
              {agents.length ? (
                agents.map((agent) => <TopologyAgentCard key={agent.id} agent={agent} />)
              ) : (
                <TopologyEmpty label="No agents" />
              )}
            </TopologyColumn>
            <TopologyColumn title="Range nodes">
              {nodes.length ? (
                nodes.map((node) => <TopologyNodeCard key={node.id} node={node} />)
              ) : (
                <TopologyEmpty label="No nodes" />
              )}
            </TopologyColumn>
            <TopologyColumn title="Behavior specs">
              {behaviorSpecs.length ? (
                behaviorSpecs.map((spec) => (
                  <TopologyBehaviorCard key={spec.id} revision={revision} spec={spec} />
                ))
              ) : (
                <TopologyEmpty label="No behavior specs" />
              )}
            </TopologyColumn>
          </div>
        )}
      </Card>

      <TopologyNodesTable nodes={nodes} />
      <div className="grid gap-6 xl:grid-cols-2">
        <TopologyNetworksTable networks={networks} />
        <TopologyGapsTable assets={missingAssets} services={missingServices} />
      </div>
    </div>
  );
}

function TopologyColumn({ title, children }: Readonly<{ title: string; children: ReactNode }>) {
  return (
    <section className="rounded-lg border border-border bg-background/40 p-3">
      <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h3>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function TopologyCard({
  title,
  subtitle,
  body,
}: Readonly<{ title: string; subtitle?: string; body?: string }>) {
  return (
    <div className="rounded-md border border-border bg-card p-3 shadow-sm">
      <div className="font-mono text-sm font-medium">{title}</div>
      {subtitle ? <div className="mt-1 text-xs text-muted-foreground">{subtitle}</div> : null}
      {body ? <p className="mt-2 text-sm leading-5 text-muted-foreground">{body}</p> : null}
    </div>
  );
}

function TopologyAgentCard({
  agent,
}: Readonly<{ agent: NonNullable<RevisionWorkspace["topology"]["agents"]>[number] }>) {
  return (
    <div className="rounded-md border border-border bg-card p-3 shadow-sm">
      <div className="font-mono text-sm font-medium">{agent.id}</div>
      <div className="mt-1 text-xs text-muted-foreground">{agent.entity}</div>
      <p className="mt-2 text-sm leading-5 text-muted-foreground">{agent.description || "—"}</p>
      <KeyValuePills label="Hosts" values={agent.initial_hosts} />
      <KeyValuePills label="Services" values={agent.initial_services} />
    </div>
  );
}

function TopologyNodeCard({
  node,
}: Readonly<{ node: NonNullable<RevisionWorkspace["topology"]["nodes"]>[number] }>) {
  return (
    <div className="rounded-md border border-border bg-card p-3 shadow-sm">
      <div className="font-mono text-sm font-medium">{node.id}</div>
      <div className="mt-1 flex flex-wrap gap-2">
        {node.type ? <Badge>{node.type}</Badge> : null}
        {node.os ? <Badge>{node.os}</Badge> : null}
        {node.implementation_status ? <Badge>{node.implementation_status}</Badge> : null}
      </div>
      <p className="mt-2 text-sm leading-5 text-muted-foreground">{node.description || "—"}</p>
      <KeyValuePills label="Networks" values={node.networks} />
      {node.services.length ? (
        <div className="mt-3 space-y-2">
          {node.services.map((service) => (
            <div key={service.id} className="rounded border border-border bg-background/50 p-2">
              <div className="font-mono text-xs font-medium">{service.id}</div>
              <div className="mt-1 text-xs text-muted-foreground">
                {service.port ? `:${service.port}` : "no port"} {service.software_component ? `/ ${service.software_component}` : ""}
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function TopologyBehaviorCard({
  revision,
  spec,
}: Readonly<{
  revision: RevisionWorkspace;
  spec: NonNullable<RevisionWorkspace["topology"]["behavior_specs"]>[number];
}>) {
  const module = revision.modules.find((candidate) => candidate.behaviorSpecification === spec.id);
  return (
    <div className="rounded-md border border-border bg-card p-3 shadow-sm">
      <div className="font-mono text-sm font-medium">{spec.id}</div>
      <div className="mt-1 flex flex-wrap gap-2">
        {spec.lifecycle_state ? <Badge>{spec.lifecycle_state}</Badge> : null}
        {module ? (
          <Link to={modulePath(revision.id, module.id)}>
            <Badge>Module {module.id}</Badge>
          </Link>
        ) : null}
      </div>
      <KeyValuePills label="Participants" values={spec.participant_refs} />
      <KeyValuePills label="AI behaviors" values={spec.ai_offensive_behavior_refs} />
    </div>
  );
}

function TopologyEmpty({ label }: Readonly<{ label: string }>) {
  return <div className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">{label}</div>;
}

function KeyValuePills({ label, values }: Readonly<{ label: string; values: string[] }>) {
  if (!values.length) return null;
  return (
    <div className="mt-3">
      <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="flex flex-wrap gap-1.5">
        {values.map((value) => (
          <span key={value} className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">
            {value}
          </span>
        ))}
      </div>
    </div>
  );
}

function TopologyNodesTable({
  nodes,
}: Readonly<{ nodes: NonNullable<RevisionWorkspace["topology"]["nodes"]> }>) {
  return (
    <Card className="overflow-hidden py-0">
      <div className="border-b border-border px-3 py-3 text-sm font-medium">SDL nodes</div>
      {nodes.length === 0 ? (
        <EmptyState title="No SDL nodes" body="No SDL node definitions are available." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>Node</Th>
              <Th>Type</Th>
              <Th>OS</Th>
              <Th>Services</Th>
              <Th>Networks</Th>
              <Th>Description</Th>
            </tr>
          </thead>
          <tbody>
            {nodes.map((node) => (
              <tr key={node.id}>
                <Td className="font-mono font-medium">{node.id}</Td>
                <Td>{node.type || "—"}</Td>
                <Td className="text-muted-foreground">
                  {[node.os, node.os_version].filter(Boolean).join(" / ") || "—"}
                </Td>
                <Td className="font-mono text-muted-foreground">
                  {node.services.length
                    ? node.services
                        .map((service) => `${service.id}${service.port ? `:${service.port}` : ""}`)
                        .join(", ")
                    : "—"}
                </Td>
                <Td className="font-mono text-muted-foreground">
                  {node.networks.length ? node.networks.join(", ") : "—"}
                </Td>
                <Td className="min-w-[320px] whitespace-normal text-muted-foreground">{node.description || "—"}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function TopologyNetworksTable({
  networks,
}: Readonly<{ networks: NonNullable<RevisionWorkspace["topology"]["networks"]> }>) {
  return (
    <Card className="overflow-hidden py-0">
      <div className="border-b border-border px-3 py-3 text-sm font-medium">Network enrichment</div>
      {networks.length === 0 ? (
        <EmptyState title="No networks" body="No supporting network contract is available." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>Network</Th>
              <Th>Zone</Th>
              <Th>Scope</Th>
              <Th>Isolation</Th>
            </tr>
          </thead>
          <tbody>
            {networks.map((network) => (
              <tr key={network.name}>
                <Td className="font-mono font-medium">{network.name}</Td>
                <Td className="text-muted-foreground">{network.zone || "—"}</Td>
                <Td className="text-muted-foreground">{network.scope || "—"}</Td>
                <Td className="text-muted-foreground">{network.isolation || "—"}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function TopologyGapsTable({
  assets,
  services,
}: Readonly<{
  assets: NonNullable<RevisionWorkspace["topology"]["coverage"]>["contract_assets_missing_from_sdl"];
  services: NonNullable<RevisionWorkspace["topology"]["coverage"]>["contract_services_missing_from_sdl"];
}>) {
  return (
    <Card className="overflow-hidden py-0">
      <div className="border-b border-border px-3 py-3 text-sm font-medium">Contract objects not represented in SDL</div>
      {assets.length === 0 && services.length === 0 ? (
        <EmptyState title="No topology gaps" body="All supporting contract assets and services are represented in SDL." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>Type</Th>
              <Th>ID</Th>
              <Th>Detail</Th>
            </tr>
          </thead>
          <tbody>
            {assets.map((asset) => (
              <tr key={`asset-${asset.id}`}>
                <Td>Asset</Td>
                <Td className="font-mono font-medium">{asset.id}</Td>
                <Td className="text-muted-foreground">{asset.role || asset.description || "—"}</Td>
              </tr>
            ))}
            {services.map((service) => (
              <tr key={`service-${service.id}`}>
                <Td>Service</Td>
                <Td className="font-mono font-medium">{service.id}</Td>
                <Td className="text-muted-foreground">{service.asset || service.description || "—"}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function ScheduleTable({ revision }: Readonly<{ revision: RevisionWorkspace }>) {
  const challengesByModule = new Map<string, RevisionWorkspace["challenges"]>();
  for (const challenge of revision.challenges) {
    for (const stepId of challenge.canonicalSteps.length ? challenge.canonicalSteps : [challenge.module]) {
      if (!stepId) continue;
      const current = challengesByModule.get(stepId) ?? [];
      current.push(challenge);
      challengesByModule.set(stepId, current);
    }
  }

  return (
    <Card className="overflow-hidden py-0">
      {revision.modules.length === 0 ? (
        <EmptyState title="No schedule" body="No module timing data is available for this revision." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>Module</Th>
              <Th>Surface</Th>
              <Th>Outcome</Th>
              <Th>Challenges</Th>
              <Th className="text-right">Minutes</Th>
              <Th className="text-right">Evidence</Th>
              <Th className="text-right">TTPs</Th>
            </tr>
          </thead>
          <tbody>
            {revision.modules.map((module) => {
              const challenges = challengesByModule.get(module.id) ?? [];
              return (
                <ClickableRow
                  key={module.id}
                  to={modulePath(revision.id, module.id)}
                  aria-label={`Open module ${module.id}`}
                >
                  <Td className="font-medium">
                    <Link to={modulePath(revision.id, module.id)} className="hover:underline">
                      {module.name || `Module ${module.id}`}
                    </Link>
                    <div className="mt-1 font-mono text-xs font-normal text-muted-foreground">Step {module.id}</div>
                  </Td>
                  <Td className="text-muted-foreground">{module.behaviorSpecification || "—"}</Td>
                  <Td className="font-mono text-muted-foreground">{module.flagOutcome || "—"}</Td>
                  <Td>
                    {challenges.length ? (
                      <div className="flex flex-wrap gap-2">
                        {challenges.map((challenge) => (
                          <Link key={challenge.id} to={challengePath(revision.id, challenge.id)}>
                            <Badge className={challenge.implemented ? "" : "bg-muted text-muted-foreground"}>
                              {challenge.status}: {challenge.flagId}
                            </Badge>
                          </Link>
                        ))}
                      </div>
                    ) : (
                      "—"
                    )}
                  </Td>
                  <Td className="text-right font-mono tabular-nums">{module.minutes ?? "—"}</Td>
                  <Td className="text-right font-mono tabular-nums">{module.evidenceCount}</Td>
                  <Td className="text-right font-mono tabular-nums">{module.techniqueCount}</Td>
                </ClickableRow>
              );
            })}
          </tbody>
        </Table>
      )}
    </Card>
  );
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

function ScoringView({ revision }: Readonly<{ revision: RevisionWorkspace }>) {
  const awards = revision.scoring.awards ?? [];
  const alternates = revision.scoring.alternate_awards ?? [];
  const bundles = revision.scoring.bundles ?? [];

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-3">
        <SummaryCard label="Mode" value={revision.scoring.mode || "—"} />
        <SummaryCard label="Max points" value={revision.scoring.max_points ?? "—"} />
        <SummaryCard label="Bundles" value={bundles.length} />
      </div>
      <Card className="overflow-hidden py-0">
        {awards.length === 0 ? (
          <EmptyState title="No scoring awards" body="No structured scoring awards are available for this revision." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-border">
                <Th>Outcome</Th>
                <Th>Evidence</Th>
                <Th>Description</Th>
                <Th className="text-right">Points</Th>
              </tr>
            </thead>
            <tbody>
              {awards.map((award) => (
                <tr key={award.id}>
                  <Td className="font-mono font-medium">{award.id}</Td>
                  <Td className="font-mono text-muted-foreground">
                    {award.evidence.length ? award.evidence.join(", ") : "—"}
                  </Td>
                  <Td className="min-w-[360px] whitespace-normal text-muted-foreground">
                    {award.description || "—"}
                  </Td>
                  <Td className="text-right font-mono tabular-nums">{award.points ?? "—"}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
      <div className="grid gap-6 xl:grid-cols-2">
        <ScoringList title="Alternate awards" rows={alternates} empty="No alternate awards are defined." />
        <Card className="overflow-hidden py-0">
          <div className="border-b border-border px-3 py-3 text-sm font-medium">Bundles</div>
          {bundles.length === 0 ? (
            <EmptyState title="No bundles" body="No scoring bundles are defined." />
          ) : (
            <Table>
              <thead>
                <tr className="border-b border-border">
                  <Th>Bundle</Th>
                  <Th>Outcomes</Th>
                  <Th className="text-right">Points</Th>
                </tr>
              </thead>
              <tbody>
                {bundles.map((bundle) => (
                  <tr key={bundle.id}>
                    <Td className="font-medium">
                      {bundle.title || bundle.id}
                      <div className="mt-1 font-mono text-xs font-normal text-muted-foreground">{bundle.id}</div>
                    </Td>
                    <Td className="whitespace-normal text-muted-foreground">
                      {bundle.outcomes.length ? bundle.outcomes.join(", ") : "—"}
                    </Td>
                    <Td className="text-right font-mono tabular-nums">{bundle.points ?? "—"}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      </div>
    </div>
  );
}

function ScoringList({
  title,
  rows,
  empty,
}: Readonly<{
  title: string;
  rows: Array<{
    id: string;
    points: number | null;
    evidence: string[];
    required_outcomes: string[];
    description: string;
  }>;
  empty: string;
}>) {
  return (
    <Card className="overflow-hidden py-0">
      <div className="border-b border-border px-3 py-3 text-sm font-medium">{title}</div>
      {rows.length === 0 ? (
        <EmptyState title={title} body={empty} />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>ID</Th>
              <Th>Evidence</Th>
              <Th className="text-right">Points</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <Td className="font-mono font-medium">{row.id}</Td>
                <Td className="font-mono text-muted-foreground">
                  {row.evidence.length ? row.evidence.join(", ") : "—"}
                </Td>
                <Td className="text-right font-mono tabular-nums">{row.points ?? "—"}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function EnvironmentView({ revision }: Readonly<{ revision: RevisionWorkspace }>) {
  const assets = revision.environment.assets ?? [];
  const services = revision.environment.services ?? [];
  const applications = revision.environment.applications ?? [];
  const datasets = revision.environment.datasets ?? [];
  const artifacts = revision.environment.artifacts ?? [];
  const plannedAssets = revision.environment.planned_assets ?? [];
  const components = revision.environment.software_components ?? [];
  const validationFlows = revision.environment.validation_flows ?? [];

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <SummaryCard label="Assets" value={assets.length} />
        <SummaryCard label="Services" value={services.length} />
        <SummaryCard label="Applications" value={applications.length} />
        <SummaryCard label="Datasets" value={datasets.length} />
        <SummaryCard label="Artifacts" value={artifacts.length} />
      </div>
      <EnvironmentAssetsTable revision={revision} assets={assets} />
      <EnvironmentServicesTable services={services} />
      <div className="grid gap-6 xl:grid-cols-2">
        <EnvironmentSimpleTable
          title="Applications"
          rows={applications.map((item) => ({
            id: item.id,
            detail: item.app_type || item.software_component,
            description: item.description,
          }))}
          empty="No applications are defined."
        />
        <EnvironmentSimpleTable
          title="Datasets"
          rows={datasets.map((item) => ({
            id: item.id,
            detail: item.kind,
            description: item.description,
          }))}
          empty="No datasets are defined."
        />
        <EnvironmentSimpleTable
          title="Artifacts"
          rows={artifacts.map((item) => ({
            id: item.id,
            detail: item.kind || item.asset,
            description: item.description,
          }))}
          empty="No artifacts are defined."
        />
        <EnvironmentSimpleTable
          title="Planned assets"
          rows={plannedAssets.map((item) => ({
            id: item.id,
            detail: item.implementation_status || item.category,
            description: item.implementation_plan,
          }))}
          empty="No planned asset inventory is defined."
        />
        <EnvironmentSimpleTable
          title="Software components"
          rows={components.map((item) => ({
            id: item.id,
            detail: item.operating_mode || item.authenticity,
            description: item.topology_refs.join(", "),
          }))}
          empty="No software inventory is defined."
        />
        <EnvironmentSimpleTable
          title="Validation flows"
          rows={validationFlows.map((item) => ({
            id: item.id,
            detail: item.command,
            description: item.covers.join(", "),
          }))}
          empty="No validation flows are defined."
        />
      </div>
    </div>
  );
}

function EnvironmentAssetsTable({
  revision,
  assets,
}: Readonly<{
  revision: RevisionWorkspace;
  assets: NonNullable<RevisionWorkspace["environment"]["assets"]>;
}>) {
  return (
    <Card className="overflow-hidden py-0">
      <div className="border-b border-border px-3 py-3 text-sm font-medium">Assets</div>
      {assets.length === 0 ? (
        <EmptyState title="No assets" body="No topology assets are defined." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>Asset</Th>
              <Th>Role</Th>
              <Th>Zone</Th>
              <Th>Software</Th>
              <Th>Status</Th>
              <Th className="text-right">Linked challenges</Th>
            </tr>
          </thead>
          <tbody>
            {assets.map((asset) => {
              const linkedChallengeCount = revision.challenges.filter((challenge) =>
                challenge.evidenceRequirements.some((requirement) => requirement.sourceAsset === asset.id),
              ).length;
              return (
                <tr key={asset.id}>
                  <Td className="font-medium">
                    {asset.hostname || asset.id}
                    <div className="mt-1 font-mono text-xs font-normal text-muted-foreground">{asset.id}</div>
                  </Td>
                  <Td className="text-muted-foreground">{asset.role || asset.asset_type || "—"}</Td>
                  <Td className="text-muted-foreground">{asset.zone || "—"}</Td>
                  <Td className="font-mono text-muted-foreground">{asset.software_component || "—"}</Td>
                  <Td>{asset.implementation_status ? <Badge>{asset.implementation_status}</Badge> : "—"}</Td>
                  <Td className="text-right font-mono tabular-nums">{linkedChallengeCount}</Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function EnvironmentServicesTable({
  services,
}: Readonly<{ services: NonNullable<RevisionWorkspace["environment"]["services"]> }>) {
  return (
    <Card className="overflow-hidden py-0">
      <div className="border-b border-border px-3 py-3 text-sm font-medium">Services</div>
      {services.length === 0 ? (
        <EmptyState title="No services" body="No topology services are defined." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>Service</Th>
              <Th>Asset</Th>
              <Th>Ports</Th>
              <Th>Software</Th>
              <Th>Visibility</Th>
              <Th>Reset owner</Th>
            </tr>
          </thead>
          <tbody>
            {services.map((service) => (
              <tr key={service.id}>
                <Td className="font-mono font-medium">{service.id}</Td>
                <Td className="font-mono text-muted-foreground">{service.asset || "—"}</Td>
                <Td className="font-mono text-muted-foreground">
                  {service.ports.length ? service.ports.join(", ") : "—"}
                </Td>
                <Td className="font-mono text-muted-foreground">{service.software_component || "—"}</Td>
                <Td className="text-muted-foreground">{service.visibility || "—"}</Td>
                <Td className="text-muted-foreground">{service.reset_owner || "—"}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function EnvironmentSimpleTable({
  title,
  rows,
  empty,
}: Readonly<{
  title: string;
  rows: Array<{ id: string; detail: string; description: string }>;
  empty: string;
}>) {
  return (
    <Card className="overflow-hidden py-0">
      <div className="border-b border-border px-3 py-3 text-sm font-medium">{title}</div>
      {rows.length === 0 ? (
        <EmptyState title={title} body={empty} />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>ID</Th>
              <Th>Detail</Th>
              <Th>Description</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <Td className="font-mono font-medium">{row.id}</Td>
                <Td className="text-muted-foreground">{row.detail || "—"}</Td>
                <Td className="min-w-[320px] whitespace-normal text-muted-foreground">
                  {row.description || "—"}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
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

function SummaryCard({ label, value }: Readonly<{ label: string; value: string | number }>) {
  return (
    <Card className="p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </Card>
  );
}

function readinessScore(readiness: Record<string, boolean>) {
  const entries = Object.values(readiness);
  if (entries.length === 0) return "—";
  const ready = entries.filter(Boolean).length;
  return `${ready}/${entries.length}`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function objectLabel(objectType: string) {
  if (objectType === "step") return "module";
  return objectType;
}
