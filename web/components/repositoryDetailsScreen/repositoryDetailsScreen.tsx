'use client';

import Stack from '@mui/material/Stack';
import { notFound } from 'next/navigation';
import { useState } from 'react';

import { AppLayout } from '@/components/appLayout/appLayout';
import { BackButton } from '@/components/backButton/backButton';
import { ColorSchemeToggle } from '@/components/colorSchemeToggle/colorSchemeToggle';
import { RepositoryActionDialog } from '@/components/repositoryActionDialog/repositoryActionDialog';
import type { RepositoryConfirmationAction } from '@/components/repositoryActionDialog/types';
import { RepositoryDetails } from '@/components/repositoryDetails/repositoryDetails';
import { TopAppBar } from '@/components/topAppBar/topAppBar';
import type { ProjectSummary } from '@/entities/catalog/project';
import type { ProjectMembership } from '@/entities/catalog/repository';
import { RepositoryActionEnum } from '@/entities/catalog/repositoryAction';
import { LABELS } from '@/labels/en';
import { MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { REPOSITORIES_ROUTE } from '@/utils/route';
import { getMockRepairInspections } from './utils';

const PAGE_STYLE = { p: { xs: 2, md: 3 }, maxWidth: '64rem', mx: 'auto' };

interface RepositoryDetailsScreenProps {
  repositoryId: string;
}

/**
 * Displays mock repository details and project memberships.
 */
export const RepositoryDetailsScreen = ({
  repositoryId,
}: RepositoryDetailsScreenProps) => {
  const [action, setAction] = useState<RepositoryConfirmationAction | null>(
    null,
  );

  const [removalProject, setRemovalProject] = useState<ProjectSummary | null>(
    null,
  );

  const repository = MOCK_REPOSITORIES.find(
    (repository) => repository.id === repositoryId,
  );

  if (repository === undefined) {
    notFound();
  }

  const inspections = getMockRepairInspections(repository);
  const handleClose = () => setAction(null);

  const handleCloseRemoval = () => setRemovalProject(null);
  const handleRemove = (membership: ProjectMembership) =>
    setRemovalProject(membership.project);

  const handleAction = (action: RepositoryActionEnum) => {
    if (
      action === RepositoryActionEnum.CHECK ||
      action === RepositoryActionEnum.RETRY ||
      action === RepositoryActionEnum.REMOVE
    ) {
      return;
    }

    setAction(action);
  };

  return (
    <AppLayout
      topAppBar={
        <TopAppBar
          title={repository.fullName}
          backButton={
            <BackButton
              href={REPOSITORIES_ROUTE}
              label={LABELS.repositoriesListBack}
            />
          }
          actions={<ColorSchemeToggle />}
        />
      }
    >
      <Stack spacing={3} sx={PAGE_STYLE}>
        <RepositoryDetails
          repository={repository}
          onAction={handleAction}
          onRemove={handleRemove}
        />
      </Stack>
      {action !== null && (
        <RepositoryActionDialog
          variant={action}
          repository={repository}
          inspections={inspections}
          isOpen
          onClose={handleClose}
          onConfirm={handleClose}
        />
      )}
      {removalProject !== null && (
        <RepositoryActionDialog
          projectName={removalProject.name}
          repositoryName={repository.fullName}
          isOpen
          onClose={handleCloseRemoval}
          onConfirm={handleCloseRemoval}
        />
      )}
    </AppLayout>
  );
};
