import Box from '@mui/material/Box';

import { ERROR_MAIN_COLOR } from '@/components/dagList/dagCard/constants';
import { NodeStates } from '@/components/dagList/dagCard/nodeStates/nodeStates';
import { NodeStateVariant } from '@/components/dagList/dagCard/nodeStates/types';
import { NodeHighlights } from '@/components/dagList/nodeHighlights/nodeHighlights';
import { SoftChip } from '@/components/softChip/softChip';
import type { DagSummary } from '@/entities/dagSummary';
import { LABELS } from '@/labels/en';
import { countNodeStates } from '@/utils/dagNodes';

interface DagCardBodyProps {
  dag: DagSummary;
  hasNodeHighlights: boolean;
}

/**
 * Renders the body section of the DagCard.
 */
export const DagCardBody = ({ dag, hasNodeHighlights }: DagCardBodyProps) => {
  if (!dag.isReadable) {
    return (
      <Box sx={{ display: 'flex' }}>
        <SoftChip color={ERROR_MAIN_COLOR} label={LABELS.dagUnreadable} />
      </Box>
    );
  }

  const states = countNodeStates(dag.nodes);

  return (
    <>
      <NodeStates states={states} variant={NodeStateVariant.BAR} />
      <NodeStates states={states} variant={NodeStateVariant.CHIP} />
      {hasNodeHighlights ? <NodeHighlights nodes={dag.nodes} /> : null}
    </>
  );
};
