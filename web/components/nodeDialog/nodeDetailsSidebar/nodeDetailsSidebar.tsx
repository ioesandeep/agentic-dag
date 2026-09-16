'use client';

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import { NodeDetailsSidebarCard } from '@/components/nodeDialog/nodeDetailsSidebar/nodeDetailsSidebarCard/nodeDetailsSidebarCard';
import type { NodeLink } from '@/entities/nodeDetail';
import { useScrollCurrentItemToTop } from '@/hooks/useScrollCurrentItemToTop';
import { LABELS } from '@/labels/en';

import { findCurrentNodeIndex } from './utils';

const SIDEBAR_STYLE = {
  minHeight: 0,
  overflowY: 'auto',
  display: 'flex',
  flexDirection: 'column',
  gap: 1,
  '& > *': { flexShrink: 0 },
};

const EMPTY_STYLE = { p: 1 };

interface NodeDetailsSidebarProps {
  dagName: string;
  nodes: NodeLink[];
  currentNodeId: string;
}

/**
 * Renders a card for every node of the dag, marking the current one.
 */
export const NodeDetailsSidebar = ({
  dagName,
  nodes,
  currentNodeId,
}: NodeDetailsSidebarProps) => {
  const currentIndex = findCurrentNodeIndex(nodes, currentNodeId);
  const listRef = useScrollCurrentItemToTop(currentIndex);

  if (nodes.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={EMPTY_STYLE}>
        {LABELS.nodesEmpty}
      </Typography>
    );
  }

  return (
    <Box
      component="nav"
      ref={listRef}
      aria-label={LABELS.nodesLabel}
      sx={SIDEBAR_STYLE}
    >
      {nodes.map((node) => (
        <NodeDetailsSidebarCard
          key={node.id}
          dagName={dagName}
          node={node}
          isCurrent={node.id === currentNodeId}
        />
      ))}
    </Box>
  );
};
