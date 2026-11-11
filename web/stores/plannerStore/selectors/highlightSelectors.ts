import type { Plan } from '@/entities/plan/plan';
import {
  PlanMessageKindEnum,
  PlanNodeChangeKindEnum,
} from '@/entities/plan/planMessage';
import type { PlannerPlan } from '@/stores/plannerStore/types';

/**
 * Returns the latest planner reply in the plan conversation.
 */
export const getLatestPlannerMessage = (plan: Plan) => {
  const messages = plan.messages.filter(
    (planMessage) => planMessage.nodeId === null,
  );

  return messages.findLast(
    (planMessage) => planMessage.kind === PlanMessageKindEnum.PLANNER,
  );
};

/**
 * Returns the nodes excluded from the current planner reply's highlights.
 */
export const getHiddenNodeIds = (plan: PlannerPlan) => {
  const plannerMessage = getLatestPlannerMessage(plan);
  const clearedNodeIds =
    plan.plannerMessageId === plannerMessage?.id ? plan.clearedNodeIds : [];

  const undoneNodeIds = plan.redo.flatMap(
    (planHistoryEntry) => planHistoryEntry.revision.nodeIds,
  );

  return [...clearedNodeIds, ...undoneNodeIds];
};

/**
 * Returns the added and changed nodes highlighted by the latest planner reply.
 */
export const getHighlightedNodes = (plan: PlannerPlan) => {
  const plannerMessage = getLatestPlannerMessage(plan);
  const hiddenNodeIds = getHiddenNodeIds(plan);

  return (
    plannerMessage?.nodeChanges.filter(
      (nodeChange) =>
        nodeChange.kind !== PlanNodeChangeKindEnum.REMOVED &&
        !hiddenNodeIds.includes(nodeChange.nodeId),
    ) ?? []
  );
};
