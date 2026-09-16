'use client';

import { useSyncExternalStore } from 'react';

import { DAG_STATES, DagState } from '@/utils/dagState';
import { isUndefined } from '@/utils/typeGuards';

const DAG_STATE_FILTER_KEY = 'dagStateFilter';

const listeners = new Set<() => void>();

const subscribe = (onStoreChange: () => void): (() => void) => {
  listeners.add(onStoreChange);

  return () => {
    listeners.delete(onStoreChange);
  };
};

const readDagState = (): DagState => {
  const text = window.localStorage.getItem(DAG_STATE_FILTER_KEY);
  const stored = DAG_STATES.find((dagState) => dagState === text);

  if (isUndefined(stored)) {
    return DagState.ANY;
  }

  return stored;
};

const writeDagState = (dagState: DagState): void => {
  window.localStorage.setItem(DAG_STATE_FILTER_KEY, dagState);
  listeners.forEach((listener) => listener());
};

const getSnapshot = () => readDagState();
const getServerSnapshot = () => DagState.ANY;

export interface StoredDagState {
  // The state the dag list is filtered by.
  dagState: DagState;
  // Stores the state the dag list is filtered by.
  setDagState: (dagState: DagState) => void;
}

/**
 * Returns the dag state stored in the browser.
 */
export const useStoredDagState = (): StoredDagState => {
  // TODO: replace this module's store with a state management library.
  const storedDagState = useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot,
  );

  const setDagState = (dagState: DagState) => writeDagState(dagState);

  return { dagState: storedDagState, setDagState };
};
