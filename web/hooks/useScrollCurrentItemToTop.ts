'use client';

import type { RefObject } from 'react';
import { useEffect, useRef } from 'react';

const scrollItemToTop = (list: HTMLElement, item: Element): void => {
  const listTop = list.getBoundingClientRect().top;
  const itemTop = item.getBoundingClientRect().top;
  list.scrollTop += itemTop - listTop;
};

/**
 * Returns the ref for a list that starts scrolled to its current item.
 */
export const useScrollCurrentItemToTop = (
  currentIndex: number,
): RefObject<HTMLDivElement | null> => {
  const listRef = useRef<HTMLDivElement>(null);
  const hasScrolledRef = useRef(false);

  useEffect(() => {
    const list = listRef.current;

    if (hasScrolledRef.current || list === null) {
      return;
    }

    const currentItem = list.children.item(currentIndex);

    if (currentItem === null) {
      return;
    }

    const frame = window.requestAnimationFrame(() => {
      hasScrolledRef.current = true;
      scrollItemToTop(list, currentItem);
    });

    return () => window.cancelAnimationFrame(frame);
  }, [currentIndex]);

  return listRef;
};
