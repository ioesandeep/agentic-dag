import type { Plan } from '@/entities/plan/plan';
import type { PlanRevision } from '@/entities/plan/planMessage';
import type { PlanProject } from '@/entities/plan/planProject';

/**
 * Specifies the plan values restored by undo and redo.
 */
export type PlanSnapshot = Pick<
  Plan,
  'name' | 'nodes' | 'executorAgent' | 'maxWorkers' | 'cooldownSeconds'
>;

/**
 * Records a revision's previous and edited plan values.
 */
export interface PlanHistoryEntry {
  revision: PlanRevision;
  before: PlanSnapshot;
  after: PlanSnapshot;
}

/**
 * Records reversible changes and cleared node highlights for a plan.
 */
export interface PlanHistory {
  undo: PlanHistoryEntry[];
  redo: PlanHistoryEntry[];
  clearedNodeIds: string[];
  plannerMessageId: string | null;
}

/**
 * Specifies the planner's records and revision history.
 */
export interface PlannerState {
  projects: PlanProject[];
  plans: PlannerPlan[];
}

/**
 * Specifies a plan with its local revision and highlight history.
 */
export interface PlannerPlan extends Plan, PlanHistory {}

/**
 * Identifies a plan operation and its conversation record.
 */
export interface PlanOperation {
  planId: string;
  messageId: string;
  currentTime: string;
}

/**
 * Specifies the first message and project of a new plan.
 */
export interface PlanCreation extends PlanOperation {
  projectId: string;
  text: string;
}

/**
 * Specifies a user message in a plan or node conversation.
 */
export interface PlanMessageInput extends PlanOperation {
  nodeId: string | null;
  text: string;
}

/**
 * Specifies an edited plan and its revision.
 */
export interface PlanChange {
  planId: string;
  plan: Plan;
  revision: PlanRevision;
  currentTime: string;
}

/**
 * Identifies a node whose highlight is cleared.
 */
export interface PlanHighlightChange {
  planId: string;
  nodeId: string;
  currentTime: string;
}

/**
 * Provides the operations that edit planner records.
 */
export interface PlannerAction {
  createPlan: (projectId: string, text: string) => string;
  sendMessage: (planId: string, nodeId: string | null, text: string) => void;
  changePlan: (planId: string, plan: Plan, revision: PlanRevision) => void;
  undo: (planId: string) => void;
  redo: (planId: string) => void;
  clearHighlight: (planId: string, nodeId: string) => void;
  approvePlan: (planId: string) => void;
  startPlan: (planId: string) => void;
}

/**
 * Specifies the planner records and their store actions.
 */
export interface PlannerStoreState extends PlannerState {
  actions: PlannerAction;
}
