/**
 * Provides fixed planner records and undo history.
 */
import { ExecutorAgentEnum } from '@/entities/plan/executorAgent';
import type { Plan } from '@/entities/plan/plan';
import { PlanStateEnum } from '@/entities/plan/plan';
import type { PlanRevision } from '@/entities/plan/planMessage';
import { PlanMessageKindEnum } from '@/entities/plan/planMessage';
import type { PlanNode } from '@/entities/plan/planNode';
import type { PlanProject } from '@/entities/plan/planProject';
import plannerProjects from './plannerProjects.json';
import {
  AUDIT_LOG_MESSAGES,
  RATE_LIMIT_MESSAGES,
  RATE_LIMIT_REVISION,
  createMockInstructionMessages,
} from './plannerMessageMocks';
import {
  CONNECTOR_PAGINATION_NODES,
  WORKER_RETRY_NODES,
} from './plannerNodeMocks';
import {
  INITIAL_RATE_LIMIT_NODES,
  RATE_LIMIT_NODES,
} from './plannerRateLimitMocks';

/**
 * Specifies the projects available for mock plans.
 */
export const MOCK_PLAN_PROJECTS: PlanProject[] = plannerProjects;

const PLAN_DEFAULTS = {
  executorAgent: ExecutorAgentEnum.CLAUDE,
  maxWorkers: 2,
  cooldownSeconds: 0,
};

const WORKER_INSTRUCTION_MESSAGES =
  createMockInstructionMessages(WORKER_RETRY_NODES);

const CONNECTOR_INSTRUCTION_MESSAGES = createMockInstructionMessages(
  CONNECTOR_PAGINATION_NODES,
);

/**
 * Provides mock plans for each planning state.
 */
export const MOCK_PLANS: Plan[] = [
  {
    ...PLAN_DEFAULTS,
    id: 'plan-audit-log-export',
    name: 'audit-log-export',
    state: PlanStateEnum.DRAFTING,
    projectId: 'project-platform',
    nodes: [],
    messages: AUDIT_LOG_MESSAGES,
    dagWrittenAt: null,
    createdAt: '2026-11-10T10:00:00Z',
    updatedAt: '2026-11-10T10:03:00Z',
  },
  {
    ...PLAN_DEFAULTS,
    id: 'plan-service-rate-limits',
    name: 'service-rate-limits',
    state: PlanStateEnum.DRAFTING,
    projectId: 'project-platform',
    nodes: RATE_LIMIT_NODES,
    messages: RATE_LIMIT_MESSAGES,
    dagWrittenAt: '2026-11-10T09:10:00Z',
    createdAt: '2026-11-10T09:00:00Z',
    updatedAt: RATE_LIMIT_REVISION.createdAt,
  },
  {
    ...PLAN_DEFAULTS,
    id: 'plan-worker-retry-backoff',
    name: 'worker-retry-backoff',
    state: PlanStateEnum.APPROVED,
    projectId: 'project-default',
    nodes: WORKER_RETRY_NODES,
    messages: [
      {
        id: 'worker-retry-request',
        nodeId: null,
        kind: PlanMessageKindEnum.USER,
        createdAt: '2026-11-10T08:00:00Z',
        text: 'Retry failed jobs in virgo/worker with exponential backoff, and move a job to a dead-letter queue after five failed attempts.',
      },
      ...WORKER_INSTRUCTION_MESSAGES,
    ],
    dagWrittenAt: '2026-11-10T09:10:00Z',
    createdAt: '2026-11-10T08:00:00Z',
    updatedAt: '2026-11-10T09:12:00Z',
  },
  {
    ...PLAN_DEFAULTS,
    id: 'plan-connector-pagination',
    name: 'connector-pagination',
    state: PlanStateEnum.STARTED,
    projectId: 'project-default',
    nodes: CONNECTOR_PAGINATION_NODES,
    messages: [
      {
        id: 'connector-pagination-request',
        nodeId: null,
        kind: PlanMessageKindEnum.USER,
        createdAt: '2026-11-10T07:00:00Z',
        text: 'Page through large result sets in virgo/connector instead of loading every record into memory at once.',
      },
      ...CONNECTOR_INSTRUCTION_MESSAGES,
    ],
    dagWrittenAt: '2026-11-10T09:10:00Z',
    createdAt: '2026-11-10T07:00:00Z',
    updatedAt: '2026-11-10T09:13:00Z',
  },
];

/**
 * Specifies the values restored when a mock plan change is undone.
 */
export interface MockPlanRevision {
  planId: string;
  revision: PlanRevision;
  nodesBefore: PlanNode[];
  settingsBefore: Pick<
    Plan,
    'name' | 'executorAgent' | 'maxWorkers' | 'cooldownSeconds'
  > | null;
}

const RATE_LIMIT_NODES_BEFORE = INITIAL_RATE_LIMIT_NODES.filter((planNode) =>
  RATE_LIMIT_REVISION.nodeIds.includes(planNode.id),
);

/**
 * Provides the undo history for mock plan changes.
 */
export const MOCK_PLAN_REVISIONS: MockPlanRevision[] = [
  {
    planId: 'plan-service-rate-limits',
    revision: RATE_LIMIT_REVISION,
    nodesBefore: RATE_LIMIT_NODES_BEFORE,
    settingsBefore: null,
  },
];
