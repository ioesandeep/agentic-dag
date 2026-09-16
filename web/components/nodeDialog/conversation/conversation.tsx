'use client';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import { Fragment, useState } from 'react';

import { EmptyState } from '@/components/emptyState/emptyState';
import { ConversationHeader } from '@/components/nodeDialog/conversation/conversationHeader/conversationHeader';
import { MessageByRole } from '@/components/nodeDialog/conversation/messageByRole/messageByRole';
import { SessionDivider } from '@/components/nodeDialog/conversation/sessionDivider/sessionDivider';
import {
  readSessionStarts,
  selectMessages,
} from '@/components/nodeDialog/conversation/utils';
import type { ConversationMessage } from '@/entities/conversationMessage';
import type { AgentSession } from '@/entities/nodeDetail';
import { LABELS } from '@/labels/en';

const CARD_STYLE = {
  flexGrow: 1,
  display: 'flex',
  flexDirection: 'column',
  minHeight: 0,
};

const MESSAGES_STYLE = {
  flexGrow: 1,
  minHeight: 0,
  overflowY: 'auto',
  p: 2,
  display: 'flex',
  flexDirection: 'column',
  gap: 2,
};

interface ConversationProps {
  messages: ConversationMessage[];
  sessions: AgentSession[];
  isWide: boolean;
  onToggleWidth: () => void;
}

/**
 * Renders a node's messages as one chat, oldest first.
 */
export const Conversation = ({
  messages,
  sessions,
  isWide,
  onToggleWidth,
}: ConversationProps) => {
  const [isShowingSubagents, setIsShowingSubagents] = useState(false);
  const handleToggleSubagents = () =>
    setIsShowingSubagents((isShowing) => !isShowing);

  const shownMessages = selectMessages(messages, isShowingSubagents);
  const sessionStarts = readSessionStarts(shownMessages, sessions);
  const header = (
    <ConversationHeader
      isWide={isWide}
      isShowingSubagents={isShowingSubagents}
      onToggleWidth={onToggleWidth}
      onToggleSubagents={handleToggleSubagents}
    />
  );

  if (shownMessages.length === 0) {
    return (
      <Card sx={CARD_STYLE}>
        {header}
        <Box sx={{ p: 2 }}>
          <EmptyState
            title={LABELS.conversationEmpty}
            body={LABELS.conversationEmptyHint}
          />
        </Box>
      </Card>
    );
  }

  return (
    <Card sx={CARD_STYLE}>
      {header}
      <Box sx={MESSAGES_STYLE}>
        {shownMessages.map((message) => (
          <Fragment key={message.uuid}>
            <SessionDivider
              sessionStart={sessionStarts.get(message.uuid) ?? null}
            />
            <MessageByRole message={message} />
          </Fragment>
        ))}
      </Box>
    </Card>
  );
};
