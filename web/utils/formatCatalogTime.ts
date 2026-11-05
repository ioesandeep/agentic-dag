import { LABELS, LOCALE } from '@/labels/en';

const TIME_CONFIG: Intl.DateTimeFormatOptions = {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'UTC',
};

const TIME_FORMAT = new Intl.DateTimeFormat(LOCALE, TIME_CONFIG);

/**
 * Formats catalog timestamps in UTC.
 */
export const formatCatalogTime = (timestamp: string | null): string => {
  if (timestamp === null) {
    return LABELS.repositoryTimeUnavailable;
  }

  const date = new Date(timestamp);

  return TIME_FORMAT.format(date);
};
