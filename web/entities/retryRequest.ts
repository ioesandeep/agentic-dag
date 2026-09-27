/**
 * Represents the request options for retrying a node.
 */
export interface RetryRequest {
  // True when the retry resets the current session and starts a new session.
  reset: boolean;
}
