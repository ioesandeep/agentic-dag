import type { PlanNode } from '@/entities/plan/planNode';
import { PlanAuthorEnum } from '@/entities/plan/planNode';
import plannerNodeDefinitions from './plannerNodeDefinitions.json';

/**
 * Defines a mock node's work before execution defaults are applied.
 */
interface MockPlanNode {
  id: string;
  name: string;
  title: string;
  dependsOn: string[];
  context: string;
  task: string;
  acceptanceCriteria: string;
}

/**
 * Creates mock nodes with versioned instructions.
 */
export const createMockPlanNodes = (
  repositoryId: string,
  mockPlanNodes: MockPlanNode[],
): PlanNode[] =>
  mockPlanNodes.map((mockPlanNode) => ({
    id: mockPlanNode.id,
    name: mockPlanNode.name,
    title: mockPlanNode.title,
    dependsOn: mockPlanNode.dependsOn,
    executorAgent: null,
    repositoryId,
    baseBranch: null,
    cooldownSeconds: null,
    instructions: {
      version: 1,
      author: PlanAuthorEnum.PLANNER,
      createdAt: '2026-11-10T09:10:00Z',
      text: `## Context\n${mockPlanNode.context}\n\n## Task\n${mockPlanNode.task}\n\n## Acceptance criteria\n${mockPlanNode.acceptanceCriteria}`,
    },
  }));

/**
 * Specifies the approved worker retry plan's nodes.
 */
export const WORKER_RETRY_NODES = createMockPlanNodes(
  'repository-worker',
  plannerNodeDefinitions.worker,
);

/**
 * Specifies the started connector pagination plan's nodes.
 */
export const CONNECTOR_PAGINATION_NODES = createMockPlanNodes(
  'repository-connector',
  plannerNodeDefinitions.connector,
);
