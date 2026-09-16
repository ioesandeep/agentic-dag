import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import type { ReactNode } from 'react';

const LABEL_WIDTH = 84;

interface DetailRowProps {
  label: string;
  children: ReactNode;
}

/**
 * Renders one labelled value row.
 */
export const DetailRow = ({ label, children }: DetailRowProps) => (
  <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, minWidth: 0 }}>
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{ width: LABEL_WIDTH, flexShrink: 0 }}
    >
      {label}
    </Typography>
    <Box sx={{ flexGrow: 1, minWidth: 0 }}>{children}</Box>
  </Box>
);
