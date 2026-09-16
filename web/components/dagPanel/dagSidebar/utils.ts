import type { SxProps, Theme } from '@mui/material/styles';

import { DagCardVariant } from '@/components/dagList/dagCard/types';
import {
  SIDEBAR_COLLAPSED_PADDING_X,
  SIDEBAR_COLLAPSED_WIDTH,
  SIDEBAR_EXPANDED_PADDING_X,
  SIDEBAR_EXPANDED_WIDTH,
} from '@/components/dagPanel/dagSidebar/constants';
import type { DagSummary } from '@/entities/dagSummary';
import { LABELS } from '@/labels/en';
import { SCREEN_ENTRANCE_MS } from '@/theme/constants';

const COLLAPSED_CHEVRON_ROTATION = 'rotate(180deg)';
const EXPANDED_CHEVRON_ROTATION = 'none';
const WIDTH_TRANSITION = 'width 200ms ease';
const ENTRANCE_ANIMATION = `dagSidebarEnter ${SCREEN_ENTRANCE_MS}ms ease-out`;
const NO_ENTRANCE_ANIMATION = 'none';
const NO_CURRENT_DAG_INDEX = -1;

const getSidebarEntranceAnimation = (isEntering: boolean): string => {
  if (isEntering) {
    return ENTRANCE_ANIMATION;
  }

  return NO_ENTRANCE_ANIMATION;
};

const getSidebarWidth = (isCollapsed: boolean): string | number => {
  if (isCollapsed) {
    return SIDEBAR_COLLAPSED_WIDTH;
  }

  return SIDEBAR_EXPANDED_WIDTH;
};

/**
 * Returns the position of the current dag in the sidebar list.
 */
export const findCurrentDagIndex = (
  dags: DagSummary[] | null,
  currentName: string,
): number => {
  if (dags === null) {
    return NO_CURRENT_DAG_INDEX;
  }

  return dags.findIndex((dag) => dag.name === currentName);
};

/**
 * Returns the horizontal padding for the sidebar list.
 */
export const getSidebarListPaddingX = (isCollapsed: boolean): number => {
  if (isCollapsed) {
    return SIDEBAR_COLLAPSED_PADDING_X;
  }

  return SIDEBAR_EXPANDED_PADDING_X;
};

/**
 * Returns the card variant for the sidebar.
 */
export const getSidebarCardVariant = (isCollapsed: boolean): DagCardVariant => {
  if (isCollapsed) {
    return DagCardVariant.MINIMAL;
  }

  return DagCardVariant.FLEXIBLE;
};

/**
 * Returns the label for the sidebar toggle button.
 */
export const getSidebarToggleLabel = (isCollapsed: boolean): string => {
  if (isCollapsed) {
    return LABELS.dagListExpand;
  }

  return LABELS.dagListCollapse;
};

/**
 * Returns the rotation for the sidebar toggle chevron.
 */
export const getSidebarChevronRotation = (isCollapsed: boolean): string => {
  if (isCollapsed) {
    return COLLAPSED_CHEVRON_ROTATION;
  }

  return EXPANDED_CHEVRON_ROTATION;
};

/**
 * Returns the style of the sidebar column.
 */
export const getSidebarStyle = (
  isCollapsed: boolean,
  isEntering: boolean,
): SxProps<Theme> => ({
  flexShrink: 0,
  borderRight: 1,
  borderColor: 'divider',
  width: { xs: 'auto', md: getSidebarWidth(isCollapsed) },
  transition: WIDTH_TRANSITION,
  animation: getSidebarEntranceAnimation(isEntering),
  '@media (prefers-reduced-motion: reduce)': {
    animation: NO_ENTRANCE_ANIMATION,
  },
});
