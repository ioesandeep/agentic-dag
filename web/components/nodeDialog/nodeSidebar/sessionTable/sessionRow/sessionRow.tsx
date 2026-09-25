'use client';

import Button from '@mui/material/Button';
import TableCell from '@mui/material/TableCell';
import TableRow from '@mui/material/TableRow';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';

import {
  endStateText,
  getScrollToSessionTooltip,
} from '@/components/nodeDialog/nodeSidebar/sessionTable/utils';
import { scrollToSession } from '@/components/nodeDialog/utils';
import { RelativeTime } from '@/components/relativeTime/relativeTime';
import type { AgentSession } from '@/entities/nodeDetail';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

interface SessionRowProps {
  session: AgentSession;
  // Which wake of the node this session is, counting from one.
  wake: number;
  // True when the session start is within the loaded part of the transcript.
  isStartLoaded: boolean;
}

/**
 * Renders one session row with a control that scrolls the conversation to it.
 */
export const SessionRow = ({
  session,
  wake,
  isStartLoaded,
}: SessionRowProps) => {
  const handleScrollToSession = () => scrollToSession(wake);
  const wakeValues = { wake };
  const scrollToSessionTooltip = getScrollToSessionTooltip(isStartLoaded, wake);

  return (
    <TableRow hover>
      <TableCell sx={{ px: 0 }}>
        <Tooltip title={scrollToSessionTooltip} describeChild>
          <span>
            <Button
              size="small"
              onClick={handleScrollToSession}
              disabled={!isStartLoaded}
              aria-label={formatLabel(
                LABELS.sessionShowInConversation,
                wakeValues,
              )}
              sx={{ minWidth: 0 }}
            >
              {wake}
            </Button>
          </span>
        </Tooltip>
      </TableCell>
      <TableCell sx={{ px: 0.5 }}>
        <RelativeTime at={session.startedAt} />
      </TableCell>
      <TableCell sx={{ px: 0.5 }}>
        <Typography variant="body2" color="text.secondary">
          {endStateText(session.endState)}
        </Typography>
      </TableCell>
    </TableRow>
  );
};
