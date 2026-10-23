'use client';

import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import TextField from '@mui/material/TextField';
import type { FormEvent } from 'react';
import { useId, useRef, useState } from 'react';

import { LABELS } from '@/labels/en';
import type { CreateProjectInput } from './types';

const FORM_STYLE = { display: 'flex', flexDirection: 'column', gap: 3, pt: 1 };
const DESCRIPTION_MIN_ROWS = 3;

interface CreateProjectDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateProject: (createProjectInput: CreateProjectInput) => void;
}

/**
 * Collects the name and description for a new project.
 */
export const CreateProjectDialog = ({
  isOpen,
  onClose,
  onCreateProject,
}: CreateProjectDialogProps) => {
  const nameInputRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [hasSubmitted, setHasSubmitted] = useState(false);

  const formId = useId();
  const titleId = useId();

  const hasNameError = hasSubmitted && name.trim() === '';
  const nameHelperText = hasNameError ? LABELS.projectNameRequired : undefined;

  const handleEntered = () => nameInputRef.current?.focus();
  const dialogSlotProps = { transition: { onEntered: handleEntered } };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setHasSubmitted(true);

    const trimmedName = name.trim();

    if (trimmedName === '') {
      nameInputRef.current?.focus();

      return;
    }

    const createProjectInput = {
      name: trimmedName,
      description: description.trim(),
    };

    onCreateProject(createProjectInput);
  };

  return (
    <Dialog
      open={isOpen}
      onClose={onClose}
      fullWidth
      maxWidth="sm"
      aria-labelledby={titleId}
      slotProps={dialogSlotProps}
    >
      <DialogTitle id={titleId}>{LABELS.projectCreate}</DialogTitle>
      <DialogContent>
        <Box
          component="form"
          id={formId}
          noValidate
          onSubmit={handleSubmit}
          sx={FORM_STYLE}
        >
          <TextField
            required
            label={LABELS.projectName}
            value={name}
            inputRef={nameInputRef}
            error={hasNameError}
            helperText={nameHelperText}
            onChange={(event) => setName(event.target.value)}
          />
          <TextField
            multiline
            minRows={DESCRIPTION_MIN_ROWS}
            label={LABELS.projectDescription}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{LABELS.projectCreateCancel}</Button>
        <Button type="submit" form={formId} variant="contained">
          {LABELS.projectCreate}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
