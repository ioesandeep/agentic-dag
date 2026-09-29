const EXIT_KEY = 'nodePageExit';
const EXIT_VALUE = 'true';

/**
 * Records an exit from the node page.
 */
export const createExitFromNodePage = (): void =>
  window.sessionStorage.setItem(EXIT_KEY, EXIT_VALUE);

/**
 * Returns true when an exit from the node page is recorded.
 */
export const isExitFromNodePage = (): boolean =>
  window.sessionStorage.getItem(EXIT_KEY) === EXIT_VALUE;

/**
 * Deletes the recorded exit from the node page.
 */
export const deleteExitFromNodePage = (): void =>
  window.sessionStorage.removeItem(EXIT_KEY);
