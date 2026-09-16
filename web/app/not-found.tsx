import Box from '@mui/material/Box';

import { AppLayout } from '@/components/appLayout/appLayout';
import { BackButton } from '@/components/backButton/backButton';
import { ColorSchemeToggle } from '@/components/colorSchemeToggle/colorSchemeToggle';
import { EmptyState } from '@/components/emptyState/emptyState';
import { TopAppBar } from '@/components/topAppBar/topAppBar';
import { LABELS } from '@/labels/en';
import { DAGS_ROUTE } from '@/utils/route';

const PAGE_STYLE = { p: { xs: 2, md: 4 }, maxWidth: '100rem', mx: 'auto' };

const NotFoundPage = () => (
  <AppLayout
    topAppBar={
      <TopAppBar
        backButton={<BackButton href={DAGS_ROUTE} label={LABELS.dagListBack} />}
        title={LABELS.notFoundTitle}
        actions={<ColorSchemeToggle />}
      />
    }
  >
    <Box sx={PAGE_STYLE}>
      <EmptyState
        title={LABELS.notFoundEmpty}
        body={LABELS.notFoundEmptyHint}
      />
    </Box>
  </AppLayout>
);

export default NotFoundPage;
