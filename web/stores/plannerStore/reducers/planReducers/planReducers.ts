import { ExecutorAgentEnum } from '@/entities/plan/executorAgent';
import { PlanStateEnum } from '@/entities/plan/plan';
import type {
  PlanChange,
  PlanCreation,
  PlanHistory,
  PlanHistoryEntry,
  PlannerPlan,
  PlannerState,
} from '@/stores/plannerStore/types';
import {
  getHiddenNodeIds,
  getLatestPlannerMessage,
} from '@/stores/plannerStore/selectors/highlightSelectors';
import { getPlanSnapshot } from '@/stores/plannerStore/selectors/historySelectors';
import { sendMessage } from '@/stores/plannerStore/reducers/conversationReducers/conversationReducers';
import { updatePlan } from '@/stores/plannerStore/reducers/planUpdate/planUpdate';

const EMPTY_HISTORY: PlanHistory = {
  undo: [],
  redo: [],
  clearedNodeIds: [],
  plannerMessageId: null,
};

const PLAN_DEFAULTS = {
  executorAgent: ExecutorAgentEnum.CLAUDE,
  maxWorkers: 2,
  cooldownSeconds: 0,
};

/**
 * Adds a drafting plan with its first user message.
 */
export const createPlan = (
  plannerState: PlannerState,
  planCreation: PlanCreation,
): PlannerState => {
  const plan: PlannerPlan = {
    ...PLAN_DEFAULTS,
    ...EMPTY_HISTORY,
    id: planCreation.planId,
    name: '',
    projectId: planCreation.projectId,
    state: PlanStateEnum.DRAFTING,
    nodes: [],
    messages: [],
    dagWrittenAt: null,
    createdAt: planCreation.currentTime,
    updatedAt: planCreation.currentTime,
  };

  const nextState = { ...plannerState, plans: [...plannerState.plans, plan] };
  const planMessageInput = { ...planCreation, nodeId: null };

  return sendMessage(nextState, planMessageInput);
};

/**
 * Saves an edited plan with an undo revision and an empty redo list.
 */
export const changePlan = (
  plannerState: PlannerState,
  planChange: PlanChange,
): PlannerState =>
  updatePlan(plannerState, planChange.planId, (plan) => {
    const planHistoryEntry: PlanHistoryEntry = {
      revision: planChange.revision,
      before: getPlanSnapshot(plan),
      after: getPlanSnapshot(planChange.plan),
    };

    return {
      ...plan,
      ...planChange.plan,
      id: plan.id,
      state: PlanStateEnum.DRAFTING,
      updatedAt: planChange.currentTime,
      undo: [...plan.undo, planHistoryEntry],
      redo: [],
      plannerMessageId: getLatestPlannerMessage(plan)?.id ?? null,
      clearedNodeIds: getHiddenNodeIds(plan),
    };
  });

const setPlanState = (
  plannerState: PlannerState,
  planId: string,
  state: PlanStateEnum,
  currentTime: string,
): PlannerState =>
  updatePlan(plannerState, planId, (plan) => ({
    ...plan,
    state,
    updatedAt: currentTime,
  }));

/**
 * Sets the plan's approval state.
 */
export const approvePlan = (
  plannerState: PlannerState,
  planId: string,
  currentTime: string,
) => setPlanState(plannerState, planId, PlanStateEnum.APPROVED, currentTime);

/**
 * Sets the plan's execution state.
 */
export const startPlan = (
  plannerState: PlannerState,
  planId: string,
  currentTime: string,
) => setPlanState(plannerState, planId, PlanStateEnum.STARTED, currentTime);
