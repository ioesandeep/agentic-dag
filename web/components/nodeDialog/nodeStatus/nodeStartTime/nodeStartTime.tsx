import { RelativeTime } from '@/components/relativeTime/relativeTime';
import { LABELS, LOCALE } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

const START_TIME_FORMAT_OPTIONS: Intl.DateTimeFormatOptions = {
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
};
const START_TIME_FORMAT = new Intl.DateTimeFormat(
  LOCALE,
  START_TIME_FORMAT_OPTIONS,
);

interface NodeStartTimeProps {
  // The node's start time, null when the node does not wait for its cooldown.
  startsAt: string | null;
}

/**
 * Renders a node's start time.
 */
export const NodeStartTime = ({ startsAt }: NodeStartTimeProps) => {
  if (startsAt === null) {
    return null;
  }

  const startTimestamp = Date.parse(startsAt);
  const startTime = START_TIME_FORMAT.format(startTimestamp);
  const startTimeValues = { startTime };
  const template = formatLabel(LABELS.nodeStartTime, startTimeValues);

  return <RelativeTime at={startsAt} template={template} />;
};
