import type { ExecutorAgentEnum } from './executorAgent';

/**
 * Identifies who changes a plan or its instructions.
 */
export enum PlanAuthorEnum {
  USER = 'user',
  PLANNER = 'planner',
}

/**
 * Records a saved version of a node's instructions.
 */
export interface InstructionVersion {
  version: number;
  text: string;
  author: PlanAuthorEnum;
  createdAt: string;
}

/**
 * Specifies a node's work and execution settings.
 */
export interface PlanNode {
  id: string;
  name: string;
  title: string;
  dependsOn: string[];
  // Null uses the plan's executor.
  executorAgent: ExecutorAgentEnum | null;
  // Null uses the plan's cooldown.
  cooldownSeconds: number | null;
  repositoryId: string;
  // Null uses the repository's project branch.
  baseBranch: string | null;
  instructions: InstructionVersion;
}
