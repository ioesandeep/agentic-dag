'use client';

import Box from '@mui/material/Box';
import LinearProgress from '@mui/material/LinearProgress';
import Typography from '@mui/material/Typography';

import { EmptyState } from '@/components/emptyState/emptyState';
import { MarkdownText } from '@/components/markdownText/markdownText';
import { RelativeTime } from '@/components/relativeTime/relativeTime';
import { RequestFailureAlert } from '@/components/requestFailureAlert/requestFailureAlert';
import type { Memory } from '@/entities/memory';
import {
  hasNoResponseToShow,
  usePolledApiResponse,
} from '@/hooks/usePolledApiResponse';
import { LABELS } from '@/labels/en';
import { getMemoryPath } from '@/utils/apiPath';

const MEMORY_STYLE = {
  display: 'flex',
  flexDirection: 'column',
  gap: 1,
  p: 2,
};

interface DagMemoryProps {
  dagName: string;
}

/**
 * Renders the Memory tab of the DagTabs.
 */
export const DagMemory = ({ dagName }: DagMemoryProps) => {
  const memoryPath = getMemoryPath(dagName);
  const memoryResponse = usePolledApiResponse<Memory>(memoryPath);
  const memory = memoryResponse.response;
  const hasNoMemoryResponse = hasNoResponseToShow(memoryResponse);

  if (hasNoMemoryResponse) {
    return (
      <Box sx={MEMORY_STYLE}>
        <EmptyState
          title={LABELS.apiRequestFailedTitle}
          body={LABELS.apiRequestFailedHint}
        />
      </Box>
    );
  }

  if (memory === null) {
    return (
      <Box role="status" aria-label={LABELS.dagMemoryLoading}>
        <LinearProgress />
      </Box>
    );
  }

  if (memory.updatedAt === null) {
    return (
      <Box sx={MEMORY_STYLE}>
        <RequestFailureAlert hasFailed={memoryResponse.hasFailed} />
        <EmptyState
          title={LABELS.dagMemoryEmpty}
          body={LABELS.dagMemoryEmptyHint}
        />
      </Box>
    );
  }

  return (
    <Box sx={MEMORY_STYLE}>
      <RequestFailureAlert hasFailed={memoryResponse.hasFailed} />
      <RelativeTime
        at={memory.updatedAt}
        template={LABELS.dagMemoryUpdatedAt}
      />
      <Typography component="div" variant="body2">
        <MarkdownText text={memory.content} />
      </Typography>
    </Box>
  );
};
