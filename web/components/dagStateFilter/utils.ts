import type { SxProps, Theme } from '@mui/material/styles';

import type { DagState } from '@/utils/dagState';
import { getDagStateColor } from '@/utils/dagState';

const BUTTON_PADDING_X = 1.25;
const BUTTON_PADDING_Y = 0.25;
const BORDER_MIX_PERCENT = 40;

const getSoftColor = (color: string, mixPercent: number): string =>
  `color-mix(in srgb, ${color} ${mixPercent}%, transparent)`;

/**
 * Returns the style of the filter button for a dag state.
 */
export const getDagStateButtonStyle = (dagState: DagState): SxProps<Theme> => {
  const color = getDagStateColor(dagState);

  return {
    px: BUTTON_PADDING_X,
    py: BUTTON_PADDING_Y,
    color,
    borderColor: getSoftColor(color, BORDER_MIX_PERCENT),
    '&:hover': { bgcolor: 'transparent', borderColor: color },
    '&.Mui-selected': {
      color: 'background.default',
      bgcolor: color,
      borderColor: color,
      '&:hover': { bgcolor: color },
    },
  };
};
