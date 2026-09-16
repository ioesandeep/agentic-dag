import type { NodeSort } from '@/components/dagPanel/dagTabs/nodeTable/types';
import {
  NodeSortColumn,
  SortDirection,
} from '@/components/dagPanel/dagTabs/nodeTable/types';

export const DEFAULT_NODE_SORT: NodeSort = {
  column: NodeSortColumn.STATE,
  direction: SortDirection.ASCENDING,
};
