import type { EdgeLabel } from '@dagrejs/dagre';
import { Graph, layout } from '@dagrejs/dagre';
import type { Dimensions, Rect, Viewport, XYPosition } from '@xyflow/react';

const GRAPH_DIRECTION = 'LR';
const NODE_SEPARATION = 28;
const RANK_SEPARATION = 110;
const READABLE_ZOOM = 1;
const GRAPH_PADDING = 24;
const ORIGIN_VIEWPORT: Viewport = { x: 0, y: 0, zoom: READABLE_ZOOM };

/**
 * Specifies a graph node's dependencies.
 */
export interface GraphDependencyNode {
  id: string;
  dependsOn: string[];
}

interface PositionedGraphNode {
  position: XYPosition;
}

const getEdgeLabel = (): EdgeLabel => ({});

/**
 * Positions dependencies before their dependent nodes.
 */
export const getNodePlacements = (
  graphNodes: GraphDependencyNode[],
  nodeWidth: number,
  nodeHeight: number,
): Map<string, XYPosition> => {
  const graph = new Graph();
  const options = {
    rankdir: GRAPH_DIRECTION,
    nodesep: NODE_SEPARATION,
    ranksep: RANK_SEPARATION,
  };

  graph.setDefaultEdgeLabel(getEdgeLabel);
  graph.setGraph(options);

  graphNodes.forEach((graphNode) => {
    const size = { width: nodeWidth, height: nodeHeight };
    graph.setNode(graphNode.id, size);
  });

  graphNodes.forEach((graphNode) => {
    graphNode.dependsOn.forEach((dependencyId) =>
      graph.setEdge(dependencyId, graphNode.id),
    );
  });

  layout(graph);

  const placements = graphNodes.map((graphNode): [string, XYPosition] => {
    const placement = graph.node(graphNode.id);
    const position = {
      x: (placement.x ?? 0) - nodeWidth / 2,
      y: (placement.y ?? 0) - nodeHeight / 2,
    };

    return [graphNode.id, position];
  });

  return new Map(placements);
};

const getGraphBounds = (
  graphNodes: PositionedGraphNode[],
  nodeWidth: number,
  nodeHeight: number,
): Rect => {
  const lefts = graphNodes.map((graphNode) => graphNode.position.x);
  const tops = graphNodes.map((graphNode) => graphNode.position.y);
  const left = Math.min(...lefts);
  const top = Math.min(...tops);

  return {
    x: left,
    y: top,
    width: Math.max(...lefts) + nodeWidth - left,
    height: Math.max(...tops) + nodeHeight - top,
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
 * Opens a graph at a readable zoom.
 */
export const getInitialViewport = (
  graphNodes: PositionedGraphNode[],
  containerDimensions: Dimensions,
  nodeWidth: number,
  nodeHeight: number,
): Viewport => {
  if (graphNodes.length === 0) {
    return ORIGIN_VIEWPORT;
  }

  const bounds = getGraphBounds(graphNodes, nodeWidth, nodeHeight);

  return {
    x: getAxisOffset(bounds.x, bounds.width, containerDimensions.width),
    y: getAxisOffset(bounds.y, bounds.height, containerDimensions.height),
    zoom: READABLE_ZOOM,
  };
};
