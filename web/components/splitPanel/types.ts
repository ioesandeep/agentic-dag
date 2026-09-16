import type { ReactNode } from 'react';

export interface SplitPanelRow {
  panel: ReactNode;
  // The percent of the height this panel holds.
  percent: number;
  // True where a drag handle follows this panel.
  hasHandle: boolean;
}
