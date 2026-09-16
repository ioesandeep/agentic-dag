/**
 * Whether the value is null.
 */
export const isNull = (value: unknown): value is null => value === null;

/**
 * Whether the value is undefined.
 */
export const isUndefined = (value: unknown): value is undefined =>
  value === undefined;
