'use client';

import { NodeDialog } from '@/components/nodeDialog/nodeDialog';
import type { DagNode } from '@/entities/dagDetail';
import type { NodeDetail } from '@/entities/nodeDetail';
import { useDag } from '@/hooks/useDag';
import { usePolledApiResponse } from '@/hooks/usePolledApiResponse';
import { getNodePath } from '@/utils/apiPath';

const NO_DAG_NODES: DagNode[] = [];

interface NodeScreenProps {
  dagName: string;
  nodeId: string;
}

/**
 * Renders a single node's dialog over the dag panel.
 */
export const NodeScreen = ({ dagName, nodeId }: NodeScreenProps) => {
  const nodePath = getNodePath(dagName, nodeId);
  const nodeDetailResponse = usePolledApiResponse<NodeDetail>(nodePath);
  const { dagDetail, hasFailed, refreshDagDetail } = useDag();

  const dagNodes = dagDetail === null ? NO_DAG_NODES : dagDetail.nodes;

  const handleNodeActionSuccess = () => {
    nodeDetailResponse.refresh();
    refreshDagDetail();
  };

  return (
    <NodeDialog
      dagName={dagName}
      nodeId={nodeId}
      nodes={dagNodes}
      detail={nodeDetailResponse.response}
      isMissing={nodeDetailResponse.isMissing}
      hasFailed={hasFailed || nodeDetailResponse.hasFailed}
      onNodeActionSuccess={handleNodeActionSuccess}
    />
  );
};
