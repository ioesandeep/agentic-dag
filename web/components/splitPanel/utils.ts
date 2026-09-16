import type { SxProps, Theme } from '@mui/material/styles';
import type { ReactNode } from 'react';

import {
  EMPTY_PERCENT,
  FULL_PERCENT,
} from '@/components/splitPanel/constants';
import type { SplitPanelRow } from '@/components/splitPanel/types';

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

/**
 * Returns the style of one panel.
 */
export const getPanelStyle = (percent: number): SxProps<Theme> => ({
  display: getPanelDisplay(percent),
  flexDirection: 'column',
  flexBasis: `${percent}%`,
  minHeight: 0,
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
 * Returns each panel with the share of the height it holds.
 */
export const getSplitPanelRows = (
  panels: ReactNode[],
  split: number[],
): SplitPanelRow[] =>
  panels.map((panel, index) => ({
    panel,
    percent: split[index] ?? EMPTY_PERCENT,
    hasHandle: index < panels.length - 1,
  }));
