'use client';

import { useEffect, useRef, useState } from 'react';

import {
  requestNodeAction,
  type NodeActionRequestBody,
} from '@/components/actions/dag/services/nodeActionService/nodeActionService';

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
