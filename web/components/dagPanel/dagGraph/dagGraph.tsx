'use client';

import '@xyflow/react/dist/base.css';

import Paper from '@mui/material/Paper';
import type { Edge, ReactFlowInstance } from '@xyflow/react';
import { Background, BackgroundVariant, ReactFlow } from '@xyflow/react';
import { useCallback, useEffect, useMemo, useRef } from 'react';

import {
  BACKGROUND_DOT_SIZE,
  BACKGROUND_GAP,
  DAG_NODE_TYPE,
  DIVIDER_COLOR,
  EDGE_WIDTH,
  SECONDARY_TEXT_COLOR,
} from '@/components/dagPanel/dagGraph/constants';
import { DagGraphNode } from '@/components/dagPanel/dagGraph/dagGraphNode/dagGraphNode';
import type { DagFlowNode } from '@/components/dagPanel/dagGraph/types';
import {
  getGraphLayout,
  getInitialViewport,
} from '@/components/dagPanel/dagGraph/utils';
import { EmptyState } from '@/components/emptyState/emptyState';
import type { DagDetail } from '@/entities/dagDetail';
import { LABELS } from '@/labels/en';

const NODE_TYPES = { [DAG_NODE_TYPE]: DagGraphNode };

interface DagGraphProps {
  dag: DagDetail;
}

/**
 * Renders the node graph of a dag.
 */
export const DagGraph = ({ dag }: DagGraphProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const flowRef = useRef<ReactFlowInstance<DagFlowNode, Edge> | null>(null);

  const graph = useMemo(() => getGraphLayout(dag), [dag]);
  const hasNodes = dag.nodes.length > 0;

  const applyInitialViewport = useCallback(() => {
    const container = containerRef.current;
    const flow = flowRef.current;

    if (container === null || flow === null) {
      return;
    }

    if (container.clientWidth === 0 || container.clientHeight === 0) {
      return;
    }

    const containerDimensions = {
      width: container.clientWidth,
      height: container.clientHeight,
    };
    const viewport = getInitialViewport(flow.getNodes(), containerDimensions);

    void flow.setViewport(viewport);
  }, []);

  const handleInit = (flow: ReactFlowInstance<DagFlowNode, Edge>) => {
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
        title={LABELS.dagNodesEmpty}
        body={LABELS.dagNodesEmptyHint}
      />
    );
  }

  return (
    <Paper
      ref={containerRef}
      variant="outlined"
      sx={{
        flexGrow: 1,
        minHeight: 0,
        overflow: 'hidden',
        '.react-flow__edge-path': {
          stroke: DIVIDER_COLOR,
          strokeWidth: EDGE_WIDTH,
        },
        '.react-flow__handle': { opacity: 0 },
        '--xy-attribution-background-color': 'transparent',
        // TODO: replace @xyflow/react with a renderer that forces no attribution link.
        '.react-flow__attribution a': { color: SECONDARY_TEXT_COLOR },
      }}
    >
      <ReactFlow
        nodes={graph.nodes}
        edges={graph.edges}
        nodeTypes={NODE_TYPES}
        onInit={handleInit}
        nodesDraggable={false}
        nodesConnectable={false}
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
