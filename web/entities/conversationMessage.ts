export type ConversationRole = 'user' | 'assistant' | 'tool_use';

export const USER_ROLE: ConversationRole = 'user';
export const ASSISTANT_ROLE: ConversationRole = 'assistant';
export const TOOL_USE_ROLE: ConversationRole = 'tool_use';

export const CONVERSATION_ROLES: readonly ConversationRole[] = [
  USER_ROLE,
  ASSISTANT_ROLE,
  TOOL_USE_ROLE,
];

export interface ConversationMessage {
  // The message's id, which is unique across pages even when the message's uuid repeats.
  id: string;
  // The transcript's own id for the message, which the messages of one record can share.
  uuid: string;
  // The role the transcript gives the message.
  role: string;
  timestamp: string;
  // True when a subagent wrote the message.
  isSidechain?: boolean;
  // The text of a user or agent message.
  text?: string;
  // The tool a tool_use message called.
  toolName?: string;
  // The arguments the tool was called with, keyed by the tool's parameter names.
  toolInput?: Record<string, unknown>;
  toolResult?: string;
}
