import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import { SubagentChip } from '@/components/nodeDialog/conversation/subagentChip/subagentChip';
import { RelativeTime } from '@/components/relativeTime/relativeTime';
import type { ConversationMessage } from '@/entities/conversationMessage';

interface MessageHeaderProps {
  title: string;
  message: ConversationMessage;
}

/**
 * Renders the author, the subagent chip and the timestamp of one message.
 */
export const MessageHeader = ({ title, message }: MessageHeaderProps) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{ fontWeight: 600, textTransform: 'uppercase' }}
    >
      {title}
    </Typography>
    <SubagentChip message={message} />
    <Box sx={{ flexGrow: 1 }} />
    <RelativeTime at={message.timestamp} />
  </Box>
);
