'use client';

import Box from '@mui/material/Box';
import LinearProgress from '@mui/material/LinearProgress';
import List from '@mui/material/List';

import { RecoverySessionRow } from '@/components/dagPanel/dagTabs/recoverySessionList/recoverySessionRow/recoverySessionRow';
import { EmptyState } from '@/components/emptyState/emptyState';
import { RequestFailureAlert } from '@/components/requestFailureAlert/requestFailureAlert';
import type { RecoverySession } from '@/entities/recoverySession';
import {
  hasNoResponseToShow,
  usePolledApiResponse,
} from '@/hooks/usePolledApiResponse';
import { LABELS } from '@/labels/en';
import { getRecoverySessionsPath } from '@/utils/apiPath';

interface RecoverySessionListProps {
  dagName: string;
}

/**
 * Renders the Recovery tab of the DagTabs.
 */
export const RecoverySessionList = ({ dagName }: RecoverySessionListProps) => {
  const recoverySessionsPath = getRecoverySessionsPath(dagName);
  const recoverySessionsResponse =
    usePolledApiResponse<RecoverySession[]>(recoverySessionsPath);
  const recoverySessions = recoverySessionsResponse.response;
  const hasNoRecoverySessionsResponse = hasNoResponseToShow(
    recoverySessionsResponse,
  );

  if (hasNoRecoverySessionsResponse) {
    return (
      <EmptyState
        title={LABELS.apiRequestFailedTitle}
        body={LABELS.apiRequestFailedHint}
      />
    );
  }

  if (recoverySessions === null) {
    return (
      <Box role="status" aria-label={LABELS.dagRecoveryLoading}>
        <LinearProgress />
      </Box>
    );
  }

  if (recoverySessions.length === 0) {
    return (
      <>
        <RequestFailureAlert hasFailed={recoverySessionsResponse.hasFailed} />
        <EmptyState
          title={LABELS.dagRecoveryEmpty}
          body={LABELS.dagRecoveryEmptyHint}
        />
      </>
    );
  }

  return (
    <>
      <RequestFailureAlert hasFailed={recoverySessionsResponse.hasFailed} />
      <List dense disablePadding>
        {recoverySessions.map((recoverySession) => (
          <RecoverySessionRow
            key={recoverySession.id}
            dagName={dagName}
            recoverySession={recoverySession}
          />
        ))}
      </List>
    </>
  );
};
