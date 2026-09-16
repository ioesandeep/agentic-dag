'use client';

import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TableSortLabel from '@mui/material/TableSortLabel';

import type { NodeSort } from '@/components/dagPanel/dagTabs/nodeTable/types';
import { NodeSortColumn } from '@/components/dagPanel/dagTabs/nodeTable/types';
import {
  getArrowDirection,
  getColumnDirection,
} from '@/components/dagPanel/dagTabs/nodeTable/utils';
import { LABELS } from '@/labels/en';

interface NodeTableHeadProps {
  sort: NodeSort;
  onSortChange: (column: NodeSortColumn) => void;
}

/**
 * Renders the header row of the NodeTable.
 */
export const NodeTableHead = ({ sort, onSortChange }: NodeTableHeadProps) => {
  const handleStateClick = () => onSortChange(NodeSortColumn.STATE);
  const handleLastActivityClick = () => onSortChange(NodeSortColumn.UPDATED_AT);

  return (
    <TableHead>
      <TableRow>
        <TableCell
          sortDirection={getColumnDirection(sort, NodeSortColumn.STATE)}
        >
          <TableSortLabel
            active={sort.column === NodeSortColumn.STATE}
            direction={getArrowDirection(sort, NodeSortColumn.STATE)}
            onClick={handleStateClick}
          >
            {LABELS.nodeState}
          </TableSortLabel>
        </TableCell>
        <TableCell>{LABELS.nodeId}</TableCell>
        <TableCell>{LABELS.nodeTitle}</TableCell>
        <TableCell>{LABELS.nodeAgent}</TableCell>
        <TableCell
          sortDirection={getColumnDirection(sort, NodeSortColumn.UPDATED_AT)}
        >
          <TableSortLabel
            active={sort.column === NodeSortColumn.UPDATED_AT}
            direction={getArrowDirection(sort, NodeSortColumn.UPDATED_AT)}
            onClick={handleLastActivityClick}
          >
            {LABELS.nodeLastActivity}
          </TableSortLabel>
        </TableCell>
      </TableRow>
    </TableHead>
  );
};
