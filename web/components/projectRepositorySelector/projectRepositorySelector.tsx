'use client';

import { Alert, Button, MenuItem, Stack, TextField, Typography } from '@mui/material';
import type { Theme } from '@mui/material/styles';

import { FOCUS_OUTLINE_OFFSET, FOCUS_OUTLINE_WIDTH } from '@/components/softChip/constants';
import { getActiveProjects, getReadyRepositories } from '@/hooks/catalog/utils';
import { LABELS } from '@/labels/en';

import type { ProjectRepositorySelectorProps } from './types';

const CONTROL_STYLE = (theme: Theme) => ({
  minWidth: 0, flex: 1,
  '& .Mui-disabled, & .MuiInputBase-input.Mui-disabled': {
    color: (theme.vars ?? theme).palette.text.secondary,
    WebkitTextFillColor: (theme.vars ?? theme).palette.text.secondary,
  },
});
const SELECTOR_STYLE = { flexDirection: { xs: 'column', sm: 'row' }, gap: 2 };
const SELECT_SLOT_PROPS = { select: { displayEmpty: true }, inputLabel: { shrink: true } };
const ACTION_STYLE = {
  '&.Mui-disabled': { color: 'text.secondary' },
  '&:focus-visible': {
    outline: `${FOCUS_OUTLINE_WIDTH} solid`, outlineColor: 'primary.main',
    outlineOffset: FOCUS_OUTLINE_OFFSET,
  },
};

/**
 * Renders project and ready repository selection controls.
 */
export const ProjectRepositorySelector = ({
  projects, repositories, projectId, repositoryId, hasFailed,
  onProjectSelect, onRepositorySelect, onAddRepository, onRetry,
}: ProjectRepositorySelectorProps) => {
  const activeProjects = getActiveProjects(projects);
  const readyRepositories = getReadyRepositories(repositories, projectId);
  const isLoading = projects === null || repositories === null;
  const hasNoReadyRepository = !isLoading && readyRepositories.length === 0;

  return (
    <Stack spacing={2}>
      <Stack sx={SELECTOR_STYLE}>
        <TextField select label={LABELS.selectionProject} value={projectId ?? ''}
          disabled={activeProjects.length === 0} sx={CONTROL_STYLE} slotProps={SELECT_SLOT_PROPS}
          onChange={(event) => onProjectSelect(event.target.value)}>
          <MenuItem value="" disabled>{LABELS.selectionProject}</MenuItem>
          {activeProjects.map((project) => <MenuItem key={project.id} value={project.id}>{project.name}</MenuItem>)}
        </TextField>
        <TextField select label={LABELS.selectionRepository} value={repositoryId ?? ''}
          disabled={readyRepositories.length === 0} required={readyRepositories.length > 1}
          sx={CONTROL_STYLE} slotProps={SELECT_SLOT_PROPS}
          onChange={(event) => onRepositorySelect(event.target.value)}>
          <MenuItem value="" disabled>{LABELS.selectionRepository}</MenuItem>
          {readyRepositories.map((repository) => <MenuItem key={repository.id} value={repository.id}>{repository.fullName}</MenuItem>)}
        </TextField>
      </Stack>
      {hasFailed && <Alert severity="error" action={<Button onClick={onRetry} sx={ACTION_STYLE}>{LABELS.projectsRetry}</Button>}>{LABELS.selectionLoadFailed}</Alert>}
      {isLoading && !hasFailed && <Typography role="status">{LABELS.selectionLoading}</Typography>}
      {hasNoReadyRepository && <Typography role="status">{LABELS.selectionNoReadyRepository}</Typography>}
      <Button onClick={onAddRepository} disabled={projectId === null} sx={ACTION_STYLE}>{LABELS.selectionAddRepository}</Button>
    </Stack>
  );
};
