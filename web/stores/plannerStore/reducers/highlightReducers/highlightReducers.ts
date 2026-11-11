import { getLatestPlannerMessage } from '@/stores/plannerStore/selectors/highlightSelectors';
import type {
  PlanHighlightChange,
  PlannerState,
} from '@/stores/plannerStore/types';
import { updatePlan } from '@/stores/plannerStore/reducers/planUpdate/planUpdate';

/**
 * Clears a node's highlight until the next plan-level planner reply.
 */
export const clearHighlight = (
  plannerState: PlannerState,
  planHighlightChange: PlanHighlightChange,
): PlannerState =>
  updatePlan(plannerState, planHighlightChange.planId, (plan) => {
    const plannerMessage = getLatestPlannerMessage(plan);
    const clearedNodeIds =
      plan.plannerMessageId === plannerMessage?.id ? plan.clearedNodeIds : [];

    return {
      ...plan,
      updatedAt: planHighlightChange.currentTime,
      plannerMessageId: plannerMessage?.id ?? null,
      clearedNodeIds: [...clearedNodeIds, planHighlightChange.nodeId],
    };
  });
