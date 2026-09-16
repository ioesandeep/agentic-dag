'use client';

import Box from '@mui/material/Box';
import { notFound } from 'next/navigation';
import type { ReactNode } from 'react';

import { EmptyState } from '@/components/emptyState/emptyState';
import { DagContext } from '@/contexts/dagContext';
import type { DagDetail } from '@/entities/dagDetail';
import type { DagSummary } from '@/entities/dagSummary';
import {
  hasNoResponseToShow,
  usePolledApiResponse,
} from '@/hooks/usePolledApiResponse';
import { LABELS } from '@/labels/en';
import { DAGS_PATH, getDagPath } from '@/utils/apiPath';

const FAILURE_STYLE = { p: { xs: 2, md: 4 } };

interface DagProviderProps {
  dagName: string;
  // The page of the route under this dag.
  children: ReactNode;
}

/**
 * Polls a dag for every page of its route and publishes what they respond with.
 */
export const DagProvider = ({ dagName, children }: DagProviderProps) => {
  const dagPath = getDagPath(dagName);
  const dagSummariesResponse = usePolledApiResponse<DagSummary[]>(DAGS_PATH);
  const dagDetailResponse = usePolledApiResponse<DagDetail>(dagPath);

  if (dagDetailResponse.isMissing) {
    notFound();
  }

  const hasNoDagSummariesResponse = hasNoResponseToShow(dagSummariesResponse);
  const hasNoDagDetailResponse = hasNoResponseToShow(dagDetailResponse);
  const hasNothingToShow = hasNoDagSummariesResponse && hasNoDagDetailResponse;

  if (hasNothingToShow) {
    return (
      <Box sx={FAILURE_STYLE}>
        <EmptyState
          title={LABELS.apiRequestFailedTitle}
          body={LABELS.apiRequestFailedHint}
        />
      </Box>
    );
  }

  const dagValue = {
    dagSummaries: dagSummariesResponse.response,
    dagDetail: dagDetailResponse.response,
    hasFailed: dagSummariesResponse.hasFailed || dagDetailResponse.hasFailed,
  };

  return <DagContext value={dagValue}>{children}</DagContext>;
};
