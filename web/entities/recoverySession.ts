/**
 * Represents a single execution of the recovery agent over a batch of nodes.
 */
export interface RecoverySession {
  id: number;
  startedAt: string;
  endedAt: string | null;
  // The ids of the nodes in the session's batch.
  nodeIds: string[];
  isProcessAlive: boolean;
}
