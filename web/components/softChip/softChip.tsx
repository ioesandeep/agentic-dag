import Chip from '@mui/material/Chip';

interface SoftChipProps {
  label: string;
  // Any CSS colour, normally a theme variable such as var(--mui-palette-primary-main).
  color: string;
  mono?: boolean;
}

export const SoftChip = ({ label, color, mono = false }: SoftChipProps) => (
  <Chip
    size="small"
    label={label}
    sx={{
      color,
      bgcolor: `color-mix(in srgb, ${color} 14%, transparent)`,
      fontWeight: 500,
      ...(mono
        ? { fontFamily: (theme) => theme.typography.fontFamilyMono }
        : {}),
    }}
  />
);
