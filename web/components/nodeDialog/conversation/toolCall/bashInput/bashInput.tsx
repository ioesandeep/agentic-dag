import {
  COMMAND_KEY,
  DESCRIPTION_KEY,
} from '@/components/nodeDialog/conversation/toolCall/constants';
import { ToolArgument } from '@/components/nodeDialog/conversation/toolCall/toolArgument/toolArgument';
import { ToolCaption } from '@/components/nodeDialog/conversation/toolCall/toolCaption/toolCaption';
import { readTextArgument } from '@/components/nodeDialog/conversation/toolCall/utils';
import { HighlightLanguage } from '@/components/codeBlock/types';
import { LABELS } from '@/labels/en';

interface BashInputProps {
  input?: Record<string, unknown>;
}

/**
 * Renders the shell command and description of a Bash call.
 */
export const BashInput = ({ input }: BashInputProps) => (
  <>
    <ToolArgument
      label={LABELS.toolCommandLabel}
      text={readTextArgument(input, COMMAND_KEY)}
      language={HighlightLanguage.BASH}
    />
    <ToolCaption text={readTextArgument(input, DESCRIPTION_KEY)} />
  </>
);
