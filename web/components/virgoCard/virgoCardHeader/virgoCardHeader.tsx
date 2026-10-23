import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import type { ReactNode } from 'react';

const HEADER_STYLE = { display: 'flex', alignItems: 'center', gap: 1 };
const TITLE_STYLE = { flexGrow: 1, minWidth: 0 };
const ACTION_STYLE = {
  position: 'relative',
  zIndex: 1,
  display: 'flex',
  alignItems: 'center',
  gap: 1,
  flexShrink: 0,
};

interface VirgoCardHeaderProps {
  title: string;
  actions?: ReactNode;
}

/**
 * Renders the header section of a card.
 */
export const VirgoCardHeader = ({ title, actions }: VirgoCardHeaderProps) => (
  <Box sx={HEADER_STYLE}>
    <Typography variant="h6" noWrap sx={TITLE_STYLE}>
      {title}
    </Typography>
    {actions !== undefined && <Box sx={ACTION_STYLE}>{actions}</Box>}
  </Box>
);
