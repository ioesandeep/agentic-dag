import Box from '@mui/material/Box';

import {
  HIGHLIGHT_COUNT,
  HIGHLIGHT_ROW_HEIGHT,
} from '@/components/dagList/nodeHighlights/constants';
import { NodeLine } from '@/components/dagList/nodeLine/nodeLine';
import type { NodePreview } from '@/entities/dagSummary';
import { pickHighlights } from '@/utils/dagNodes';

interface NodeHighlightsProps {
  nodes: NodePreview[];
}

/**
 * Renders the highlighted nodes of a dag.
 */
export const NodeHighlights = ({ nodes }: NodeHighlightsProps) => (
  <Box
    sx={{
      display: 'flex',
      flexDirection: 'column',
      gap: 0.5,
      minHeight: HIGHLIGHT_COUNT * HIGHLIGHT_ROW_HEIGHT,
    }}
  >
    {pickHighlights(nodes, HIGHLIGHT_COUNT).map((node) => (
      <NodeLine key={node.id} node={node} />
    ))}
  </Box>
);
