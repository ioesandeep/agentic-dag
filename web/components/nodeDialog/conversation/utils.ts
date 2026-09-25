import { FIRST_WAKE } from '@/components/nodeDialog/constants';
import type { SessionStart } from '@/components/nodeDialog/conversation/types';
import { isSessionStartLoaded } from '@/components/nodeDialog/utils';
import type {
  ConversationMessage,
  ConversationRole,
} from '@/entities/conversationMessage';
import { CONVERSATION_ROLES } from '@/entities/conversationMessage';
import type { AgentSession } from '@/entities/nodeDetail';
import { LABELS } from '@/labels/en';

const BEFORE_EVERY_MESSAGE = '';

type SessionStartEntry = readonly [string, SessionStart];

const isWithin = (
  timestamp: string,
  opensAt: string,
  closesAt: string | undefined,
): boolean => {
  if (timestamp < opensAt) {
    return false;
  }

  if (closesAt === undefined) {
    return true;
  }

  return timestamp < closesAt;
};

const readSessionStart = (sessions: AgentSession[], index: number): string => {
  if (index === 0) {
    return BEFORE_EVERY_MESSAGE;
  }

  return sessions[index]?.startedAt ?? BEFORE_EVERY_MESSAGE;
};

const isStart = (start: SessionStartEntry | null): start is SessionStartEntry =>
  start !== null;

/**
 * Returns true when this screen can render a message with the given role.
 */
export const isKnownRole = (role: string): role is ConversationRole =>
  CONVERSATION_ROLES.some((known) => known === role);

/**
 * Returns true when a subagent wrote the message.
 */
export const isFromSubagent = (message: ConversationMessage): boolean =>
  message.isSidechain === true;

/**
 * Returns the messages this screen can render, without subagent messages unless asked for.
 */
export const selectMessages = (
  messages: ConversationMessage[],
  isShowingSubagents: boolean,
): ConversationMessage[] =>
  messages.filter((message) => {
    if (!isKnownRole(message.role)) {
      return false;
    }

    return isShowingSubagents || !isFromSubagent(message);
  });

/**
 * Returns each loaded session start indexed by its first shown message id.
 */
export const readSessionStarts = (
  messages: ConversationMessage[],
  sessions: AgentSession[],
  loadedSince: string | null,
): Map<string, SessionStart> => {
  const starts = sessions.map((session, index): SessionStartEntry | null => {
    const opensAt = readSessionStart(sessions, index);
    const closesAt = sessions[index + 1]?.startedAt;
    const isStartLoaded = isSessionStartLoaded(session, loadedSince);
    const first = messages.find((message) =>
      isWithin(message.timestamp, opensAt, closesAt),
    );

    if (!isStartLoaded || first === undefined) {
      return null;
    }

    const sessionStart = { session, wake: index + FIRST_WAKE };

    return [first.id, sessionStart];
  });

  return new Map(starts.filter(isStart));
};

/**
 * Returns the label for the width control's next action.
 */
export const widthToggleLabel = (isWide: boolean): string => {
  if (isWide) {
    return LABELS.conversationNarrow;
  }

  return LABELS.conversationWiden;
};
