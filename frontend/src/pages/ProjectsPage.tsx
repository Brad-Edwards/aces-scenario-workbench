import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getProjects } from "@/api/client";
import { Card, EmptyState, PageHeader, Table, Td, Th } from "@/components/ui";

export function ProjectsPage() {
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["projects"], queryFn: getProjects });
  const projects = query.data?.projects ?? [];

  return (
    <>
      <PageHeader
        title="Projects"
        description="The projects your account can access. Open a project to work with its scenarios and revisions."
      />
      <Card className="overflow-hidden py-0">
        {query.isLoading ? (
          <div className="p-6 text-sm text-muted-foreground">Loading projects…</div>
        ) : query.isError ? (
          <div className="p-6 text-sm text-destructive">Could not load projects.</div>
        ) : projects.length === 0 ? (
          <EmptyState title="No projects yet" body="Ask a workspace administrator to add you to a project." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-border">
                <Th>Project</Th>
                <Th>Role</Th>
                <Th className="text-right">Scenarios</Th>
                <Th className="text-right">Revisions</Th>
                <Th>Updated</Th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => (
                <tr
                  key={project.slug}
                  role="link"
                  tabIndex={0}
                  onClick={() => navigate(`/app/projects/${project.slug}`)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      navigate(`/app/projects/${project.slug}`);
                    }
                  }}
                  className="cursor-pointer transition-colors hover:bg-muted/50 focus:bg-muted/50 focus:outline-none"
                >
                  <Td className="font-medium">
                    <Link to={`/app/projects/${project.slug}`} className="hover:underline">
                      {project.name}
                    </Link>
                    {project.description ? (
                      <div className="mt-1 max-w-2xl text-sm font-normal text-muted-foreground">
                        {project.description}
                      </div>
                    ) : null}
                  </Td>
                  <Td className="capitalize text-muted-foreground">{project.role}</Td>
                  <Td className="text-right font-mono tabular-nums">{project.scenarioCount}</Td>
                  <Td className="text-right font-mono tabular-nums">{project.revisionCount}</Td>
                  <Td className="text-muted-foreground">{formatDate(project.updatedAt)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}
