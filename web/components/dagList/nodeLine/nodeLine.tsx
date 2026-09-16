import Box from '@mui/material/Box';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';

import type { NodePreview } from '@/entities/dagSummary';
import { NODE_STATE_LABELS } from '@/labels/en';

export const NodeLine = ({ node }: { node: NodePreview }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
    <Tooltip title={NODE_STATE_LABELS[node.state]}>
      <Box
        sx={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          flexShrink: 0,
          bgcolor: (theme) => (theme.vars ?? theme).palette.state[node.state],
        }}
      />
    </Tooltip>
    <Typography variant="body1" noWrap sx={{ flexGrow: 1, minWidth: 0 }}>
      {node.title}
    </Typography>
    <Typography
      variant="body2"
      color="text.secondary"
      noWrap
      sx={{ flexShrink: 0 }}
    >
      {node.agentName}
    </Typography>
  </Box>
);
