'use client';

import Box from '@mui/material/Box';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import Snackbar from '@mui/material/Snackbar';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { AddRepositoryActionButton } from '@/components/addRepositoryActionButton/addRepositoryActionButton';
import { AppLayout } from '@/components/appLayout/appLayout';
import { ColorSchemeToggle } from '@/components/colorSchemeToggle/colorSchemeToggle';
import { RepositoryList } from '@/components/repositoryList/repositoryList';
import { RepositoryListVariantEnum } from '@/components/repositoryList/types';
import { TopAppBar } from '@/components/topAppBar/topAppBar';
import type { Repository } from '@/entities/catalog/repository';
import { LABELS } from '@/labels/en';
import { MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { getRepositoryRoute } from '@/utils/route';
import { formatLabel } from '@/utils/formatLabel';

const PAGE_STYLE = { p: { xs: 2, md: 4 }, maxWidth: '100rem', mx: 'auto' };
const ARCHIVE_LABEL_STYLE = { m: 0, whiteSpace: 'nowrap' };
const NOTICE_SLOT_PROPS = { content: { role: 'status' } };

/**
 * Displays the mock repository catalog.
 */
export const RepositoriesScreen = () => {
  const [showArchived, setShowArchived] = useState(false);
  const [retryNotice, setRetryNotice] = useState<string | null>(null);
  const [retryNoticeVersion, setRetryNoticeVersion] = useState(0);
  const router = useRouter();

  const repositories = MOCK_REPOSITORIES.filter((repository) => showArchived || repository.archivedAt === null);
  const handleToggleArchived = () => setShowArchived(!showArchived);
  const handleCloseRetryNotice = () => setRetryNotice(null);
  const handleRetryClone = (repository: Repository) => {
    const repositoryValues = { repository: repository.fullName };
    const notice = formatLabel(LABELS.repositoryCloneRetryUnavailable, repositoryValues);
    setRetryNotice(notice);
    setRetryNoticeVersion(retryNoticeVersion + 1);
  };

  const handleOpenRepository = (repository: Repository) => {
    const repositoryRoute = getRepositoryRoute(repository.id);
    router.push(repositoryRoute);
  };

  return (
    <AppLayout
      topAppBar={
        <TopAppBar
          title={LABELS.repositoriesHeading}
          actions={
            <>
              <FormControlLabel
                label={LABELS.repositoriesShowArchived}
                sx={ARCHIVE_LABEL_STYLE}
                control={<Switch size="small" checked={showArchived} onChange={handleToggleArchived} />}
              />
              <AddRepositoryActionButton />
              <ColorSchemeToggle />
            </>
          }
        />
      }
    >
      <Box sx={PAGE_STYLE}>
        <RepositoryList
          variant={RepositoryListVariantEnum.GLOBAL}
          repositories={repositories}
          onOpenDetails={handleOpenRepository}
          onRetryClone={handleRetryClone}
        />
      </Box>
      <Snackbar
        key={retryNoticeVersion}
        open={retryNotice !== null}
        message={retryNotice}
        onClose={handleCloseRetryNotice}
        slotProps={NOTICE_SLOT_PROPS}
      />
    </AppLayout>
  );
};
