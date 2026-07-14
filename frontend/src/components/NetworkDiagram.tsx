import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
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
  UserRound,
  type LucideIcon,
} from "lucide-react";
import { useMemo } from "react";

import type {
  TopologyAgent,
  TopologyInfrastructure,
  TopologyNode,
  TopologyRelationship,
} from "@/api/client";
import { Badge } from "@/components/ui";

type NetworkDiagramProps = Readonly<{
  infrastructure: TopologyInfrastructure[];
  relationships: TopologyRelationship[];
  systems: TopologyNode[];
  agents: TopologyAgent[];
}>;

type SegmentData = {
  kind: "segment";
  label: string;
  cidr: string;
  gateway: string;
  description: string;
  hostCount: number;
};

type SystemData = {
  kind: "system";
  label: string;
  description: string;
  type: string;
  os: string;
  services: TopologyNode["services"];
};

type ActorData = {
  kind: "actor";
  label: string;
  description: string;
};

type DiagramData = SegmentData | SystemData | ActorData;

const SEGMENT_WIDTH = 456;
const SYSTEM_WIDTH = 204;
const SYSTEM_HEIGHT = 82;
const SEGMENT_HEADER_HEIGHT = 88;
const SYSTEM_GAP = 12;
const GRID_COLUMNS = 3;
const COLUMN_GAP = 64;
const ROW_GAP = 54;

export function NetworkDiagram({ infrastructure, relationships, systems, agents }: NetworkDiagramProps) {
  const { nodes, edges } = useMemo(
    () => buildDiagram(infrastructure, relationships, systems, agents),
    [agents, infrastructure, relationships, systems],
  );

  return (
    <div className="h-[760px] overflow-hidden rounded-lg border border-border bg-background">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.12, maxZoom: 1 }}
        minZoom={0.35}
        maxZoom={1.75}
        nodesDraggable={false}
        nodesConnectable={false}
        elevateEdgesOnSelect
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="var(--border)" />
        <MiniMap
          pannable
          zoomable
          nodeColor={(node) => (node.type === "segment" ? "#2f6f70" : node.type === "actor" ? "#b78342" : "#64748b")}
          maskColor="rgba(9, 12, 16, 0.72)"
        />
        <Controls showInteractive={false} />
        <div className="absolute left-3 top-3 z-10 flex flex-wrap gap-3 rounded-md border border-border bg-card/95 px-3 py-2 text-xs text-muted-foreground shadow-sm backdrop-blur">
          <Legend icon={Network} label="Subnet" />
          <Legend icon={Server} label="System" />
          <Legend icon={UserRound} label="Actor" />
          <span>Arrows show allowed network relationships</span>
        </div>
      </ReactFlow>
    </div>
  );
}

