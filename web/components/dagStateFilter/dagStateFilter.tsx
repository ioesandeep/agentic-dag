'use client';

import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import type { MouseEvent } from 'react';

import { getDagStateButtonStyle } from '@/components/dagStateFilter/utils';
import { useStoredDagState } from '@/hooks/useStoredDagState';
import { DAG_STATE_LABELS, LABELS } from '@/labels/en';
import { DAG_STATES, DagState } from '@/utils/dagState';
import { isNull } from '@/utils/typeGuards';

/**
 * Renders the control that filters the dag list by dag state.
 */
export const DagStateFilter = () => {
  const dagFilter = useStoredDagState();

  const handleChange = (
    _: MouseEvent<HTMLElement>,
    dagState: DagState | null,
  ) => dagFilter.setDagState(isNull(dagState) ? DagState.ANY : dagState);

  return (
    <ToggleButtonGroup
      exclusive
      size="small"
      value={dagFilter.dagState}
      onChange={handleChange}
      aria-label={LABELS.dagStateFilter}
    >
      {DAG_STATES.map((dagState) => (
        <ToggleButton
          key={dagState}
          value={dagState}
          sx={getDagStateButtonStyle(dagState)}
        >
          {DAG_STATE_LABELS[dagState]}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
};
