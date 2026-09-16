import Box from '@mui/material/Box';

import { SoftChip } from '@/components/softChip/softChip';
import { LABELS, NODE_STATE_LABELS_LOWERCASE } from '@/labels/en';
import type { NodeStateCount } from '@/utils/dagNodes';
import { formatLabel } from '@/utils/formatLabel';
import { getStateColor } from '@/utils/getStateColor';

interface NodeStateChipsProps {
  states: NodeStateCount[];
}

/**
 * Renders the node state counts as chips.
 */
export const NodeStateChips = ({ states }: NodeStateChipsProps) => (
  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
    {states.map(({ state, count }) => {
      const chipValues = { count, state: NODE_STATE_LABELS_LOWERCASE[state] };

      return (
        <SoftChip
          key={state}
          color={getStateColor(state)}
          label={formatLabel(LABELS.nodeStateCountLowercase, chipValues)}
        />
      );
    })}
  </Box>
);
