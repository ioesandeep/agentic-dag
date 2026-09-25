'use client';

import type { RefObject } from 'react';
import { useEffect, useRef } from 'react';

const BOTTOM_EDGE_DISTANCE_PX = 32;

interface ScrollAnchor {
  // The first element of the message list at the person's last scroll.
  element: HTMLElement;
  // The element's distance from the top of the list's visible area.
  viewportOffset: number;
}

/**
 * Represents the refs and the scroll handler of a conversation's message list.
 */
export interface ConversationScroll {
  // The scrolling element around the messages.
  listRef: RefObject<HTMLDivElement | null>;
  // The element above the first message, visible when the list is at its top edge.
  topEdgeRef: RefObject<HTMLDivElement | null>;
  // The element that contains the messages.
  messagesRef: RefObject<HTMLDivElement | null>;
  // Records where the person scrolls the list.
  handleScroll: () => void;
}

const getScrollAnchor = (
  list: HTMLElement,
  messagesElement: HTMLElement,
): ScrollAnchor | null => {
  const firstElement = messagesElement.firstElementChild;

  if (!(firstElement instanceof HTMLElement)) {
    return null;
  }

  const viewportOffset = firstElement.offsetTop - list.scrollTop;

  return { element: firstElement, viewportOffset };
};

const getDistanceFromBottom = (list: HTMLElement): number =>
  list.scrollHeight - list.scrollTop - list.clientHeight;

const getScrollTopAfterResize = (
  list: HTMLElement,
  scrollAnchor: ScrollAnchor | null,
  isAtBottom: boolean,
): number => {
  if (isAtBottom) {
    return list.scrollHeight;
  }

  if (scrollAnchor === null || !scrollAnchor.element.isConnected) {
    return list.scrollTop;
  }

  return scrollAnchor.element.offsetTop - scrollAnchor.viewportOffset;
};

/**
 * Keeps a message list at its bottom edge or at the person's scroll position, and calls `onReachTopEdge` when its top edge is visible.
 */
export const useConversationScroll = (
  hasOlderPage: boolean,
  onReachTopEdge: () => void,
): ConversationScroll => {
  const listRef = useRef<HTMLDivElement>(null);
  const topEdgeRef = useRef<HTMLDivElement>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const scrollAnchorRef = useRef<ScrollAnchor | null>(null);
  const isAtBottomRef = useRef(true);
  const resizeScrollTopRef = useRef<number | null>(null);

  const handleScroll = () => {
    const list = listRef.current;
    const messagesElement = messagesRef.current;

    if (list === null || messagesElement === null) {
      return;
    }

    const isScrollFromResize = list.scrollTop === resizeScrollTopRef.current;
    const distanceFromBottom = getDistanceFromBottom(list);
    isAtBottomRef.current = distanceFromBottom <= BOTTOM_EDGE_DISTANCE_PX;

    if (!isScrollFromResize) {
      scrollAnchorRef.current = getScrollAnchor(list, messagesElement);
    }
  };

  useEffect(() => {
    const list = listRef.current;
    const messagesElement = messagesRef.current;

    if (list === null || messagesElement === null) {
      return;
    }

    const handleResize = () => {
      list.scrollTop = getScrollTopAfterResize(
        list,
        scrollAnchorRef.current,
        isAtBottomRef.current,
      );
      resizeScrollTopRef.current = list.scrollTop;
    };
    const resizeObserver = new ResizeObserver(handleResize);

    resizeObserver.observe(list);
    resizeObserver.observe(messagesElement);

    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    const list = listRef.current;
    const topEdge = topEdgeRef.current;

    if (!hasOlderPage || list === null || topEdge === null) {
      return;
    }

    const handleIntersection = (entries: IntersectionObserverEntry[]) => {
      const isTopEdgeVisible = entries.some((entry) => entry.isIntersecting);

      if (isTopEdgeVisible) {
        onReachTopEdge();
      }
    };
    const observerOptions = { root: list };
    const observer = new IntersectionObserver(
      handleIntersection,
      observerOptions,
    );

    observer.observe(topEdge);

    return () => observer.disconnect();
  }, [hasOlderPage, onReachTopEdge]);

  return { listRef, topEdgeRef, messagesRef, handleScroll };
};
