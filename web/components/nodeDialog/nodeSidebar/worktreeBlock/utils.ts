import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

/**
 * Returns the pull request number as text, or the none label when there is none.
 */
export const pullRequestText = (prNumber: number): string => {
  if (prNumber === 0) {
    return LABELS.worktreeNoPullRequest;
  }

  const numberValues = { number: prNumber };

  return formatLabel(LABELS.worktreePullRequestNumber, numberValues);
};
