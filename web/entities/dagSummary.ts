import type { NodeState } from '@/entities/nodeState';

export interface NodePreview {
  id: string;
  title: string;
  agentName: string;
  state: NodeState;
  updatedAt: string | null;
}

export interface DagSummary {
  name: string;
  baseBranch: string;
  tickIntervalSeconds: number;
  nodeCount: number;
  // The nodes of this dag.
  nodes: NodePreview[];
  // The time this dag last recorded activity, null when it never has.
  lastActivityAt: string | null;
  isScheduled: boolean;
  isWatching: boolean;
  // False when this dag's database could not be opened.
  isReadable: boolean;
}
