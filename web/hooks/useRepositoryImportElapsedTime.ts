'use client';

import { useSyncExternalStore } from 'react';

import type { RepositoryImport } from '@/entities/catalog/repositoryImport';
import { LABELS, LOCALE } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

const REFRESH_INTERVAL_MS = 1000;
const SECONDS_PER_MINUTE = 60;
const SECONDS_PER_HOUR = 3600;
const DURATION_UNITS = [
  { unit: 'hour', seconds: SECONDS_PER_HOUR },
  { unit: 'minute', seconds: SECONDS_PER_MINUTE },
  { unit: 'second', seconds: 1 },
];

const DURATION_LIST_CONFIG: Intl.ListFormatOptions = { style: 'short', type: 'unit' };
const DURATION_LIST_FORMAT = new Intl.ListFormat(LOCALE, DURATION_LIST_CONFIG);

const getCurrentTimeSeconds = () => {
  const currentTimeMs = Date.now();

  return Math.floor(currentTimeMs / REFRESH_INTERVAL_MS);
};

const getServerTimeSeconds = () => null;
const subscribeWithoutTimer = () => () => undefined;
const subscribeToCurrentTime = (onChange: () => void) => {
  const timer = window.setInterval(onChange, REFRESH_INTERVAL_MS);

  return () => window.clearInterval(timer);
};

const formatElapsedTime = (elapsedSeconds: number): string => {
  const durationParts = DURATION_UNITS.flatMap(({ unit, seconds }, index) => {
    const remainingSeconds = elapsedSeconds % (DURATION_UNITS[index - 1]?.seconds ?? Infinity);
    const count = Math.floor(remainingSeconds / seconds);
    if (count === 0 && unit !== 'second') {
      return [];
    }

    const numberFormatConfig: Intl.NumberFormatOptions = {
      style: 'unit',
      unit,
      unitDisplay: 'short',
    };

    const numberFormat = new Intl.NumberFormat(LOCALE, numberFormatConfig);

    return [numberFormat.format(count)];
  });

  const duration = DURATION_LIST_FORMAT.format(durationParts);
  const elapsedValues = { duration };

  return formatLabel(LABELS.repositoryCloneElapsed, elapsedValues);
};

/**
 * Returns the elapsed time of an active repository clone attempt.
 */
export const useRepositoryImportElapsedTime = (
  repositoryImport: RepositoryImport | null,
): string | null => {
  const subscribe = repositoryImport === null ? subscribeWithoutTimer : subscribeToCurrentTime;
  const currentTimeSeconds = useSyncExternalStore(
    subscribe,
    getCurrentTimeSeconds,
    getServerTimeSeconds,
  );

  if (repositoryImport === null || currentTimeSeconds === null) {
    return null;
  }

  const startedAt = repositoryImport.startedAt ?? repositoryImport.createdAt;
  const startedAtSeconds = Date.parse(startedAt) / REFRESH_INTERVAL_MS;
  const elapsedSeconds = Math.max(0, currentTimeSeconds - startedAtSeconds);

  return formatElapsedTime(elapsedSeconds);
};
