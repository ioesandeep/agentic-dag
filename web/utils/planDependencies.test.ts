import { expect, test } from 'vitest';

import { canConnectPlanNodes } from './planDependencies';

test.each([
  {
    condition: 'the source and target are the same node',
    sourceId: 'RL-1',
    targetId: 'RL-1',
    accepted: false,
  },
  {
    condition: 'the dependency already exists',
    sourceId: 'RL-1',
    targetId: 'RL-2',
    accepted: false,
  },
  {
    condition: 'the dependency would create a cycle',
    sourceId: 'RL-3',
    targetId: 'RL-1',
    accepted: false,
  },
  {
    condition: 'the dependency is valid',
    sourceId: 'RL-1',
    targetId: 'RL-4',
    accepted: true,
  },
])(
  'canConnectPlanNodes returns $accepted when $condition',
  ({ sourceId, targetId, accepted }) => {
    const graphNodes = [
      { id: 'RL-1', dependsOn: [] },
      { id: 'RL-2', dependsOn: ['RL-1'] },
      { id: 'RL-3', dependsOn: ['RL-2'] },
      { id: 'RL-4', dependsOn: [] },
    ];

    const canConnect = canConnectPlanNodes(graphNodes, sourceId, targetId);

    expect(canConnect).toBe(accepted);
  },
);
