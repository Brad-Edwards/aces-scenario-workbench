import { Graph, layout } from "@dagrejs/dagre";
import {
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import {
  BrainCircuit,
  Database,
  Monitor,
  Network,
  Server,
  Shield,
  type LucideIcon,
} from "lucide-react";
import { useMemo } from "react";

import type {
  TopologyInfrastructure,
  TopologyNode,
  TopologyRelationship,
} from "@/api/client";

type NetworkDiagramProps = Readonly<{
  infrastructure: TopologyInfrastructure[];
  relationships: TopologyRelationship[];
  systems: TopologyNode[];
}>;

type SubnetData = {
  kind: "subnet";
  label: string;
  cidr: string;
};

type HostData = {
  kind: "host";
  label: string;
  system: TopologyNode;
};

type DiagramData = SubnetData | HostData;
type SubnetLayout = {
  id: string;
  label: string;
  cidr: string;
  systems: TopologyNode[];
  width: number;
  height: number;
};

const SUBNET_WIDTH = 240;
const SUBNET_HEADER_HEIGHT = 54;
const HOST_WIDTH = 102;
const HOST_HEIGHT = 50;
const HOST_GAP = 10;
const SUBNET_PADDING = 10;

export function NetworkDiagram({ infrastructure, relationships, systems }: NetworkDiagramProps) {
  const { nodes, edges } = useMemo(
    () => buildDiagram(infrastructure, relationships, systems),
    [infrastructure, relationships, systems],
  );

  return (
    <div className="h-[600px] overflow-hidden rounded-lg border border-border bg-background">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.12, maxZoom: 1.15 }}
        minZoom={0.3}
        maxZoom={1.5}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

function buildDiagram(
  infrastructure: TopologyInfrastructure[],
  relationships: TopologyRelationship[],
  systems: TopologyNode[],
): { nodes: Node<DiagramData>[]; edges: Edge[] } {
  const subnets = infrastructure.filter((item) => item.type === "switch" && item.cidr);
  const subnetIds = new Set(subnets.map((subnet) => subnet.id));
  const hosts = systems.filter((system) => system.type !== "switch");
  const systemsBySubnet = assignSystemsToSubnets(hosts, subnetIds);

  const subnetLayouts: SubnetLayout[] = subnets.map((subnet) => {
    const members = (systemsBySubnet.get(subnet.id) ?? []).sort((left, right) =>
      left.id.localeCompare(right.id),
    );
    return {
      id: subnet.id,
      label: humanize(subnet.id),
      cidr: subnet.cidr,
      systems: members,
      width: SUBNET_WIDTH,
      height: subnetHeight(members.length),
    };
  });

  const unassigned = systemsBySubnet.get("") ?? [];
  if (unassigned.length) {
    subnetLayouts.push({
      id: "unassigned",
      label: "Unassigned",
      cidr: "",
      systems: unassigned.sort((left, right) => left.id.localeCompare(right.id)),
      width: SUBNET_WIDTH,
      height: subnetHeight(unassigned.length),
    });
  }

  const connections = uniqueSubnetConnections(relationships, subnetIds);
  const positions = layoutSubnets(subnetLayouts, connections);
  const nodes: Node<DiagramData>[] = [];

  for (const subnet of subnetLayouts) {
    const subnetNodeId = `subnet:${subnet.id}`;
    nodes.push({
      id: subnetNodeId,
      type: "subnet",
      position: positions.get(subnet.id) ?? { x: 0, y: 0 },
      data: { kind: "subnet", label: subnet.label, cidr: subnet.cidr },
      style: { width: subnet.width, height: subnet.height },
      zIndex: 0,
    });

    for (const [index, system] of subnet.systems.entries()) {
      nodes.push({
        id: `host:${system.id}`,
        type: "host",
        parentId: subnetNodeId,
        extent: "parent",
        position: {
          x: SUBNET_PADDING + (index % 2) * (HOST_WIDTH + HOST_GAP),
          y: SUBNET_HEADER_HEIGHT + Math.floor(index / 2) * (HOST_HEIGHT + HOST_GAP),
        },
        data: { kind: "host", label: humanize(system.id), system },
        style: { width: HOST_WIDTH, height: HOST_HEIGHT },
        zIndex: 2,
      });
    }
  }

  const edges: Edge[] = connections.map(({ source, target }) => ({
    id: `connection:${source}:${target}`,
    source: `subnet:${source}`,
    target: `subnet:${target}`,
    type: "smoothstep",
    style: { stroke: "#64748b", strokeWidth: 1.5 },
    zIndex: 1,
  }));

  return { nodes, edges };
}

function assignSystemsToSubnets(systems: TopologyNode[], subnetIds: Set<string>) {
  const assigned = new Map<string, TopologyNode[]>();
  for (const system of systems) {
    const subnetId = system.networks.find((network) => subnetIds.has(shortRef(network))) ?? "";
    const normalizedSubnetId = shortRef(subnetId);
    assigned.set(normalizedSubnetId, [...(assigned.get(normalizedSubnetId) ?? []), system]);
  }
  return assigned;
}

function uniqueSubnetConnections(
  relationships: TopologyRelationship[],
  subnetIds: Set<string>,
): Array<{ source: string; target: string }> {
  const connections = new Map<string, { source: string; target: string }>();
  for (const relationship of relationships) {
    const source = shortRef(relationship.source);
    const target = shortRef(relationship.target);
    if (source === target || !subnetIds.has(source) || !subnetIds.has(target)) continue;
    const key = [source, target].sort().join("::");
    if (!connections.has(key)) connections.set(key, { source, target });
  }
  return [...connections.values()];
}

function layoutSubnets(
  subnets: SubnetLayout[],
  connections: Array<{ source: string; target: string }>,
) {
  const graph = new Graph().setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "TB", ranksep: 54, nodesep: 36, edgesep: 20, marginx: 16, marginy: 16 });
  for (const subnet of subnets) graph.setNode(subnet.id, { width: subnet.width, height: subnet.height });
  for (const connection of spanningForest(subnets, connections)) {
    graph.setEdge(connection.source, connection.target);
  }
  layout(graph);

  return new Map(
    subnets.map((subnet) => {
      const position = graph.node(subnet.id) as { x: number; y: number };
      return [subnet.id, { x: position.x - subnet.width / 2, y: position.y - subnet.height / 2 }];
    }),
  );
}

