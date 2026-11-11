import { expect, test } from 'vitest';

import { createPlannerStore } from './plannerStore';
import type { PlannerState } from './types';

test('createPlannerStore applies actions to supplied state when mock initialization is replaced', () => {
  const plannerState: PlannerState = { projects: [], plans: [] };
  const plannerStore = createPlannerStore(plannerState);
  const { actions } = plannerStore.getState();

  const planId = actions.createPlan(
    'project-platform',
    'Add audit exports to virgo.',
  );

  const { plans } = plannerStore.getState();

  expect(plans).toHaveLength(1);
  expect(plans[0]?.id).toBe(planId);
  expect(plannerState.plans).toEqual([]);
});
