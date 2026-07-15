import { Link, useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getRevision, type RevisionWorkspace } from "@/api/client";
import { NetworkDiagram } from "@/components/NetworkDiagram";
import { Badge, Card, ClickableRow, EmptyState, PageHeader, Table, Td, Th } from "@/components/ui";
import { challengePath, evidencePath, modulePath, techniquePath } from "@/lib/workspaceRoutes";

type TabKey =
  | "challenges"
  | "topology"
  | "modules"
  | "techniques"
  | "environment";

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: "challenges", label: "Challenges" },
  { key: "topology", label: "Topology" },
  { key: "modules", label: "Modules" },
  { key: "techniques", label: "Behaviors" },
  { key: "environment", label: "Environment" },
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
        <SummaryCard label="Behaviors" value={revision.summary.techniqueCount} />
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
      {active === "modules" ? <ModulesTable revision={revision} /> : null}
      {active === "techniques" ? <BehaviorsTable revision={revision} /> : null}
      {active === "environment" ? <EnvironmentView revision={revision} /> : null}
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
              <Th className="text-right">Behaviors</Th>
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
                  {challenge.question ? (
                    <p className="mt-2 max-w-xl whitespace-normal text-sm font-normal leading-5 text-muted-foreground">
                      {challenge.question}
                    </p>
                  ) : null}
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
  const infrastructure = topology.infrastructure ?? [];
  const relationships = topology.relationships ?? [];
  const nodes = topology.nodes ?? [];

  return (
    <Card className="p-6">
      <h2 className="mb-5 text-sm font-medium">Network diagram</h2>
      {infrastructure.length === 0 && nodes.length === 0 ? (
          <EmptyState title="No topology" body="This revision does not include network topology data." />
        ) : (
          <NetworkDiagram
            infrastructure={infrastructure}
            relationships={relationships}
            systems={nodes}
          />
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
              <Th className="text-right">Behaviors</Th>
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

function BehaviorsTable({ revision }: Readonly<{ revision: RevisionWorkspace }>) {
  return (
    <Card className="overflow-hidden py-0">
      <Table>
        <thead>
          <tr className="border-b border-border">
            <Th>ID</Th>
            <Th>Name</Th>
            <Th>Module</Th>
            <Th>Behavior refs</Th>
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

function SummaryCard({ label, value }: Readonly<{ label: string; value: string | number }>) {
  return (
    <Card className="p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </Card>
  );
}
