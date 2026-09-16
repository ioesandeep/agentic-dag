import type { NodeState } from '@/entities/nodeState';

/**
 * Returns the theme colour for a node state.
 */
export const getStateColor = (state: NodeState): string =>
  `var(--mui-palette-state-${state})`;
