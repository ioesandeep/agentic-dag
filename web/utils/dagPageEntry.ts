const ENTRY_KEY = 'dagPageEntry';
const ENTRY_MARK = 'true';

/**
 * Records that the dag page is opening one of its nodes.
 */
export const createEntryFromDagPage = (): void =>
  window.sessionStorage.setItem(ENTRY_KEY, ENTRY_MARK);

/**
 * Returns true where the dag page opened the node on screen.
 */
export const isEntryFromDagPage = (): boolean => {
  if (typeof window === 'undefined') {
    return false;
  }

  return window.sessionStorage.getItem(ENTRY_KEY) === ENTRY_MARK;
};

/**
 * Drops the record the dag page left, so a later visit reads none.
 */
export const deleteEntryFromDagPage = (): void =>
  window.sessionStorage.removeItem(ENTRY_KEY);
