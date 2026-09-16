import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import { CodeBlock } from '@/components/codeBlock/codeBlock';
import { PRIMARY_MAIN_COLOR } from '@/components/nodeDialog/constants';
import { DetailRow } from '@/components/nodeDialog/nodeSidebar/detailRow/detailRow';
import { pullRequestText } from '@/components/nodeDialog/nodeSidebar/worktreeBlock/utils';
import { WorktreeDisk } from '@/components/nodeDialog/nodeSidebar/worktreeBlock/worktreeDisk/worktreeDisk';
import { RelativeTime } from '@/components/relativeTime/relativeTime';
import { SoftChip } from '@/components/softChip/softChip';
import type { NodeWorktree } from '@/entities/nodeDetail';
import { LABELS } from '@/labels/en';

interface WorktreeBlockProps {
  // The node's worktree, or null when none was cut.
  worktree: NodeWorktree | null;
}

/**
 * Renders the worktree's path, branch, pull request, cut time and disk state.
 */
export const WorktreeBlock = ({ worktree }: WorktreeBlockProps) => {
  if (worktree === null) {
    return (
      <Typography variant="body2" color="text.secondary">
        {LABELS.worktreeNone}
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      <DetailRow label={LABELS.worktreePath}>
        <CodeBlock text={worktree.absolutePath} />
      </DetailRow>
      <DetailRow label={LABELS.worktreeBranch}>
        <SoftChip mono color={PRIMARY_MAIN_COLOR} label={worktree.branch} />
      </DetailRow>
      <DetailRow label={LABELS.worktreePullRequest}>
        <Typography variant="body2">
          {pullRequestText(worktree.prNumber)}
        </Typography>
      </DetailRow>
      <DetailRow label={LABELS.worktreeCut}>
        <RelativeTime at={worktree.createdAt} />
      </DetailRow>
      <DetailRow label={LABELS.worktreeDisk}>
        <WorktreeDisk reclaimedAt={worktree.reclaimedAt} />
      </DetailRow>
    </Box>
  );
};
