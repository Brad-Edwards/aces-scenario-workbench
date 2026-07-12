import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getScenarios } from "@/api/client";
import { Card, EmptyState, PageHeader, Table, Td, Th } from "@/components/ui";

export function ScenariosPage() {
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["scenarios"], queryFn: getScenarios });
  const scenarios = query.data?.scenarios ?? [];

  return (
    <>
      <PageHeader
        title="Scenarios"
        description="The scenarios your account can access. Open one to work with its revisions."
      />
      <Card className="overflow-hidden py-0">
        {query.isLoading ? (
          <div className="p-6 text-sm text-muted-foreground">Loading scenarios…</div>
        ) : query.isError ? (
          <div className="p-6 text-sm text-destructive">Could not load scenarios.</div>
        ) : scenarios.length === 0 ? (
          <EmptyState title="No scenarios yet" body="Ask a workspace administrator to add you to a scenario." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-border">
                <Th>Scenario</Th>
                <Th>Role</Th>
                <Th className="text-right">Revisions</Th>
                <Th>Updated</Th>
              </tr>
            </thead>
            <tbody>
              {scenarios.map((scenario) => (
                <tr
                  key={scenario.slug}
                  role="link"
                  tabIndex={0}
                  onClick={() => navigate(`/app/scenarios/${scenario.slug}`)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      navigate(`/app/scenarios/${scenario.slug}`);
                    }
                  }}
                  className="cursor-pointer transition-colors hover:bg-muted/50 focus:bg-muted/50 focus:outline-none"
                >
                  <Td className="font-medium">
                    <Link to={`/app/scenarios/${scenario.slug}`} className="hover:underline">
                      {scenario.name}
                    </Link>
                    {scenario.description ? (
                      <div className="mt-1 max-w-2xl text-sm font-normal text-muted-foreground">
                        {scenario.description}
                      </div>
                    ) : null}
                  </Td>
                  <Td className="capitalize text-muted-foreground">{scenario.role}</Td>
                  <Td className="text-right font-mono tabular-nums">{scenario.revisionCount}</Td>
                  <Td className="text-muted-foreground">{formatDate(scenario.updatedAt)}</Td>
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
