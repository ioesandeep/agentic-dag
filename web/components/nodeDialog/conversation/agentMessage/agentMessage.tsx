import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import { MarkdownText } from '@/components/markdownText/markdownText';
import { MessageHeader } from '@/components/nodeDialog/conversation/messageHeader/messageHeader';
import type { ConversationMessage } from '@/entities/conversationMessage';
import { LABELS } from '@/labels/en';

interface AgentMessageProps {
  message: ConversationMessage;
}

/**
 * Renders the agent's text for one message.
 */
export const AgentMessage = ({ message }: AgentMessageProps) => (
  <Box>
    <MessageHeader title={LABELS.agentMessageTitle} message={message} />
    <Typography component="div" variant="body1">
      <MarkdownText text={message.text ?? ''} />
    </Typography>
  </Box>
);
