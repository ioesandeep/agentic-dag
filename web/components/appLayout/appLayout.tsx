import Box from '@mui/material/Box';
import type { ReactNode } from 'react';

import { CatalogNavigation } from '@/components/catalogNavigation/catalogNavigation';

const LAYOUT_STYLE = {
  height: '100dvh',
  display: 'flex',
  overflow: 'hidden',
  bgcolor: 'background.default',
};

const CONTENT_STYLE = {
  flex: 1,
  minWidth: 0,
  display: 'grid',
  gridTemplateRows: 'auto minmax(0, 1fr)',
};

const MAIN_STYLE = { minWidth: 0, minHeight: 0, overflow: 'auto' };

interface AppLayoutProps {
  // The bar this page puts above its content.
  topAppBar: ReactNode;
  children: ReactNode;
}

/**
 * Renders console navigation, the page toolbar, and page content.
 */
export const AppLayout = ({ topAppBar, children }: AppLayoutProps) => (
  <Box sx={LAYOUT_STYLE}>
    <CatalogNavigation />
    <Box sx={CONTENT_STYLE}>
      {topAppBar}
      <Box component="main" sx={MAIN_STYLE}>
        {children}
      </Box>
    </Box>
  </Box>
);
