import Typography from '@mui/material/Typography';

import { RelativeTime } from '@/components/relativeTime/relativeTime';
import { LABELS } from '@/labels/en';

interface LastActivityProps {
  at: string | null;
}

/**
 * Renders the last activity time of a dag.
 */
export const LastActivity = ({ at }: LastActivityProps) => {
  if (at === null) {
    return (
      <Typography variant="body2" color="text.secondary">
        {LABELS.dagNeverActive}
      </Typography>
    );
  }

  return <RelativeTime at={at} />;
};
