import { assert, expect, test } from 'vitest';

import { createMockPlannerState } from '@/stores/plannerStore/initialState';
import type { PlannerState } from '@/stores/plannerStore/types';
import type { PlanRevision } from '@/entities/plan/planMessage';
import {
  PlanMessageKindEnum,
  PlanNodeChangeKindEnum,
} from '@/entities/plan/planMessage';
import { PlanAuthorEnum } from '@/entities/plan/planNode';
import { getPlannerValue } from '@/stores/plannerStore/selectors/plannerSelectors';
import { changePlan } from '@/stores/plannerStore/reducers/planReducers/planReducers';
import { clearHighlight } from './highlightReducers';
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

test('clearHighlight excludes cleared nodes from highlights after redo when the latest planner reply is unchanged', () => {
  const plannerState = createMockPlannerState();
  const highlightChange = { ...OPERATION, nodeId: 'RL-1' };
  const clearedState = clearHighlight(plannerState, highlightChange);

  const undoneState = undo(clearedState, OPERATION);
  const redoneState = redo(undoneState, OPERATION);
  const controls = getPlannerValue(redoneState);
  const highlightedIds = controls.highlightedNodes[PLAN_ID]?.map(
    (nodeChange) => nodeChange.nodeId,
  );

  expect(highlightedIds).toEqual(['RL-3']);

  const plan = getPlan(redoneState);
  const latestReply = plan.messages.findLast(
    (planMessage) => planMessage.kind === PlanMessageKindEnum.PLANNER,
  );

  assert(latestReply?.kind === PlanMessageKindEnum.PLANNER);

  const newReply = {
    ...latestReply,
    id: 'next-planner-reply',
    nodeChanges: [
      { nodeId: 'RL-1', kind: PlanNodeChangeKindEnum.ADDED },
      { nodeId: 'RL-3', kind: PlanNodeChangeKindEnum.REMOVED },
    ],
  };

  const editedPlan = { ...plan, messages: [...plan.messages, newReply] };
  const planChange = {
    ...OPERATION,
    plan: editedPlan,
    revision: { ...USER_REVISION, author: PlanAuthorEnum.PLANNER },
  };

  const updatedState = changePlan(redoneState, planChange);
  const updatedControls = getPlannerValue(updatedState);
  const updatedHighlightIds = updatedControls.highlightedNodes[PLAN_ID]?.map(
    (nodeChange) => nodeChange.nodeId,
  );

  expect(updatedHighlightIds).toEqual(['RL-1']);
});
