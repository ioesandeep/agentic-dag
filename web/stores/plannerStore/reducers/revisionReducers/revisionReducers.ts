import { PlanStateEnum } from '@/entities/plan/plan';
import type { PlanMessage } from '@/entities/plan/planMessage';
import { PlanMessageKindEnum } from '@/entities/plan/planMessage';
import type {
  PlanHistoryEntry,
  PlanOperation,
  PlannerPlan,
  PlannerState,
} from '@/stores/plannerStore/types';
import { updatePlan } from '@/stores/plannerStore/reducers/planUpdate/planUpdate';

const createRevisionMessage = (
  planOperation: PlanOperation,
  planHistoryEntry: PlanHistoryEntry,
  isUndo: boolean,
): PlanMessage => ({
  id: planOperation.messageId,
  nodeId: null,
  kind: PlanMessageKindEnum.REVISION,
  revision: planHistoryEntry.revision,
  isUndo,
  createdAt: planOperation.currentTime,
});

const getRevisionValues = (
  plan: PlannerPlan,
  planHistoryEntry: PlanHistoryEntry,
  isUndo: boolean,
) => {
  if (isUndo) {
    return {
      ...planHistoryEntry.before,
      undo: plan.undo.slice(0, -1),
      redo: [...plan.redo, planHistoryEntry],
    };
  }

  return {
    ...planHistoryEntry.after,
    undo: [...plan.undo, planHistoryEntry],
    redo: plan.redo.slice(0, -1),
  };
};

const getPlanAfterRevision = (
  plan: PlannerPlan,
  planOperation: PlanOperation,
  planHistoryEntry: PlanHistoryEntry,
  isUndo: boolean,
): PlannerPlan => {
  const planMessage = createRevisionMessage(
    planOperation,
    planHistoryEntry,
    isUndo,
  );

  const revisionValues = getRevisionValues(plan, planHistoryEntry, isUndo);

  return {
    ...plan,
    ...revisionValues,
    state: PlanStateEnum.DRAFTING,
    messages: [...plan.messages, planMessage],
    updatedAt: planOperation.currentTime,
  };
};

const applyRevision = (
  plannerState: PlannerState,
  planOperation: PlanOperation,
  isUndo: boolean,
): PlannerState =>
  updatePlan(plannerState, planOperation.planId, (plan) => {
    const revisions = isUndo ? plan.undo : plan.redo;
    const planHistoryEntry = revisions.at(-1);

    if (!planHistoryEntry) {
      return plan;
    }

    return getPlanAfterRevision(plan, planOperation, planHistoryEntry, isUndo);
  });

/**
 * Restores the values before the plan's latest revision.
 */
export const undo = (
  plannerState: PlannerState,
  planOperation: PlanOperation,
) => applyRevision(plannerState, planOperation, true);

/**
 * Reapplies the plan's most recently undone revision.
 */
export const redo = (
  plannerState: PlannerState,
  planOperation: PlanOperation,
) => applyRevision(plannerState, planOperation, false);
