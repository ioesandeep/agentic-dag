import { SoftChip } from '@/components/softChip/softChip';
import type { SoftChipLink } from '@/components/softChip/types';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

import { PULL_REQUEST_CHIP_COLOR } from './constants';

interface PullRequestChipProps {
  // The pull request number, 0 when the node has none.
  prNumber: number;
  // The pull request url, empty when the node has none.
  prUrl: string;
}

/**
 * Renders the pull request number of a node.
 */
export const PullRequestChip = ({ prNumber, prUrl }: PullRequestChipProps) => {
  if (prNumber === 0) {
    return null;
  }

  const numberValues = { number: prNumber };
  const label = formatLabel(LABELS.worktreePullRequestNumber, numberValues);

  if (prUrl === '') {
    return <SoftChip color={PULL_REQUEST_CHIP_COLOR} label={label} />;
  }

  const pullRequestLink: SoftChipLink = {
    url: prUrl,
    ariaLabel: formatLabel(LABELS.nodePullRequestOpen, numberValues),
  };

  return (
    <SoftChip
      color={PULL_REQUEST_CHIP_COLOR}
      label={label}
      link={pullRequestLink}
    />
  );
};
