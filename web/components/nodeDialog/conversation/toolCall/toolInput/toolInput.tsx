import { BashInput } from '@/components/nodeDialog/conversation/toolCall/bashInput/bashInput';
import { EditInput } from '@/components/nodeDialog/conversation/toolCall/editInput/editInput';
import { GenericInput } from '@/components/nodeDialog/conversation/toolCall/genericInput/genericInput';
import { ReadInput } from '@/components/nodeDialog/conversation/toolCall/readInput/readInput';
import { ToolName } from '@/components/nodeDialog/conversation/toolCall/types';
import { WriteInput } from '@/components/nodeDialog/conversation/toolCall/writeInput/writeInput';

interface ToolInputProps {
  toolName: string;
  input?: Record<string, unknown>;
}

/**
 * Renders the arguments of a tool call with the component that matches the tool.
 */
export const ToolInput = ({ toolName, input }: ToolInputProps) => {
  switch (toolName) {
    case ToolName.BASH:
      return <BashInput input={input} />;
    case ToolName.READ:
      return <ReadInput input={input} />;
    case ToolName.WRITE:
      return <WriteInput input={input} />;
    case ToolName.EDIT:
      return <EditInput input={input} />;
    default:
      return <GenericInput input={input} />;
  }
};
