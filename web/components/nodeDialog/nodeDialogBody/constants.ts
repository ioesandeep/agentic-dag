import {
  CONVERSATION_COLUMN_WIDTH,
  SIDEBAR_COLUMN_WIDTH,
} from '@/components/nodeDialog/constants';

const STACKED_COLUMN_HEIGHT = '18rem';

const COLUMN_HEIGHT = { xs: STACKED_COLUMN_HEIGHT, md: '100%' };

export const CONVERSATION_SKELETON_STYLE = {
  flexGrow: { md: CONVERSATION_COLUMN_WIDTH },
  flexBasis: { md: 0 },
  minWidth: 0,
  height: COLUMN_HEIGHT,
};

export const SIDEBAR_SKELETON_STYLE = {
  flexGrow: { md: SIDEBAR_COLUMN_WIDTH },
  flexBasis: { md: 0 },
  minWidth: 0,
  height: COLUMN_HEIGHT,
};

export const COLUMNS_STYLE = {
  flexGrow: 1,
  minWidth: 0,
  minHeight: { md: 0 },
  display: 'flex',
  flexDirection: { xs: 'column', md: 'row' },
  gap: 2,
};
