import Box from '@mui/material/Box';
import Skeleton from '@mui/material/Skeleton';

import {
  COLUMNS_STYLE,
  CONVERSATION_SKELETON_STYLE,
  SIDEBAR_SKELETON_STYLE,
} from '@/components/nodeDialog/nodeDialogBody/constants';
import { LABELS } from '@/labels/en';

/**
 * Renders the columns of a single node before its first response arrives.
 */
export const NodeDetailColumnsSkeleton = () => (
  <Box role="status" aria-label={LABELS.nodeLoading} sx={COLUMNS_STYLE}>
    <Skeleton sx={CONVERSATION_SKELETON_STYLE} />
    <Skeleton sx={SIDEBAR_SKELETON_STYLE} />
  </Box>
);
