'use client';

import Box from '@mui/material/Box';
import { useState } from 'react';

import { SIDEBAR_COLLAPSE_KEY } from '@/components/dagPanel/dagSidebar/constants';
import { EmptyState } from '@/components/emptyState/emptyState';
import { NodeDetailsSidebar } from '@/components/nodeDialog/nodeDetailsSidebar/nodeDetailsSidebar';
import { NodeDetailColumns } from '@/components/nodeDialog/nodeDialogBody/nodeDetailColumns/nodeDetailColumns';
import { NodeDialogBodySkeleton } from '@/components/nodeDialog/nodeDialogBody/nodeDialogBodySkeleton/nodeDialogBodySkeleton';
import {
  findDetailOfNode,
  getNodeDetailsSidebarStyle,
} from '@/components/nodeDialog/utils';
import type { NodeDetail, NodeLink } from '@/entities/nodeDetail';
import { useEntryFromDagPage } from '@/hooks/useEntryFromDagPage';
import { useStoredFlag } from '@/hooks/useStoredFlag';
import { LABELS } from '@/labels/en';

const MISSING_STYLE = { p: { xs: 2, md: 4 } };

const BODY_STYLE = {
  flexGrow: 1,
  minHeight: 0,
  display: 'flex',
  flexDirection: { xs: 'column', md: 'row' },
  gap: 2,
  p: { xs: 2, md: 3 },
  overflowY: { xs: 'auto', md: 'hidden' },
  overflowX: 'hidden',
};

interface NodeDialogBodyProps {
  dagName: string;
  nodeId: string;
  // Every node of the dag.
  nodes: NodeLink[];
  // The node's record, null until the api sends it.
  detail: NodeDetail | null;
  // True where the dag records no node with this id.
  isMissing: boolean;
}

/**
 * Renders the columns of the node screen.
 */
export const NodeDialogBody = ({
  dagName,
  nodeId,
  nodes,
  detail,
  isMissing,
}: NodeDialogBodyProps) => {
  const [isConversationWide, setIsConversationWide] = useState(false);
  const dagSidebarCollapse = useStoredFlag(SIDEBAR_COLLAPSE_KEY, false);
  const isEnteringFromDagPage = useEntryFromDagPage();

  const handleToggleWidth = () => setIsConversationWide((isWide) => !isWide);
  const nodeDetail = findDetailOfNode(detail, nodeId);

  if (isMissing) {
    return (
      <Box sx={MISSING_STYLE}>
        <EmptyState title={nodeId} body={LABELS.nodeUnknown} />
      </Box>
    );
  }

  if (nodes.length === 0 && nodeDetail === null) {
    return <NodeDialogBodySkeleton />;
  }

  return (
    <Box sx={BODY_STYLE}>
      <Box
        sx={getNodeDetailsSidebarStyle(
          isConversationWide,
          dagSidebarCollapse.isOn,
          isEnteringFromDagPage,
        )}
      >
        <NodeDetailsSidebar
          dagName={dagName}
          nodes={nodes}
          currentNodeId={nodeId}
        />
      </Box>
      <NodeDetailColumns
        dagName={dagName}
        nodes={nodes}
        detail={nodeDetail}
        isConversationWide={isConversationWide}
        onToggleWidth={handleToggleWidth}
      />
    </Box>
  );
};
