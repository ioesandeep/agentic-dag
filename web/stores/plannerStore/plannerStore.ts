import type { StateCreator, StoreApi } from 'zustand/vanilla';
import { createStore } from 'zustand/vanilla';

import { createMockPlannerState } from './initialState';
import type {
  PlanOperation,
  PlannerAction,
  PlannerState,
  PlannerStoreState,
} from './types';
import {
  createPlan,
  changePlan,
  approvePlan,
  startPlan,
} from '@/stores/plannerStore/reducers/planReducers/planReducers';
import { sendMessage } from '@/stores/plannerStore/reducers/conversationReducers/conversationReducers';
import { clearHighlight } from '@/stores/plannerStore/reducers/highlightReducers/highlightReducers';
import {
  undo,
  redo,
} from '@/stores/plannerStore/reducers/revisionReducers/revisionReducers';

const getOperation = (planId: string): PlanOperation => {
  const currentDate = new Date();

  return {
    planId,
    messageId: crypto.randomUUID(),
    currentTime: currentDate.toISOString(),
  };
};

const createPlannerActions: StateCreator<
  PlannerStoreState,
  [],
  [],
  PlannerAction
> = (set) => ({
  createPlan: (projectId, text) => {
    const planId = crypto.randomUUID();
    const planCreation = { ...getOperation(planId), projectId, text };
    set((plannerState) => createPlan(plannerState, planCreation));

    return planId;
  },
  sendMessage: (planId, nodeId, text) => {
    const planMessageInput = { ...getOperation(planId), nodeId, text };
    set((plannerState) => sendMessage(plannerState, planMessageInput));
  },
  changePlan: (planId, plan, revision) => {
    const currentDate = new Date();
    const currentTime = currentDate.toISOString();
    const planChange = { planId, plan, revision, currentTime };
    set((plannerState) => changePlan(plannerState, planChange));
  },
  undo: (planId) => {
    const planOperation = getOperation(planId);
    set((plannerState) => undo(plannerState, planOperation));
  },
  redo: (planId) => {
    const planOperation = getOperation(planId);
    set((plannerState) => redo(plannerState, planOperation));
  },
  clearHighlight: (planId, nodeId) => {
    const currentDate = new Date();
    const currentTime = currentDate.toISOString();
    const planHighlightChange = { planId, nodeId, currentTime };
    set((plannerState) => clearHighlight(plannerState, planHighlightChange));
  },
  approvePlan: (planId) => {
    const currentDate = new Date();
    const currentTime = currentDate.toISOString();
    set((plannerState) => approvePlan(plannerState, planId, currentTime));
  },
  startPlan: (planId) => {
    const currentDate = new Date();
    const currentTime = currentDate.toISOString();
    set((plannerState) => startPlan(plannerState, planId, currentTime));
  },
});

/**
 * Creates an independent planner store for an application instance.
 */
export const createPlannerStore = (
  plannerState: PlannerState = createMockPlannerState(),
): StoreApi<PlannerStoreState> => {
  const createPlannerStoreState: StateCreator<PlannerStoreState> = (
    set,
    get,
    store,
  ) => {
    const actions = createPlannerActions(set, get, store);

    return { ...plannerState, actions };
  };

  return createStore<PlannerStoreState>(createPlannerStoreState);
};
