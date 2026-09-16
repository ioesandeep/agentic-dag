import { CodeBlock } from '@/components/codeBlock/codeBlock';
import { HighlightLanguage } from '@/components/codeBlock/types';
import { ToolCaption } from '@/components/nodeDialog/conversation/toolCall/toolCaption/toolCaption';
import { renderArguments } from '@/components/nodeDialog/conversation/toolCall/utils';
import { LABELS } from '@/labels/en';

interface GenericInputProps {
  input?: Record<string, unknown>;
}

/**
 * Renders the arguments of a tool call as json.
 */
export const GenericInput = ({ input }: GenericInputProps) => {
  const rendered = renderArguments(input);

  if (rendered === '') {
    return <ToolCaption text={LABELS.toolNoInput} />;
  }

  return <CodeBlock text={rendered} language={HighlightLanguage.JSON} />;
};
