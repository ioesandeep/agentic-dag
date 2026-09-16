'use client';

import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined';
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import { useColorScheme } from '@mui/material/styles';

import { LABELS } from '@/labels/en';

export const ColorSchemeToggle = () => {
  const { mode, systemMode, setMode } = useColorScheme();

  if (!mode) {
    return (
      <IconButton disabled size="small">
        <LightModeOutlinedIcon fontSize="small" />
      </IconButton>
    );
  }

  const resolved = mode === 'system' ? systemMode : mode;

  return (
    <Tooltip title={LABELS.themeToggle}>
      <IconButton
        size="small"
        onClick={() => setMode(resolved === 'dark' ? 'light' : 'dark')}
        aria-label={LABELS.themeToggle}
      >
        {resolved === 'dark' ? (
          <LightModeOutlinedIcon fontSize="small" />
        ) : (
          <DarkModeOutlinedIcon fontSize="small" />
        )}
      </IconButton>
    </Tooltip>
  );
};
