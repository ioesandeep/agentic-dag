'use client';

import { useEffect, useRef, useState } from 'react';

import type { ApiErrorResponse } from '@/entities/apiErrorResponse';
import type { RetryRequest } from '@/entities/retryRequest';
import type { WakeRequest } from '@/entities/wakeRequest';
import { LABELS } from '@/labels/en';
import { ContentTypeEnum } from '@/utils/contentType';
import { HttpMethodEnum } from '@/utils/httpMethod';

const JSON_HEADERS = { 'Content-Type': ContentTypeEnum.APPLICATION_JSON };

type NodeActionRequestBody = RetryRequest | WakeRequest;

/**
 * Represents the mutation that posts an action on a node.
 */
export interface NodeActionMutation {
  // True while the request is in flight.
  isPending: boolean;
  // The detail of the last failed request, or null when the last request succeeded or none was sent.
  failureDetail: string | null;
  postNodeAction: (requestBody: NodeActionRequestBody | null) => void;
}

const hasDetail = (body: unknown): body is ApiErrorResponse =>
  typeof body === 'object' &&
  body !== null &&
  'detail' in body &&
  typeof body.detail === 'string';

const getRequestInit = (
  requestBody: NodeActionRequestBody | null,
  controller: AbortController,
): RequestInit => {
  if (requestBody === null) {
    return { method: HttpMethodEnum.POST, signal: controller.signal };
  }

  return {
    method: HttpMethodEnum.POST,
    headers: JSON_HEADERS,
    body: JSON.stringify(requestBody),
    signal: controller.signal,
  };
};

const getFailureDetail = async (httpResponse: Response): Promise<string> => {
  try {
    const body: unknown = await httpResponse.json();
    const isApiErrorResponse = hasDetail(body);

    if (isApiErrorResponse) {
      return body.detail;
    }

    return LABELS.nodeActionFailed;
  } catch {
    return LABELS.nodeActionFailed;
  }
};

const requestNodeAction = async (
  nodeActionPath: string,
  requestBody: NodeActionRequestBody | null,
  controller: AbortController,
): Promise<string | null> => {
  try {
    const requestInit = getRequestInit(requestBody, controller);
    const httpResponse = await fetch(nodeActionPath, requestInit);

    if (httpResponse.ok) {
      return null;
    }

    return await getFailureDetail(httpResponse);
  } catch {
    return LABELS.nodeActionFailed;
  }
};

/**
 * Returns the mutation that posts an action on a node, and calls `onSuccess` when the api responds with a success status.
 */
export const useNodeAction = (
  nodeActionPath: string,
  onSuccess: () => void,
): NodeActionMutation => {
  const controllerRef = useRef<AbortController | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [failureDetail, setFailureDetail] = useState<string | null>(null);

  const sendNodeAction = async (
    requestBody: NodeActionRequestBody | null,
    controller: AbortController,
  ): Promise<void> => {
    const requestFailureDetail = await requestNodeAction(
      nodeActionPath,
      requestBody,
      controller,
    );

    if (controller.signal.aborted) {
      return;
    }

    setIsPending(false);
    setFailureDetail(requestFailureDetail);

    if (requestFailureDetail === null) {
      onSuccess();
    }
  };

  const postNodeAction = (requestBody: NodeActionRequestBody | null) => {
    const controller = new AbortController();
    controllerRef.current = controller;

    setIsPending(true);
    setFailureDetail(null);
    void sendNodeAction(requestBody, controller);
  };

  useEffect(() => () => controllerRef.current?.abort(), []);

  return { isPending, failureDetail, postNodeAction };
};
