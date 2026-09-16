import {
  CURRENT_BORDER_COLOR,
  CURRENT_PAGE,
  RESTING_BORDER_COLOR,
} from '@/components/dagList/dagCard/constants';
import type { NodeState } from '@/entities/nodeState';
import { LABELS } from '@/labels/en';
import { getStateColor } from '@/utils/getStateColor';

/**
 * Returns the colour for a dag flag icon.
 */
export const getFlagIconColor = (isOn: boolean): string => {
  if (isOn) {
    return 'text.secondary';
  }

  return 'divider';
};

/**
 * Returns the tooltip text for a dag's schedule flag.
 */
export const getScheduleTooltip = (isScheduled: boolean): string => {
  if (isScheduled) {
    return LABELS.dagScheduledOn;
  }

  return LABELS.dagScheduledOff;
};

/**
 * Returns the tooltip text for a dag's watcher flag.
 */
export const getWatchTooltip = (isWatching: boolean): string => {
  if (isWatching) {
    return LABELS.dagWatchingOn;
  }

  return LABELS.dagWatchingOff;
};

/**
 * Returns the aria-current value for a dag card.
 */
export const getAriaCurrent = (isCurrent: boolean): 'page' | undefined => {
  if (isCurrent) {
    return CURRENT_PAGE;
  }

  return undefined;
};

/**
 * Returns the border colour for a dag card.
 */
export const getCardBorderColor = (isCurrent: boolean): string => {
  if (isCurrent) {
    return CURRENT_BORDER_COLOR;
  }

  return RESTING_BORDER_COLOR;
};

/**
 * Returns the colour for a dag's latest state dot.
 */
export const getLatestStateColor = (
  state: NodeState | null,
): string | undefined => {
  if (state === null) {
    return undefined;
  }

  return getStateColor(state);
};
