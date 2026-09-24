import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import Accordion from '@mui/material/Accordion';
import AccordionDetails from '@mui/material/AccordionDetails';
import AccordionSummary from '@mui/material/AccordionSummary';
import Typography from '@mui/material/Typography';

import { CodeBlock } from '@/components/codeBlock/codeBlock';
import { LABELS } from '@/labels/en';

interface ToolResultProps {
  text?: string;
}

/**
 * Renders the result of a tool call inside a collapsed section.
 */
export const ToolResult = ({ text }: ToolResultProps) => {
  if (text === undefined || text === '') {
    return null;
  }

  return (
    <Accordion
      disableGutters
      elevation={0}
      sx={{ bgcolor: 'transparent', '&::before': { display: 'none' } }}
      slotProps={{ transition: { unmountOnExit: true } }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon fontSize="small" />}
        sx={{ minHeight: 0, px: 0 }}
      >
        <Typography variant="caption" color="text.secondary">
          {LABELS.toolResultHeading}
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ px: 0, pb: 0 }}>
        <CodeBlock text={text} />
      </AccordionDetails>
    </Accordion>
  );
};
