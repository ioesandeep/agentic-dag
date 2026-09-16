'use client';

import Box from '@mui/material/Box';

import { DagList } from '@/components/dagList/dagList';
import { EmptyState } from '@/components/emptyState/emptyState';
import { RequestFailureAlert } from '@/components/requestFailureAlert/requestFailureAlert';
import type { DagSummary } from '@/entities/dagSummary';
import {
  hasNoResponseToShow,
  usePolledApiResponse,
} from '@/hooks/usePolledApiResponse';
import { useStoredDagState } from '@/hooks/useStoredDagState';
import { LABELS } from '@/labels/en';
import { DAGS_PATH } from '@/utils/apiPath';
import { getDagsInState } from '@/utils/dagState';
import { isNull } from '@/utils/typeGuards';

const SCREEN_STYLE = { display: 'flex', flexDirection: 'column', gap: 2 };

/**
 * Renders the dag listing.
 */
export const DagsScreen = () => {
  const dagSummariesResponse = usePolledApiResponse<DagSummary[]>(DAGS_PATH);
  const dagFilter = useStoredDagState();
  const hasNoDagSummaries = hasNoResponseToShow(dagSummariesResponse);

  if (hasNoDagSummaries) {
    return (
      <EmptyState
        title={LABELS.apiRequestFailedTitle}
        body={LABELS.apiRequestFailedHint}
      />
    );
  }

  const dagSummaries = dagSummariesResponse.response;
  const visibleDags = getDagsInState(dagSummaries, dagFilter.dagState);
  const hasDagSummaries = !isNull(dagSummaries) && dagSummaries.length > 0;
  const hasNoDagsInState = hasDagSummaries && visibleDags?.length === 0;

  if (hasNoDagsInState) {
    return (
      <Box sx={SCREEN_STYLE}>
        <RequestFailureAlert hasFailed={dagSummariesResponse.hasFailed} />
        <EmptyState
          title={LABELS.dagsFilteredEmpty}
          body={LABELS.dagsFilteredEmptyHint}
        />
      </Box>
    );
  }

  return (
    <Box sx={SCREEN_STYLE}>
      <RequestFailureAlert hasFailed={dagSummariesResponse.hasFailed} />
      <DagList dags={visibleDags} />
    </Box>
  );
};
