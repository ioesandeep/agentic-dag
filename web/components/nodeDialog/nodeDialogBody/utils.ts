import type { SxProps, Theme } from '@mui/material/styles';

import { REDUCED_MOTION_SELECTOR } from '@/components/nodeDialog/constants';
import { COLUMNS_STYLE } from '@/components/nodeDialog/nodeDialogBody/constants';

const COLUMNS_GAP = 2;
const CLOSED_COLUMNS_GAP = 0;
const COLUMNS_TRANSITION = 'gap 200ms ease';

const getColumnsGap = (isSidebarHidden: boolean): number => {
  if (isSidebarHidden) {
    return CLOSED_COLUMNS_GAP;
  }

  return COLUMNS_GAP;
};

/**
 * Returns the style of the row that holds a node's columns.
 */
export const getColumnsStyle = (isSidebarHidden: boolean): SxProps<Theme> => ({
  ...COLUMNS_STYLE,
  gap: getColumnsGap(isSidebarHidden),
  transition: COLUMNS_TRANSITION,
  [REDUCED_MOTION_SELECTOR]: { transition: 'none' },
});
