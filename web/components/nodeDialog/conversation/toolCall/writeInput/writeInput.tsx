import { languageForFile } from '@/components/codeBlock/utils';
import {
  CONTENT_KEY,
  FILE_PATH_KEY,
} from '@/components/nodeDialog/conversation/toolCall/constants';
import { ToolArgument } from '@/components/nodeDialog/conversation/toolCall/toolArgument/toolArgument';
import { readTextArgument } from '@/components/nodeDialog/conversation/toolCall/utils';
import { LABELS } from '@/labels/en';

interface WriteInputProps {
  input?: Record<string, unknown>;
}

/**
 * Renders the file path and the content of a Write call.
 */
export const WriteInput = ({ input }: WriteInputProps) => {
  const filePath = readTextArgument(input, FILE_PATH_KEY);

  return (
    <>
      <ToolArgument label={LABELS.toolFileLabel} text={filePath} />
      <ToolArgument
        label={LABELS.toolContentLabel}
        text={readTextArgument(input, CONTENT_KEY)}
        language={languageForFile(filePath)}
      />
    </>
  );
};
