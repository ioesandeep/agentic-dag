import type { NodeSort } from '@/components/dagPanel/dagTabs/nodeTable/types';
import {
  NodeSortColumn,
  SortDirection,
} from '@/components/dagPanel/dagTabs/nodeTable/types';
import type { DagNode } from '@/entities/dagDetail';
import { NODE_STATES } from '@/entities/nodeState';

const ASCENDING_SIGN = 1;
const DESCENDING_SIGN = -1;

const compareByColumn = (
  left: DagNode,
  right: DagNode,
  column: NodeSortColumn,
): number => {
  if (column === NodeSortColumn.STATE) {
    return NODE_STATES.indexOf(left.state) - NODE_STATES.indexOf(right.state);
  }

  return (left.updatedAt ?? '').localeCompare(right.updatedAt ?? '');
};

const getDirectionSign = (direction: SortDirection): number => {
  if (direction === SortDirection.ASCENDING) {
    return ASCENDING_SIGN;
  }

  return DESCENDING_SIGN;
};

const flipDirection = (direction: SortDirection): SortDirection => {
  if (direction === SortDirection.ASCENDING) {
    return SortDirection.DESCENDING;
  }

  return SortDirection.ASCENDING;
};

/**
 * Returns the nodes of a dag in sorted order.
 */
export const sortNodes = (nodes: DagNode[], sort: NodeSort): DagNode[] => {
  const sign = getDirectionSign(sort.direction);

  return [...nodes].sort(
    (left, right) => sign * compareByColumn(left, right, sort.column),
  );
};

/**
 * Returns the next sort for a NodeTable column.
 */
export const getNextSort = (
  sort: NodeSort,
  column: NodeSortColumn,
): NodeSort => {
  if (sort.column !== column) {
    return { column, direction: SortDirection.ASCENDING };
  }

  return { column, direction: flipDirection(sort.direction) };
};

/**
 * Returns the sort direction of a NodeTable column.
 */
export const getColumnDirection = (
  sort: NodeSort,
  column: NodeSortColumn,
): SortDirection | false => {
  if (sort.column !== column) {
    return false;
  }

  return sort.direction;
};

/**
 * Returns the sort arrow direction for a NodeTable column.
 */
export const getArrowDirection = (
  sort: NodeSort,
  column: NodeSortColumn,
): SortDirection => {
  if (sort.column !== column) {
    return SortDirection.ASCENDING;
  }

  return sort.direction;
};
