import Box from '@mui/material/Box';
import Skeleton from '@mui/material/Skeleton';

import {
  GRAPH_PERCENT,
  TABS_PERCENT,
} from '@/components/dagPanel/dagPanelBody/constants';
import { getPanelStyle } from '@/components/splitPanel/utils';
import { LABELS } from '@/labels/en';

const BODY_STYLE = {
  flexGrow: 1,
  minHeight: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 2,
};

/**
 * Renders the graph and the tab panel before the dag's first response arrives.
 */
export const DagPanelBodySkeleton = () => (
  <Box role="status" aria-label={LABELS.dagLoading} sx={BODY_STYLE}>
    <Skeleton sx={getPanelStyle(GRAPH_PERCENT)} />
    <Skeleton sx={getPanelStyle(TABS_PERCENT)} />
  </Box>
);
