import Box from '@mui/material/Box';
import Tooltip from '@mui/material/Tooltip';

import { LABELS, NODE_STATE_LABELS } from '@/labels/en';
import type { NodeStateCount } from '@/utils/dagNodes';
import { formatLabel } from '@/utils/formatLabel';
import { getStateColor } from '@/utils/getStateColor';

const SWEEP_COLOR = 'var(--mui-palette-common-white)';

const BAR_TRACK = {
  display: 'flex',
  height: 8,
  borderRadius: 999,
  overflow: 'hidden',
  bgcolor: 'action.hover',
};

const RUNNING_SEGMENT = {
  position: 'relative',
  overflow: 'hidden',
  '&::after': {
    content: '""',
    position: 'absolute',
    inset: 0,
    background: `linear-gradient(90deg, transparent, color-mix(in srgb, ${SWEEP_COLOR} 70%, transparent), transparent)`,
    animation: 'dagSweep 1.7s ease-in-out infinite',
  },
  '@media (prefers-reduced-motion: reduce)': {
    '&::after': { animation: 'none' },
  },
};

interface NodeStateBarProps {
  states: NodeStateCount[];
}

/**
 * Renders the node state counts as a bar.
 */
export const NodeStateBar = ({ states }: NodeStateBarProps) => {
  if (states.length === 0) {
    return (
      <Box sx={BAR_TRACK}>
        <Box sx={{ flexGrow: 1 }} />
      </Box>
    );
  }

  return (
    <Box sx={BAR_TRACK}>
      {states.map(({ state, count }) => {
        const segmentValues = { state: NODE_STATE_LABELS[state], count };

        return (
          <Tooltip
            key={state}
            title={formatLabel(LABELS.nodeStateCount, segmentValues)}
          >
            <Box
              sx={{
                flexGrow: count,
                transition: 'flex-grow 400ms ease',
                bgcolor: getStateColor(state),
                ...(state === 'in_progress' ? RUNNING_SEGMENT : {}),
              }}
            />
          </Tooltip>
        );
      })}
    </Box>
  );
};
