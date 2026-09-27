import type { AuditLine } from '@/entities/dagDetail';
import type { NodeStateEnum } from '@/entities/nodeState';

export interface NodeLink {
  id: string;
  title: string;
  state: NodeStateEnum;
  // The node's pull request url, empty when the node has no pull request.
  prUrl: string;
  // The node's pull request number, or 0 when the node has no pull request.
  prNumber: number;
}

export interface NodeWorktree {
  name: string;
  absolutePath: string;
  branch: string;
  // The pull request number, 0 until one is opened for the branch.
  prNumber: number;
  createdAt: string;
  // When the disk was reclaimed, or null while the copy is still there.
  reclaimedAt: string | null;
  // How far each pull request signal has been acted on, keyed by signal name.
  signalMarks: Record<string, string>;
}

export type SignalKind = 'pr' | 'comments' | 'checks' | 'approval' | 'conflict';

export const SIGNAL_KINDS: readonly SignalKind[] = [
  'pr',
  'comments',
  'checks',
  'approval',
  'conflict',
];

/**
 * The end states of an agent session that the api sends.
 */
export enum SessionEndStateEnum {
  ALIVE = 'alive',
  FINISHED = 'finished',
  OVERDUE = 'overdue',
  ABORTED = 'aborted',
  STOPPED = 'stopped',
}

export interface AgentSession {
  id: number;
  startedAt: string;
  // When the session ended, or null while it is still running.
  endedAt: string | null;
  // How the session ended, empty while it is still running.
  endState: SessionEndStateEnum | '';
  // What started the session, launch for the first one and wake for the rest.
  triggeredBy: string;
}

/**
 * The causes of a node recovery sent between the console and the api.
 */
export enum RecoveryCauseEnum {
  TURN_CAP_REACHED = 'turn_cap_reached',
  BACKGROUND_WAIT_TERMINATED = 'background_wait_terminated',
  USAGE_LIMIT = 'usage_limit',
  PROVIDER_FAILURE = 'provider_failure',
  PROCESS_KILLED = 'process_killed',
  NO_PULL_REQUEST = 'no_pull_request',
  OVERDUE = 'overdue',
  WORKSPACE_INCONSISTENT = 'workspace_inconsistent',
}

export const RECOVERY_CAUSES: readonly RecoveryCauseEnum[] =
  Object.values(RecoveryCauseEnum);

export interface NodeRecovery {
  id: number;
  // The session that ended in this failure.
  sessionId: number;
  detectedAt: string;
  cause: RecoveryCauseEnum;
  recoverable: boolean;
  // When the node becomes eligible for recovery.
  recoverAt: string;
  // The action the recovery agent took for this failure.
  action: string;
}

export interface SlackNotification {
  id: number;
  channel: string;
  // The Slack thread the notification opened.
  threadId: string;
  createdAt: string;
}

export interface NodeDetail {
  id: string;
  title: string;
  agentName: string;
  state: NodeStateEnum;
  // The ids of the nodes this node waits for.
  dependsOn: string[];
  // The time this node's state was last written, null when it never was.
  updatedAt: string | null;
  wakes: number;
  // The agent session this node resumes, empty when none is recorded.
  sessionId: string;
  // The pull request this node opened, empty when it has none.
  prUrl: string;
  // The worktree this node's agent builds in, empty when it has none.
  worktreeName: string;
  branch: string;
  // The instructions the node's agent was launched with.
  instructions: string;
  // The ids of the nodes that wait for this one.
  blocks: string[];
  // The node's worktree, or null when none was cut.
  worktree: NodeWorktree | null;
  // The sessions of this node's agent, oldest first.
  sessions: AgentSession[];
  // The audit entries this node recorded, newest first.
  audits: AuditLine[];
  // The Slack notification threads opened for this node.
  slackNotifications: SlackNotification[];
  // The exit code of the newest session, null when none is recorded.
  exitCode: number | null;
  // The last log lines of the newest session, null when none is recorded.
  logTail: string | null;
  // The newest recorded failure of this node, null when it has none.
  nodeRecovery: NodeRecovery | null;
}
