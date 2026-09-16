import type { MouseEvent } from 'react';

/**
 * Returns true where a click opens the link in the tab it happens in.
 */
export const isSameTabClick = (event: MouseEvent<HTMLElement>): boolean =>
  !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
