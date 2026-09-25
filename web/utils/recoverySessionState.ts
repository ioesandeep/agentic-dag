import type { RecoverySession } from '@/entities/recoverySession';

/**
 * The states the Recovery tab shows a recovery session in.
 */
export enum RecoverySessionState {
  RUNNING = 'running',
  ENDED = 'ended',
  ENDED_WITHOUT_CLOSE = 'endedWithoutClose',
}

const INFO_MAIN_COLOR = 'var(--mui-palette-info-main)';
const SECONDARY_TEXT_COLOR = 'var(--mui-palette-text-secondary)';
const WARNING_MAIN_COLOR = 'var(--mui-palette-warning-main)';

// The colour of each recovery session state's chip.
const RECOVERY_SESSION_STATE_COLORS: Record<RecoverySessionState, string> = {
  [RecoverySessionState.RUNNING]: INFO_MAIN_COLOR,
  [RecoverySessionState.ENDED]: SECONDARY_TEXT_COLOR,
  [RecoverySessionState.ENDED_WITHOUT_CLOSE]: WARNING_MAIN_COLOR,
};

/**
 * Returns the state of a recovery session.
 */
export const getRecoverySessionState = (
  recoverySession: RecoverySession,
): RecoverySessionState => {
  if (recoverySession.endedAt !== null) {
    return RecoverySessionState.ENDED;
  }

  if (recoverySession.isProcessAlive) {
    return RecoverySessionState.RUNNING;
  }

  return RecoverySessionState.ENDED_WITHOUT_CLOSE;
};

/**
 * Returns the theme colour of a recovery session state.
 */
export const getRecoverySessionStateColor = (
  recoverySessionState: RecoverySessionState,
): string => RECOVERY_SESSION_STATE_COLORS[recoverySessionState];
