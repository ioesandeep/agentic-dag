import type { MouseEvent } from 'react';

/**
 * The handler a DagCard calls when a person clicks it.
 */
export type DagCardSelect = (event: MouseEvent<HTMLElement>) => void;

/**
 * The variants of the DagCard.
 */
export enum DagCardVariant {
  FULL = 'full',
  FLEXIBLE = 'flexible',
  MINIMAL = 'minimal',
}
