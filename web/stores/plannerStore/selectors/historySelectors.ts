import type { Plan } from '@/entities/plan/plan';
import type { PlanSnapshot } from '@/stores/plannerStore/types';

/**
 * Returns the plan values saved for undo and redo.
 */
export const getPlanSnapshot = (plan: Plan): PlanSnapshot => ({
  name: plan.name,
  nodes: plan.nodes,
  executorAgent: plan.executorAgent,
  maxWorkers: plan.maxWorkers,
  cooldownSeconds: plan.cooldownSeconds,
});
