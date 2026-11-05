import { RetryNodeAction } from '@/components/actions/dag/retryNodeAction/retryNodeAction';
import { StopNodeAction } from '@/components/actions/dag/stopNodeAction/stopNodeAction';
import { WakeNodeAction } from '@/components/actions/dag/wakeNodeAction/wakeNodeAction';
import { NodeStateEnum } from '@/entities/nodeState';

interface NodeActionByStateProps {
  dagName: string;
  nodeId: string;
  state: NodeStateEnum;
  onNodeActionSuccess: () => void;
}

/**
 * Renders the action a node's state allows, or nothing for a state that allows none.
 */
export const NodeActionByState = ({
  dagName,
  nodeId,
  state,
  onNodeActionSuccess,
}: NodeActionByStateProps) => {
  switch (state) {
    case NodeStateEnum.ERRORED:
    case NodeStateEnum.NEEDS_HUMAN:
      return (
        <RetryNodeAction
          dagName={dagName}
          nodeId={nodeId}
          onNodeActionSuccess={onNodeActionSuccess}
        />
      );
    case NodeStateEnum.RESTING:
      return (
        <WakeNodeAction
          dagName={dagName}
          nodeId={nodeId}
          onNodeActionSuccess={onNodeActionSuccess}
        />
      );
    case NodeStateEnum.IN_PROGRESS:
      return (
        <StopNodeAction
          dagName={dagName}
          nodeId={nodeId}
          onNodeActionSuccess={onNodeActionSuccess}
        />
      );
    case NodeStateEnum.PENDING:
    case NodeStateEnum.MERGED:
    case NodeStateEnum.SKIPPED:
      return null;
  }
};
