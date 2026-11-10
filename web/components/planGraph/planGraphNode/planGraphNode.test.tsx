import { render, screen } from '@testing-library/react';
import { ReactFlowProvider } from '@xyflow/react';
import { expect, test, vi } from 'vitest';

import type { PlanGraphNodeData } from '@/components/planGraph/types';
import { EXECUTOR_AGENT_LABELS, LABELS } from '@/labels/en';
import { PlanGraphNode } from './planGraphNode';

test.each([null, LABELS.planNodeChanged, LABELS.planNodeNew])(
  'PlanGraphNode displays its chips when the change label is %s',
  (changeLabel) => {
    const data: PlanGraphNodeData = {
      title: 'Add the rate limit settings',
      nodeId: 'RL-1',
      executorLabel: EXECUTOR_AGENT_LABELS.claude,
      repositoryName: 'virgo/service',
      changeLabel,
      onSelectNode: vi.fn(),
    };

    render(
      <ReactFlowProvider>
        <PlanGraphNode
          id={data.nodeId}
          data={data}
          type="planNode"
          selected={false}
          dragging={false}
          isConnectable
          positionAbsoluteX={0}
          positionAbsoluteY={0}
          zIndex={0}
          draggable={false}
          selectable
          deletable={false}
        />
      </ReactFlowProvider>,
    );

    expect(screen.getByText(data.title)).toBeVisible();
    expect(screen.getByText(data.nodeId)).toBeVisible();
    expect(screen.getByText(data.executorLabel)).toBeVisible();
    expect(screen.getByText(data.repositoryName)).toBeVisible();

    if (changeLabel !== null) {
      expect(screen.getByText(changeLabel)).toBeVisible();

      return;
    }

    expect(screen.queryByText(LABELS.planNodeChanged)).not.toBeInTheDocument();
    expect(screen.queryByText(LABELS.planNodeNew)).not.toBeInTheDocument();
  },
);
