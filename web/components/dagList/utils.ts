import type { DagSummary } from '@/entities/dagSummary';
import { NodeStateEnum } from '@/entities/nodeState';

const countRunning = (dag: DagSummary): number =>
  dag.nodes.filter((node) => node.state === NodeStateEnum.IN_PROGRESS).length;

/**
 * Compares two dags by how active they are.
 */
export const compareByLiveliness = (
  left: DagSummary,
  right: DagSummary,
): number => {
  if (countRunning(left) !== countRunning(right)) {
    return countRunning(right) - countRunning(left);
  }

  const leftAt = left.lastActivityAt ?? '';
  const rightAt = right.lastActivityAt ?? '';

  if (leftAt !== rightAt) {
    return rightAt.localeCompare(leftAt);
  }

  return left.name.localeCompare(right.name);
};
