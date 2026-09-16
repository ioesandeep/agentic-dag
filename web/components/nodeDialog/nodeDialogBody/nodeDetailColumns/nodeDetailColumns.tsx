'use client';

import Box from '@mui/material/Box';
import Slide from '@mui/material/Slide';

import { CONVERSATION_COLUMN_WIDTH } from '@/components/nodeDialog/constants';
import { Conversation } from '@/components/nodeDialog/conversation/conversation';
import { NodeDetailColumnsSkeleton } from '@/components/nodeDialog/nodeDialogBody/nodeDetailColumns/nodeDetailColumnsSkeleton/nodeDetailColumnsSkeleton';
import { getColumnsStyle } from '@/components/nodeDialog/nodeDialogBody/utils';
import { NodeSidebar } from '@/components/nodeDialog/nodeSidebar/nodeSidebar';
import { NodeStatus } from '@/components/nodeDialog/nodeStatus/nodeStatus';
import { SessionFailure } from '@/components/nodeDialog/sessionFailure/sessionFailure';
import type { NodeDetail, NodeLink } from '@/entities/nodeDetail';

const CONVERSATION_STYLE = {
  flexGrow: { md: CONVERSATION_COLUMN_WIDTH },
  flexBasis: { md: 0 },
  minWidth: 0,
  minHeight: { md: 0 },
  display: 'flex',
  flexDirection: 'column',
  gap: 2,
};

interface NodeDetailColumnsProps {
  dagName: string;
  // Every node of the dag.
  nodes: NodeLink[];
  // The node's record, null until the api sends it.
  detail: NodeDetail | null;
  isConversationWide: boolean;
  onToggleWidth: () => void;
}

/**
 * Renders the conversation column and the sidebar of a single node.
 */
export const NodeDetailColumns = ({
  dagName,
  nodes,
  detail,
  isConversationWide,
  onToggleWidth,
}: NodeDetailColumnsProps) => {
  if (detail === null) {
    return <NodeDetailColumnsSkeleton />;
  }

  return (
    <Slide direction="left" in appear>
      <Box sx={getColumnsStyle(isConversationWide)}>
        <Box sx={CONVERSATION_STYLE}>
          <NodeStatus detail={detail} />
          <SessionFailure
            exitCode={detail.exitCode}
            logTail={detail.logTail}
            nodeRecovery={detail.nodeRecovery}
          />
          <Conversation
            messages={detail.transcript}
            sessions={detail.sessions}
            isWide={isConversationWide}
            onToggleWidth={onToggleWidth}
          />
        </Box>
        <NodeSidebar
          dagName={dagName}
          nodes={nodes}
          detail={detail}
          isHidden={isConversationWide}
        />
      </Box>
    </Slide>
  );
};
