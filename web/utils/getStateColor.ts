import type { NodeStateEnum } from '@/entities/nodeState';

/**
 * Returns the theme colour for a node state.
 */
export const getStateColor = (state: NodeStateEnum): string =>
  `var(--mui-palette-state-${state})`;
