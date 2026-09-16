import Box from '@mui/material/Box';
import Skeleton from '@mui/material/Skeleton';

import { NODE_DETAILS_SIDEBAR_WIDTH } from '@/components/nodeDialog/constants';
import {
  CONVERSATION_SKELETON_STYLE,
  SIDEBAR_SKELETON_STYLE,
} from '@/components/nodeDialog/nodeDialogBody/constants';
import { LABELS } from '@/labels/en';

const BODY_STYLE = {
  flexGrow: 1,
  minHeight: 0,
  display: 'flex',
  flexDirection: { xs: 'column', md: 'row' },
  gap: 2,
  p: { xs: 2, md: 3 },
};

const DETAILS_SIDEBAR_STYLE = {
  width: NODE_DETAILS_SIDEBAR_WIDTH,
  flexShrink: 0,
  height: '100%',
  display: { xs: 'none', md: 'block' },
};

/**
 * Renders the node dialog's columns before its first response arrives.
 */
export const NodeDialogBodySkeleton = () => (
  <Box role="status" aria-label={LABELS.nodeLoading} sx={BODY_STYLE}>
    <Skeleton sx={DETAILS_SIDEBAR_STYLE} />
    <Skeleton sx={CONVERSATION_SKELETON_STYLE} />
    <Skeleton sx={SIDEBAR_SKELETON_STYLE} />
  </Box>
);
