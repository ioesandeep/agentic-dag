import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

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
      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
        {message.text ?? ''}
      </Typography>
    </Box>
  </Box>
);
