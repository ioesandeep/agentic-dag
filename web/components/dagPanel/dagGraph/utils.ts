import type { Edge, XYPosition } from '@xyflow/react';
import { Position } from '@xyflow/react';

import { DAG_NODE_TYPE, EDGE_TYPE, NODE_HEIGHT, NODE_WIDTH } from './constants';
import type { DagFlowNode, DagGraphLayout } from './types';
import type { DagDetail, DagNode } from '@/entities/dagDetail';
import { getNodePlacements } from '@/utils/graphLayout';

const ORIGIN: XYPosition = { x: 0, y: 0 };

const getEdges = (nodes: DagNode[]): Edge[] =>
  nodes.flatMap((node) =>
    node.dependsOn.map((dependencyId) => ({
      id: `${dependencyId}-${node.id}`,
      source: dependencyId,
      target: node.id,
      type: EDGE_TYPE,
    })),
  );

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
  const placements = getNodePlacements(dag.nodes, NODE_WIDTH, NODE_HEIGHT);
  const nodes = dag.nodes.map((node) =>
    getFlowNode(node, dag.name, placements),
  );

  return { nodes, edges };
};
