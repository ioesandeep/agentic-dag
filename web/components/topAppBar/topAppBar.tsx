import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import type { ReactNode } from 'react';

const APP_BAR_STYLE = {
  borderBottom: 1,
  borderColor: 'divider',
  backdropFilter: 'blur(8px)',
};

const TOOLBAR_STYLE = { gap: 2 };

const BACK_BUTTON_STYLE = {
  flex: 1,
  display: 'flex',
  alignItems: 'center',
  minWidth: 0,
};

const TITLE_STYLE = { fontWeight: 600, minWidth: 0 };

const ACTIONS_STYLE = {
  flex: 1,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  gap: 1,
};

interface TopAppBarProps {
  // The control that leaves this screen, absent where nothing sits above it.
  backButton?: ReactNode;
  title: string;
  // The controls this screen offers, laid out after the title.
  actions?: ReactNode;
}

/**
 * Renders the bar at the top of a screen, with its title centred.
 */
export const TopAppBar = ({ backButton, title, actions }: TopAppBarProps) => (
  <AppBar position="sticky" sx={APP_BAR_STYLE}>
    <Toolbar variant="dense" sx={TOOLBAR_STYLE}>
      <Box sx={BACK_BUTTON_STYLE}>{backButton}</Box>
      <Typography variant="subtitle1" component="h1" noWrap sx={TITLE_STYLE}>
        {title}
      </Typography>
      <Box sx={ACTIONS_STYLE}>{actions}</Box>
    </Toolbar>
  </AppBar>
);
