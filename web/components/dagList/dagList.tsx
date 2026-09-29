'use client';

import Box from '@mui/material/Box';
import Grow from '@mui/material/Grow';
import Slide from '@mui/material/Slide';
import type { MouseEvent } from 'react';

import { DAG_GRID_COLUMNS } from '@/components/dagList/constants';
import { DagCard } from '@/components/dagList/dagCard/dagCard';
import { DagCardVariant } from '@/components/dagList/dagCard/types';
import { compareByLiveliness } from '@/components/dagList/utils';
import { EmptyState } from '@/components/emptyState/emptyState';
import type { DagSummary } from '@/entities/dagSummary';
import { useExitFromDagPage } from '@/hooks/useExitFromDagPage';
import { LABELS } from '@/labels/en';
import { createEntryFromDagList } from '@/utils/dagListEntry';
import { isSameTabClick } from '@/utils/isSameTabClick';

const ENTRANCE_MS = 260;

const GRID_STYLE = {
  display: 'grid',
  gap: 2,
  gridTemplateColumns: DAG_GRID_COLUMNS,
  transformOrigin: 'top center',
};

interface DagListProps {
  dags: DagSummary[];
}

/**
 * Renders a card for every dag on this host.
 */
export const DagList = ({ dags }: DagListProps) => {
  const isReturningFromDagPage = useExitFromDagPage();

  if (dags.length === 0) {
    return <EmptyState title={LABELS.dagsEmpty} body={LABELS.dagsEmptyHint} />;
  }

  const handleSelect = (event: MouseEvent<HTMLElement>) => {
    if (!isSameTabClick(event)) {
      return;
    }

    createEntryFromDagList(dags);
  };

  const dagGrid = (
    <Box sx={GRID_STYLE}>
      {[...dags].sort(compareByLiveliness).map((dag) => (
        <DagCard
          key={dag.name}
          dag={dag}
          variant={DagCardVariant.FULL}
          onSelect={handleSelect}
        />
      ))}
    </Box>
  );

  if (isReturningFromDagPage) {
    return (
      <Slide direction="right" in appear>
        {dagGrid}
      </Slide>
    );
  }

  return (
    <Grow in appear timeout={ENTRANCE_MS}>
      {dagGrid}
    </Grow>
  );
};
