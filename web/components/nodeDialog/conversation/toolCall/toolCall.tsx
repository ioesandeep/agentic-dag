import Box from '@mui/material/Box';
import Card from '@mui/material/Card';

import { MessageHeader } from '@/components/nodeDialog/conversation/messageHeader/messageHeader';
import { ToolInput } from '@/components/nodeDialog/conversation/toolCall/toolInput/toolInput';
import { ToolResult } from '@/components/nodeDialog/conversation/toolCall/toolResult/toolResult';
import type { ConversationMessage } from '@/entities/conversationMessage';
import { LABELS } from '@/labels/en';

interface ToolCallProps {
  message: ConversationMessage;
}

/**
 * Renders one tool call with its name, its arguments and its result.
 */
export const ToolCall = ({ message }: ToolCallProps) => {
  const toolName = message.toolName ?? '';

  return (
    <Box>
      <MessageHeader title={toolName || LABELS.toolUnnamed} message={message} />
      <Card
        sx={{ p: 1.5, display: 'flex', flexDirection: 'column', gap: 0.75 }}
      >
        <ToolInput toolName={toolName} input={message.toolInput} />
        <ToolResult text={message.toolResult} />
      </Card>
    </Box>
  );
};
