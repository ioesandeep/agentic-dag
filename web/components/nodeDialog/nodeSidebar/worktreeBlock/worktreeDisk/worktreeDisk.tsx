import Typography from '@mui/material/Typography';

import { RelativeTime } from '@/components/relativeTime/relativeTime';
import { LABELS } from '@/labels/en';

interface WorktreeDiskProps {
  // When the disk was reclaimed, or null while the copy is still there.
  reclaimedAt: string | null;
}

/**
 * Renders when the worktree was reclaimed, or that it is still on disk.
 */
export const WorktreeDisk = ({ reclaimedAt }: WorktreeDiskProps) => {
  if (reclaimedAt === null) {
    return (
      <Typography variant="body2" color="text.secondary">
        {LABELS.worktreeOnDisk}
      </Typography>
    );
  }

  return (
    <RelativeTime at={reclaimedAt} template={LABELS.worktreeReclaimedAt} />
  );
};
