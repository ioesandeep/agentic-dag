'use client';

import Box from '@mui/material/Box';
import type { ReactNode } from 'react';
import { Fragment, useRef, useState } from 'react';

import { FULL_PERCENT } from './constants';
import { DragHandle } from '@/components/splitPanel/dragHandle/dragHandle';
import { SplitPanelDirectionEnum } from './types';
import {
  getContainerSize,
  getInitialSplit,
  getPanelStyle,
  getResizedSplit,
  getSplitPanelRows,
} from './utils';

const SPLIT_PANEL_STYLE = {
  flexGrow: 1,
  minHeight: 0,
  minWidth: 0,
  display: 'flex',
};

interface SplitPanelProps {
  // The panels in layout order.
  panels: ReactNode[];
  // The starting percentage of each panel along the layout axis.
  initialSplit?: number[];
  direction?: SplitPanelDirectionEnum;
  expandedPanel?: number | null;
}

/**
 * Renders panels a person resizes by dragging the handles between them.
 */
export const SplitPanel = ({
  panels,
  initialSplit,
  direction = SplitPanelDirectionEnum.COLUMN,
  expandedPanel = null,
}: SplitPanelProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [split, setSplit] = useState(() =>
    getInitialSplit(panels.length, initialSplit),
  );

  const rows = getSplitPanelRows(panels, split, expandedPanel);
  const containerStyle = { ...SPLIT_PANEL_STYLE, flexDirection: direction };

  const handleDrag = (index: number, movedPixels: number) => {
    const container = containerRef.current;

    if (container === null) {
      return;
    }

    const containerSize = getContainerSize(container, direction);
    const movedPercent = (movedPixels / containerSize) * FULL_PERCENT;

    setSplit((currentSplit) =>
      getResizedSplit(currentSplit, index, movedPercent),
    );
  };

  return (
    <Box ref={containerRef} sx={containerStyle}>
      {rows.map((row, index) => (
        <Fragment key={index}>
          <Box sx={getPanelStyle(row.percent)}>{row.panel}</Box>
          {row.hasHandle && (
            <DragHandle
              direction={direction}
              percent={row.percent}
              onDrag={(movedPixels) => handleDrag(index, movedPixels)}
            />
          )}
        </Fragment>
      ))}
    </Box>
  );
};
