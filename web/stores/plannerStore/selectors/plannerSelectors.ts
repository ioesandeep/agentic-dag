import { PlanStateEnum } from '@/entities/plan/plan';
import type { PlannerPlan, PlannerState } from '@/stores/plannerStore/types';
import { getHighlightedNodes } from './highlightSelectors';

const getPlanControl = (plan: PlannerPlan) => {
  const canChange = plan.state !== PlanStateEnum.STARTED;

  return {
    id: plan.id,
    canUndo: canChange && plan.undo.length > 0,
    canRedo: canChange && plan.redo.length > 0,
    lastUndoneRevision: plan.redo.at(-1)?.revision ?? null,
    highlightedNodes: getHighlightedNodes(plan),
  };
};

type PlanControl = ReturnType<typeof getPlanControl>;

const getControlMap = <Key extends keyof PlanControl>(
  planControls: PlanControl[],
  key: Key,
): Record<string, PlanControl[Key]> => {
  const controlEntries = planControls.map((planControl) => [
    planControl.id,
    planControl[key],
  ]);

  return Object.fromEntries(controlEntries);
};

/**
 * Returns the planner records and available revision controls.
 */
export const getPlannerValue = (plannerState: PlannerState) => {
  const planControls = plannerState.plans.map(getPlanControl);

  return {
    projects: plannerState.projects,
    plans: plannerState.plans,
    canUndo: getControlMap(planControls, 'canUndo'),
    canRedo: getControlMap(planControls, 'canRedo'),
    lastUndoneRevision: getControlMap(planControls, 'lastUndoneRevision'),
    highlightedNodes: getControlMap(planControls, 'highlightedNodes'),
  };
};
