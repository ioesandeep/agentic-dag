'use client';

import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import { useState } from 'react';

import { DEFAULT_NODE_SORT } from '@/components/dagPanel/dagTabs/nodeTable/constants';
import { NodeTableHead } from '@/components/dagPanel/dagTabs/nodeTable/nodeTableHead/nodeTableHead';
import { NodeTableRow } from '@/components/dagPanel/dagTabs/nodeTable/nodeTableRow/nodeTableRow';
import type { NodeSortColumn } from '@/components/dagPanel/dagTabs/nodeTable/types';
import {
  getNextSort,
  sortNodes,
} from '@/components/dagPanel/dagTabs/nodeTable/utils';
import { EmptyState } from '@/components/emptyState/emptyState';
import type { DagNode } from '@/entities/dagDetail';
import { LABELS } from '@/labels/en';

interface NodeTableProps {
  dagName: string;
  nodes: DagNode[];
}

/**
 * Renders the Nodes tab of the DagTabs.
 */
export const NodeTable = ({ dagName, nodes }: NodeTableProps) => {
  const [sort, setSort] = useState(DEFAULT_NODE_SORT);

  const handleSortChange = (column: NodeSortColumn) =>
    setSort(getNextSort(sort, column));

  if (nodes.length === 0) {
    return (
      <EmptyState
        title={LABELS.dagNodesEmpty}
        body={LABELS.dagNodesEmptyHint}
      />
    );
  }

  return (
    <Table size="small" stickyHeader>
      <NodeTableHead sort={sort} onSortChange={handleSortChange} />
      <TableBody>
        {sortNodes(nodes, sort).map((node) => (
          <NodeTableRow key={node.id} dagName={dagName} node={node} />
        ))}
      </TableBody>
    </Table>
  );
};