function buildDiagram(
  infrastructure: TopologyInfrastructure[],
  relationships: TopologyRelationship[],
  systems: TopologyNode[],
  agents: TopologyAgent[],
): { nodes: Node<DiagramData>[]; edges: Edge[] } {
  const segments = infrastructure.filter((item) => item.cidr || item.type === "switch");
  const segmentIds = new Set(segments.map((segment) => segment.id));
  const systemsBySegment = new Map<string, TopologyNode[]>();
  const unassigned: TopologyNode[] = [];

  for (const system of systems.filter((node) => node.type !== "switch")) {
    const segmentId = system.networks.find((network) => segmentIds.has(network));
    if (segmentId) {
      const members = systemsBySegment.get(segmentId) ?? [];
      members.push(system);
      systemsBySegment.set(segmentId, members);
    } else {
      unassigned.push(system);
    }
  }

  const positions = layoutSegments(segments, relationships, systemsBySegment);
  const nodes: Node<DiagramData>[] = [];

  for (const segment of segments) {
    const members = (systemsBySegment.get(segment.id) ?? []).sort((a, b) => a.id.localeCompare(b.id));
    const height = segmentHeight(members.length);
    nodes.push({
      id: segment.id,
      type: "segment",
      position: positions.get(segment.id) ?? { x: 0, y: 0 },
      data: {
        kind: "segment",
        label: segment.id,
        cidr: segment.cidr,
        gateway: segment.gateway,
        description: segment.description,
        hostCount: members.length,
      },
      style: { width: SEGMENT_WIDTH, height },
      zIndex: 0,
    });
    for (const [index, system] of members.entries()) {
      nodes.push({
        id: `system:${system.id}`,
        type: "system",
        parentId: segment.id,
        extent: "parent",
        position: {
          x: 18 + (index % 2) * (SYSTEM_WIDTH + SYSTEM_GAP),
          y: SEGMENT_HEADER_HEIGHT + Math.floor(index / 2) * (SYSTEM_HEIGHT + SYSTEM_GAP),
        },
        data: systemData(system),
        style: { width: SYSTEM_WIDTH, height: SYSTEM_HEIGHT },
        zIndex: 2,
      });
    }
  }

  const maxX = Math.max(0, ...Array.from(positions.values(), (position) => position.x));
  for (const [index, system] of unassigned.sort((a, b) => a.id.localeCompare(b.id)).entries()) {
    nodes.push({
      id: `system:${system.id}`,
      type: "system",
      position: { x: maxX + SEGMENT_WIDTH + COLUMN_GAP, y: 128 + index * (SYSTEM_HEIGHT + SYSTEM_GAP) },
      data: systemData(system),
      style: { width: SYSTEM_WIDTH, height: SYSTEM_HEIGHT },
    });
  }

  const rootSegment = segments.find((segment) => segment.id.includes("participant"))?.id ?? segments[0]?.id;
  const rootPosition = rootSegment ? positions.get(rootSegment) : undefined;
  for (const [index, agent] of agents.entries()) {
    nodes.push({
      id: `actor:${agent.id}`,
      type: "actor",
      position: {
        x: (rootPosition?.x ?? 0) + 24 + index * 232,
        y: Math.max(0, (rootPosition?.y ?? 128) - 116),
      },
      data: { kind: "actor", label: agent.id, description: agent.description },
      style: { width: 220 },
      zIndex: 3,
    });
  }

  const edges = relationshipEdges(relationships, segmentIds);
  for (const agent of agents) {
    for (const host of agent.initial_hosts) {
      if (systems.some((system) => system.id === host)) {
        edges.push({
          id: `actor:${agent.id}:${host}`,
          source: `actor:${agent.id}`,
          target: `system:${host}`,
          type: "smoothstep",
          markerEnd: { type: MarkerType.ArrowClosed, color: "#b78342" },
          style: { stroke: "#b78342", strokeWidth: 1.7, strokeDasharray: "5 4" },
          label: "starts at",
          labelStyle: { fill: "#b78342", fontSize: 11 },
          zIndex: 4,
        });
      }
    }
  }
  return { nodes, edges };
}

