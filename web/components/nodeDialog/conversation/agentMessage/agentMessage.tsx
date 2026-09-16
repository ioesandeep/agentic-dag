import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

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
    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
      {message.text ?? ''}
    </Typography>
  </Box>
);
