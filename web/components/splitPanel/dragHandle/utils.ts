import type { SxProps, Theme } from '@mui/material/styles';
import type { AriaAttributes, PointerEvent as ReactPointerEvent } from 'react';

import { SplitPanelDirectionEnum } from '@/components/splitPanel/types';

import {
  GROW_KEY,
  GROW_ROW_KEY,
  KEY_DRAG_PIXELS,
  NO_DRAG_PIXELS,
  SHRINK_KEY,
  SHRINK_ROW_KEY,
} from './constants';

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
export const getKeyDragPixels = (
  key: string,
  direction: SplitPanelDirectionEnum,
): number => {
  const isRow = direction === SplitPanelDirectionEnum.ROW;
  const shrinkKey = isRow ? SHRINK_ROW_KEY : SHRINK_KEY;
  const growKey = isRow ? GROW_ROW_KEY : GROW_KEY;

  if (key === shrinkKey) {
    return -KEY_DRAG_PIXELS;
  }

  if (key === growKey) {
    return KEY_DRAG_PIXELS;
  }

  return NO_DRAG_PIXELS;
};

/**
 * Returns the style of the drag handle.
 */
export const getDragHandleStyle = (
  isDragging: boolean,
  direction: SplitPanelDirectionEnum,
): SxProps<Theme> => ({
  flexShrink: 0,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor:
    direction === SplitPanelDirectionEnum.ROW ? 'col-resize' : 'row-resize',
  touchAction: 'none',
  color: getHandleColor(isDragging),
  '&:hover': { color: ACTIVE_HANDLE_COLOR },
  '&:focus-visible': { color: ACTIVE_HANDLE_COLOR },
});

/**
 * Returns the resize icon's style for the layout axis.
 */
export const getDragHandleIconStyle = (
  direction: SplitPanelDirectionEnum,
): SxProps<Theme> => ({
  transform:
    direction === SplitPanelDirectionEnum.ROW ? 'rotate(90deg)' : 'none',
});

/**
 * Returns the separator orientation for the layout axis.
 */
export const getDragHandleOrientation = (
  direction: SplitPanelDirectionEnum,
): AriaAttributes['aria-orientation'] =>
  direction === SplitPanelDirectionEnum.ROW ? 'vertical' : 'horizontal';

/**
 * Returns the pointer coordinate along the layout axis.
 */
export const getPointerPosition = (
  pointerEvent: PointerEvent | ReactPointerEvent<HTMLDivElement>,
  direction: SplitPanelDirectionEnum,
): number => {
  if (direction === SplitPanelDirectionEnum.ROW) {
    return pointerEvent.clientX;
  }

  return pointerEvent.clientY;
};
