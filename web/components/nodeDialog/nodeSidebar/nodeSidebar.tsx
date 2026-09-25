import Box from '@mui/material/Box';

import { DependencyList } from '@/components/nodeDialog/nodeSidebar/dependencyList/dependencyList';
import { InstructionsText } from '@/components/nodeDialog/nodeSidebar/instructionsText/instructionsText';
import { NodeSidebarCard } from '@/components/nodeDialog/nodeSidebar/nodeSidebarCard/nodeSidebarCard';
import { SessionTable } from '@/components/nodeDialog/nodeSidebar/sessionTable/sessionTable';
import { SignalMarkList } from '@/components/nodeDialog/nodeSidebar/signalMarkList/signalMarkList';
import { SlackNotificationList } from '@/components/nodeDialog/nodeSidebar/slackNotificationList/slackNotificationList';
import { WorktreeBlock } from '@/components/nodeDialog/nodeSidebar/worktreeBlock/worktreeBlock';
import { getNodeSidebarStyle } from '@/components/nodeDialog/nodeSidebar/utils';
import { listNodeLinksByIds } from '@/components/nodeDialog/utils';
import type { NodeDetail, NodeLink } from '@/entities/nodeDetail';
import { LABELS } from '@/labels/en';

interface NodeSidebarProps {
  dagName: string;
  // Every node of the dag.
  nodes: NodeLink[];
  detail: NodeDetail;
  // The timestamp of the oldest loaded message, or null when every message of the transcript is loaded.
  loadedSince: string | null;
  // True while the conversation takes the whole width.
  isHidden: boolean;
}

/**
 * Renders the sidebar cards for one node.
 */
export const NodeSidebar = ({
  dagName,
  nodes,
  detail,
  loadedSince,
  isHidden,
}: NodeSidebarProps) => {
  const dependsOnNodes = listNodeLinksByIds(detail.dependsOn, nodes);
  const blockedNodes = listNodeLinksByIds(detail.blocks, nodes);

  return (
    <Box inert={isHidden} sx={getNodeSidebarStyle(isHidden)}>
      <NodeSidebarCard title={LABELS.dependsOnHeading}>
        <DependencyList dagName={dagName} nodes={dependsOnNodes} />
      </NodeSidebarCard>
      <NodeSidebarCard title={LABELS.blocksHeading}>
        <DependencyList dagName={dagName} nodes={blockedNodes} />
      </NodeSidebarCard>
      <NodeSidebarCard title={LABELS.worktreeHeading}>
        <WorktreeBlock worktree={detail.worktree} />
      </NodeSidebarCard>
      <NodeSidebarCard title={LABELS.signalMarksHeading}>
        <SignalMarkList worktree={detail.worktree} />
      </NodeSidebarCard>
      <NodeSidebarCard title={LABELS.slackNotificationsHeading}>
        <SlackNotificationList
          slackNotifications={detail.slackNotifications}
        />
      </NodeSidebarCard>
      <NodeSidebarCard title={LABELS.sessionsHeading}>
        <SessionTable
          sessions={detail.sessions}
          loadedSince={loadedSince}
        />
      </NodeSidebarCard>
      <NodeSidebarCard title={LABELS.instructionsHeading}>
        <InstructionsText instructions={detail.instructions} />
      </NodeSidebarCard>
    </Box>
  );
};
