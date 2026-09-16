import Box from '@mui/material/Box';
import Card from '@mui/material/Card';

import { DagCardHeader } from '@/components/dagList/dagCard/dagCardHeader/dagCardHeader';
import { NO_ACTIONS } from '@/components/nodeDialog/constants';
import { ExitCodeChip } from '@/components/nodeDialog/sessionFailure/exitCodeChip/exitCodeChip';
import { LogTail } from '@/components/nodeDialog/sessionFailure/logTail/logTail';
import { RecoveryState } from '@/components/nodeDialog/sessionFailure/recoveryState/recoveryState';
import type { NodeRecovery } from '@/entities/nodeDetail';
import { LABELS } from '@/labels/en';

import { hasSessionFailure } from './utils';

const CARD_STYLE = {
  p: 2,
  flexShrink: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 1.5,
};

const SUMMARY_STYLE = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: 1.5,
};

interface SessionFailureProps {
  // The session exit code to display.
  exitCode: number | null;
  // The log tail to display.
  logTail: string | null;
  // The newest recorded failure of the node, null when it has none.
  nodeRecovery: NodeRecovery | null;
}

/**
 * Renders the exit code, the log tail and the recovery state of a failed node.
 */
export const SessionFailure = ({
  exitCode,
  logTail,
  nodeRecovery,
}: SessionFailureProps) => {
  const isFailed = hasSessionFailure(exitCode, nodeRecovery);

  if (!isFailed) {
    return null;
  }

  return (
    <Card sx={CARD_STYLE}>
      <DagCardHeader title={LABELS.sessionFailureHeading} actions={NO_ACTIONS} />
      <Box sx={SUMMARY_STYLE}>
        <ExitCodeChip exitCode={exitCode} />
        <RecoveryState nodeRecovery={nodeRecovery} />
      </Box>
      <LogTail logTail={logTail} />
    </Card>
  );
};
