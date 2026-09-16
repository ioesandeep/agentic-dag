import Box from '@mui/material/Box';
import Skeleton from '@mui/material/Skeleton';

import { DAG_GRID_COLUMNS } from '@/components/dagList/constants';
import { LABELS } from '@/labels/en';

const CARD_COUNT = 6;
const CARD_HEIGHT = '11rem';
const CARD_KEYS = Array.from({ length: CARD_COUNT }, (_, index) => index);

/**
 * Renders the dag grid before its first response arrives.
 */
export const DagListSkeleton = () => (
  <Box
    role="status"
    aria-label={LABELS.dagsLoading}
    sx={{ display: 'grid', gap: 2, gridTemplateColumns: DAG_GRID_COLUMNS }}
  >
    {CARD_KEYS.map((key) => (
      <Skeleton key={key} height={CARD_HEIGHT} />
    ))}
  </Box>
);
