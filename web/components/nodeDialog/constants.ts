import type { DagCardAction } from '@/components/dagList/dagCard/dagCardHeader/types';

export const NO_ACTIONS: DagCardAction[] = [];
export const CONVERSATION_COLUMN_WIDTH = 8;
export const SIDEBAR_COLUMN_WIDTH = 4;
export const SESSION_ANCHOR_PREFIX = 'nodeDialogWake';
export const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';
export const REDUCED_MOTION_SELECTOR = `@media ${REDUCED_MOTION_QUERY}`;
export const SCROLL_BLOCK: ScrollLogicalPosition = 'start';
export const NODE_DETAILS_SIDEBAR_WIDTH = '16.25rem';
export const GRAPH_LEFT_EDGE = 'calc(20vw - 0.5rem)';
export const COLLAPSED_GRAPH_LEFT_EDGE = '4rem';
export const INFO_MAIN_COLOR = 'var(--mui-palette-info-main)';
export const PRIMARY_MAIN_COLOR = 'var(--mui-palette-primary-main)';
export const ERROR_MAIN_COLOR = 'var(--mui-palette-error-main)';
export const FIRST_WAKE = 1;
