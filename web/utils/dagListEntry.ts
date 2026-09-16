import type { DagSummary } from '@/entities/dagSummary';

const ENTRY_KEY = 'dagListEntry';

/**
 * Records the dags the dag list is handing to a dag page it opens.
 */
export const createEntryFromDagList = (dags: DagSummary[]): void => {
  const entry = JSON.stringify(dags);

  window.sessionStorage.setItem(ENTRY_KEY, entry);
};

/**
 * Returns the dags the dag list handed over, null where it opened nothing.
 */
export const findEntryFromDagList = (): DagSummary[] | null => {
  if (typeof window === 'undefined') {
    return null;
  }

  const entry = window.sessionStorage.getItem(ENTRY_KEY);

  if (entry === null) {
    return null;
  }

  return JSON.parse(entry) as DagSummary[];
};

/**
 * Drops the record the dag list left, so a later visit reads none.
 */
export const deleteEntryFromDagList = (): void =>
  window.sessionStorage.removeItem(ENTRY_KEY);
