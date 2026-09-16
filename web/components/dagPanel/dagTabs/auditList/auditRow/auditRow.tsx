import ListItem from '@mui/material/ListItem';
import Typography from '@mui/material/Typography';

import { RelativeTime } from '@/components/relativeTime/relativeTime';
import { SoftChip } from '@/components/softChip/softChip';
import type { AuditLine } from '@/entities/dagDetail';
import { NODE_STATE_LABELS } from '@/labels/en';
import { getStateColor } from '@/utils/getStateColor';

interface AuditRowProps {
  line: AuditLine;
}

/**
 * Renders one entry of the AuditList.
 */
export const AuditRow = ({ line }: AuditRowProps) => (
  <ListItem divider sx={{ display: 'flex', gap: 1.5, px: 2, py: 1 }}>
    <SoftChip
      color={getStateColor(line.state)}
      label={NODE_STATE_LABELS[line.state]}
    />
    <Typography
      variant="body2"
      noWrap
      sx={{
        fontFamily: (theme) => theme.typography.fontFamilyMono,
        flexShrink: 0,
      }}
    >
      {line.nodeId}
    </Typography>
    <Typography
      variant="body2"
      color="text.secondary"
      noWrap
      sx={{ flexGrow: 1, minWidth: 0 }}
    >
      {line.note}
    </Typography>
    <RelativeTime at={line.createdAt} />
  </ListItem>
);
