import type { PlanMessage, PlanRevision } from '@/entities/plan/planMessage';
import {
  PlanMessageKindEnum,
  PlanNodeChangeKindEnum,
} from '@/entities/plan/planMessage';
import type { PlanNode } from '@/entities/plan/planNode';
import { PlanAuthorEnum } from '@/entities/plan/planNode';
import {
  INITIAL_RATE_LIMIT_NODES,
  RATE_LIMIT_NODES,
} from './plannerRateLimitMocks';

/**
 * Creates instruction entries for mock node conversations.
 */
export const createMockInstructionMessages = (
  planNodes: PlanNode[],
): PlanMessage[] =>
  planNodes.map((planNode) => ({
    id: `${planNode.id}-instructions-v${planNode.instructions.version}`,
    kind: PlanMessageKindEnum.INSTRUCTIONS,
    nodeId: planNode.id,
    createdAt: planNode.instructions.createdAt,
    instructions: planNode.instructions,
  }));

/**
 * Identifies the change to the default rate limit.
 */
export const RATE_LIMIT_REVISION: PlanRevision = {
  id: 'revision-rate-limit-default',
  author: PlanAuthorEnum.PLANNER,
  nodeIds: ['RL-1', 'RL-3'],
  createdAt: '2026-11-10T09:20:00Z',
};

const PLAN_MESSAGE_DEFAULTS = { nodeId: null };
const PLANNER_MESSAGE_DEFAULTS = {
  ...PLAN_MESSAGE_DEFAULTS,
  kind: PlanMessageKindEnum.PLANNER,
  nodeChanges: [],
  instructionVersion: null,
  offersDag: false,
} satisfies Omit<
  Extract<PlanMessage, { kind: PlanMessageKindEnum.PLANNER }>,
  'id' | 'text' | 'createdAt'
>;

const ADDED_RATE_LIMIT_NODES = INITIAL_RATE_LIMIT_NODES.map((planNode) => ({
  nodeId: planNode.id,
  kind: PlanNodeChangeKindEnum.ADDED,
}));

const INITIAL_INSTRUCTION_MESSAGES = createMockInstructionMessages(
  INITIAL_RATE_LIMIT_NODES,
);

const UPDATED_RATE_LIMIT_NODES = RATE_LIMIT_NODES.filter(
  (planNode) => planNode.instructions.version === 2,
);

const UPDATED_INSTRUCTION_MESSAGES = createMockInstructionMessages(
  UPDATED_RATE_LIMIT_NODES,
);

const MIDDLEWARE_INSTRUCTION_MESSAGES = UPDATED_INSTRUCTION_MESSAGES.filter(
  (planMessage) => planMessage.nodeId === 'RL-6',
);

const DEFAULT_LIMIT_INSTRUCTION_MESSAGES = UPDATED_INSTRUCTION_MESSAGES.filter(
  (planMessage) => planMessage.nodeId !== 'RL-6',
);

/**
 * Records the rate limit plan and node conversations.
 */
