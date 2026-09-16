import Typography from '@mui/material/Typography';

interface ToolCaptionProps {
  text: string;
}

/**
 * Renders the description of a tool call, or nothing when it has none.
 */
export const ToolCaption = ({ text }: ToolCaptionProps) => {
  if (text === '') {
    return null;
  }

  return (
    <Typography variant="caption" color="text.secondary">
      {text}
    </Typography>
  );
};
