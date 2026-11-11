import type { Plan } from '@/entities/plan/plan';
import {
  MOCK_PLANS,
  MOCK_PLAN_PROJECTS,
  MOCK_PLAN_REVISIONS,
} from '@/mocks/plannerMocks';
import type { PlanHistory, PlannerState } from './types';
import { getPlanSnapshot } from '@/stores/plannerStore/selectors/historySelectors';

/**
 * Returns the undo history available for a mock plan.
 */
const getSeededHistory = (plan: Plan): PlanHistory => {
  const after = getPlanSnapshot(plan);
  const undo = MOCK_PLAN_REVISIONS.filter(
    (mockPlanRevision) => mockPlanRevision.planId === plan.id,
  ).map((mockPlanRevision) => ({
    revision: mockPlanRevision.revision,
    after,
    before: {
      ...after,
      ...mockPlanRevision.settingsBefore,
      nodes: plan.nodes.map(
        (planNode) =>
          mockPlanRevision.nodesBefore.find(
            (previousNode) => previousNode.id === planNode.id,
          ) ?? planNode,
      ),
    },
  }));

  return { undo, redo: [], clearedNodeIds: [], plannerMessageId: null };
};

/**
 * Creates independent planner state from the mock records.
 */
export const createMockPlannerState = (): PlannerState => {
  const plans = MOCK_PLANS.map((plan) => ({
    ...plan,
    ...getSeededHistory(plan),
  }));

  const plannerState = { projects: MOCK_PLAN_PROJECTS, plans };

  return structuredClone(plannerState);
};
