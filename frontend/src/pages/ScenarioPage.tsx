import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getScenario } from "@/api/client";
import { Card, ClickableRow, EmptyState, PageHeader, Table, Td, Th } from "@/components/ui";

export function ScenarioPage() {
  const { slug = "" } = useParams();
  const query = useQuery({
    queryKey: ["scenario", slug],
    queryFn: () => getScenario(slug),
    enabled: Boolean(slug),
  });
  const scenario = query.data?.scenario;
  const revisions = query.data?.revisions ?? [];

  return (
    <>
      <PageHeader
        title={scenario?.name ?? "Scenario"}
        description={scenario?.description || "Imported revisions for this scenario."}
      />
      {query.isLoading ? <p className="text-sm text-muted-foreground">Loading scenario…</p> : null}
      {query.isError ? <p className="text-sm text-destructive">Could not load scenario.</p> : null}
      {revisions.length === 0 && !query.isLoading ? (
        <Card>
          <EmptyState title="No revisions" body="No review bundle has been imported for this scenario." />
        </Card>
      ) : (
        <Card className="overflow-hidden py-0">
          <Table>
            <thead>
              <tr className="border-b border-border">
                <Th>Revision</Th>
                <Th>Framework</Th>
                <Th className="text-right">Modules</Th>
                <Th className="text-right">Techniques</Th>
                <Th className="text-right">Evidence</Th>
                <Th className="text-right">Challenges</Th>
                <Th className="text-right">Comments</Th>
                <Th className="text-right">Decisions</Th>
                <Th>Imported</Th>
              </tr>
            </thead>
            <tbody>
              {revisions.map((revision) => (
                <ClickableRow
                  key={revision.id}
                  to={`/app/revisions/${revision.id}`}
                  aria-label={`Open revision ${revision.label}`}
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
                  <Td className="text-right font-mono tabular-nums">{revision.challengeCount}</Td>
                  <Td className="text-right font-mono tabular-nums">{revision.commentCount}</Td>
                  <Td className="text-right font-mono tabular-nums">{revision.decisionCount}</Td>
                  <Td className="text-muted-foreground">{formatDate(revision.createdAt)}</Td>
                </ClickableRow>
              ))}
            </tbody>
          </Table>
        </Card>
      )}
    </>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}
