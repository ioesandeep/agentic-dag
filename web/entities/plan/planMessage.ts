import type { InstructionVersion, PlanAuthorEnum } from './planNode';

/**
 * Identifies how a planner reply changes a node.
 */
export enum PlanNodeChangeKindEnum {
  ADDED = 'added',
  CHANGED = 'changed',
  REMOVED = 'removed',
}

/**
 * Records a node affected by a planner reply.
 */
export interface PlanNodeChange {
  nodeId: string;
  kind: PlanNodeChangeKindEnum;
}

/**
 * Identifies a change that can be undone or redone.
 */
export interface PlanRevision {
  id: string;
  author: PlanAuthorEnum;
  nodeIds: string[];
  createdAt: string;
}

/**
 * Identifies the record in a plan conversation.
 */
export enum PlanMessageKindEnum {
  USER = 'user',
  PLANNER = 'planner',
  TOOL_CALL = 'tool_call',
  INSTRUCTIONS = 'instructions',
  REVISION = 'revision',
}

interface PlanMessageBase {
  id: string;
  nodeId: string | null;
  createdAt: string;
}

interface PlanUserMessage extends PlanMessageBase {
  kind: PlanMessageKindEnum.USER;
  text: string;
}

interface PlanPlannerMessage extends PlanMessageBase {
  kind: PlanMessageKindEnum.PLANNER;
  text: string;
  nodeChanges: PlanNodeChange[];
  instructionVersion: number | null;
  offersDag: boolean;
}

interface PlanToolCallMessage extends PlanMessageBase {
  kind: PlanMessageKindEnum.TOOL_CALL;
  toolName: string;
  toolInput: Record<string, unknown>;
  toolResult: string;
}

interface PlanInstructionsMessage extends PlanMessageBase {
  kind: PlanMessageKindEnum.INSTRUCTIONS;
  instructions: InstructionVersion;
}

interface PlanRevisionMessage extends PlanMessageBase {
  kind: PlanMessageKindEnum.REVISION;
  revision: PlanRevision;
  isUndo: boolean;
}

/**
 * Records a conversation entry for a plan or a node.
 */
export type PlanMessage =
  | PlanUserMessage
  | PlanPlannerMessage
  | PlanToolCallMessage
  | PlanInstructionsMessage
  | PlanRevisionMessage;
