'use client';

import { useCallback, useEffect, useEffectEvent, useState } from 'react';

import type { ConversationMessage } from '@/entities/conversationMessage';
import type { ConversationPage } from '@/entities/conversationPage';
import { useIsTabVisible } from '@/hooks/useIsTabVisible';
import type { PolledApiResponse } from '@/hooks/usePolledApiResponse';
import {
  getApiResponse,
  POLL_INTERVAL_MS,
  stopPolling,
} from '@/hooks/usePolledApiResponse';
import { getConversationPath } from '@/utils/apiPath';
import type { ConversationCache, PolledPageList } from '@/utils/conversationCache';
import {
  getNextPollCursor,
  getLoadedSince,
  mergePolledPages,
  NO_CONVERSATION_CACHE,
  prependOlderPage,
} from '@/utils/conversationCache';

interface ConversationRequest {
  dagName: string;
  nodeId: string;
  controller: AbortController;
}

/**
 * Represents the loaded messages of a node's agent transcript with the state of their page requests.
 */
export interface Transcript {
  // The loaded messages in oldest-first order.
  messages: ConversationMessage[];
  // The agent session id, or an empty string when the node has no transcript.
  sessionId: string;
  // True while the newest page or an older page is loading.
  isLoadingPage: boolean;
  isNewestPageLoaded: boolean;
  // True when the transcript has messages older than the loaded ones.
  hasOlderPage: boolean;
  // The timestamp of the oldest loaded message, or null when every message of the transcript is loaded.
  loadedSince: string | null;
  // True where the last request failed and the messages on screen are out of date.
  hasFailed: boolean;
  loadOlderPage: () => void;
}

const getConversationPageResponse = (
  conversationRequest: ConversationRequest,
  before: number | null,
): Promise<PolledApiResponse<ConversationPage>> => {
  const conversationPath = getConversationPath(
    conversationRequest.dagName,
    conversationRequest.nodeId,
    before,
  );

  return getApiResponse<ConversationPage>(
    conversationPath,
    conversationRequest.controller,
  );
};

const getPagesUntilOverlap = async (
  conversationRequest: ConversationRequest,
  conversationCache: ConversationCache,
  polledPageList: PolledPageList,
): Promise<PolledPageList | null> => {
  const nextPollCursor = getNextPollCursor(conversationCache, polledPageList);

  if (nextPollCursor === null) {
    return polledPageList;
  }

  const pageResponse = await getConversationPageResponse(
    conversationRequest,
    nextPollCursor,
  );

  if (pageResponse.isMissing) {
    return polledPageList;
  }

  if (pageResponse.response === null) {
    return null;
  }

  const nextPolledPageList: PolledPageList = [
    ...polledPageList,
    pageResponse.response,
  ];

  return getPagesUntilOverlap(
    conversationRequest,
    conversationCache,
    nextPolledPageList,
  );
};

const getPolledPages = async (
  conversationRequest: ConversationRequest,
  conversationCache: ConversationCache,
): Promise<PolledPageList | null> => {
  const newestPageResponse = await getConversationPageResponse(
    conversationRequest,
    null,
  );

  if (newestPageResponse.response === null) {
    return null;
  }

  const newestPageList: PolledPageList = [newestPageResponse.response];

  return getPagesUntilOverlap(
    conversationRequest,
    conversationCache,
    newestPageList,
  );
};

/**
 * Returns the loaded part of a node's agent transcript.
 */
export const useConversationPages = (
  dagName: string,
  nodeId: string,
): Transcript => {
  const [conversationCache, setConversationCache] = useState(
    NO_CONVERSATION_CACHE,
  );
  const [olderPageCursor, setOlderPageCursor] = useState<number | null>(null);
  const [hasFailed, setHasFailed] = useState(false);
  const isTabVisible = useIsTabVisible();
  const getCurrentConversationCache = useEffectEvent(() => conversationCache);

  const isLoadingNewestPage =
    !conversationCache.isNewestPageLoaded && !hasFailed;
  const isLoadingOlderPage = olderPageCursor !== null;

  const loadOlderPage = useCallback(() => {
    if (isLoadingOlderPage || hasFailed) {
      return;
    }

    setOlderPageCursor(conversationCache.nextCursor);
  }, [conversationCache.nextCursor, isLoadingOlderPage, hasFailed]);

  useEffect(() => {
    if (!isTabVisible) {
      return;
    }

    const controller = new AbortController();
    const conversationRequest = { dagName, nodeId, controller };

    const refreshNewestPage = async (): Promise<void> => {
      const currentConversationCache = getCurrentConversationCache();
      const polledPageList = await getPolledPages(
        conversationRequest,
        currentConversationCache,
      );

      if (controller.signal.aborted) {
        return;
      }

      setHasFailed(polledPageList === null);

      if (polledPageList === null) {
        return;
      }

      setConversationCache((previousCache) =>
        mergePolledPages(previousCache, polledPageList),
      );
    };

    void refreshNewestPage();
    const timer = window.setInterval(refreshNewestPage, POLL_INTERVAL_MS);

    return () => stopPolling(timer, controller);
  }, [dagName, nodeId, isTabVisible]);

  useEffect(() => {
    if (olderPageCursor === null) {
      return;
    }

    const controller = new AbortController();
    const conversationRequest = { dagName, nodeId, controller };

    const requestOlderPage = async (): Promise<void> => {
      const olderPageResponse = await getConversationPageResponse(
        conversationRequest,
        olderPageCursor,
      );

      if (controller.signal.aborted) {
        return;
      }

      setOlderPageCursor(null);
      setHasFailed(olderPageResponse.hasFailed);

      if (olderPageResponse.hasFailed) {
        return;
      }

      setConversationCache((previousCache) =>
        prependOlderPage(
          previousCache,
          olderPageResponse.response,
          olderPageCursor,
        ),
      );
    };

    void requestOlderPage();

    return () => controller.abort();
  }, [dagName, nodeId, olderPageCursor]);

  return {
    messages: conversationCache.messages,
    sessionId: conversationCache.sessionId,
    isLoadingPage: isLoadingNewestPage || isLoadingOlderPage,
    isNewestPageLoaded: conversationCache.isNewestPageLoaded,
    hasOlderPage: conversationCache.nextCursor !== null,
    loadedSince: getLoadedSince(conversationCache),
    hasFailed,
    loadOlderPage,
  };
};
