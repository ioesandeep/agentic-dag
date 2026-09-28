import { LOCALE } from '@/labels/en';

interface TimeUnit {
  name: Intl.RelativeTimeFormatUnit;
  // The number of seconds per unit.
  seconds: number;
}

const MILLISECONDS_PER_SECOND = 1000;
const TIME_LEFT_FORMAT_OPTIONS: Intl.RelativeTimeFormatOptions = {
  numeric: 'auto',
  style: 'narrow',
};
const TIME_LEFT_FORMAT = new Intl.RelativeTimeFormat(
  LOCALE,
  TIME_LEFT_FORMAT_OPTIONS,
);
const TIME_UNITS_LARGEST_FIRST: TimeUnit[] = [
  { name: 'day', seconds: 86400 },
  { name: 'hour', seconds: 3600 },
  { name: 'minute', seconds: 60 },
];
const SECOND_TIME_UNIT: TimeUnit = { name: 'second', seconds: 1 };

/**
 * Returns the formatted time left until a start time.
 */
export const formatTimeLeft = (startsAt: string): string => {
  const millisecondsLeft = Date.parse(startsAt) - Date.now();
  const secondsLeft = millisecondsLeft / MILLISECONDS_PER_SECOND;

  const absoluteSecondsLeft = Math.abs(secondsLeft);
  const largestTimeUnit =
    TIME_UNITS_LARGEST_FIRST.find(
      (timeUnit) => absoluteSecondsLeft >= timeUnit.seconds,
    ) ?? SECOND_TIME_UNIT;
  const unitCount = Math.round(secondsLeft / largestTimeUnit.seconds);

  return TIME_LEFT_FORMAT.format(unitCount, largestTimeUnit.name);
};
