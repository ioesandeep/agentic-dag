import { SoftChip } from '@/components/softChip/softChip';
import type { NodeStateEnum } from '@/entities/nodeState';
import { NODE_STATE_LABELS } from '@/labels/en';

interface NodeStateChipProps {
  state: NodeStateEnum;
}

/**
 * Renders a chip with the node state's label and colour.
 */
export const NodeStateChip = ({ state }: NodeStateChipProps) => (
  <SoftChip
    color={`var(--mui-palette-state-${state})`}
    label={NODE_STATE_LABELS[state]}
  />
);