export const RATE_LIMIT_MESSAGES: PlanMessage[] = [
  {
    ...PLAN_MESSAGE_DEFAULTS,
    id: 'rate-limit-request',
    kind: PlanMessageKindEnum.USER,
    createdAt: '2026-11-10T09:00:00Z',
    text: "Add per-organization rate limits to virgo/service. Count requests per organization in Redis, return 429 with a Retry-After header when an organization goes over its limit, and show each organization's limit on the console.",
  },
  {
    ...PLAN_MESSAGE_DEFAULTS,
    id: 'rate-limit-search',
    kind: PlanMessageKindEnum.TOOL_CALL,
    createdAt: '2026-11-10T09:01:00Z',
    toolName: 'Grep',
    toolInput: { pattern: 'rate_limit', path: 'virgo/service' },
    toolResult: 'No matches',
  },
  {
    ...PLANNER_MESSAGE_DEFAULTS,
    id: 'rate-limit-question',
    createdAt: '2026-11-10T09:02:00Z',
    text: 'virgo/service has no rate limiting yet, and `service/cache.py` already connects to Redis. Should admins change the limits on the console, or only see them?',
  },
  {
    ...PLAN_MESSAGE_DEFAULTS,
    id: 'rate-limit-scope',
    kind: PlanMessageKindEnum.USER,
    createdAt: '2026-11-10T09:04:00Z',
    text: 'Only see them for now. Editing comes later.',
  },
  {
    ...PLANNER_MESSAGE_DEFAULTS,
    id: 'rate-limit-offer',
    createdAt: '2026-11-10T09:05:00Z',
    offersDag: true,
    text: 'Then the dag needs 8 nodes: the settings, a Redis request counter, the organization limit lookup, the 429 response, an admin route that lists the limits, the middleware, a read-only limits page on the console, and an end-to-end test.\n\nIf this plan looks right, use Create dag below and I will write the nodes. Otherwise, tell me what to change.',
  },
  {
    ...PLAN_MESSAGE_DEFAULTS,
    id: 'rate-limit-create',
    kind: PlanMessageKindEnum.USER,
    createdAt: '2026-11-10T09:09:00Z',
    text: 'Create the dag.',
  },
  {
    ...PLANNER_MESSAGE_DEFAULTS,
    id: 'rate-limit-created',
    createdAt: '2026-11-10T09:10:00Z',
    nodeChanges: ADDED_RATE_LIMIT_NODES,
    text: 'I created the dag with 8 nodes. RL-1 to RL-6 and RL-8 build in `virgo/service` from `release/1.0`, and RL-7 builds in `virgo/console` from `develop`.\n\nRL-3 gives an organization without its own limit 1,000 requests per minute. Tell me if you want a different default.',
  },
  ...INITIAL_INSTRUCTION_MESSAGES,
  {
    id: 'middleware-exclusions',
    nodeId: 'RL-6',
    kind: PlanMessageKindEnum.USER,
    createdAt: '2026-11-10T09:15:00Z',
    text: 'The load balancer calls /healthz every few seconds. Make sure those calls never get a 429, and skip /metrics too.',
  },
  {
    ...PLANNER_MESSAGE_DEFAULTS,
    id: 'middleware-updated',
    nodeId: 'RL-6',
    createdAt: '2026-11-10T09:16:00Z',
    instructionVersion: 2,
    nodeChanges: [{ nodeId: 'RL-6', kind: PlanNodeChangeKindEnum.CHANGED }],
    text: 'The middleware now skips `/healthz` and `/metrics`, and a new acceptance criterion checks that neither gets a 429.',
  },
  ...MIDDLEWARE_INSTRUCTION_MESSAGES,
  {
    ...PLAN_MESSAGE_DEFAULTS,
    id: 'rate-limit-default-request',
    kind: PlanMessageKindEnum.USER,
    createdAt: '2026-11-10T09:19:00Z',
    text: '600 requests per minute, and make it a setting.',
  },
  ...DEFAULT_LIMIT_INSTRUCTION_MESSAGES,
  {
    ...PLANNER_MESSAGE_DEFAULTS,
    id: 'rate-limit-default-updated',
    createdAt: RATE_LIMIT_REVISION.createdAt,
    nodeChanges: [
      { nodeId: 'RL-1', kind: PlanNodeChangeKindEnum.CHANGED },
      { nodeId: 'RL-3', kind: PlanNodeChangeKindEnum.CHANGED },
    ],
    text: 'RL-1 now adds the `RATE_LIMIT_DEFAULT_PER_MINUTE` setting with 600 as its default, and RL-3 returns it for an organization with no limit of its own.',
  },
];

/**
 * Records the audit log discussion before dag creation.
 */
export const AUDIT_LOG_MESSAGES: PlanMessage[] = [
  {
    ...PLAN_MESSAGE_DEFAULTS,
    id: 'audit-log-request',
    kind: PlanMessageKindEnum.USER,
    createdAt: '2026-11-10T10:00:00Z',
    text: "Add an audit log export to virgo/service. Let administrators export an organization's audit events as CSV.",
  },
  {
    ...PLAN_MESSAGE_DEFAULTS,
    id: 'audit-log-search',
    kind: PlanMessageKindEnum.TOOL_CALL,
    createdAt: '2026-11-10T10:01:00Z',
    toolName: 'Grep',
    toolInput: { pattern: 'audit', path: 'virgo/service' },
    toolResult: 'service/audit.py stores organization audit events.',
  },
  {
    ...PLANNER_MESSAGE_DEFAULTS,
    id: 'audit-log-analysis',
    createdAt: '2026-11-10T10:02:00Z',
    text: '`service/audit.py` stores audit events by organization. The export route can use the existing administrator permission check.',
  },
  {
    ...PLANNER_MESSAGE_DEFAULTS,
    id: 'audit-log-offer',
    createdAt: '2026-11-10T10:03:00Z',
    offersDag: true,
    text: 'The plan needs a CSV serializer, an authorized export route, and tests for organization isolation. Use Create dag below and I will write the nodes.',
  },
];
