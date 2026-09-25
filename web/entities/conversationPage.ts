import type { ConversationMessage } from '@/entities/conversationMessage';

/**
 * The cursor and the size of a page of a collection.
 */
export interface Pagination {
  // The cursor for the page of older items, or null for the page with the oldest items.
  nextCursor: number | null;
  // The requested page size.
  perPage: number;
}

/**
 * Represents a page of a node's agent transcript.
 */
export interface ConversationPage {
  // The agent session id, or an empty string when the node has no transcript.
  sessionId: string;
  // The page's messages in newest-first order.
  messages: ConversationMessage[];
  pagination: Pagination;
}
