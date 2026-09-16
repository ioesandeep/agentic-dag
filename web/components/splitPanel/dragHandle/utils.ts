import type { SxProps, Theme } from '@mui/material/styles';

import {
  GROW_KEY,
  KEY_DRAG_PIXELS,
  NO_DRAG_PIXELS,
  SHRINK_KEY,
} from '@/components/splitPanel/dragHandle/constants';

const RESTING_HANDLE_COLOR = 'text.disabled';
const ACTIVE_HANDLE_COLOR = 'primary.main';

const getHandleColor = (isDragging: boolean): string => {
  if (isDragging) {
    return ACTIVE_HANDLE_COLOR;
  }

  return RESTING_HANDLE_COLOR;
};

/**
 * Returns the pixels a pressed key drags the handle by.
 */
export const getKeyDragPixels = (key: string): number => {
  if (key === SHRINK_KEY) {
    return -KEY_DRAG_PIXELS;
  }

  if (key === GROW_KEY) {
    return KEY_DRAG_PIXELS;
  }

  return NO_DRAG_PIXELS;
};

/**
 * Returns the style of the drag handle.
 */
export const getDragHandleStyle = (isDragging: boolean): SxProps<Theme> => ({
  flexShrink: 0,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'row-resize',
  touchAction: 'none',
  color: getHandleColor(isDragging),
  '&:hover': { color: ACTIVE_HANDLE_COLOR },
  '&:focus-visible': { color: ACTIVE_HANDLE_COLOR },
});
