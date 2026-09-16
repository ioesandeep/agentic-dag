import Typography from '@mui/material/Typography';
import { Fragment } from 'react';

import { ERROR_MAIN_COLOR } from '@/components/nodeDialog/constants';
import { RelativeTime } from '@/components/relativeTime/relativeTime';
import { SoftChip } from '@/components/softChip/softChip';
import type { NodeRecovery } from '@/entities/nodeDetail';
import { LABELS, RECOVERY_CAUSE_LABELS } from '@/labels/en';

interface RecoveryStateProps {
  // The newest recorded failure of the node, null when it has none.
  nodeRecovery: NodeRecovery | null;
}

/**
 * Renders a node's retry time or unrecoverable recovery cause.
 */
export const RecoveryState = ({ nodeRecovery }: RecoveryStateProps) => {
  if (nodeRecovery === null) {
    return null;
  }

  if (nodeRecovery.recoverable) {
    return (
      <RelativeTime
        at={nodeRecovery.recoverAt}
        template={LABELS.recoveryRetryAt}
      />
    );
  }

  return (
    <Fragment>
      <SoftChip color={ERROR_MAIN_COLOR} label={LABELS.recoveryUnrecoverable} />
      <Typography variant="body2" color="text.secondary">
        {RECOVERY_CAUSE_LABELS[nodeRecovery.cause]}
      </Typography>
    </Fragment>
  );
};
