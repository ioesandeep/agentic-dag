'use client';

import Box from '@mui/material/Box';
import Slide from '@mui/material/Slide';
import { useState } from 'react';

import { PANEL_HEIGHT } from '@/components/dagPanel/constants';
import { DagPanelBody } from '@/components/dagPanel/dagPanelBody/dagPanelBody';
import { DagSidebar } from '@/components/dagPanel/dagSidebar/dagSidebar';
import { RequestFailureAlert } from '@/components/requestFailureAlert/requestFailureAlert';
import type { DagDetail } from '@/entities/dagDetail';
import type { DagSummary } from '@/entities/dagSummary';
import { useEntryFromDagList } from '@/hooks/useEntryFromDagList';

const ROW_STYLE = { display: 'flex', height: PANEL_HEIGHT, overflow: 'hidden' };

const COLUMN_STYLE = {
  flexGrow: 1,
  minWidth: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 2,
  p: 2,
};

interface DagPanelProps {
  // The dags of this host, null until the api sends them.
  dags: DagSummary[] | null;
  currentName: string;
  // The current dag's detail, null until the api sends it.
  dag: DagDetail | null;
  // True where the last request to the api failed.
  hasFailed: boolean;
}

/**
 * Renders the dag page as a split panel.
 */
export const DagPanel = ({
  dags,
  currentName,
  dag,
  hasFailed,
}: DagPanelProps) => {
  const dagsFromList = useEntryFromDagList();
  const isEntering = dagsFromList !== null;
  const [hasSettled, setHasSettled] = useState(!isEntering);

  const handleSettle = () => setHasSettled(true);

  return (
    <Box sx={ROW_STYLE}>
      <DagSidebar
        dags={dags ?? dagsFromList}
        currentName={currentName}
        isEntering={isEntering}
      />
      <Slide direction="left" in appear={isEntering} onEntered={handleSettle}>
        <Box sx={COLUMN_STYLE}>
          <RequestFailureAlert hasFailed={hasFailed} />
          <DagPanelBody dag={dag} hasSettled={hasSettled} />
        </Box>
      </Slide>
    </Box>
  );
};
