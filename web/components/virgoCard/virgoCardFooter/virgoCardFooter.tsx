import Box from '@mui/material/Box';
import type { ReactNode } from 'react';

const FOOTER_STYLE = {
  px: 2.5,
  py: 1.5,
  display: 'flex',
  alignItems: 'center',
  flexWrap: 'wrap',
  gap: 1,
  borderTop: 1,
  borderColor: 'divider',
};

const CHIP_STYLE = {
  display: 'flex',
  alignItems: 'center',
  flexWrap: 'wrap',
  gap: 1,
};

const ACTION_STYLE = {
  position: 'relative',
  zIndex: 1,
  display: 'flex',
  alignItems: 'center',
  flexWrap: 'wrap',
  gap: 1,
  ml: 'auto',
};

interface VirgoCardFooterProps {
  chips?: ReactNode;
  actions?: ReactNode;
}

/**
 * Renders chips and actions in a card footer.
 */
export const VirgoCardFooter = ({ chips, actions }: VirgoCardFooterProps) => (
  <Box sx={FOOTER_STYLE}>
    <Box sx={CHIP_STYLE}>{chips}</Box>
    <Box sx={ACTION_STYLE}>{actions}</Box>
  </Box>
);
