import type { SxProps, Theme } from '@mui/material/styles';

import {
  REDUCED_MOTION_SELECTOR,
  SIDEBAR_COLUMN_WIDTH,
} from '@/components/nodeDialog/constants';

const HIDDEN_COLUMN_GROW = 0;
const COLUMN_TRANSITION = 'flex-grow 200ms ease';

const getColumnGrow = (isHidden: boolean): number => {
  if (isHidden) {
    return HIDDEN_COLUMN_GROW;
  }

  return SIDEBAR_COLUMN_WIDTH;
};

const getColumnDisplay = (isHidden: boolean): Record<string, string> => {
  if (isHidden) {
    return { xs: 'none', md: 'flex' };
  }

  return { xs: 'flex', md: 'flex' };
};

/**
 * Returns the style of the node sidebar column.
 */
export const getNodeSidebarStyle = (isHidden: boolean): SxProps<Theme> => ({
  flexGrow: { md: getColumnGrow(isHidden) },
  flexBasis: { md: 0 },
  minWidth: 0,
  minHeight: { md: 0 },
  display: getColumnDisplay(isHidden),
  flexDirection: 'column',
  gap: 2,
  overflowX: 'hidden',
  overflowY: { md: 'auto' },
  transition: COLUMN_TRANSITION,
  [REDUCED_MOTION_SELECTOR]: { transition: 'none' },
  '& > *': { flexShrink: 0 },
});
