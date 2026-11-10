'use client';

import DragHandleOutlinedIcon from '@mui/icons-material/DragHandleOutlined';
import Box from '@mui/material/Box';
import type { KeyboardEvent, PointerEvent as ReactPointerEvent } from 'react';
import { useEffect, useRef, useState } from 'react';

import { EMPTY_PERCENT, FULL_PERCENT } from '@/components/splitPanel/constants';
import { NO_DRAG_PIXELS } from './constants';
import {
  getDragHandleIconStyle,
  getDragHandleOrientation,
  getDragHandleStyle,
  getKeyDragPixels,
  getPointerPosition,
} from './utils';
import type { SplitPanelDirectionEnum } from '@/components/splitPanel/types';
import { LABELS } from '@/labels/en';

interface DragHandleProps {
  // The percentage of the panel before this handle along the layout axis.
  percent: number;
  direction: SplitPanelDirectionEnum;
  // Receives the pixels the handle has moved since the last event.
  onDrag: (movedPixels: number) => void;
}

/**
 * Renders the boundary a person drags to resize the panels around it.
 */
export const DragHandle = ({ percent, direction, onDrag }: DragHandleProps) => {
  const lastPointerPosition = useRef<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const roundedPercent = Math.round(percent);
  const orientation = getDragHandleOrientation(direction);
  const iconStyle = getDragHandleIconStyle(direction);

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    lastPointerPosition.current = getPointerPosition(event, direction);
    setIsDragging(true);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const dragPixels = getKeyDragPixels(event.key, direction);

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
      const previousPosition = lastPointerPosition.current;

      if (previousPosition === null) {
        return;
      }

      const pointerPosition = getPointerPosition(event, direction);
      lastPointerPosition.current = pointerPosition;
      onDrag(pointerPosition - previousPosition);
    };

    const stopDrag = () => {
      lastPointerPosition.current = null;
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
  }, [isDragging, onDrag, direction]);

  return (
    <Box
      role="separator"
      tabIndex={0}
      aria-label={LABELS.splitResize}
      aria-orientation={orientation}
      aria-valuenow={roundedPercent}
      aria-valuemin={EMPTY_PERCENT}
      aria-valuemax={FULL_PERCENT}
      onPointerDown={handlePointerDown}
      onKeyDown={handleKeyDown}
      sx={getDragHandleStyle(isDragging, direction)}
    >
      <DragHandleOutlinedIcon fontSize="small" aria-hidden sx={iconStyle} />
    </Box>
  );
};
