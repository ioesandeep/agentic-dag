import Typography from '@mui/material/Typography';

import { ExpandableText } from '@/components/nodeDialog/nodeSidebar/instructionsText/expandableText/expandableText';
import { LABELS } from '@/labels/en';

interface InstructionsTextProps {
  instructions: string;
}

/**
 * Renders the launch instructions, or a message when the node has none.
 */
export const InstructionsText = ({ instructions }: InstructionsTextProps) => {
  if (instructions === '') {
    return (
      <Typography variant="body2" color="text.secondary">
        {LABELS.instructionsEmpty}
      </Typography>
    );
  }

  return <ExpandableText text={instructions} />;
};
