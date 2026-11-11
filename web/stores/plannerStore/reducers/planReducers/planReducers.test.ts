import { assert, expect, test } from 'vitest';

import { createMockPlannerState } from '@/stores/plannerStore/initialState';
import type { PlannerState } from '@/stores/plannerStore/types';
import { ExecutorAgentEnum } from '@/entities/plan/executorAgent';
import { PlanStateEnum } from '@/entities/plan/plan';
import type { PlanRevision } from '@/entities/plan/planMessage';
import { PlanMessageKindEnum } from '@/entities/plan/planMessage';
import { PlanAuthorEnum } from '@/entities/plan/planNode';
import { getPlannerValue } from '@/stores/plannerStore/selectors/plannerSelectors';
import { approvePlan, changePlan, createPlan, startPlan } from './planReducers';
import { sendMessage } from '@/stores/plannerStore/reducers/conversationReducers/conversationReducers';
import { clearHighlight } from '@/stores/plannerStore/reducers/highlightReducers/highlightReducers';
import {
  redo,
  undo,
} from '@/stores/plannerStore/reducers/revisionReducers/revisionReducers';

const PLAN_ID = 'plan-service-rate-limits';
const CURRENT_TIME = '2026-11-10T12:00:00Z';
const OPERATION = {
  planId: PLAN_ID,
  messageId: 'revision-message',
  currentTime: CURRENT_TIME,
};

const USER_REVISION: PlanRevision = {
  id: 'user-revision',
  author: PlanAuthorEnum.USER,
  nodeIds: ['RL-6'],
  createdAt: CURRENT_TIME,
};

const getPlan = (plannerState: PlannerState, planId = PLAN_ID) => {
  const plan = plannerState.plans.find((plan) => plan.id === planId);
  assert(plan);

  return plan;
};

test('createPlan adds a drafting plan with default settings when a project and message are supplied', () => {
  const plannerState = createMockPlannerState();
  const planCreation = {
    ...OPERATION,
    planId: 'new-plan',
    projectId: 'project-platform',
    text: 'Add audit exports to virgo.',
  };

  const updatedState = createPlan(plannerState, planCreation);
  const plan = getPlan(updatedState, planCreation.planId);
  const settings = [plan.executorAgent, plan.maxWorkers, plan.cooldownSeconds];
  const firstMessage = plan.messages[0];

  expect(settings).toEqual([ExecutorAgentEnum.CLAUDE, 2, 0]);
  expect(plan.state).toBe(PlanStateEnum.DRAFTING);
  expect(plan.name).toBe('');

  expect(plan.nodes).toEqual([]);
  expect(plan.dagWrittenAt).toBeNull();
  expect(plan.updatedAt).toBe(CURRENT_TIME);

  assert(firstMessage?.kind === PlanMessageKindEnum.USER);
  expect(firstMessage.nodeId).toBeNull();
  expect(firstMessage.text).toBe(planCreation.text);
});

test('changePlan returns an approved plan to drafting when a user edits its settings', () => {
  const plannerState = createMockPlannerState();
  const approvedState = approvePlan(plannerState, PLAN_ID, CURRENT_TIME);

  const plan = { ...getPlan(approvedState), maxWorkers: 4 };
  const planChange = { ...OPERATION, plan, revision: USER_REVISION };

  const updatedState = changePlan(approvedState, planChange);
  const undoneState = undo(updatedState, OPERATION);
  const redoneState = redo(undoneState, OPERATION);

  const updatedPlan = getPlan(updatedState);
  const undonePlan = getPlan(undoneState);
  const redonePlan = getPlan(redoneState);

  expect(updatedPlan.state).toBe(PlanStateEnum.DRAFTING);
  expect(updatedPlan.updatedAt).toBe(CURRENT_TIME);
  expect(undonePlan.maxWorkers).toBe(2);
  expect(redonePlan.maxWorkers).toBe(4);
});

test('changePlan empties the redo list when a new revision follows undo', () => {
  const plannerState = createMockPlannerState();
  const undoneState = undo(plannerState, OPERATION);
  const plan = { ...getPlan(undoneState), name: 'updated-rate-limits' };
  const planChange = { ...OPERATION, plan, revision: USER_REVISION };

  const updatedState = changePlan(undoneState, planChange);
  const controls = getPlannerValue(updatedState);

  expect(controls.canRedo[PLAN_ID]).toBe(false);
  expect(controls.lastUndoneRevision[PLAN_ID]).toBeNull();
  expect(controls.highlightedNodes[PLAN_ID]).toEqual([]);
});

test('started plans remain unchanged when an editing operation runs', () => {
  const plannerState = createMockPlannerState();
  const planChange = {
    ...OPERATION,
    plan: getPlan(plannerState),
    revision: USER_REVISION,
  };

  const changedState = changePlan(plannerState, planChange);
  const undoneState = undo(changedState, OPERATION);

  const startedState = startPlan(undoneState, PLAN_ID, CURRENT_TIME);
  const startedPlan = getPlan(startedState);
  const planMessageInput = {
    ...OPERATION,
    nodeId: null,
    text: 'Change the plan.',
  };

  const highlightChange = { ...OPERATION, nodeId: 'RL-1' };

  const attemptedStates = [
    changePlan(startedState, planChange),
    sendMessage(startedState, planMessageInput),
    undo(startedState, OPERATION),
    redo(startedState, OPERATION),
    clearHighlight(startedState, highlightChange),
    approvePlan(startedState, PLAN_ID, CURRENT_TIME),
  ];

  for (const state of attemptedStates) {
    const plan = getPlan(state);

    expect(plan).toBe(startedPlan);
  }
});
