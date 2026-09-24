import { memo } from 'react';

import { AgentMessage } from '@/components/nodeDialog/conversation/agentMessage/agentMessage';
import { ToolCall } from '@/components/nodeDialog/conversation/toolCall/toolCall';
import { UserMessage } from '@/components/nodeDialog/conversation/userMessage/userMessage';
import type { ConversationMessage } from '@/entities/conversationMessage';
import {
  ASSISTANT_ROLE,
  TOOL_USE_ROLE,
  USER_ROLE,
} from '@/entities/conversationMessage';

interface MessageByRoleProps {
  message: ConversationMessage;
}

/**
 * Renders one message with the component that matches its role.
 */
export const MessageByRole = memo(({ message }: MessageByRoleProps) => {
  switch (message.role) {
    case USER_ROLE:
      return <UserMessage message={message} />;
    case ASSISTANT_ROLE:
      return <AgentMessage message={message} />;
    case TOOL_USE_ROLE:
      return <ToolCall message={message} />;
    default:
      return null;
  }
});

MessageByRole.displayName = 'MessageByRole';
