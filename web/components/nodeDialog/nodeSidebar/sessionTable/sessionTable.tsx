import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';

import { FIRST_WAKE } from '@/components/nodeDialog/constants';
import { SessionRow } from '@/components/nodeDialog/nodeSidebar/sessionTable/sessionRow/sessionRow';
import type { AgentSession } from '@/entities/nodeDetail';
import { LABELS } from '@/labels/en';

interface SessionTableProps {
  // The sessions of the node's agent, oldest first.
  sessions: AgentSession[];
}

/**
 * Renders one row per session of a node.
 */
export const SessionTable = ({ sessions }: SessionTableProps) => {
  if (sessions.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        {LABELS.sessionsEmpty}
      </Typography>
    );
  }

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell sx={{ px: 0 }}>{LABELS.sessionsWakeColumn}</TableCell>
          <TableCell sx={{ px: 0.5 }}>
            {LABELS.sessionsStartedColumn}
          </TableCell>
          <TableCell sx={{ px: 0.5 }}>{LABELS.sessionsEndColumn}</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {sessions.map((session, index) => (
          <SessionRow
            key={session.id}
            session={session}
            wake={index + FIRST_WAKE}
          />
        ))}
      </TableBody>
    </Table>
  );
};
