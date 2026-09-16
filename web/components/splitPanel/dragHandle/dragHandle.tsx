'use client';

import DragHandleOutlinedIcon from '@mui/icons-material/DragHandleOutlined';
import Box from '@mui/material/Box';
import type { KeyboardEvent, PointerEvent as ReactPointerEvent } from 'react';
import { useEffect, useRef, useState } from 'react';

import {
  EMPTY_PERCENT,
  FULL_PERCENT,
} from '@/components/splitPanel/constants';
import { NO_DRAG_PIXELS } from '@/components/splitPanel/dragHandle/constants';
import {
  getDragHandleStyle,
  getKeyDragPixels,
} from '@/components/splitPanel/dragHandle/utils';
import { LABELS } from '@/labels/en';

interface DragHandleProps {
  // The percent of the height the panel above this handle holds.
  percent: number;
  // Receives the pixels the handle has moved since the last event.
  onDrag: (movedPixels: number) => void;
}

/**
 * Renders the boundary a person drags to resize the panels around it.
 */
export const DragHandle = ({ percent, onDrag }: DragHandleProps) => {
  const lastPointerY = useRef<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const roundedPercent = Math.round(percent);

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    lastPointerY.current = event.clientY;
    setIsDragging(true);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const dragPixels = getKeyDragPixels(event.key);

    if (dragPixels === NO_DRAG_PIXELS) {
      return;
    }

    event.preventDefault();
    onDrag(dragPixels);
  };

  useEffect(() => {
    if (!isDragging) {
      return;
    }

    const trackPointer = (event: PointerEvent) => {
      const pointerY = lastPointerY.current;

      if (pointerY === null) {
        return;
      }

      lastPointerY.current = event.clientY;
      onDrag(event.clientY - pointerY);
    };

    const stopDrag = () => {
      lastPointerY.current = null;
      setIsDragging(false);
    };

    window.addEventListener('pointermove', trackPointer);
    window.addEventListener('pointerup', stopDrag);
    window.addEventListener('pointercancel', stopDrag);

    return () => {
      window.removeEventListener('pointermove', trackPointer);
      window.removeEventListener('pointerup', stopDrag);
      window.removeEventListener('pointercancel', stopDrag);
    };
  }, [isDragging, onDrag]);

  return (
    <Box
      role="separator"
      tabIndex={0}
      aria-label={LABELS.splitResize}
      aria-orientation="horizontal"
      aria-valuenow={roundedPercent}
      aria-valuemin={EMPTY_PERCENT}
      aria-valuemax={FULL_PERCENT}
      onPointerDown={handlePointerDown}
      onKeyDown={handleKeyDown}
      sx={getDragHandleStyle(isDragging)}
    >
      <DragHandleOutlinedIcon fontSize="small" aria-hidden />
    </Box>
  );
};
