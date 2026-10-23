'use client';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import type { MouseEventHandler, ReactNode } from 'react';

const CARD_STYLE = {
  height: '100%',
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',
  transition: 'border-color 200ms ease, box-shadow 200ms ease',
  '&:hover': { borderColor: 'primary.main', boxShadow: 3 },
  '@media (prefers-reduced-motion: reduce)': { transition: 'none' },
};

const CONTENT_STYLE = {
  p: 2.5,
  pb: 2,
  flexGrow: 1,
  display: 'flex',
  flexDirection: 'column',
  gap: 1.5,
  minWidth: 0,
};

const ACTION_STYLE = { position: 'absolute', inset: 0, height: '100%' };

interface VirgoCardProps {
  header: ReactNode;
  body: ReactNode;
  footer: ReactNode;
  ariaLabel?: string;
  onSelect?: MouseEventHandler<HTMLElement>;
}

/**
 * Renders a card with a header, body, and footer.
 */
export const VirgoCard = ({
  header,
  body,
  footer,
  ariaLabel,
  onSelect,
}: VirgoCardProps) => (
  <Card component="article" aria-label={ariaLabel} sx={CARD_STYLE}>
    <Box sx={CONTENT_STYLE}>
      {header}
      {body}
    </Box>
    {footer}
    {onSelect !== undefined && (
      <CardActionArea
        aria-label={ariaLabel}
        onClick={onSelect}
        sx={ACTION_STYLE}
      />
    )}
  </Card>
);
