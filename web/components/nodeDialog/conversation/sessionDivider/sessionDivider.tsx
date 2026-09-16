import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';
import Typography from '@mui/material/Typography';

import { sessionAnchorId } from '@/components/nodeDialog/utils';
import type { SessionStart } from '@/components/nodeDialog/conversation/types';
import { RelativeTime } from '@/components/relativeTime/relativeTime';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

const ANCHOR_MARGIN = '0.5rem';

interface SessionDividerProps {
  // The session this divider names, or null when the message begins none.
  sessionStart: SessionStart | null;
}

/**
 * Renders a divider naming the wake a session started on.
 */
export const SessionDivider = ({ sessionStart }: SessionDividerProps) => {
  if (sessionStart === null) {
    return null;
  }

  const wakeValues = { wake: sessionStart.wake };

  return (
    <Divider
      id={sessionAnchorId(sessionStart.wake)}
      sx={{ scrollMarginTop: ANCHOR_MARGIN }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="overline" sx={{ fontWeight: 600 }}>
          {formatLabel(LABELS.sessionWake, wakeValues)}
        </Typography>
        <RelativeTime
          at={sessionStart.session.startedAt}
          template={LABELS.sessionStartedAt}
        />
      </Box>
    </Divider>
  );
};
