import type { ApiErrorResponse } from '@/entities/apiErrorResponse';
import type { RetryRequest } from '@/entities/retryRequest';
import type { WakeRequest } from '@/entities/wakeRequest';
import { LABELS } from '@/labels/en';
import { ContentTypeEnum } from '@/utils/contentType';
import { HttpMethodEnum } from '@/utils/httpMethod';

const JSON_HEADERS = { 'Content-Type': ContentTypeEnum.APPLICATION_JSON };

/**
 * The body of a node action request; retry and wake send one, stop sends none.
 */
export type NodeActionRequestBody = RetryRequest | WakeRequest;

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

/**
 * Posts an action on a node and returns the failure detail, or null when the api accepts it.
 */
export const requestNodeAction = async (
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
