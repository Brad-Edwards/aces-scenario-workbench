import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getProject } from "@/api/client";
import { Card, EmptyState, PageHeader, Table, Td, Th } from "@/components/ui";

export function ProjectPage() {
  const { slug = "" } = useParams();
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["project", slug], queryFn: () => getProject(slug), enabled: Boolean(slug) });
  const project = query.data?.project;
  const scenarios = query.data?.scenarios ?? [];

  return (
    <>
      <PageHeader
        title={project?.name ?? "Project"}
        description={project?.description || "Scenarios and imported revisions in this project."}
      />
      {query.isLoading ? <p className="text-sm text-muted-foreground">Loading project…</p> : null}
      {query.isError ? <p className="text-sm text-destructive">Could not load project.</p> : null}
      {scenarios.length === 0 && !query.isLoading ? (
        <Card>
          <EmptyState title="No scenarios yet" body="Import or create a scenario revision to begin." />
        </Card>
      ) : (
        <div className="flex flex-col gap-6">
          {scenarios.map((scenario) => (
            <Card key={scenario.slug} className="overflow-hidden py-0">
              <div className="border-b border-border px-4 py-3">
                <h2 className="font-semibold">{scenario.name}</h2>
                {scenario.description ? <p className="mt-1 text-sm text-muted-foreground">{scenario.description}</p> : null}
              </div>
              {scenario.revisions.length === 0 ? (
                <EmptyState title="No revisions" body="No review bundle has been imported for this scenario." />
              ) : (
                <Table>
                  <thead>
                    <tr className="border-b border-border">
                      <Th>Revision</Th>
                      <Th>Framework</Th>
                      <Th className="text-right">Modules</Th>
                      <Th className="text-right">Techniques</Th>
                      <Th className="text-right">Evidence</Th>
                      <Th className="text-right">Comments</Th>
                      <Th className="text-right">Decisions</Th>
                      <Th>Imported</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {scenario.revisions.map((revision) => (
                      <tr
                        key={revision.id}
                        role="link"
                        tabIndex={0}
                        onClick={() => navigate(`/app/revisions/${revision.id}`)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            navigate(`/app/revisions/${revision.id}`);
                          }
                        }}
                        className="cursor-pointer transition-colors hover:bg-muted/50 focus:bg-muted/50 focus:outline-none"
                      >
                        <Td className="font-medium">
                          <Link to={`/app/revisions/${revision.id}`} className="hover:underline">
                            {revision.label}
                          </Link>
                          {revision.packVersion ? (
                            <div className="mt-1 text-sm font-normal text-muted-foreground">
                              Pack {revision.packVersion}
                            </div>
                          ) : null}
                        </Td>
                        <Td className="text-muted-foreground">{revision.framework || "—"}</Td>
                        <Td className="text-right font-mono tabular-nums">{revision.moduleCount}</Td>
                        <Td className="text-right font-mono tabular-nums">{revision.techniqueCount}</Td>
                        <Td className="text-right font-mono tabular-nums">{revision.evidenceCount}</Td>
                        <Td className="text-right font-mono tabular-nums">{revision.commentCount}</Td>
                        <Td className="text-right font-mono tabular-nums">{revision.decisionCount}</Td>
                        <Td className="text-muted-foreground">{formatDate(revision.createdAt)}</Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}
