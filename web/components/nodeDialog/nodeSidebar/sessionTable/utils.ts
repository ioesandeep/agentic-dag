import type { SessionEndState } from '@/entities/nodeDetail';
import { LABELS, SESSION_END_STATE_LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

const NO_TOOLTIP = '';

/**
 * Returns the label for how a session ended, or the running label.
 */
export const endStateText = (endState: SessionEndState | ''): string => {
  if (endState === '') {
    return LABELS.sessionRunning;
  }

  return SESSION_END_STATE_LABELS[endState];
};

/**
 * Returns the tooltip for scrolling the conversation to a session, or an empty string when the session start is loaded.
 */
export const getScrollToSessionTooltip = (
  isStartLoaded: boolean,
  wake: number,
): string => {
  if (isStartLoaded) {
    return NO_TOOLTIP;
  }

  const wakeValues = { wake };

  return formatLabel(LABELS.sessionStartNotLoaded, wakeValues);
};
