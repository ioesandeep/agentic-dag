import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import type { ReactNode } from 'react';

const VALUE_STYLE = {
  minHeight: '2.5rem',
  display: 'flex',
  alignItems: 'center',
  overflowWrap: 'anywhere',
};

const TEXT_STYLE = { fontWeight: 500 };

interface ProjectDetailFieldProps {
  label: string;
  value: string;
  isEditing: boolean;
  children: ReactNode;
}

/**
 * Displays a project field above its value or edit control.
 */
export const ProjectDetailField = ({
  label,
  value,
  isEditing,
  children,
}: ProjectDetailFieldProps) => (
  <Stack spacing={0.5}>
    <Typography variant="body2" color="text.secondary">
      {label}
    </Typography>
    {isEditing && children}
    {!isEditing && (
      <Box sx={VALUE_STYLE}>
        <Typography variant="body1" sx={TEXT_STYLE}>
          {value}
        </Typography>
      </Box>
    )}
  </Stack>
);
