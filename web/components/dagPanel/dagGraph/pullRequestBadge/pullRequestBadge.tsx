import CallSplitOutlinedIcon from '@mui/icons-material/CallSplitOutlined';
import Tooltip from '@mui/material/Tooltip';

import { LABELS } from '@/labels/en';

interface PullRequestBadgeProps {
  prUrl: string;
}

/**
 * Renders the pull request marker on a DagGraph node.
 */
export const PullRequestBadge = ({ prUrl }: PullRequestBadgeProps) => {
  if (prUrl === '') {
    return null;
  }

  return (
    <Tooltip title={LABELS.nodePullRequest}>
      <CallSplitOutlinedIcon
        fontSize="small"
        titleAccess={LABELS.nodePullRequest}
        sx={{ color: 'info.main', flexShrink: 0 }}
      />
    </Tooltip>
  );
};
