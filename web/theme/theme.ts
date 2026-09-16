'use client';

import { createTheme } from '@mui/material/styles';

import { SCREEN_ENTRANCE_MS } from '@/theme/constants';

const LIGHT_STATE = {
  pending: '#8c887c',
  in_progress: '#0e7490',
  resting: '#b45309',
  merged: '#15803d',
  needs_human: '#c2362b',
  errored: '#8a241c',
  skipped: '#4f46c0',
};

const DARK_STATE = {
  pending: '#7a766a',
  in_progress: '#67c3d4',
  resting: '#d99a4e',
  merged: '#5fbb82',
  needs_human: '#f87171',
  errored: '#c4564f',
  skipped: '#948ce4',
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
