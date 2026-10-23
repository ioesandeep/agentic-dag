'use client';

import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { AppLayout } from '@/components/appLayout/appLayout';
import { ColorSchemeToggle } from '@/components/colorSchemeToggle/colorSchemeToggle';
import { CreateProjectDialog } from '@/components/createProjectDialog/createProjectDialog';
import { ProjectList } from '@/components/projectList/projectList';
import { TopAppBar } from '@/components/topAppBar/topAppBar';
import { LABELS } from '@/labels/en';
import { MOCK_PROJECTS, MOCK_REPOSITORIES } from '@/mocks/catalogMocks';

const PROJECTS_ROUTE = '/projects';
const ACTION_BUTTON_STYLE = { whiteSpace: 'nowrap' };
const ARCHIVE_LABEL_STYLE = { m: 0, whiteSpace: 'nowrap' };

const ACTIONS_STYLE = {
  display: 'flex',
  flexWrap: 'wrap',
  justifyContent: 'flex-end',
  gap: 1,
};

const PAGE_STYLE = { p: { xs: 2, md: 4 }, maxWidth: '100rem', mx: 'auto' };

/**
 * Renders the mock project catalog.
 */
export const ProjectsScreen = () => {
  const [showArchived, setShowArchived] = useState(false);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const router = useRouter();

  const handleToggleArchived = () => setShowArchived(!showArchived);
  const handleCreateProject = () => setIsCreateDialogOpen(true);
  const handleCloseCreateDialog = () => setIsCreateDialogOpen(false);
  const handleSelectProject = (projectId: string) => {
    const encodedProjectId = encodeURIComponent(projectId);
    router.push(`${PROJECTS_ROUTE}/${encodedProjectId}`);
  };

  return (
    <AppLayout
      topAppBar={
        <TopAppBar
          title={LABELS.projectsHeading}
          actions={
            <Box sx={ACTIONS_STYLE}>
              <FormControlLabel
                label={LABELS.projectsShowArchived}
                sx={ARCHIVE_LABEL_STYLE}
                control={
                  <Switch
                    size="small"
                    checked={showArchived}
                    onChange={handleToggleArchived}
                  />
                }
              />
              <Button
                size="small"
                variant="outlined"
                onClick={handleCreateProject}
                sx={ACTION_BUTTON_STYLE}
              >
                {LABELS.projectCreate}
              </Button>
              <ColorSchemeToggle />
            </Box>
          }
        />
      }
    >
      <Box sx={PAGE_STYLE}>
        <ProjectList
          projects={MOCK_PROJECTS}
          repositories={MOCK_REPOSITORIES}
          showArchived={showArchived}
          onSelectProject={handleSelectProject}
        />
      </Box>
      {isCreateDialogOpen && (
        <CreateProjectDialog
          isOpen
          onClose={handleCloseCreateDialog}
          onCreateProject={handleCloseCreateDialog}
        />
      )}
    </AppLayout>
  );
};
