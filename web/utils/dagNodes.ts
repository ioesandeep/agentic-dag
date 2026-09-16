import type { NodePreview } from '@/entities/dagSummary';
import type { NodeState } from '@/entities/nodeState';
import { NODE_STATES } from '@/entities/nodeState';

const HIGHLIGHT_ORDER: readonly NodeState[] = [
  'in_progress',
  'needs_human',
  'errored',
  'resting',
  'pending',
  'merged',
  'skipped',
];

export interface NodeStateCount {
  state: NodeState;
  // The number of nodes in that state.
  count: number;
}

/**
 * Returns the node counts of a dag by state.
 */
export const countNodeStates = (nodes: NodePreview[]): NodeStateCount[] => {
  const counts = new Map<NodeState, number>();

  for (const node of nodes) {
    counts.set(node.state, (counts.get(node.state) ?? 0) + 1);
  }

  return NODE_STATES.filter((state) => counts.has(state)).map((state) => ({
    state,
    count: counts.get(state) ?? 0,
  }));
};

/**
 * Returns the state of a dag's most recently updated node.
 */
export const getLatestNodeState = (nodes: NodePreview[]): NodeState | null => {
  const moved = nodes.filter((node) => node.updatedAt !== null);

  if (moved.length === 0) {
    return null;
  }

  return moved.reduce((latest, node) =>
    (node.updatedAt ?? '') > (latest.updatedAt ?? '') ? node : latest,
  ).state;
};

export const pickHighlights = (
  nodes: NodePreview[],
  limit: number,
): NodePreview[] =>
  [...nodes]
    .sort((left, right) => {
      const rank =
        HIGHLIGHT_ORDER.indexOf(left.state) -
        HIGHLIGHT_ORDER.indexOf(right.state);

      if (rank !== 0) {
        return rank;
      }

      return (right.updatedAt ?? '').localeCompare(left.updatedAt ?? '');
    })
    .slice(0, limit);
