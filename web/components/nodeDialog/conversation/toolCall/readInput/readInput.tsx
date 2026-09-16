import { FILE_PATH_KEY } from '@/components/nodeDialog/conversation/toolCall/constants';
import { ToolArgument } from '@/components/nodeDialog/conversation/toolCall/toolArgument/toolArgument';
import { readTextArgument } from '@/components/nodeDialog/conversation/toolCall/utils';
import { LABELS } from '@/labels/en';

interface ReadInputProps {
  input?: Record<string, unknown>;
}

/**
 * Renders the file path of a Read call.
 */
export const ReadInput = ({ input }: ReadInputProps) => (
  <ToolArgument
    label={LABELS.toolFileLabel}
    text={readTextArgument(input, FILE_PATH_KEY)}
  />
);
