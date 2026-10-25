'use client';

import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { useRef, useState } from 'react';

import { AppLayout } from '@/components/appLayout/appLayout';
import { BackButton } from '@/components/backButton/backButton';
import { getProjectRepositories } from '@/components/projectList/utils';
import { ProjectActions } from '@/components/projectDetailsScreen/projectActions/projectActions';
import { ProjectDetailsForm } from '@/components/projectDetailsScreen/projectDetailsForm/projectDetailsForm';
import { ProjectRepositoryList } from '@/components/projectDetailsScreen/projectRepositoryList/projectRepositoryList';
import { RepositoryActionDialog } from '@/components/repositoryActionDialog/repositoryActionDialog';
import { TopAppBar } from '@/components/topAppBar/topAppBar';
import type { Project } from '@/entities/catalog/project';
import type { Repository } from '@/entities/catalog/repository';
import { LABELS } from '@/labels/en';
import { MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { PROJECTS_ROUTE } from '@/utils/route';
import type { ProjectDetailsInput } from './types';

const PAGE_STYLE = { p: { xs: 2, md: 3 }, maxWidth: '64rem', mx: 'auto' };
const REPOSITORIES_STYLE = { mt: 3, p: { xs: 2, sm: 2.5 } };
const HEADER_STYLE = { alignItems: 'center', justifyContent: 'space-between', mb: 1.5 };
const EMPTY_STYLE = { py: 1.5, color: 'text.secondary' };

interface ProjectDetailsScreenProps {
  project: Project;
}

/**
 * Displays a project's details and mock repositories.
 */
export const ProjectDetailsScreen = ({ project }: ProjectDetailsScreenProps) => {
  const editButtonRef = useRef<HTMLButtonElement>(null);
  const [projectChanges, setProjectChanges] = useState<ProjectDetailsInput | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  const [removalRepository, setRemovalRepository] = useState<Repository | null>(null);
  const projectDetailsInput = projectChanges ?? {
    name: project.name,
    description: project.description,
    isArchived: project.archivedAt !== null,
  };

  const repositories = getProjectRepositories(project, MOCK_REPOSITORIES);
  const formKey = Number(isEditing);

  const handleEdit = () => setIsEditing(true);
  const handleCancel = () => {
    setIsEditing(false);
    editButtonRef.current?.focus();
  };

  const handleApply = (projectDetailsInput: ProjectDetailsInput) => {
    setProjectChanges(projectDetailsInput);
    handleCancel();
  };

  const handleArchive = () => {
    const archivedProjectDetailsInput = {
      ...projectDetailsInput,
      isArchived: !projectDetailsInput.isArchived,
    };

    setProjectChanges(archivedProjectDetailsInput);
  };

  const handleRemove = (repository: Repository) => setRemovalRepository(repository);
  const handleCloseRemoval = () => setRemovalRepository(null);

  return (
    <AppLayout
      topAppBar={
        <TopAppBar
          backButton={<BackButton href={PROJECTS_ROUTE} label={LABELS.projectListBack} />}
          title={projectDetailsInput.name}
          actions={
            <ProjectActions
              isArchived={projectDetailsInput.isArchived}
              isEditing={isEditing}
              editButtonRef={editButtonRef}
              onEdit={handleEdit}
              onArchive={handleArchive}
            />
          }
        />
      }
    >
      <Box sx={PAGE_STYLE}>
        <ProjectDetailsForm
          key={formKey}
          projectDetailsInput={projectDetailsInput}
          isEditing={isEditing}
          onCancel={handleCancel}
          onApply={handleApply}
        />
        <Paper variant="outlined" component="section" sx={REPOSITORIES_STYLE}>
          <Stack direction="row" spacing={2} sx={HEADER_STYLE}>
            <Typography variant="h6" component="h2">
              {LABELS.projectRepositories}
            </Typography>
            <Button variant="outlined" size="small" disabled>
              {LABELS.projectRepositoryAdd}
            </Button>
          </Stack>
          <ProjectRepositoryList
            repositories={repositories}
            projectId={project.id}
            isReadOnly={projectDetailsInput.isArchived}
            onRemove={handleRemove}
          />
          {repositories.length === 0 && (
            <Typography sx={EMPTY_STYLE}>{LABELS.projectRepositoriesEmpty}</Typography>
          )}
        </Paper>
      </Box>
      {removalRepository !== null && (
        <RepositoryActionDialog
          projectName={projectDetailsInput.name}
          repositoryName={removalRepository.fullName}
          isOpen
          onClose={handleCloseRemoval}
          onConfirm={handleCloseRemoval}
        />
      )}
    </AppLayout>
  );
};
