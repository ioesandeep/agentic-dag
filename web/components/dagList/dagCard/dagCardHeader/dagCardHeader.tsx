import Box from '@mui/material/Box';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';

import type { DagCardAction } from '@/components/dagList/dagCard/dagCardHeader/types';

interface DagCardHeaderProps {
  title: string;
  actions: DagCardAction[];
}

/**
 * Renders the header section of a card.
 */
export const DagCardHeader = ({ title, actions }: DagCardHeaderProps) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
    <Typography variant="h6" noWrap sx={{ flexGrow: 1 }}>
      {title}
    </Typography>
    {actions.map((action) => (
      <Tooltip key={action.title} title={action.title}>
        <Box sx={{ display: 'flex' }}>{action.icon}</Box>
      </Tooltip>
    ))}
  </Box>
);
