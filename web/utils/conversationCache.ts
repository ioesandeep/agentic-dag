import type { ConversationMessage } from '@/entities/conversationMessage';
import type { ConversationPage } from '@/entities/conversationPage';

const MAX_POLLED_PAGES = 10;
const NOT_FOUND_INDEX = -1;

/**
 * Represents the nonempty pages returned by a poll in newest-first order.
 */
export type PolledPageList = [ConversationPage, ...ConversationPage[]];

/**
 * Represents the loaded part of a node's agent transcript.
 */
export interface ConversationCache {
  // The agent session id, or an empty string when the node has no transcript.
  sessionId: string;
  // The loaded messages in oldest-first order.
  messages: ConversationMessage[];
  // The cursor for the page of older messages, or null when the oldest message is loaded.
  nextCursor: number | null;
  isNewestPageLoaded: boolean;
}

export const NO_CONVERSATION_CACHE: ConversationCache = {
  sessionId: '',
  messages: [],
  nextCursor: null,
  isNewestPageLoaded: false,
};

const listMessageIds = (messages: ConversationMessage[]): Set<string> =>
  new Set(messages.map((message) => message.id));

const createConversationCache = (
  newestPage: ConversationPage,
): ConversationCache => ({
  sessionId: newestPage.sessionId,
  messages: newestPage.messages.toReversed(),
  nextCursor: newestPage.pagination.nextCursor,
  isNewestPageLoaded: true,
});

const isSameMessage = (
  cachedMessage: ConversationMessage,
  polledMessage: ConversationMessage,
): boolean => {
  const cachedMessageJson = JSON.stringify(cachedMessage);
  const polledMessageJson = JSON.stringify(polledMessage);

  return cachedMessageJson === polledMessageJson;
};

const getLatestMessage = (
  cachedMessage: ConversationMessage,
  polledMessagesById: Map<string, ConversationMessage>,
): ConversationMessage => {
  const polledMessage = polledMessagesById.get(cachedMessage.id);

  if (polledMessage === undefined) {
    return cachedMessage;
  }

  const isUnchanged = isSameMessage(cachedMessage, polledMessage);

  if (isUnchanged) {
    return cachedMessage;
  }

  return polledMessage;
};

/**
 * Returns the cache with the polled messages merged in, or a cache of the newest polled page when the polled and cached messages do not overlap.
 */
export const mergePolledPages = (
  conversationCache: ConversationCache,
  polledPageList: PolledPageList,
): ConversationCache => {
  const [newestPage] = polledPageList;
  const polledMessages = polledPageList.flatMap((page) => page.messages);
  const cachedMessageIds = listMessageIds(conversationCache.messages);
  const overlapIndex = polledMessages.findIndex((message) =>
    cachedMessageIds.has(message.id),
  );
  const isSameSession =
    conversationCache.isNewestPageLoaded &&
    conversationCache.sessionId === newestPage.sessionId;

  if (!isSameSession || overlapIndex === NOT_FOUND_INDEX) {
    return createConversationCache(newestPage);
  }

  const polledMessagesById = new Map(
    polledMessages.map((message) => [message.id, message]),
  );
  const cachedMessages = conversationCache.messages.map((message) =>
    getLatestMessage(message, polledMessagesById),
  );
  const newMessages = polledMessages.slice(0, overlapIndex).toReversed();

  return {
    ...conversationCache,
    messages: [...cachedMessages, ...newMessages],
  };
};

/**
 * Returns the cache with `olderPage` prepended, the cache unchanged when `before` is no longer its next cursor, or an empty cache when `olderPage` is null or has a different session id.
 */
export const prependOlderPage = (
  conversationCache: ConversationCache,
  olderPage: ConversationPage | null,
  before: number,
): ConversationCache => {
  if (conversationCache.nextCursor !== before) {
    return conversationCache;
  }

  const isSameSession = olderPage?.sessionId === conversationCache.sessionId;

  if (olderPage === null || !isSameSession) {
    return NO_CONVERSATION_CACHE;
  }

  const olderMessages = olderPage.messages.toReversed();

  return {
    ...conversationCache,
    messages: [...olderMessages, ...conversationCache.messages],
    nextCursor: olderPage.pagination.nextCursor,
  };
};

/**
 * Returns the timestamp of the oldest loaded message, or null when every message of the transcript is loaded.
 */
export const getLoadedSince = (
  conversationCache: ConversationCache,
): string | null => {
  if (conversationCache.nextCursor === null) {
    return null;
  }

  return conversationCache.messages[0]?.timestamp ?? null;
};

/**
 * Returns the cursor of the next older page to poll, or null when the poll needs no more pages.
 */
export const getNextPollCursor = (
  conversationCache: ConversationCache,
  polledPageList: PolledPageList,
): number | null => {
  const [newestPage] = polledPageList;
  const polledMessages = polledPageList.flatMap((page) => page.messages);
  const cachedMessageIds = listMessageIds(conversationCache.messages);
  const hasOverlap = polledMessages.some((message) =>
    cachedMessageIds.has(message.id),
  );
  const canOverlap =
    cachedMessageIds.size > 0 &&
    conversationCache.sessionId === newestPage.sessionId;
  const hasPageLeft = polledPageList.length < MAX_POLLED_PAGES;

  if (hasOverlap || !canOverlap || !hasPageLeft) {
    return null;
  }

  return polledPageList.at(-1)?.pagination.nextCursor ?? null;
};
