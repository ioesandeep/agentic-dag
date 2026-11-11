import { assert, expect, test } from 'vitest';

import { createMockPlannerState } from '@/stores/plannerStore/initialState';
import type { PlannerState } from '@/stores/plannerStore/types';
import { PlanStateEnum } from '@/entities/plan/plan';
import { PlanMessageKindEnum } from '@/entities/plan/planMessage';
import { getPlannerValue } from '@/stores/plannerStore/selectors/plannerSelectors';
import { approvePlan } from '@/stores/plannerStore/reducers/planReducers/planReducers';
import { redo, undo } from './revisionReducers';

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

test('seeded revisions restore node instructions when undo and redo run', () => {
  const plannerState = createMockPlannerState();
  const approvedState = approvePlan(plannerState, PLAN_ID, CURRENT_TIME);

  const undoneState = undo(approvedState, OPERATION);
  const approvedUndoState = approvePlan(undoneState, PLAN_ID, CURRENT_TIME);

  const redoneState = redo(approvedUndoState, OPERATION);

  const revisionStates = [undoneState, redoneState];

  for (const [index, state] of revisionStates.entries()) {
    const plan = getPlan(state);
    const controls = getPlannerValue(state);
    const nodes = plan.nodes.filter((planNode) =>
      ['RL-1', 'RL-3'].includes(planNode.id),
    );

    const versions = nodes.map((planNode) => planNode.instructions.version);
    const lastMessage = plan.messages.at(-1);

    expect(versions).toEqual([index + 1, index + 1]);
    expect(lastMessage?.kind).toBe(PlanMessageKindEnum.REVISION);
    expect(plan.state).toBe(PlanStateEnum.DRAFTING);
    expect(plan.updatedAt).toBe(CURRENT_TIME);

    expect(controls.canUndo[PLAN_ID]).toBe(index === 1);
    expect(controls.canRedo[PLAN_ID]).toBe(index === 0);
    expect(controls.highlightedNodes[PLAN_ID]).toHaveLength(index * 2);
  }

  const undonePlan = getPlan(undoneState);
  const lastMessage = undonePlan.messages.at(-1);
  assert(lastMessage?.kind === PlanMessageKindEnum.REVISION);

  expect(lastMessage.isUndo).toBe(true);
  expect(lastMessage.revision.id).toBe('revision-rate-limit-default');
});
