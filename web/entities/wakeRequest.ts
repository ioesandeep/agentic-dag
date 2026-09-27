import type { RecoveryCauseEnum } from '@/entities/nodeDetail';

/**
 * Represents a request to wake a node.
 */
export interface WakeRequest {
  // The cause recorded for the node's recovery.
  cause: RecoveryCauseEnum;
  // The action recorded for the node's recovery.
  action: string;
  // The message that resumes the node's conversation.
  message: string;
}
