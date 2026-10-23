'use client';

import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import Typography from '@mui/material/Typography';

import { EmptyState } from '@/components/emptyState/emptyState';
import { SoftChip } from '@/components/softChip/softChip';
import { VirgoCard } from '@/components/virgoCard/virgoCard';
import { VirgoCardBody } from '@/components/virgoCard/virgoCardBody/virgoCardBody';
import { VirgoCardFooter } from '@/components/virgoCard/virgoCardFooter/virgoCardFooter';
import { VirgoCardHeader } from '@/components/virgoCard/virgoCardHeader/virgoCardHeader';
import type { Project } from '@/entities/catalog/project';
import type { Repository } from '@/entities/catalog/repository';
import { LABELS } from '@/labels/en';
import {
  compareProjects,
  getProjectRepositoryCountLabel,
  getProjectRepositories,
  getProjectStatusLabel,
} from './utils';

const LIST_STYLE = {
  p: 0,
  display: 'grid',
  gap: 2,
  gridTemplateColumns: {
    xs: '1fr',
    sm: 'repeat(2, minmax(0, 1fr))',
    lg: 'repeat(3, minmax(0, 1fr))',
  },
};

const ITEM_STYLE = { p: 0, display: 'block', minWidth: 0 };
const REPOSITORY_LIST_STYLE = {
  p: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 0.5,
};

const REPOSITORY_ROW_STYLE = { gap: 1, minWidth: 0 };
const REPOSITORY_NAME_STYLE = { flexGrow: 1, minWidth: 0 };
const REPOSITORY_DOT_STYLE = {
  width: '0.5rem',
  height: '0.5rem',
  borderRadius: '50%',
  flexShrink: 0,
};

const PROJECT_REPOSITORY_PREVIEW_LIMIT = 3;

const REPOSITORY_BAR_STYLE = {
  display: 'flex',
  height: '0.5rem',
  borderRadius: 1,
  overflow: 'hidden',
  bgcolor: 'grey.500',
};

const REPOSITORY_COLORS = [
  'primary.main',
  'info.main',
  'success.main',
  'warning.main',
  'error.main',
  'secondary.main',
];

const STATUS_COLOR = 'var(--mui-palette-primary-main)';
const COUNT_COLOR = 'var(--mui-palette-info-main)';

interface ProjectListProps {
  projects: Project[];
  repositories: Repository[];
  showArchived: boolean;
  onSelectProject: (projectId: string) => void;
}

/**
 * Renders the project catalog.
 */
export const ProjectList = ({
  projects,
  repositories,
  showArchived,
  onSelectProject,
}: ProjectListProps) => {
  const visibleProjects = projects.filter(
    (project) => showArchived || project.archivedAt === null,
  );

  const sortedProjects = visibleProjects.toSorted(compareProjects);

  if (sortedProjects.length === 0) {
    return (
      <EmptyState
        title={LABELS.projectsEmpty}
        body={LABELS.projectsEmptyHint}
      />
    );
  }

  return (
    <List aria-label={LABELS.projectsHeading} sx={LIST_STYLE}>
      {sortedProjects.map((project) => {
        const projectRepositories = getProjectRepositories(
          project,
          repositories,
        );

        const previewRepositories = projectRepositories.slice(
          0,
          PROJECT_REPOSITORY_PREVIEW_LIMIT,
        );

        const handleSelectProject = () => onSelectProject(project.id);
        const header = <VirgoCardHeader title={project.name} />;

        const body = (
          <VirgoCardBody
            content={
              <>
                <Box
                  role="group"
                  aria-label={LABELS.projectRepositories}
                  sx={REPOSITORY_BAR_STYLE}
                >
                  {projectRepositories.map((repository, index) => {
                    const colorIndex = index % REPOSITORY_COLORS.length;
                    const repositoryColor = REPOSITORY_COLORS[colorIndex];

                    return (
                      <Box
                        key={repository.id}
                        role="img"
                        aria-label={repository.fullName}
                        sx={{ flexGrow: 1, bgcolor: repositoryColor }}
                      />
                    );
                  })}
                </Box>
                <Typography variant="body1">{project.description}</Typography>
                {previewRepositories.length > 0 && (
                  <List
                    aria-label={LABELS.projectRepositories}
                    sx={REPOSITORY_LIST_STYLE}
                  >
                    {previewRepositories.map((repository, index) => {
                      const colorIndex = index % REPOSITORY_COLORS.length;
                      const repositoryColor = REPOSITORY_COLORS[colorIndex];

                      return (
                        <ListItem
                          key={repository.id}
                          disablePadding
                          sx={REPOSITORY_ROW_STYLE}
                        >
                          <Box
                            aria-hidden
                            sx={{
                              ...REPOSITORY_DOT_STYLE,
                              bgcolor: repositoryColor,
                            }}
                          />
                          <Typography
                            variant="body1"
                            noWrap
                            sx={REPOSITORY_NAME_STYLE}
                          >
                            {repository.fullName}
                          </Typography>
                        </ListItem>
                      );
                    })}
                  </List>
                )}
                {previewRepositories.length === 0 && (
                  <Typography variant="body1" color="text.secondary">
                    {LABELS.projectRepositoriesEmpty}
                  </Typography>
                )}
              </>
            }
          />
        );

        const footer = (
          <VirgoCardFooter
            chips={
              <>
                <SoftChip
                  label={getProjectStatusLabel(project)}
                  color={STATUS_COLOR}
                />
                <SoftChip
                  label={getProjectRepositoryCountLabel(
                    project.repositoryCounts,
                  )}
                  color={COUNT_COLOR}
                />
              </>
            }
          />
        );

        return (
          <ListItem key={project.id} sx={ITEM_STYLE}>
            <VirgoCard
              ariaLabel={project.name}
              header={header}
              body={body}
              footer={footer}
              onSelect={handleSelectProject}
            />
          </ListItem>
        );
      })}
    </List>
  );
};
