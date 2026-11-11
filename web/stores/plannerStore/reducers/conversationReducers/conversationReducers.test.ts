import { assert, expect, test } from 'vitest';

import { createMockPlannerState } from '@/stores/plannerStore/initialState';
import type { PlannerState } from '@/stores/plannerStore/types';
import { PlanMessageKindEnum } from '@/entities/plan/planMessage';
import { sendMessage } from './conversationReducers';

const PLAN_ID = 'plan-service-rate-limits';
const CURRENT_TIME = '2026-11-10T12:00:00Z';
const OPERATION = {
  planId: PLAN_ID,
  messageId: 'revision-message',
  currentTime: CURRENT_TIME,
};

const getPlan = (plannerState: PlannerState, planId = PLAN_ID) => {
  const plan = plannerState.plans.find((plan) => plan.id === planId);
  assert(plan);

  return plan;
};

test.each([null, 'RL-1'])(
  'sendMessage appends a user message when nodeId is %s',
  (nodeId) => {
    const plannerState = createMockPlannerState();
    const initialPlan = getPlan(plannerState);
    const planMessageInput = {
      ...OPERATION,
      nodeId,
      text: 'Use 500 requests per minute.',
    };

    const updatedState = sendMessage(plannerState, planMessageInput);
    const plan = getPlan(updatedState);
    const message = plan.messages.at(-1);

    expect(plan.messages).toHaveLength(initialPlan.messages.length + 1);
    expect(plan.updatedAt).toBe(CURRENT_TIME);

    assert(message?.kind === PlanMessageKindEnum.USER);
    expect(message.nodeId).toBe(nodeId);
    expect(message.text).toBe(planMessageInput.text);
  },
);
