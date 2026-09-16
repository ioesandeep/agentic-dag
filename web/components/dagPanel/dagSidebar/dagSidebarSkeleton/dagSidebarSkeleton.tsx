import Box from '@mui/material/Box';
import Skeleton from '@mui/material/Skeleton';

import { getSidebarStyle } from '@/components/dagPanel/dagSidebar/utils';
import { LABELS } from '@/labels/en';

const IS_ENTERING = false;
const CARD_COUNT = 6;
const CARD_HEIGHT = '5rem';
const CARD_KEYS = Array.from({ length: CARD_COUNT }, (_, index) => index);

const LIST_STYLE = {
  display: { xs: 'none', md: 'flex' },
  flexDirection: 'column',
  gap: 1,
  p: 1.5,
};

interface DagSidebarSkeletonProps {
  isCollapsed: boolean;
}

/**
 * Renders the sidebar column before its first response arrives.
 */
export const DagSidebarSkeleton = ({
  isCollapsed,
}: DagSidebarSkeletonProps) => (
  <Box component="nav" sx={getSidebarStyle(isCollapsed, IS_ENTERING)}>
    <Box role="status" aria-label={LABELS.dagsLoading} sx={LIST_STYLE}>
      {CARD_KEYS.map((key) => (
        <Skeleton key={key} height={CARD_HEIGHT} />
      ))}
    </Box>
  </Box>
);
