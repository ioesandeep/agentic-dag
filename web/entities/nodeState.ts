/**
 * The states of a node that the api sends.
 */
export enum NodeStateEnum {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  RESTING = 'resting',
  MERGED = 'merged',
  NEEDS_HUMAN = 'needs_human',
  ERRORED = 'errored',
  SKIPPED = 'skipped',
}

export const NODE_STATES: readonly NodeStateEnum[] =
  Object.values(NodeStateEnum);
