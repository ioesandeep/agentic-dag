import type { Edge, Node } from '@xyflow/react';

import type { DagNode } from '@/entities/dagDetail';

export interface DagGraphNodeData extends Record<string, unknown> {
  node: DagNode;
  // The name of the dag this node belongs to.
  dagName: string;
}

export type DagFlowNode = Node<DagGraphNodeData, 'dagNode'>;

export interface DagGraphLayout {
  nodes: DagFlowNode[];
  edges: Edge[];
}
