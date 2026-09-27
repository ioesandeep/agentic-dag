import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Typography from '@mui/material/Typography';

import { INFO_MAIN_COLOR } from '@/components/nodeDialog/constants';
import { NodeActionByState } from '@/components/nodeDialog/nodeStatus/nodeActionByState/nodeActionByState';
import { NodeUpdatedTime } from '@/components/nodeDialog/nodeStatus/nodeUpdatedTime/nodeUpdatedTime';
import { PullRequestLink } from '@/components/nodeDialog/nodeStatus/pullRequestLink/pullRequestLink';
import { NodeStateChip } from '@/components/nodeStateChip/nodeStateChip';
import { SoftChip } from '@/components/softChip/softChip';
import type { NodeDetail } from '@/entities/nodeDetail';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

interface NodeStatusProps {
  dagName: string;
  detail: NodeDetail;
  onNodeActionSuccess: () => void;
}

/**
 * Renders the node's state, agent, wake count, pull request link, last update, and the actions its state allows.
 */
export const NodeStatus = ({
  dagName,
  detail,
  onNodeActionSuccess,
}: NodeStatusProps) => {
  const wakeValues = { wakes: detail.wakes };

  return (
    <Card
      sx={{
        p: 2,
        flexShrink: 0,
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: 1.5,
      }}
    >
      <NodeStateChip state={detail.state} />
      <Typography variant="body1" sx={{ fontWeight: 500 }}>
        {detail.agentName}
      </Typography>
      <SoftChip
        color={INFO_MAIN_COLOR}
        label={formatLabel(LABELS.nodeWakes, wakeValues)}
      />
      <Box sx={{ flexGrow: 1 }} />
      <PullRequestLink url={detail.prUrl} />
      <NodeUpdatedTime at={detail.updatedAt} />
      <NodeActionByState
        dagName={dagName}
        nodeId={detail.id}
        state={detail.state}
        onNodeActionSuccess={onNodeActionSuccess}
      />
    </Card>
  );
};
