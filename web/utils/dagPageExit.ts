const EXIT_KEY = 'dagPageExit';
const EXIT_VALUE = 'true';

/**
 * Records an exit from the dag page.
 */
export const createExitFromDagPage = (): void =>
  window.sessionStorage.setItem(EXIT_KEY, EXIT_VALUE);

/**
 * Returns true when an exit from the dag page is recorded.
 */
export const isExitFromDagPage = (): boolean => {
  if (typeof window === 'undefined') {
    return false;
  }

  return window.sessionStorage.getItem(EXIT_KEY) === EXIT_VALUE;
};

/**
 * Deletes the recorded exit from the dag page.
 */
export const deleteExitFromDagPage = (): void =>
  window.sessionStorage.removeItem(EXIT_KEY);
