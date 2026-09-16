export enum NodeSortColumn {
  STATE = 'state',
  UPDATED_AT = 'updatedAt',
}

export enum SortDirection {
  ASCENDING = 'asc',
  DESCENDING = 'desc',
}

export interface NodeSort {
  column: NodeSortColumn;
  direction: SortDirection;
}
