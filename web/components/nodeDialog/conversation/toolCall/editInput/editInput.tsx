import { languageForFile } from '@/components/codeBlock/utils';
import {
  FILE_PATH_KEY,
  NEW_STRING_KEY,
  OLD_STRING_KEY,
} from '@/components/nodeDialog/conversation/toolCall/constants';
import { ToolArgument } from '@/components/nodeDialog/conversation/toolCall/toolArgument/toolArgument';
import { readTextArgument } from '@/components/nodeDialog/conversation/toolCall/utils';
import { LABELS } from '@/labels/en';

interface EditInputProps {
  input?: Record<string, unknown>;
}

/**
 * Renders the file path and both sides of the replacement of an Edit call.
 */
export const EditInput = ({ input }: EditInputProps) => {
  const filePath = readTextArgument(input, FILE_PATH_KEY);
  const language = languageForFile(filePath);

  return (
    <>
      <ToolArgument label={LABELS.toolFileLabel} text={filePath} />
      <ToolArgument
        label={LABELS.toolBeforeLabel}
        text={readTextArgument(input, OLD_STRING_KEY)}
        language={language}
      />
      <ToolArgument
        label={LABELS.toolAfterLabel}
        text={readTextArgument(input, NEW_STRING_KEY)}
        language={language}
      />
    </>
  );
};
