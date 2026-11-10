import { buttonBaseClasses } from '@mui/material/ButtonBase';
import type { SxProps, Theme } from '@mui/material/styles';

export const NODE_WIDTH = 320;
export const NODE_HEIGHT = 92;
export const PLAN_NODE_TYPE = 'planNode';
export const EDGE_TYPE = 'smoothstep';
export const CONNECTION_RADIUS = 20;
export const BACKGROUND_GAP = 20;
export const BACKGROUND_DOT_SIZE = 1;
export const EDGE_WIDTH = 1.5;
export const PRIMARY_COLOR = 'var(--mui-palette-primary-main)';
export const SECONDARY_COLOR = 'var(--mui-palette-text-secondary)';
export const DIVIDER_COLOR = 'var(--mui-palette-divider)';
export const PAPER_COLOR = 'var(--mui-palette-background-paper)';
export const OUTLINE_WIDTH = '0.125rem';
export const SELECTION_RING_WIDTH = '0.25rem';
export const HANDLE_SIZE = '0.5rem';
export const REM_PIXELS = 16;

export const GRAPH_STYLE: SxProps<Theme> = {
  flexGrow: 1,
  minHeight: 0,
  overflow: 'hidden',
  '--xy-edge-stroke': DIVIDER_COLOR,
  '--xy-edge-stroke-width': EDGE_WIDTH,
  '--xy-connectionline-stroke': PRIMARY_COLOR,
  '--xy-handle-background-color': PAPER_COLOR,
  '.react-flow__handle': {
    width: HANDLE_SIZE,
    height: HANDLE_SIZE,
    border: 1,
    borderRadius: '50%',
    borderColor: SECONDARY_COLOR,
  },
  '.react-flow__node:focus-visible': { outlineColor: PRIMARY_COLOR },
  '--xy-attribution-background-color': 'transparent',
  '.react-flow__attribution a': { color: SECONDARY_COLOR },
};

export const NODE_BUTTON_STYLE: SxProps<Theme> = {
  position: 'static',
  justifyContent: 'flex-start',
  minWidth: 0,
  '&::after': { content: '""', position: 'absolute', inset: 0 },
  [`&.${buttonBaseClasses.focusVisible}::after`]: {
    borderRadius: 1,
    outline: `${OUTLINE_WIDTH} solid ${PRIMARY_COLOR}`,
  },
};
