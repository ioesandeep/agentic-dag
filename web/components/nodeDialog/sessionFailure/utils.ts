import type { NodeRecovery } from '@/entities/nodeDetail';

const CLEAN_EXIT_CODE = 0;

/**
 * Returns true when the exit code is recorded and nonzero.
 */
export const isFailedExitCode = (exitCode: number | null): exitCode is number =>
  exitCode !== null && exitCode !== CLEAN_EXIT_CODE;

/**
 * Returns whether an exit code is nonzero or a node recovery exists.
 */
export const hasSessionFailure = (
  exitCode: number | null,
  nodeRecovery: NodeRecovery | null,
): boolean => {
  if (nodeRecovery !== null) {
    return true;
  }

  return isFailedExitCode(exitCode);
};
