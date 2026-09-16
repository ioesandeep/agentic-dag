import type { SessionEndState } from '@/entities/nodeDetail';
import { LABELS, SESSION_END_STATE_LABELS } from '@/labels/en';

/**
 * Returns the label for how a session ended, or the running label.
 */
export const endStateText = (endState: SessionEndState | ''): string => {
  if (endState === '') {
    return LABELS.sessionRunning;
  }

  return SESSION_END_STATE_LABELS[endState];
};
