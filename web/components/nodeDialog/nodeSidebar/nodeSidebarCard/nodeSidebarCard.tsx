import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import type { ReactNode } from 'react';

import { DagCardHeader } from '@/components/dagList/dagCard/dagCardHeader/dagCardHeader';
import { NO_ACTIONS } from '@/components/nodeDialog/constants';
import { CARD_BODY_STYLE } from '@/components/nodeDialog/nodeSidebar/constants';

interface NodeSidebarCardProps {
  title: string;
  children: ReactNode;
}

/**
 * Renders a card of the node sidebar.
 */
export const NodeSidebarCard = ({ title, children }: NodeSidebarCardProps) => (
  <Card>
    <Box sx={CARD_BODY_STYLE}>
      <DagCardHeader title={title} actions={NO_ACTIONS} />
      {children}
    </Box>
  </Card>
);
