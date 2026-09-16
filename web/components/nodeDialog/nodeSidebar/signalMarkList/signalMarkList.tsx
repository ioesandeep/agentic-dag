import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import { DetailRow } from '@/components/nodeDialog/nodeSidebar/detailRow/detailRow';
import { listSignalMarks } from '@/components/nodeDialog/nodeSidebar/signalMarkList/utils';
import type { NodeWorktree } from '@/entities/nodeDetail';
import { LABELS, SIGNAL_LABELS } from '@/labels/en';

interface SignalMarkListProps {
  // The node's worktree, or null when none was cut.
  worktree: NodeWorktree | null;
}

/**
 * Renders a row for each delivery signal with the mark it has reached.
 */
export const SignalMarkList = ({ worktree }: SignalMarkListProps) => {
  const signalMarks = listSignalMarks(worktree);

  if (signalMarks.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        {LABELS.signalMarksEmpty}
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {signalMarks.map((signalMark) => (
        <DetailRow
          key={signalMark.signal}
          label={SIGNAL_LABELS[signalMark.signal]}
        >
          <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>
            {signalMark.mark}
          </Typography>
        </DetailRow>
      ))}
    </Box>
  );
};
