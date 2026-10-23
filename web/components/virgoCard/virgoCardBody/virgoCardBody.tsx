import Box from '@mui/material/Box';
import type { ReactNode } from 'react';

const BODY_STYLE = {
  display: 'flex',
  flexDirection: 'column',
  gap: 1.5,
  minWidth: 0,
};

interface VirgoCardBodyProps {
  content: ReactNode;
}

/**
 * Renders the content section of a card.
 */
export const VirgoCardBody = ({ content }: VirgoCardBodyProps) => (
  <Box sx={BODY_STYLE}>{content}</Box>
);
