import type { ExecutorAgentEnum } from './executorAgent';
import type { PlanMessage } from './planMessage';
import type { PlanNode } from './planNode';

/**
 * Identifies a plan's approval and execution state.
 */
export enum PlanStateEnum {
  DRAFTING = 'drafting',
  APPROVED = 'approved',
  STARTED = 'started',
}

/**
 * Specifies the dag being planned and its conversation history.
 */
export interface Plan {
  id: string;
  name: string;
  state: PlanStateEnum;
  projectId: string;
  executorAgent: ExecutorAgentEnum;
  maxWorkers: number;
  cooldownSeconds: number;
  nodes: PlanNode[];
  messages: PlanMessage[];
  dagWrittenAt: string | null;
  createdAt: string;
  updatedAt: string;
}
