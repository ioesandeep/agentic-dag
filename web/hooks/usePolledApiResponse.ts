'use client';

import { useEffect, useState } from 'react';

import { useIsTabVisible } from '@/hooks/useIsTabVisible';

export const POLL_INTERVAL_MS = 5000;
const NOT_FOUND_STATUS = 404;
const NO_RESPONSE_YET = { response: null, isMissing: false, hasFailed: false };

export interface PolledApiResponse<TResponse> {
  // The last body the api sent, null until it sends one.
  response: TResponse | null;
  // True where the api responds 404 because this host has no such record.
  isMissing: boolean;
  // True where the last request failed and the body on screen is out of date.
  hasFailed: boolean;
}

/**
 * Returns the response of an api path, with no body when the path responds 404 or the request fails.
 */
export const getApiResponse = async <TResponse>(
  path: string,
  controller: AbortController,
): Promise<PolledApiResponse<TResponse>> => {
  try {
    const requestInit = { signal: controller.signal };
    const httpResponse = await fetch(path, requestInit);

    if (httpResponse.status === NOT_FOUND_STATUS) {
      return { response: null, isMissing: true, hasFailed: false };
    }

    if (!httpResponse.ok) {
      return { response: null, isMissing: false, hasFailed: true };
    }

    const body = (await httpResponse.json()) as TResponse;

    return { response: body, isMissing: false, hasFailed: false };
  } catch {
    return { response: null, isMissing: false, hasFailed: true };
  }
};

const getLatestResponse = <TResponse>(
  previousResponse: PolledApiResponse<TResponse>,
  apiResponse: PolledApiResponse<TResponse>,
): PolledApiResponse<TResponse> => {
  if (!apiResponse.hasFailed) {
    return apiResponse;
  }

  return {
    response: previousResponse.response,
    isMissing: false,
    hasFailed: true,
  };
};

/**
 * Cancels a poll and its in-flight request.
 */
export const stopPolling = (
  timer: number,
  controller: AbortController,
): void => {
  window.clearInterval(timer);
  controller.abort();
};

/**
 * Returns true where a failed request has left a screen with nothing to show.
 */
export const hasNoResponseToShow = (
  polledResponse: PolledApiResponse<unknown>,
): boolean => polledResponse.hasFailed && polledResponse.response === null;

/**
 * Returns the latest body an api path sent, refetched while the tab is visible.
 */
export const usePolledApiResponse = <TResponse>(
  path: string,
): PolledApiResponse<TResponse> => {
  const [polledResponse, setPolledResponse] =
    useState<PolledApiResponse<TResponse>>(NO_RESPONSE_YET);
  const isTabVisible = useIsTabVisible();

  useEffect(() => {
    if (!isTabVisible) {
      return;
    }

    const controller = new AbortController();

    const refreshResponse = async (): Promise<void> => {
      const apiResponse = await getApiResponse<TResponse>(path, controller);

      if (controller.signal.aborted) {
        return;
      }

      setPolledResponse((previousResponse) =>
        getLatestResponse(previousResponse, apiResponse),
      );
    };

    void refreshResponse();
    const timer = window.setInterval(refreshResponse, POLL_INTERVAL_MS);

    return () => stopPolling(timer, controller);
  }, [path, isTabVisible]);

  return polledResponse;
};
