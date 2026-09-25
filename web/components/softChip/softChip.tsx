import Chip, { chipClasses } from '@mui/material/Chip';
import type { Theme } from '@mui/material/styles';

import { FOCUS_OUTLINE_OFFSET, FOCUS_OUTLINE_WIDTH } from './constants';
import type { SoftChipLink } from './types';

interface SoftChipProps {
  label: string;
  // Any CSS colour, normally a theme variable such as var(--mui-palette-primary-main).
  color: string;
  mono?: boolean;
  link?: SoftChipLink;
}

/**
 * Renders a small chip tinted with its colour.
 */
export const SoftChip = ({
  label,
  color,
  mono = false,
  link,
}: SoftChipProps) => {
  const backgroundColor = `color-mix(in srgb, ${color} 14%, transparent)`;
  const chipStyle = {
    color,
    bgcolor: backgroundColor,
    fontWeight: 500,
    ...(mono
      ? { fontFamily: (theme: Theme) => theme.typography.fontFamilyMono }
      : {}),
    [`&.${chipClasses.clickable}:hover`]: {
      bgcolor: backgroundColor,
      textDecoration: 'underline',
    },
    [`&.${chipClasses.focusVisible}`]: {
      bgcolor: backgroundColor,
      outline: `${FOCUS_OUTLINE_WIDTH} solid ${color}`,
      outlineOffset: FOCUS_OUTLINE_OFFSET,
    },
  };

  if (link === undefined) {
    return <Chip size="small" label={label} sx={chipStyle} />;
  }

  return (
    <Chip
      component="a"
      href={link.url}
      target="_blank"
      rel="noreferrer"
      clickable
      size="small"
      label={label}
      aria-label={link.ariaLabel}
      sx={chipStyle}
    />
  );
};