function layoutSegments(
  segments: TopologyInfrastructure[],
  relationships: TopologyRelationship[],
  systemsBySegment: Map<string, TopologyNode[]>,
) {
  const ids = new Set(segments.map((segment) => segment.id));
  const adjacency = new Map<string, Set<string>>();
  for (const id of ids) adjacency.set(id, new Set());
  for (const relationship of relationships) {
    const source = shortRef(relationship.source);
    const target = shortRef(relationship.target);
    if (source !== target && ids.has(source) && ids.has(target)) {
      adjacency.get(source)?.add(target);
      adjacency.get(target)?.add(source);
    }
  }

  const root = segments.find((segment) => segment.id.includes("participant"))?.id ?? segments[0]?.id;
  const depth = new Map<string, number>();
  if (root) {
    depth.set(root, 0);
    const queue = [root];
    while (queue.length) {
      const current = queue.shift()!;
      for (const neighbor of adjacency.get(current) ?? []) {
        if (!depth.has(neighbor)) {
          depth.set(neighbor, (depth.get(current) ?? 0) + 1);
          queue.push(neighbor);
        }
      }
    }
  }
  const disconnectedDepth = Math.max(0, ...depth.values()) + 1;
  for (const id of ids) if (!depth.has(id)) depth.set(id, disconnectedDepth);

  const orderedIds = [...segments]
    .sort((left, right) => {
      const depthDelta = (depth.get(left.id) ?? disconnectedDepth) - (depth.get(right.id) ?? disconnectedDepth);
      if (depthDelta) return depthDelta;
      const degreeDelta = (adjacency.get(right.id)?.size ?? 0) - (adjacency.get(left.id)?.size ?? 0);
      return degreeDelta || left.id.localeCompare(right.id);
    })
    .map((segment) => segment.id);

  const positions = new Map<string, { x: number; y: number }>();
  const rowHeights: number[] = [];
  for (let index = 0; index < orderedIds.length; index += GRID_COLUMNS) {
    rowHeights.push(
      Math.max(
        ...orderedIds
          .slice(index, index + GRID_COLUMNS)
          .map((id) => segmentHeight(systemsBySegment.get(id)?.length ?? 0)),
      ),
    );
  }
  let rowY = 128;
  for (const [index, id] of orderedIds.entries()) {
    const row = Math.floor(index / GRID_COLUMNS);
    const column = index % GRID_COLUMNS;
    if (column === 0 && row > 0) rowY += rowHeights[row - 1] + ROW_GAP;
    positions.set(id, { x: column * (SEGMENT_WIDTH + COLUMN_GAP), y: rowY });
  }
  return positions;
}

function relationshipEdges(relationships: TopologyRelationship[], segmentIds: Set<string>): Edge[] {
  const grouped = new Map<string, TopologyRelationship[]>();
  for (const relationship of relationships) {
    const source = shortRef(relationship.source);
    const target = shortRef(relationship.target);
    if (source === target || !segmentIds.has(source) || !segmentIds.has(target)) continue;
    const key = [source, target].sort().join("::");
    grouped.set(key, [...(grouped.get(key) ?? []), relationship]);
  }

  return [...grouped.entries()].map(([key, rows]) => {
    const [groupSource, groupTarget] = key.split("::");
    const directions = new Set(rows.map((row) => `${shortRef(row.source)}>${shortRef(row.target)}`));
    const bidirectional = directions.size > 1;
    const source = bidirectional ? groupSource : shortRef(rows[0].source);
    const target = bidirectional ? groupTarget : shortRef(rows[0].target);
    const categories = [...new Set(rows.map((row) => row.category).filter(Boolean))];
    const ports = [...new Set(rows.map((row) => row.ports).filter(Boolean))];
    return {
      id: `relationship:${key}`,
      source,
      target,
      type: "smoothstep",
      markerStart: bidirectional ? { type: MarkerType.ArrowClosed, color: "#4d9393" } : undefined,
      markerEnd: { type: MarkerType.ArrowClosed, color: "#4d9393" },
      style: { stroke: "#4d9393", strokeWidth: 1.8 },
      label: [categories.join(" / "), ports.length ? `:${ports.join(" · ")}` : ""].filter(Boolean).join(" "),
      labelStyle: { fill: "#94a3b8", fontSize: 10 },
      labelBgStyle: { fill: "#11161d", fillOpacity: 0.92 },
      labelBgPadding: [5, 3] as [number, number],
      labelBgBorderRadius: 4,
      zIndex: 1,
    };
  });
}

