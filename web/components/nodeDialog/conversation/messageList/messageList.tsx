'use client';

import Box from '@mui/material/Box';
import { Fragment } from 'react';

import { MessageByRole } from '@/components/nodeDialog/conversation/messageByRole/messageByRole';
import { SessionDivider } from '@/components/nodeDialog/conversation/sessionDivider/sessionDivider';
import type { SessionStart } from '@/components/nodeDialog/conversation/types';
import type { ConversationMessage } from '@/entities/conversationMessage';
import { useConversationScroll } from '@/hooks/useConversationScroll';

const LIST_STYLE = {
  flexGrow: 1,
  minHeight: 0,
  overflowY: 'auto',
  overflowAnchor: 'none',
  p: 2,
  display: 'flex',
  flexDirection: 'column',
};

const TOP_EDGE_STYLE = { flexGrow: 1 };

const MESSAGES_STYLE = {
  display: 'flex',
  flexDirection: 'column',
  gap: 2,
};

interface MessageListProps {
  messages: ConversationMessage[];
  // The session start for each divider, indexed by the id of the message below it.
  sessionStarts: Map<string, SessionStart>;
  // True when the transcript has messages older than the loaded ones.
  hasOlderPage: boolean;
  onReachTopEdge: () => void;
}

/**
 * Renders the scrolling list of a node's messages.
 */
export const MessageList = ({
  messages,
  sessionStarts,
  hasOlderPage,
  onReachTopEdge,
}: MessageListProps) => {
  const { listRef, topEdgeRef, messagesRef, handleScroll } =
    useConversationScroll(hasOlderPage, onReachTopEdge);

  return (
    <Box ref={listRef} onScroll={handleScroll} sx={LIST_STYLE}>
      <Box ref={topEdgeRef} aria-hidden sx={TOP_EDGE_STYLE} />
      <Box ref={messagesRef} sx={MESSAGES_STYLE}>
        {messages.map((message) => (
          <Fragment key={message.id}>
            <SessionDivider
              sessionStart={sessionStarts.get(message.id) ?? null}
            />
            <MessageByRole message={message} />
          </Fragment>
        ))}
      </Box>
    </Box>
  );
};
