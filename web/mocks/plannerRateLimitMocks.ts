import { ExecutorAgentEnum } from '@/entities/plan/executorAgent';
import type { InstructionVersion } from '@/entities/plan/planNode';
import { PlanAuthorEnum } from '@/entities/plan/planNode';
import { createMockPlanNodes } from './plannerNodeMocks';
import plannerNodeDefinitions from './plannerNodeDefinitions.json';

const RATE_LIMIT_BASE_NODES = createMockPlanNodes(
  'repository-service',
  plannerNodeDefinitions.rateLimit,
);

/**
 * Specifies the rate limit nodes before instruction changes.
 */
export const INITIAL_RATE_LIMIT_NODES = RATE_LIMIT_BASE_NODES.map(
  (planNode) => {
    const usesCodex = planNode.id === 'RL-2' || planNode.id === 'RL-8';

    return {
      ...planNode,
      executorAgent: usesCodex ? ExecutorAgentEnum.CODEX : null,
      repositoryId:
        planNode.id === 'RL-7' ? 'repository-console' : planNode.repositoryId,
    };
  },
);

const RATE_LIMIT_INSTRUCTION_UPDATES: Record<string, InstructionVersion> = {
  'RL-1': {
    version: 2,
    author: PlanAuthorEnum.PLANNER,
    createdAt: '2026-11-10T09:20:00Z',
    text: '## Context\nvirgo/service needs per-organization rate limits.\n\n## Task\nAdd settings to enable rate limiting and configure the Redis counter expiry. Add `RATE_LIMIT_DEFAULT_PER_MINUTE` with 600 as its default.\n\n## Acceptance criteria\nRate limiting can be disabled. The default limit is configurable and defaults to 600 requests per minute.',
  },
  'RL-3': {
    version: 2,
    author: PlanAuthorEnum.PLANNER,
    createdAt: '2026-11-10T09:20:00Z',
    text: "## Context\nRL-1 defines `RATE_LIMIT_DEFAULT_PER_MINUTE` with a default of 600.\n\n## Task\nAdd `OrganizationLimitLookup` to return an organization's limit in requests per minute. Use `RATE_LIMIT_DEFAULT_PER_MINUTE` for an organization without its own limit.\n\n## Acceptance criteria\nAn organization-specific limit takes precedence. An organization without its own limit gets the configured default of 600 requests per minute.",
  },
  'RL-6': {
    version: 2,
    author: PlanAuthorEnum.PLANNER,
    createdAt: '2026-11-10T09:16:00Z',
    text: "## Context\nRL-3 adds `OrganizationLimitLookup`, which returns an organization's limit in requests per minute. RL-4 adds `rate_limit_response`, which builds the 429 response with a `Retry-After` header. `RequestCounter` from RL-2 counts each organization's requests per minute in Redis.\n\n## Task\nAdd `RateLimitMiddleware` in `service/middleware/rate_limit.py` and register it in `service/app.py`. For each request it finds the organization from the API key, adds the request to the organization's count for the current minute, and returns the 429 response when the count is over the organization's limit. Requests to `/healthz` and `/metrics` skip the check.\n\n## Acceptance criteria\n- A request over the limit gets 429 with `Retry-After`.\n- `/healthz` and `/metrics` never get 429.\n- Two organizations are counted separately.",
  },
};

/**
 * Specifies the current rate limit nodes.
 */
export const RATE_LIMIT_NODES = INITIAL_RATE_LIMIT_NODES.map((planNode) => ({
  ...planNode,
  instructions:
    RATE_LIMIT_INSTRUCTION_UPDATES[planNode.id] ?? planNode.instructions,
}));
