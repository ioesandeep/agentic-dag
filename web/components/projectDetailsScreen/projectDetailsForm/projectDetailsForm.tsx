'use client';

import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import MenuItem from '@mui/material/MenuItem';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import type { FormEvent } from 'react';
import { useRef, useState } from 'react';

import { ProjectDetailField } from '@/components/projectDetailsScreen/projectDetailField/projectDetailField';
import { ProjectStateEnum } from '@/components/projectDetailsScreen/types';
import type { ProjectDetailsInput } from '@/components/projectDetailsScreen/types';
import { LABELS } from '@/labels/en';

const PANEL_STYLE = { p: { xs: 2, sm: 2.5 } };
const NAME_SIZE = { xs: 12, sm: 8 };
const STATE_SIZE = { xs: 12, sm: 4 };
const NAME_SLOT_PROPS = { htmlInput: { 'aria-label': LABELS.projectDetailsName } };
const DESCRIPTION_SLOT_PROPS = { htmlInput: { 'aria-label': LABELS.projectDetailsDescription } };
const ACTION_STYLE = { mt: 2 };
const STATE_SLOT_PROPS = { select: { 'aria-label': LABELS.projectDetailsState } };

interface ProjectDetailsFormProps {
  projectDetailsInput: ProjectDetailsInput;
  isEditing: boolean;
  onCancel: () => void;
  onApply: (projectDetailsInput: ProjectDetailsInput) => void;
}

/**
 * Displays and edits a project's name, description, and state.
 */
export const ProjectDetailsForm = ({
  projectDetailsInput,
  isEditing,
  onCancel,
  onApply,
}: ProjectDetailsFormProps) => {
  const nameInputRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState(projectDetailsInput.name);
  const [description, setDescription] = useState(projectDetailsInput.description);
  const [isArchived, setIsArchived] = useState(projectDetailsInput.isArchived);

  const [hasSubmitted, setHasSubmitted] = useState(false);
  const state = isArchived ? ProjectStateEnum.ARCHIVED : ProjectStateEnum.ACTIVE;
  const hasNameError = hasSubmitted && name.trim() === '';
  const nameHelperText = hasNameError ? LABELS.projectNameRequired : undefined;

  const archived = projectDetailsInput.isArchived;
  const currentState = archived ? LABELS.projectStateArchived : LABELS.projectStateActive;
  const currentDescription = projectDetailsInput.description || LABELS.projectDescriptionEmpty;
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setHasSubmitted(true);

    const trimmedName = name.trim();
    if (trimmedName === '') {
      nameInputRef.current?.focus();

      return;
    }

    const projectDetailsInput = { name: trimmedName, description: description.trim(), isArchived };
    onApply(projectDetailsInput);
  };

  return (
    <Paper variant="outlined" component="form" noValidate onSubmit={handleSubmit} sx={PANEL_STYLE}>
      <Grid container spacing={2}>
        <Grid size={NAME_SIZE}>
          <ProjectDetailField
            label={LABELS.projectDetailsName}
            value={projectDetailsInput.name}
            isEditing={isEditing}
          >
            <TextField
              required
              autoFocus
              size="small"
              fullWidth
              value={name}
              inputRef={nameInputRef}
              slotProps={NAME_SLOT_PROPS}
              error={hasNameError}
              helperText={nameHelperText}
              onChange={(event) => setName(event.target.value)}
            />
          </ProjectDetailField>
        </Grid>
        <Grid size={STATE_SIZE}>
          <ProjectDetailField
            label={LABELS.projectDetailsState}
            value={currentState}
            isEditing={isEditing}
          >
            <TextField
              select
              size="small"
              fullWidth
              value={state}
              slotProps={STATE_SLOT_PROPS}
              onChange={(event) => setIsArchived(event.target.value === ProjectStateEnum.ARCHIVED)}
            >
              <MenuItem value={ProjectStateEnum.ACTIVE}>{LABELS.projectStateActive}</MenuItem>
              <MenuItem value={ProjectStateEnum.ARCHIVED}>{LABELS.projectStateArchived}</MenuItem>
            </TextField>
          </ProjectDetailField>
        </Grid>
        <Grid size={12}>
          <ProjectDetailField
            label={LABELS.projectDetailsDescription}
            value={currentDescription}
            isEditing={isEditing}
          >
            <TextField
              multiline
              size="small"
              fullWidth
              value={description}
              slotProps={DESCRIPTION_SLOT_PROPS}
              onChange={(event) => setDescription(event.target.value)}
            />
          </ProjectDetailField>
        </Grid>
      </Grid>
      {isEditing && (
        <Stack direction="row" spacing={1} sx={ACTION_STYLE}>
          <Button onClick={onCancel}>{LABELS.projectEditCancel}</Button>
          <Button type="submit" variant="contained">
            {LABELS.projectEditApply}
          </Button>
        </Stack>
      )}
    </Paper>
  );
};
