'use client';

import { useSyncExternalStore } from 'react';

const VISIBLE_STATE = 'visible';
const VISIBILITY_EVENT = 'visibilitychange';

const subscribeToTabVisibility = (onStoreChange: () => void): (() => void) => {
  document.addEventListener(VISIBILITY_EVENT, onStoreChange);

  return () => document.removeEventListener(VISIBILITY_EVENT, onStoreChange);
};

const getIsTabVisible = (): boolean =>
  document.visibilityState === VISIBLE_STATE;

const getIsTabVisibleOnServer = (): boolean => false;

/**
 * Returns true while the browser tab holding this screen is visible.
 */
export const useIsTabVisible = (): boolean =>
  useSyncExternalStore(
    subscribeToTabVisibility,
    getIsTabVisible,
    getIsTabVisibleOnServer,
  );
