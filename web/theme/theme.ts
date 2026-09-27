'use client';

import { createTheme } from '@mui/material/styles';

import { NodeStateEnum } from '@/entities/nodeState';
import { SCREEN_ENTRANCE_MS } from '@/theme/constants';

const LIGHT_STATE = {
  [NodeStateEnum.PENDING]: '#8c887c',
  [NodeStateEnum.IN_PROGRESS]: '#0e7490',
  [NodeStateEnum.RESTING]: '#b45309',
  [NodeStateEnum.MERGED]: '#15803d',
  [NodeStateEnum.NEEDS_HUMAN]: '#c2362b',
  [NodeStateEnum.ERRORED]: '#8a241c',
  [NodeStateEnum.SKIPPED]: '#4f46c0',
};

const DARK_STATE = {
  [NodeStateEnum.PENDING]: '#7a766a',
  [NodeStateEnum.IN_PROGRESS]: '#67c3d4',
  [NodeStateEnum.RESTING]: '#d99a4e',
  [NodeStateEnum.MERGED]: '#5fbb82',
  [NodeStateEnum.NEEDS_HUMAN]: '#f87171',
  [NodeStateEnum.ERRORED]: '#c4564f',
  [NodeStateEnum.SKIPPED]: '#948ce4',
};

export const theme = createTheme({
  cssVariables: { colorSchemeSelector: 'data-mui-color-scheme' },
  colorSchemes: {
    light: {
      palette: {
        primary: { main: '#4f46c0' },
        info: { main: '#0e7490' },
        success: { main: '#15803d' },
        warning: { main: '#b45309' },
        error: { main: '#c2362b' },
        background: { default: '#faf9f5', paper: '#ffffff' },
        text: { primary: '#1c1b18', secondary: '#57544b' },
        divider: '#e4e1d6',
        state: LIGHT_STATE,
      },
    },
    dark: {
      palette: {
        primary: { main: '#948ce4' },
        info: { main: '#67c3d4' },
        success: { main: '#5fbb82' },
        warning: { main: '#d99a4e' },
        error: { main: '#f87171' },
        background: { default: '#131210', paper: '#201e1a' },
        text: { primary: '#ece9e0', secondary: '#a8a496' },
        divider: '#32302a',
        state: DARK_STATE,
      },
    },
  },
  motion: { reducedMotion: 'system' },
  transitions: { duration: { enteringScreen: SCREEN_ENTRANCE_MS } },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: 'var(--font-body), system-ui, sans-serif',
    fontFamilyMono: 'var(--font-mono), monospace',
    button: { textTransform: 'none' },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { fontVariantNumeric: 'tabular-nums' },
        '@keyframes dagSweep': {
          '0%': { transform: 'translateX(-110%)' },
          '100%': { transform: 'translateX(110%)' },
        },
        '@keyframes dagSidebarEnter': {
          '0%': { transform: 'translateX(25%)' },
          '100%': { transform: 'none' },
        },
        '@keyframes nodeSidebarEnter': {
          '0%': { transform: 'translateX(var(--node-sidebar-offset))' },
          '100%': { transform: 'none' },
        },
        '@keyframes dagPulse': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.45 },
        },
      },
    },
    MuiCard: {
      defaultProps: { variant: 'outlined' },
    },
    MuiDialog: {
      styleOverrides: { paper: { backgroundImage: 'none' } },
    },
    MuiSkeleton: {
      defaultProps: { variant: 'rounded' },
      styleOverrides: {
        root: {
          '@media (prefers-reduced-motion: reduce)': { animation: 'none' },
        },
      },
    },
    MuiAppBar: {
      defaultProps: { elevation: 0, color: 'transparent' },
    },
    MuiTooltip: {
      defaultProps: { enterDelay: 400 },
    },
  },
});
