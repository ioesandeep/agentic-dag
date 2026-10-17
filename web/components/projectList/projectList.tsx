'use client';

import {
  Alert,
  Button,
  Checkbox,
  FormControlLabel,
  List,
  ListItem,
  Stack,
  Typography,
} from '@mui/material';

import { EmptyState } from '@/components/emptyState/emptyState';
import { FOCUS_OUTLINE_OFFSET, FOCUS_OUTLINE_WIDTH } from '@/components/softChip/constants';
import type { Project } from '@/entities/catalog/project';
import { LABELS } from '@/labels/en';

import { getProjectStatus, getRepositoryCountLabel, getVisibleProjects } from './utils';

const HEADER_STYLE = {
  flexDirection: { xs: 'column', sm: 'row' },
  justifyContent: 'space-between',
  gap: 2,
};
const PROJECT_STYLE = {
  alignItems: 'flex-start',
  borderBottom: 1,
  borderColor: 'divider',
  px: 0,
  py: 2,
  overflowWrap: 'anywhere',
};
const FOCUS_VISIBLE_STYLE = {
  '&:focus-visible': {
    outline: `${FOCUS_OUTLINE_WIDTH} solid`,
    outlineColor: 'primary.main',
    outlineOffset: FOCUS_OUTLINE_OFFSET,
  },
};
const NAME_STYLE = { ...FOCUS_VISIBLE_STYLE, alignSelf: 'flex-start', textAlign: 'left' };
const CREATE_BUTTON_STYLE = { ...FOCUS_VISIBLE_STYLE, '&:hover': { bgcolor: 'primary.main' } };

interface ProjectListProps {
  projects: Project[] | null;
  hasFailed: boolean;
  onProjectSelect: (projectId: string) => void;
  showArchived: boolean;
  onShowArchivedChange: (showArchived: boolean) => void;
  onCreate: () => void;
  onRetry: () => void;
}

/**
 * Renders project selection and creation controls.
 */
export const ProjectList = ({
  projects,
  hasFailed,
  showArchived,
  onShowArchivedChange,
  onCreate,
  onRetry,
  onProjectSelect,
}: ProjectListProps) => {
  const visibleProjects = getVisibleProjects(projects, showArchived);
  const failureLabel = projects === null ? LABELS.projectsLoadFailed : LABELS.projectsRefreshFailed;
  const isLoading = projects === null && !hasFailed;
  const isEmpty = visibleProjects?.length === 0;

  return (
    <Stack spacing={2}>
      <Stack sx={HEADER_STYLE}>
        <Typography variant="h5" component="h1">
          {LABELS.projectsHeading}
        </Typography>
        <Button variant="contained" onClick={onCreate} sx={CREATE_BUTTON_STYLE} disableRipple>
          {LABELS.projectCreate}
        </Button>
      </Stack>
      <FormControlLabel
        label={LABELS.projectsShowArchived}
        control={
          <Checkbox
            checked={showArchived}
            onChange={(_, isChecked) => onShowArchivedChange(isChecked)}
          />
        }
      />
      {hasFailed && (
        <Alert
          severity="error"
          action={
            <Button onClick={onRetry} sx={FOCUS_VISIBLE_STYLE} disableRipple>
              {LABELS.projectsRetry}
            </Button>
          }
        >
          {failureLabel}
        </Alert>
      )}
      {isLoading && <Typography role="status">{LABELS.projectsLoading}</Typography>}
      {isEmpty && <EmptyState title={LABELS.projectsEmpty} body={LABELS.projectsEmptyHint} />}
      {visibleProjects && !isEmpty && (
        <List aria-label={LABELS.projectsHeading} disablePadding>
          {visibleProjects.map((project) => (
            <ListItem key={project.id} sx={PROJECT_STYLE}>
              <Stack spacing={1}>
                <Button onClick={() => onProjectSelect(project.id)} sx={NAME_STYLE} disableRipple>
                  {project.name}
                </Button>
                <Typography variant="body2">{project.description}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {getRepositoryCountLabel(project.repositoryCounts)}
                </Typography>
                <Typography variant="body2">{getProjectStatus(project)}</Typography>
              </Stack>
            </ListItem>
          ))}
        </List>
      )}
    </Stack>
  );
};
