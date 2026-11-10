import type { ReactNode } from 'react';

/**
 * Defines the layout axis of the panels.
 */
export enum SplitPanelDirectionEnum {
  COLUMN = 'column',
  ROW = 'row',
}

/**
 * Describes a panel's visible size and resize handle.
 */
export interface SplitPanelRow {
  panel: ReactNode;
  // The percentage of the container's size along the layout axis.
  percent: number;
  // True where a drag handle follows this panel.
  hasHandle: boolean;
}
