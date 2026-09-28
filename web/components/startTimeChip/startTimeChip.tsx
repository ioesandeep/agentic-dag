'use client';

import { useEffect, useState } from 'react';

import { SoftChip } from '@/components/softChip/softChip';
import {
  START_TIME_CHIP_COLOR,
  TIME_LEFT_REFRESH_INTERVAL_MS,
} from '@/components/startTimeChip/constants';
import { formatTimeLeft } from '@/components/startTimeChip/utils';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

interface StartTimeChipProps {
  // The time the node starts.
  startsAt: string;
}

/**
 * Renders the time left until a node starts.
 */
export const StartTimeChip = ({ startsAt }: StartTimeChipProps) => {
  const [timeLeft, setTimeLeft] = useState(() => formatTimeLeft(startsAt));

  useEffect(() => {
    const refresh = () => {
      const currentTimeLeft = formatTimeLeft(startsAt);
      setTimeLeft(currentTimeLeft);
    };

    refresh();
    const timer = window.setInterval(refresh, TIME_LEFT_REFRESH_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [startsAt]);

  const timeLeftValues = { time: timeLeft };

  return (
    <SoftChip
      color={START_TIME_CHIP_COLOR}
      label={formatLabel(LABELS.nodeStartsAt, timeLeftValues)}
    />
  );
};
