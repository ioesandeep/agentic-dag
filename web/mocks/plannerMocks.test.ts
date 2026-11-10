import { expect, test } from 'vitest';
import type { PlanNode } from '@/entities/plan/planNode';
import {
  PlanMessageKindEnum,
  PlanNodeChangeKindEnum,
} from '@/entities/plan/planMessage';
import {
  MOCK_PLANS,
  MOCK_PLAN_PROJECTS,
  MOCK_PLAN_REVISIONS,
} from './plannerMocks';

const hasDependencyCycle = (
  planNodes: PlanNode[],
  nodeId: string,
  visitedNodeIds: string[] = [],
): boolean => {
  const hasVisitedNode = visitedNodeIds.includes(nodeId);

  if (hasVisitedNode) {
    return true;
  }

  const planNode = planNodes.find((planNode) => planNode.id === nodeId);
  const nextVisitedNodeIds = [...visitedNodeIds, nodeId];

  return (
    planNode?.dependsOn.some((dependencyId) =>
      hasDependencyCycle(planNodes, dependencyId, nextVisitedNodeIds),
    ) ?? false
  );
};

test.each(MOCK_PLANS)(
  'planner dependencies reference plan nodes when the plan is $name',
  (plan) => {
    const nodeIds = plan.nodes.map((planNode) => planNode.id);

    for (const planNode of plan.nodes) {
      for (const dependencyId of planNode.dependsOn) {
        expect(nodeIds).toContain(dependencyId);
      }
    }
  },
);

test.each(MOCK_PLANS)(
  'planner messages reference plan nodes when the plan is $name',
  (plan) => {
    const nodeIds = plan.nodes.map((planNode) => planNode.id);

    for (const planMessage of plan.messages) {
      if (planMessage.nodeId !== null) {
        expect(nodeIds).toContain(planMessage.nodeId);
      }

      if (planMessage.kind === PlanMessageKindEnum.PLANNER) {
        for (const nodeChange of planMessage.nodeChanges) {
          if (nodeChange.kind !== PlanNodeChangeKindEnum.REMOVED) {
            expect(nodeIds).toContain(nodeChange.nodeId);
          }
        }
      }
    }
  },
);

test.each(MOCK_PLANS)(
  'planner node repositories belong to the project when the plan is $name',
  (plan) => {
    const planProject = MOCK_PLAN_PROJECTS.find(
      (planProject) => planProject.id === plan.projectId,
    );

    const repositoryIds = planProject?.repositories.map(
      (planRepository) => planRepository.id,
    );

    expect(planProject).toBeDefined();

    for (const planNode of plan.nodes) {
      expect(repositoryIds).toContain(planNode.repositoryId);
    }
  },
);

test.each(MOCK_PLANS)(
  'planner dependencies have no cycle when the plan is $name',
  (plan) => {
    const hasCycle = plan.nodes.some((planNode) =>
      hasDependencyCycle(plan.nodes, planNode.id),
    );

    expect(hasCycle).toBe(false);
  },
);

test.each(MOCK_PLANS)(
  'planner nodes exist only after the dag is written when the plan is $name',
  (plan) => {
    const hasNodes = plan.nodes.length > 0;
    const hasDag = plan.dagWrittenAt !== null;

    expect(hasNodes).toBe(hasDag);
  },
);

test.each(MOCK_PLAN_REVISIONS)(
  'planner revision nodes belong to the plan when the plan id is $planId',
  (mockPlanRevision) => {
    const plan = MOCK_PLANS.find((plan) => plan.id === mockPlanRevision.planId);
    const nodeIds = plan?.nodes.map((planNode) => planNode.id);

    expect(plan).toBeDefined();

    for (const nodeId of mockPlanRevision.revision.nodeIds) {
      expect(nodeIds).toContain(nodeId);
    }

    for (const planNode of mockPlanRevision.nodesBefore) {
      expect(mockPlanRevision.revision.nodeIds).toContain(planNode.id);
      expect(nodeIds).toContain(planNode.id);
    }
  },
);
