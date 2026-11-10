import type { Edge, XYPosition } from '@xyflow/react';
import { Position } from '@xyflow/react';

import type { PlanNode } from '@/entities/plan/planNode';
import type { PlanNodeChange } from '@/entities/plan/planMessage';
import { PlanNodeChangeKindEnum } from '@/entities/plan/planMessage';
import { EXECUTOR_AGENT_LABELS, LABELS } from '@/labels/en';
import { getNodePlacements } from '@/utils/graphLayout';
import {
  EDGE_TYPE,
  NODE_HEIGHT,
  NODE_WIDTH,
  PLAN_NODE_TYPE,
} from './constants';
import type { PlanFlowNode, PlanGraphInput, PlanGraphLayout } from './types';

const ORIGIN = { x: 0, y: 0 };

const getChangeLabel = (
  planNodeChange: PlanNodeChange | undefined,
): string | null => {
  switch (planNodeChange?.kind) {
    case PlanNodeChangeKindEnum.ADDED:
      return LABELS.planNodeNew;
    case PlanNodeChangeKindEnum.CHANGED:
      return LABELS.planNodeChanged;
    case PlanNodeChangeKindEnum.REMOVED:
    case undefined:
      return null;
  }
};

const getFlowNode = (
  planNode: PlanNode,
  planGraphInput: PlanGraphInput,
  placements: Map<string, XYPosition>,
): PlanFlowNode => {
  const repository = planGraphInput.repositories.find(
    (candidate) => candidate.id === planNode.repositoryId,
  );

  const change = planGraphInput.highlightedNodes.find(
    (candidate) => candidate.nodeId === planNode.id,
  );

  const executor = planNode.executorAgent ?? planGraphInput.executorAgent;

  return {
    id: planNode.id,
    type: PLAN_NODE_TYPE,
    position: placements.get(planNode.id) ?? ORIGIN,
    selected: planNode.id === planGraphInput.selectedNodeId,
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      title: planNode.title,
      nodeId: planNode.id,
      executorLabel: EXECUTOR_AGENT_LABELS[executor],
      repositoryName: repository?.fullName ?? planNode.repositoryId,
      changeLabel: getChangeLabel(change),
      onSelectNode: planGraphInput.onSelectNode,
    },
  };
};

const getEdges = (planNodes: PlanNode[]): Edge[] =>
  planNodes.flatMap((planNode) =>
    planNode.dependsOn.map((dependencyId) => ({
      id: `${dependencyId}-${planNode.id}`,
      source: dependencyId,
      target: planNode.id,
      type: EDGE_TYPE,
    })),
  );

/**
 * Creates the positioned cards and dependencies of a plan.
 */
export const getPlanGraphLayout = (
  planGraphInput: PlanGraphInput,
): PlanGraphLayout => {
  const placements = getNodePlacements(
    planGraphInput.nodes,
    NODE_WIDTH,
    NODE_HEIGHT,
  );

  const nodes = planGraphInput.nodes.map((planNode) =>
    getFlowNode(planNode, planGraphInput, placements),
  );

  const edges = getEdges(planGraphInput.nodes);

  return { nodes, edges };
};
