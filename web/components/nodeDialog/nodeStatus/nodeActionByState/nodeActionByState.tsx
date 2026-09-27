import { RetryAction } from '@/components/nodeDialog/nodeStatus/nodeActionByState/retryAction/retryAction';
import { StopAction } from '@/components/nodeDialog/nodeStatus/nodeActionByState/stopAction/stopAction';
import { WakeAction } from '@/components/nodeDialog/nodeStatus/nodeActionByState/wakeAction/wakeAction';
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
        <RetryAction
          dagName={dagName}
          nodeId={nodeId}
          onNodeActionSuccess={onNodeActionSuccess}
        />
      );
    case NodeStateEnum.RESTING:
      return (
        <WakeAction
          dagName={dagName}
          nodeId={nodeId}
          onNodeActionSuccess={onNodeActionSuccess}
        />
      );
    case NodeStateEnum.IN_PROGRESS:
      return (
        <StopAction
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
