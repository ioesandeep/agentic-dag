import type { SxProps, Theme } from '@mui/material/styles';

import type { NodeDetail, NodeLink } from '@/entities/nodeDetail';
import {
  COLLAPSED_GRAPH_LEFT_EDGE,
  GRAPH_LEFT_EDGE,
  NODE_DETAILS_SIDEBAR_WIDTH,
  REDUCED_MOTION_QUERY,
  REDUCED_MOTION_SELECTOR,
  SCROLL_BLOCK,
  SESSION_ANCHOR_PREFIX,
} from '@/components/nodeDialog/constants';
import { SCREEN_ENTRANCE_MS } from '@/theme/constants';

const readScrollBehavior = (): ScrollBehavior => {
  if (window.matchMedia(REDUCED_MOTION_QUERY).matches) {
    return 'auto';
  }

  return 'smooth';
};

const ENTRANCE_ANIMATION = `nodeSidebarEnter ${SCREEN_ENTRANCE_MS}ms ease-out`;
const NO_ENTRANCE_ANIMATION = 'none';

const getEntranceAnimation = (isEnteringFromDagPage: boolean): string => {
  if (isEnteringFromDagPage) {
    return ENTRANCE_ANIMATION;
  }

  return NO_ENTRANCE_ANIMATION;
};

const getGraphLeftEdge = (isDagSidebarCollapsed: boolean): string => {
  if (isDagSidebarCollapsed) {
    return COLLAPSED_GRAPH_LEFT_EDGE;
  }

  return GRAPH_LEFT_EDGE;
};

const getSidebarDisplay = (
  isConversationWide: boolean,
): Record<string, string> => {
  if (isConversationWide) {
    return { xs: 'none', md: 'none' };
  }

  return { xs: 'none', md: 'flex' };
};

/**
 * Returns the style of the node details sidebar column.
 */
export const getNodeDetailsSidebarStyle = (
  isConversationWide: boolean,
  isDagSidebarCollapsed: boolean,
  isEnteringFromDagPage: boolean,
): SxProps<Theme> => ({
  width: NODE_DETAILS_SIDEBAR_WIDTH,
  flexShrink: 0,
  minHeight: 0,
  display: getSidebarDisplay(isConversationWide),
  flexDirection: 'column',
  '--node-sidebar-offset': getGraphLeftEdge(isDagSidebarCollapsed),
  animation: getEntranceAnimation(isEnteringFromDagPage),
  [REDUCED_MOTION_SELECTOR]: { animation: NO_ENTRANCE_ANIMATION },
});

/**
 * Returns the record of the node on screen, null while another one's is held.
 */
export const findDetailOfNode = (
  detail: NodeDetail | null,
  nodeId: string,
): NodeDetail | null => {
  if (detail === null || detail.id !== nodeId) {
    return null;
  }

  return detail;
};

/**
 * Returns the nodes carrying one of these ids.
 */
export const listNodeLinksByIds = (
  nodeIds: string[],
  nodeLinks: NodeLink[],
): NodeLink[] => nodeLinks.filter((nodeLink) => nodeIds.includes(nodeLink.id));

/**
 * Returns the url of a node's screen.
 */
export const nodePath = (dagName: string, nodeId: string): string =>
  `/dags/${dagName}/${nodeId}`;

/**
 * Returns the dom id of a session's divider.
 */
export const sessionAnchorId = (wake: number): string =>
  `${SESSION_ANCHOR_PREFIX}${wake}`;

/**
 * Scrolls the conversation to where a session begins.
 */
export const scrollToSession = (wake: number): void => {
  const anchor = document.getElementById(sessionAnchorId(wake));

  if (anchor === null) {
    return;
  }

  const scrollOptions: ScrollIntoViewOptions = {
    behavior: readScrollBehavior(),
    block: SCROLL_BLOCK,
  };

  anchor.scrollIntoView(scrollOptions);
};
