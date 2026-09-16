import Box from '@mui/material/Box';
import type { ReactNode } from 'react';

const LAYOUT_STYLE = { minHeight: '100dvh', bgcolor: 'background.default' };

interface AppLayoutProps {
  // The bar this page puts above its content.
  topAppBar: ReactNode;
  children: ReactNode;
}

/**
 * Renders a page under the top app bar it configures.
 */
export const AppLayout = ({ topAppBar, children }: AppLayoutProps) => (
  <Box sx={LAYOUT_STYLE}>
    {topAppBar}
    <Box component="main">{children}</Box>
  </Box>
);