function spanningForest(
  subnets: SubnetLayout[],
  connections: Array<{ source: string; target: string }>,
) {
  const adjacency = new Map(subnets.map((subnet) => [subnet.id, new Set<string>()]));
  for (const { source, target } of connections) {
    adjacency.get(source)?.add(target);
    adjacency.get(target)?.add(source);
  }

  const preferredRoot = subnets.find((subnet) => subnet.id.includes("participant"))?.id;
  const roots = [preferredRoot, ...subnets.map((subnet) => subnet.id)].filter(
    (id): id is string => Boolean(id),
  );
  const visited = new Set<string>();
  const tree: Array<{ source: string; target: string }> = [];

  for (const root of roots) {
    if (visited.has(root)) continue;
    visited.add(root);
    const queue = [root];
    while (queue.length) {
      const source = queue.shift()!;
      for (const target of adjacency.get(source) ?? []) {
        if (visited.has(target)) continue;
        visited.add(target);
        queue.push(target);
        tree.push({ source, target });
      }
    }
  }
  return tree;
}

function SubnetNode({ data }: NodeProps) {
  const subnet = data as SubnetData;
  return (
    <div className="h-full w-full rounded-lg border border-dashed border-border bg-card/45">
      <Handle type="target" position={Position.Top} className="!opacity-0" />
      <Handle type="source" position={Position.Bottom} className="!opacity-0" />
      <div className="flex h-[46px] items-center gap-2 border-b border-border px-3">
        <Network size={15} className="shrink-0 text-muted-foreground" />
        <span className="truncate text-xs font-medium text-foreground">{subnet.label}</span>
        {subnet.cidr ? (
          <span className="ml-auto shrink-0 font-mono text-[10px] text-muted-foreground">{subnet.cidr}</span>
        ) : null}
      </div>
    </div>
  );
}

function HostNode({ data }: NodeProps) {
  const host = data as HostData;
  const Icon = systemIcon(host.system);
  return (
    <div className="flex h-full items-center gap-2 rounded-md border border-border bg-card px-2.5 shadow-sm">
      <Icon size={17} className="shrink-0 text-muted-foreground" />
      <span className="line-clamp-2 text-[11px] font-medium leading-4 text-foreground">{host.label}</span>
    </div>
  );
}

function systemIcon(system: TopologyNode): LucideIcon {
  const value = `${system.id} ${system.role} ${system.services.map((service) => service.id).join(" ")}`;
  if (/workstation|desktop|notebook|portal/i.test(value)) return Monitor;
  if (/database|dataset|store|registry|artifact|repo/i.test(value)) return Database;
  if (/model|inference|distillation|ai-/i.test(value)) return BrainCircuit;
  if (/policy|identity|idp|guardrail|proof|telemetry/i.test(value)) return Shield;
  return Server;
}

function subnetHeight(hostCount: number) {
  const rows = Math.max(1, Math.ceil(hostCount / 2));
  return SUBNET_HEADER_HEIGHT + rows * HOST_HEIGHT + (rows - 1) * HOST_GAP + SUBNET_PADDING;
}

function humanize(value: string) {
  return value
    .replace(/^infrastructure\./, "")
    .replace(/-\d+$/, "")
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function shortRef(value: string) {
  return value.replace(/^infrastructure\./, "");
}

const nodeTypes = {
  subnet: SubnetNode,
  host: HostNode,
};
