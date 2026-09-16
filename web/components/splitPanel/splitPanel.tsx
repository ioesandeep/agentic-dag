'use client';

import Box from '@mui/material/Box';
import type { ReactNode } from 'react';
import { Fragment, useRef, useState } from 'react';

import { FULL_PERCENT } from '@/components/splitPanel/constants';
import { DragHandle } from '@/components/splitPanel/dragHandle/dragHandle';
import {
  getInitialSplit,
  getPanelStyle,
  getResizedSplit,
  getSplitPanelRows,
} from '@/components/splitPanel/utils';

const SPLIT_PANEL_STYLE = {
  flexGrow: 1,
  minHeight: 0,
  display: 'flex',
  flexDirection: 'column',
};

interface SplitPanelProps {
  // The panels stacked from top to bottom.
  panels: ReactNode[];
  // The percent of the height each panel starts with, equal shares where absent.
  initialSplit?: number[];
}

/**
 * Renders panels a person resizes by dragging the handles between them.
 */
export const SplitPanel = ({ panels, initialSplit }: SplitPanelProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [split, setSplit] = useState(() =>
    getInitialSplit(panels.length, initialSplit),
  );

  const rows = getSplitPanelRows(panels, split);

  const handleDrag = (index: number, movedPixels: number) => {
    const container = containerRef.current;

    if (container === null) {
      return;
    }

    const movedPercent = (movedPixels / container.clientHeight) * FULL_PERCENT;

    setSplit((currentSplit) =>
      getResizedSplit(currentSplit, index, movedPercent),
    );
  };

  return (
    <Box ref={containerRef} sx={SPLIT_PANEL_STYLE}>
      {rows.map((row, index) => (
        <Fragment key={index}>
          <Box sx={getPanelStyle(row.percent)}>{row.panel}</Box>
          {row.hasHandle && (
            <DragHandle
              percent={row.percent}
              onDrag={(movedPixels) => handleDrag(index, movedPixels)}
            />
          )}
        </Fragment>
      ))}
    </Box>
  );
};
