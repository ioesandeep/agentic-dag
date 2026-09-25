import type { NodeState } from '@/entities/nodeState';

export interface DagNode {
  id: string;
  title: string;
  agentName: string;
  // The ids of the nodes this node waits for.
  dependsOn: string[];
  state: NodeState;
  // The time this node's state was last written, null when it never was.
  updatedAt: string | null;
  // The number of sessions started for this node.
  wakes: number;
  // The agent session this node resumes, empty when none is recorded.
  sessionId: string;
  // The pull request this node opened, empty when it has none.
  prUrl: string;
  // The node's pull request number, or 0 when the node has no pull request.
  prNumber: number;
  // The worktree this node's agent builds in, empty when it has none.
  worktreeName: string;
  branch: string;
}

export interface AuditLine {
  nodeId: string;
  // The state the node moved to.
  state: NodeState;
  // The reason recorded for the state change.
  note: string;
  createdAt: string;
}

export interface DagDetail {
  name: string;
  baseBranch: string;
  // The seconds the host waits between passes over this dag.
  tickIntervalSeconds: number;
  nodeCount: number;
  nodes: DagNode[];
  // The time this dag last recorded activity, null when it never has.
  lastActivityAt: string | null;
  isScheduled: boolean;
  isWatching: boolean;
  // False when this dag's database could not be opened.
  isReadable: boolean;
  // The audit entries this dag recorded, newest first.
  audit: AuditLine[];
}
