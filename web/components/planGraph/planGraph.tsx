'use client';

import '@xyflow/react/dist/base.css';

import Paper from '@mui/material/Paper';
import type { Connection, Edge, ReactFlowInstance } from '@xyflow/react';
import { Background, BackgroundVariant, ReactFlow } from '@xyflow/react';
import { useCallback, useEffect, useMemo, useRef } from 'react';

import { EmptyState } from '@/components/emptyState/emptyState';
import { LABELS } from '@/labels/en';
import { getInitialViewport } from '@/utils/graphLayout';
import { canConnectPlanNodes } from '@/utils/planDependencies';
import {
  BACKGROUND_DOT_SIZE,
  BACKGROUND_GAP,
  CONNECTION_RADIUS,
  DIVIDER_COLOR,
  GRAPH_STYLE,
  NODE_HEIGHT,
  NODE_WIDTH,
  PLAN_NODE_TYPE,
} from './constants';
import { PlanGraphNode } from './planGraphNode/planGraphNode';
import type { PlanFlowNode, PlanGraphInput } from './types';
import { getPlanGraphLayout } from './utils';

const NODE_TYPES = { [PLAN_NODE_TYPE]: PlanGraphNode };

interface PlanGraphProps extends PlanGraphInput {
  onConnect: (sourceId: string, targetId: string) => void;
  connectable: boolean;
}

/**
 * Displays editable dependencies between plan nodes.
 */
export const PlanGraph = ({
  nodes,
  repositories,
  executorAgent,
  highlightedNodes,
  selectedNodeId,
  onSelectNode,
  onConnect,
  connectable,
}: PlanGraphProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const flowRef = useRef<ReactFlowInstance<PlanFlowNode, Edge> | null>(null);
  const hasInitialViewport = useRef(false);

  const graph = useMemo(() => {
    const input = {
      nodes,
      repositories,
      executorAgent,
      highlightedNodes,
      selectedNodeId,
      onSelectNode,
    };

    return getPlanGraphLayout(input);
  }, [
    nodes,
    repositories,
    executorAgent,
    highlightedNodes,
    selectedNodeId,
    onSelectNode,
  ]);

  const hasNodes = nodes.length > 0;
  const isValidConnection = (connection: Connection | Edge) =>
    canConnectPlanNodes(nodes, connection.source, connection.target);

  const handleConnect = (connection: Connection) => {
    const isValid = isValidConnection(connection);

    if (connectable && isValid) {
      onConnect(connection.source, connection.target);
    }
  };

  const applyInitialViewport = useCallback(() => {
    const container = containerRef.current;
    const flow = flowRef.current;

    if (hasInitialViewport.current || container === null || flow === null) {
      return;
    }

    if (container.clientWidth === 0 || container.clientHeight === 0) {
      return;
    }

    const containerDimensions = {
      width: container.clientWidth,
      height: container.clientHeight,
    };

    const flowNodes = flow.getNodes();
    const viewport = getInitialViewport(
      flowNodes,
      containerDimensions,
      NODE_WIDTH,
      NODE_HEIGHT,
    );

    hasInitialViewport.current = true;
    void flow.setViewport(viewport);
  }, []);

  const handleInit = (flow: ReactFlowInstance<PlanFlowNode, Edge>) => {
    flowRef.current = flow;
    applyInitialViewport();
  };

  useEffect(() => {
    const container = containerRef.current;

    if (container === null) {
      return;
    }

    const observer = new ResizeObserver(applyInitialViewport);
    observer.observe(container);

    return () => observer.disconnect();
  }, [hasNodes, applyInitialViewport]);

  if (!hasNodes) {
    return (
      <EmptyState
        title={LABELS.planNodesEmpty}
        body={LABELS.planNodesEmptyHint}
      />
    );
  }

  return (
    <Paper ref={containerRef} variant="outlined" sx={GRAPH_STYLE}>
      <ReactFlow
        nodes={graph.nodes}
        edges={graph.edges}
        nodeTypes={NODE_TYPES}
        onInit={handleInit}
        onConnect={handleConnect}
        isValidConnection={isValidConnection}
        connectionRadius={CONNECTION_RADIUS}
        nodesFocusable={false}
        nodesDraggable={false}
        nodesConnectable={connectable}
        edgesReconnectable={false}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={BACKGROUND_GAP}
          size={BACKGROUND_DOT_SIZE}
          color={DIVIDER_COLOR}
        />
      </ReactFlow>
    </Paper>
  );
};
