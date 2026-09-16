import { NodeStateChips } from '@/components/dagList/dagCard/nodeStates/nodeStateChips/nodeStateChips';
import { NodeStateBar } from '@/components/dagList/dagCard/nodeStates/nodeStateBar/nodeStateBar';
import { NodeStateVariant } from '@/components/dagList/dagCard/nodeStates/types';
import type { NodeStateCount } from '@/utils/dagNodes';

interface NodeStatesProps {
  states: NodeStateCount[];
  variant: NodeStateVariant;
}

/**
 * Renders the node state counts of a dag in the requested variant.
 */
export const NodeStates = ({ states, variant }: NodeStatesProps) => {
  if (variant === NodeStateVariant.BAR) {
    return <NodeStateBar states={states} />;
  }

  return <NodeStateChips states={states} />;
};
