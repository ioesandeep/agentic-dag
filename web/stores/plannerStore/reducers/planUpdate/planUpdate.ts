import { PlanStateEnum } from '@/entities/plan/plan';
import type { PlannerPlan, PlannerState } from '@/stores/plannerStore/types';

/**
 * Applies plan edits unless execution has started.
 */
export const updatePlan = (
  plannerState: PlannerState,
  planId: string,
  getPlanUpdate: (plan: PlannerPlan) => PlannerPlan,
): PlannerState => ({
  ...plannerState,
  plans: plannerState.plans.map((plan) => {
    if (plan.id !== planId || plan.state === PlanStateEnum.STARTED) {
      return plan;
    }

    return getPlanUpdate(plan);
  }),
});
