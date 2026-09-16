import { TAB_ID_PREFIX } from '@/components/dagPanel/dagTabs/constants';
import type { DagTab } from '@/components/dagPanel/dagTabs/types';

/**
 * Returns the element id of a dag tab.
 */
export const getTabId = (tab: DagTab): string => `${TAB_ID_PREFIX}-${tab}`;
