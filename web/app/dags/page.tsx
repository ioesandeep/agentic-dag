import Box from '@mui/material/Box';

import { AppLayout } from '@/components/appLayout/appLayout';
import { ColorSchemeToggle } from '@/components/colorSchemeToggle/colorSchemeToggle';
import { DagsScreen } from '@/components/dagsScreen/dagsScreen';
import { DagStateFilter } from '@/components/dagStateFilter/dagStateFilter';
import { TopAppBar } from '@/components/topAppBar/topAppBar';
import { LABELS } from '@/labels/en';

const PAGE_STYLE = { p: { xs: 2, md: 4 }, maxWidth: '100rem', mx: 'auto' };

const DagsPage = () => (
  <AppLayout
    topAppBar={
      <TopAppBar
        title={LABELS.dagsHeading}
        actions={
          <>
            <DagStateFilter />
            <ColorSchemeToggle />
          </>
        }
      />
    }
  >
    <Box sx={PAGE_STYLE}>
      <DagsScreen />
    </Box>
  </AppLayout>
);

export default DagsPage;
