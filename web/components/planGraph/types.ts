import type { Edge, Node } from '@xyflow/react';

import type { ExecutorAgentEnum } from '@/entities/plan/executorAgent';
import type { PlanNodeChange } from '@/entities/plan/planMessage';
import type { PlanNode } from '@/entities/plan/planNode';
import type { PlanRepository } from '@/entities/plan/planProject';

/**
 * Specifies a plan graph's content and selection.
 */
export interface PlanGraphInput {
  nodes: PlanNode[];
  repositories: PlanRepository[];
  executorAgent: ExecutorAgentEnum;
  highlightedNodes: PlanNodeChange[];
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
}

/**
 * Specifies a plan card's display values.
 */
export interface PlanGraphNodeData extends Record<string, unknown> {
  title: string;
  nodeId: string;
  executorLabel: string;
  repositoryName: string;
  changeLabel: string | null;
  onSelectNode: (nodeId: string) => void;
}

/**
 * Defines a plan node in React Flow.
 */
export type PlanFlowNode = Node<PlanGraphNodeData, 'planNode'>;

/**
 * Defines the positioned nodes and dependencies of a plan.
 */
export interface PlanGraphLayout {
  nodes: PlanFlowNode[];
  edges: Edge[];
}
