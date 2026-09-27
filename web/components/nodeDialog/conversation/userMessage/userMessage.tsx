import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import { MarkdownText } from '@/components/markdownText/markdownText';
import { MessageHeader } from '@/components/nodeDialog/conversation/messageHeader/messageHeader';
import type { ConversationMessage } from '@/entities/conversationMessage';
import { LABELS } from '@/labels/en';

interface UserMessageProps {
  message: ConversationMessage;
}

/**
 * Renders the prompt text for one message.
 */
export const UserMessage = ({ message }: UserMessageProps) => (
  <Box>
    <MessageHeader title={LABELS.userMessageTitle} message={message} />
    <Box
      sx={{
        p: 1.5,
        borderRadius: 1,
        borderLeft: 3,
        borderColor: 'primary.main',
        bgcolor: 'action.hover',
      }}
    >
      <Typography component="div" variant="body2">
        <MarkdownText text={message.text ?? ''} />
      </Typography>
    </Box>
  </Box>
);
