export type NodeState =
  | 'pending'
  | 'in_progress'
  | 'resting'
  | 'merged'
  | 'needs_human'
  | 'errored'
  | 'skipped';

export const NODE_STATES: readonly NodeState[] = [
  'pending',
  'in_progress',
  'resting',
  'merged',
  'needs_human',
  'errored',
  'skipped',
];
