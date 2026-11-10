import type { SxProps, Theme } from '@mui/material/styles';
import type { ReactNode } from 'react';

import { EMPTY_PERCENT, FULL_PERCENT } from './constants';
import { SplitPanelDirectionEnum } from './types';
import type { SplitPanelRow } from './types';

const COLLAPSED_PANEL_DISPLAY = 'none';
const OPEN_PANEL_DISPLAY = 'flex';

const getPanelDisplay = (percent: number): string => {
  if (percent === EMPTY_PERCENT) {
    return COLLAPSED_PANEL_DISPLAY;
  }

  return OPEN_PANEL_DISPLAY;
};

const getClampedPercent = (percent: number, total: number): number => {
  if (percent < EMPTY_PERCENT) {
    return EMPTY_PERCENT;
  }

  if (percent > total) {
    return total;
  }

  return percent;
};

const getVisiblePercent = (
  split: number[],
  index: number,
  expandedPanel: number | null,
): number => {
  if (expandedPanel === null) {
    return split[index] ?? EMPTY_PERCENT;
  }

  return index === expandedPanel ? FULL_PERCENT : EMPTY_PERCENT;
};

/**
 * Returns the container dimension along the layout axis.
 */
export const getContainerSize = (
  container: HTMLElement,
  direction: SplitPanelDirectionEnum,
): number => {
  if (direction === SplitPanelDirectionEnum.ROW) {
    return container.clientWidth;
  }

  return container.clientHeight;
};

/**
 * Returns the style of one panel.
 */
export const getPanelStyle = (percent: number): SxProps<Theme> => ({
  display: getPanelDisplay(percent),
  flexDirection: 'column',
  flexBasis: `${percent}%`,
  minHeight: 0,
  minWidth: 0,
});

/**
 * Returns the percent each panel starts with, equal shares where none is given.
 */
export const getInitialSplit = (
  panelCount: number,
  initialSplit?: number[],
): number[] => {
  if (initialSplit !== undefined) {
    return initialSplit;
  }

  const equalPercent = FULL_PERCENT / panelCount;

  return Array.from({ length: panelCount }, () => equalPercent);
};

/**
 * Returns the split after a handle moves, resizing the two panels beside it.
 */
export const getResizedSplit = (
  split: number[],
  index: number,
  movedPercent: number,
): number[] => {
  const abovePercent = split[index] ?? EMPTY_PERCENT;
  const belowPercent = split[index + 1] ?? EMPTY_PERCENT;
  const totalPercent = abovePercent + belowPercent;
  const nextAbovePercent = getClampedPercent(
    abovePercent + movedPercent,
    totalPercent,
  );

  return split.map((percent, position) => {
    if (position === index) {
      return nextAbovePercent;
    }

    if (position === index + 1) {
      return totalPercent - nextAbovePercent;
    }

    return percent;
  });
};

/**
 * Returns the visible panel sizes and resize handles.
 */
export const getSplitPanelRows = (
  panels: ReactNode[],
  split: number[],
  expandedPanel: number | null = null,
): SplitPanelRow[] =>
  panels.map((panel, index) => ({
    panel,
    percent: getVisiblePercent(split, index, expandedPanel),
    hasHandle: expandedPanel === null && index < panels.length - 1,
  }));
