import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import { CodeBlock } from '@/components/codeBlock/codeBlock';
import type { HighlightLanguage } from '@/components/codeBlock/types';

interface ToolArgumentProps {
  label: string;
  text: string;
  // The language to highlight the text in.
  language?: HighlightLanguage;
}

/**
 * Renders one named argument of a tool call as a labelled code block.
 */
export const ToolArgument = ({
  label,
  text,
  language,
}: ToolArgumentProps) => (
  <Box>
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{ display: 'block', mb: 0.25 }}
    >
      {label}
    </Typography>
    <CodeBlock text={text} language={language} />
  </Box>
);
