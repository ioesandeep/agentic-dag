'use client';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import LinearProgress from '@mui/material/LinearProgress';
import { useState } from 'react';

import { EmptyState } from '@/components/emptyState/emptyState';
import { ConversationHeader } from '@/components/nodeDialog/conversation/conversationHeader/conversationHeader';
import { MessageList } from '@/components/nodeDialog/conversation/messageList/messageList';
import {
  readSessionStarts,
  selectMessages,
} from '@/components/nodeDialog/conversation/utils';
import { RequestFailureAlert } from '@/components/requestFailureAlert/requestFailureAlert';
import type { AgentSession } from '@/entities/nodeDetail';
import type { Transcript } from '@/hooks/useConversationPages';
import { LABELS } from '@/labels/en';

const CARD_STYLE = {
  flexGrow: 1,
  display: 'flex',
  flexDirection: 'column',
  minHeight: 0,
};

const LIST_AREA_STYLE = {
  position: 'relative',
  flexGrow: 1,
  minHeight: 0,
  display: 'flex',
  flexDirection: 'column',
};

const PAGE_LOADING_STYLE = {
  position: 'absolute',
  top: 0,
  left: 0,
  right: 0,
  zIndex: 1,
};

interface ConversationProps {
  transcript: Transcript;
  sessions: AgentSession[];
  isWide: boolean;
  onToggleWidth: () => void;
}

/**
 * Renders the conversation card of a node.
 */
export const Conversation = ({
  transcript,
  sessions,
  isWide,
  onToggleWidth,
}: ConversationProps) => {
  const [isShowingSubagents, setIsShowingSubagents] = useState(false);
  const handleToggleSubagents = () =>
    setIsShowingSubagents((isShowing) => !isShowing);

  const shownMessages = selectMessages(
    transcript.messages,
    isShowingSubagents,
  );
  const sessionStarts = readSessionStarts(
    shownMessages,
    sessions,
    transcript.loadedSince,
  );
  const isEmpty =
    transcript.isNewestPageLoaded &&
    !transcript.hasOlderPage &&
    shownMessages.length === 0;
  const header = (
    <ConversationHeader
      isWide={isWide}
      isShowingSubagents={isShowingSubagents}
      onToggleWidth={onToggleWidth}
      onToggleSubagents={handleToggleSubagents}
    />
  );

  if (isEmpty) {
    return (
      <Card sx={CARD_STYLE}>
        {header}
        <RequestFailureAlert hasFailed={transcript.hasFailed} />
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
      <RequestFailureAlert hasFailed={transcript.hasFailed} />
      <Box sx={LIST_AREA_STYLE}>
        {transcript.isLoadingPage && (
          <Box
            role="status"
            aria-label={LABELS.conversationLoading}
            sx={PAGE_LOADING_STYLE}
          >
            <LinearProgress />
          </Box>
        )}
        <MessageList
          key={transcript.sessionId}
          messages={shownMessages}
          sessionStarts={sessionStarts}
          hasOlderPage={transcript.hasOlderPage}
          onReachTopEdge={transcript.loadOlderPage}
        />
      </Box>
    </Card>
  );
};
