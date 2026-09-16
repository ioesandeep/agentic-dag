import type { NodeLink } from '@/entities/nodeDetail';

/**
 * Returns the position of the current node in the details sidebar list.
 */
export const findCurrentNodeIndex = (
  nodes: NodeLink[],
  currentNodeId: string,
): number => nodes.findIndex((node) => node.id === currentNodeId);