function SegmentNode({ data }: NodeProps) {
  const segment = data as SegmentData;
  return (
    <div className="h-full w-full rounded-xl border-2 border-teal-700/70 bg-teal-950/20 shadow-lg shadow-black/10">
      <Handle type="target" position={Position.Left} className="!h-2.5 !w-2.5 !border-teal-300 !bg-teal-700" />
      <Handle type="source" position={Position.Right} className="!h-2.5 !w-2.5 !border-teal-300 !bg-teal-700" />
      <div className="flex items-start gap-3 border-b border-teal-800/60 px-4 py-3">
        <span className="rounded-md bg-teal-900/60 p-2 text-teal-200"><Network size={18} /></span>
        <div className="min-w-0">
          <div className="truncate font-mono text-sm font-semibold text-foreground">{segment.label}</div>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {segment.cidr ? <Badge>{segment.cidr}</Badge> : null}
            {segment.gateway ? <span className="font-mono text-[10px] text-muted-foreground">GW {segment.gateway}</span> : null}
          </div>
        </div>
      </div>
      {segment.hostCount === 0 ? (
        <p className="px-4 py-3 text-xs text-muted-foreground">No systems assigned</p>
      ) : null}
    </div>
  );
}

function SystemNode({ data }: NodeProps) {
  const system = data as SystemData;
  const Icon = systemIcon(system);
  return (
    <div className="h-full rounded-lg border border-border bg-card px-3 py-2.5 shadow-md">
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !border-slate-300 !bg-slate-600" />
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !border-slate-300 !bg-slate-600" />
      <div className="flex gap-2.5">
        <span className="mt-0.5 text-muted-foreground"><Icon size={17} /></span>
        <div className="min-w-0 flex-1">
          <div className="truncate font-mono text-xs font-semibold text-foreground">{system.label}</div>
          <div className="mt-1 truncate text-[10px] text-muted-foreground">
            {system.services.length
              ? system.services.slice(0, 2).map((service) => `${service.id}${service.port ? `:${service.port}` : ""}`).join(" · ")
              : system.os || system.type}
          </div>
          <div className="mt-1 line-clamp-2 text-[10px] leading-4 text-muted-foreground">{system.description}</div>
        </div>
      </div>
    </div>
  );
}

function ActorNode({ data }: NodeProps) {
  const actor = data as ActorData;
  return (
    <div className="rounded-lg border border-amber-700/60 bg-amber-950/30 p-3 shadow-md">
      <Handle type="source" position={Position.Bottom} className="!h-2.5 !w-2.5 !border-amber-300 !bg-amber-700" />
      <div className="flex items-center gap-2 font-mono text-sm font-semibold"><UserRound size={17} />{actor.label}</div>
      <p className="mt-2 text-xs leading-4 text-muted-foreground">{actor.description}</p>
    </div>
  );
}

function systemData(system: TopologyNode): SystemData {
  return {
    kind: "system",
    label: system.id,
    description: system.description,
    type: system.type,
    os: system.os,
    services: system.services,
  };
}

function systemIcon(system: SystemData): LucideIcon {
  const value = `${system.label} ${system.services.map((service) => service.id).join(" ")}`;
  if (/workstation|desktop|notebook|jupyter/i.test(value)) return Monitor;
  if (/database|postgres|dataset|store|registry|artifact/i.test(value)) return Database;
  if (/model|inference|ai-/i.test(value)) return BrainCircuit;
  if (/policy|identity|guardrail|proof/i.test(value)) return Shield;
  return Server;
}

function segmentHeight(hostCount: number) {
  return SEGMENT_HEADER_HEIGHT + Math.ceil(Math.max(1, hostCount) / 2) * (SYSTEM_HEIGHT + SYSTEM_GAP) + 14;
}

function shortRef(value: string) {
  return value.replace(/^infrastructure\./, "");
}

function Legend({ icon: Icon, label }: Readonly<{ icon: LucideIcon; label: string }>) {
  return <span className="flex items-center gap-1.5"><Icon size={13} />{label}</span>;
}

const nodeTypes = {
  segment: SegmentNode,
  system: SystemNode,
  actor: ActorNode,
};
