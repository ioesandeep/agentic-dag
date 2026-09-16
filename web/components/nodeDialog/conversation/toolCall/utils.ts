import { JSON_INDENT } from '@/components/nodeDialog/conversation/toolCall/constants';

/**
 * Returns one text argument of a tool call, or an empty string when it is absent.
 */
export const readTextArgument = (
  input: Record<string, unknown> | undefined,
  key: string,
): string => {
  const value = input?.[key];

  if (typeof value === 'string') {
    return value;
  }

  return '';
};

/**
 * Returns a tool call's arguments as formatted json.
 */
export const renderArguments = (
  input: Record<string, unknown> | undefined,
): string => {
  if (input === undefined) {
    return '';
  }

  return JSON.stringify(input, null, JSON_INDENT);
};
