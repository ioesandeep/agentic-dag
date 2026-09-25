import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import Typography from '@mui/material/Typography';
import Link from 'next/link';

import {
  getAriaCurrent,
  getCardBorderColor,
} from '@/components/dagList/dagCard/utils';
import { nodePath } from '@/components/nodeDialog/utils';
import { NodeStateChip } from '@/components/nodeStateChip/nodeStateChip';
import { PullRequestChip } from '@/components/pullRequestChip/pullRequestChip';
import type { NodeLink } from '@/entities/nodeDetail';

const BORDER_TRANSITION = 'border-color 200ms ease';
const HOVER_BORDER_COLOR = 'primary.main';

const ACTION_STYLE = {
  position: 'static',
  '&::after': { content: '""', position: 'absolute', inset: 0 },
};

const BODY_STYLE = {
  p: 1.25,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'flex-start',
  gap: 0.75,
};

const CHIP_ROW_STYLE = { display: 'flex', alignItems: 'center', gap: 0.75 };

interface NodeDetailsSidebarCardProps {
  dagName: string;
  node: NodeLink;
  isCurrent: boolean;
}

/**
 * Renders a node's card in the node details sidebar.
 */
export const NodeDetailsSidebarCard = ({
  dagName,
  node,
  isCurrent,
}: NodeDetailsSidebarCardProps) => (
  <Card
    sx={{
      position: 'relative',
      transition: BORDER_TRANSITION,
      borderColor: getCardBorderColor(isCurrent),
      '&:hover': { borderColor: HOVER_BORDER_COLOR },
    }}
  >
    <Box sx={BODY_STYLE}>
      <CardActionArea
        component={Link}
        href={nodePath(dagName, node.id)}
        aria-current={getAriaCurrent(isCurrent)}
        sx={ACTION_STYLE}
      >
        <Typography variant="body2" sx={{ fontWeight: 500 }}>
          {node.title}
        </Typography>
      </CardActionArea>
      <Box sx={CHIP_ROW_STYLE}>
        <NodeStateChip state={node.state} />
        <PullRequestChip prNumber={node.prNumber} prUrl={node.prUrl} />
      </Box>
    </Box>
  </Card>
);
