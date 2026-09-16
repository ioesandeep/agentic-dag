import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

interface EmptyStateProps {
  title: string;
  body: string;
}

export const EmptyState = ({ title, body }: EmptyStateProps) => (
  <Box
    sx={{
      border: 1,
      borderStyle: 'dashed',
      borderColor: 'divider',
      borderRadius: 2,
      p: 6,
      textAlign: 'center',
    }}
  >
    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
      {title}
    </Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
      {body}
    </Typography>
  </Box>
);
