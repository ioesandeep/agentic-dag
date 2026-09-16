'use client';

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Link from 'next/link';

interface BackButtonProps {
  // The route the button returns to.
  href: string;
  // The button's tooltip and its accessible name.
  label: string;
}

/**
 * Renders the control that returns to the screen above this one.
 */
export const BackButton = ({ href, label }: BackButtonProps) => (
  <Tooltip title={label}>
    <IconButton
      component={Link}
      href={href}
      edge="start"
      size="small"
      aria-label={label}
    >
      <ArrowBackIcon fontSize="small" />
    </IconButton>
  </Tooltip>
);
