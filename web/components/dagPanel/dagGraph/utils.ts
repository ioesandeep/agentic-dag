import type { EdgeLabel, NodeLabel } from '@dagrejs/dagre';
import { Graph, layout } from '@dagrejs/dagre';
import type { Dimensions, Edge, Rect, Viewport, XYPosition } from '@xyflow/react';
import { Position } from '@xyflow/react';

import {
  DAG_NODE_TYPE,
  EDGE_TYPE,
  GRAPH_DIRECTION,
  GRAPH_PADDING,
  NODE_HEIGHT,
  NODE_SEPARATION,
  NODE_WIDTH,
  RANK_SEPARATION,
  READABLE_ZOOM,
} from '@/components/dagPanel/dagGraph/constants';
import type {
  DagFlowNode,
  DagGraphLayout,
} from '@/components/dagPanel/dagGraph/types';
import type { DagDetail, DagNode } from '@/entities/dagDetail';

const ORIGIN: XYPosition = { x: 0, y: 0 };
const ORIGIN_VIEWPORT: Viewport = { x: 0, y: 0, zoom: READABLE_ZOOM };

const getEdgeLabel = (): EdgeLabel => ({});

const getEdges = (nodes: DagNode[]): Edge[] =>
  nodes.flatMap((node) =>
    node.dependsOn.map((dependencyId) => ({
      id: `${dependencyId}-${node.id}`,
      source: dependencyId,
      target: node.id,
      type: EDGE_TYPE,
    })),
  );

const getTopLeft = (placement: NodeLabel): XYPosition => {
  const x = (placement.x ?? 0) - NODE_WIDTH / 2;
  const y = (placement.y ?? 0) - NODE_HEIGHT / 2;

  return { x, y };
};

const getNodePlacements = (
  nodes: DagNode[],
  edges: Edge[],
): Map<string, XYPosition> => {
  const graph = new Graph();
  const options = {
    rankdir: GRAPH_DIRECTION,
    nodesep: NODE_SEPARATION,
    ranksep: RANK_SEPARATION,
  };

  graph.setDefaultEdgeLabel(getEdgeLabel);
  graph.setGraph(options);

  nodes.forEach((node) => {
    const size = { width: NODE_WIDTH, height: NODE_HEIGHT };

    graph.setNode(node.id, size);
  });
  edges.forEach((edge) => graph.setEdge(edge.source, edge.target));
  layout(graph);

  const placements = nodes.map((node): [string, XYPosition] => {
    const placement = graph.node(node.id);

    return [node.id, getTopLeft(placement)];
  });

  return new Map(placements);
};

const getFlowNode = (
  node: DagNode,
  dagName: string,
  placements: Map<string, XYPosition>,
): DagFlowNode => {
  const data = { node, dagName };

  return {
    id: node.id,
    type: DAG_NODE_TYPE,
    position: placements.get(node.id) ?? ORIGIN,
    data,
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  };
};

/**
 * Returns the laid out nodes and edges of a dag graph.
 */
export const getGraphLayout = (dag: DagDetail): DagGraphLayout => {
  const edges = getEdges(dag.nodes);
  const placements = getNodePlacements(dag.nodes, edges);
  const nodes = dag.nodes.map((node) =>
    getFlowNode(node, dag.name, placements),
  );

  return { nodes, edges };
};

const getGraphBounds = (dagFlowNodes: DagFlowNode[]): Rect => {
  const lefts = dagFlowNodes.map((dagFlowNode) => dagFlowNode.position.x);
  const tops = dagFlowNodes.map((dagFlowNode) => dagFlowNode.position.y);
  const left = Math.min(...lefts);
  const top = Math.min(...tops);

  return {
    x: left,
    y: top,
    width: Math.max(...lefts) + NODE_WIDTH - left,
    height: Math.max(...tops) + NODE_HEIGHT - top,
  };
};

const getAxisOffset = (
  boundsStart: number,
  boundsLength: number,
  containerLength: number,
): number => {
  const graphLength = boundsLength * READABLE_ZOOM;
  const hasRoom = graphLength + GRAPH_PADDING * 2 <= containerLength;
  const offset = hasRoom ? (containerLength - graphLength) / 2 : GRAPH_PADDING;

  return offset - boundsStart * READABLE_ZOOM;
};

/**
 * Returns the viewport that opens a dag graph at a readable zoom.
 */
export const getInitialViewport = (
  dagFlowNodes: DagFlowNode[],
  containerDimensions: Dimensions,
): Viewport => {
  if (dagFlowNodes.length === 0) {
    return ORIGIN_VIEWPORT;
  }

  const bounds = getGraphBounds(dagFlowNodes);

  return {
    x: getAxisOffset(bounds.x, bounds.width, containerDimensions.width),
    y: getAxisOffset(bounds.y, bounds.height, containerDimensions.height),
    zoom: READABLE_ZOOM,
  };
};
