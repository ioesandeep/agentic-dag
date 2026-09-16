import Box from '@mui/material/Box';

import {
  INFO_MAIN_COLOR,
  PRIMARY_MAIN_COLOR,
} from '@/components/dagList/dagCard/constants';
import { LastActivity } from '@/components/dagList/dagCard/lastActivity/lastActivity';
import { SoftChip } from '@/components/softChip/softChip';
import type { DagSummary } from '@/entities/dagSummary';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

interface DagCardFooterProps {
  dag: DagSummary;
}

/**
 * Renders the footer section of the DagCard.
 */
export const DagCardFooter = ({ dag }: DagCardFooterProps) => {
  const nodeCountValues = { count: dag.nodeCount };

  return (
    <Box
      sx={{
        px: 2.5,
        py: 1.5,
        display: 'flex',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 1,
        borderTop: 1,
        borderColor: 'divider',
      }}
    >
      <SoftChip
        color={INFO_MAIN_COLOR}
        label={formatLabel(LABELS.dagNodeCount, nodeCountValues)}
      />
      <SoftChip mono color={PRIMARY_MAIN_COLOR} label={dag.baseBranch} />
      <Box sx={{ flexGrow: 1 }} />
      <LastActivity at={dag.lastActivityAt} />
    </Box>
  );
};
