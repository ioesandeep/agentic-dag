'use client';

import { useSyncExternalStore } from 'react';

const TRUE_TEXT = 'true';

const listeners = new Set<() => void>();

const subscribe = (onStoreChange: () => void): (() => void) => {
  listeners.add(onStoreChange);

  return () => {
    listeners.delete(onStoreChange);
  };
};

const readFlag = (key: string, fallback: boolean): boolean => {
  const stored = window.localStorage.getItem(key);

  if (stored === null) {
    return fallback;
  }

  return stored === TRUE_TEXT;
};

const writeFlag = (key: string, value: boolean): void => {
  window.localStorage.setItem(key, String(value));
  listeners.forEach((listener) => listener());
};

export interface StoredFlag {
  isOn: boolean;
  // Flips the flag and stores the new value.
  toggle: () => void;
}

/**
 * Returns a boolean stored in the browser.
 */
export const useStoredFlag = (key: string, fallback: boolean): StoredFlag => {
  const getSnapshot = () => readFlag(key, fallback);
  const getServerSnapshot = () => fallback;
  const isOn = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const toggle = () => writeFlag(key, !isOn);

  return { isOn, toggle };
};
