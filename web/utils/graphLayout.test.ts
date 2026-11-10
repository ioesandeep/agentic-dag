import { expect, test } from 'vitest';

import { getInitialViewport, getNodePlacements } from './graphLayout';

test.each([240, 320])(
  'getNodePlacements positions dependent nodes to the right with width %s',
  (nodeWidth) => {
    const graphNodes = [
      { id: 'RL-1', dependsOn: [] },
      { id: 'RL-2', dependsOn: [] },
      { id: 'RL-3', dependsOn: ['RL-1', 'RL-2'] },
    ];

    const placements = getNodePlacements(graphNodes, nodeWidth, 84);

    expect(placements.get('RL-3')?.x).toBeGreaterThan(
      placements.get('RL-1')?.x ?? Infinity,
    );

    expect(placements.get('RL-3')?.x).toBeGreaterThan(
      placements.get('RL-2')?.x ?? Infinity,
    );
  },
);

test('getInitialViewport centers nodes when the container has room', () => {
  const graphNodes = [{ position: { x: 110, y: 28 } }];
  const dimensions = { width: 1000, height: 600 };

  const viewport = getInitialViewport(graphNodes, dimensions, 320, 92);

  expect(viewport).toEqual({ x: 230, y: 226, zoom: 1 });
});

test('getInitialViewport aligns nodes to the padding when the graph exceeds the container', () => {
  const graphNodes = [{ position: { x: 110, y: 28 } }];
  const dimensions = { width: 200, height: 100 };

  const viewport = getInitialViewport(graphNodes, dimensions, 320, 92);

  expect(viewport).toEqual({ x: -86, y: -4, zoom: 1 });
});
