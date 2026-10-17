'use client';

import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import { buttonClasses } from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import TextField from '@mui/material/TextField';
import type { ChangeEvent, FormEvent } from 'react';
import { useEffect, useId, useRef, useState } from 'react';

import { LABELS } from '@/labels/en';

import type { CreateProjectDialogProps } from './types';

const FORM_STYLE = { display: 'flex', flexDirection: 'column', gap: 2, pt: 1 };
const DESCRIPTION_MIN_ROWS = 3;
const ACTION_STYLE = {
  [`&.${buttonClasses.disabled}`]: { color: 'text.secondary' },
};
const SUBMIT_STYLE = {
  ...ACTION_STYLE,
  '&:hover': { backgroundColor: 'primary.main' },
};

/**
 * Renders the project creation form.
 */
export const CreateProjectDialog = ({
  isOpen,
  isPending,
  createProjectRequest,
  nameError,
  descriptionError,
  failureDetail,
  onChange,
  onSubmit,
  onClose,
}: CreateProjectDialogProps) => {
  const dialogPaperRef = useRef<HTMLDivElement>(null);
  const nameInputRef = useRef<HTMLInputElement>(null);
  const descriptionInputRef = useRef<HTMLTextAreaElement>(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const formId = useId();
  const titleId = useId();

  const isNameMissing = createProjectRequest.name.trim() === '';
  const nameHelperText = hasSubmitted && isNameMissing ? LABELS.projectNameRequired : nameError;
  const hasNameError = Boolean(nameHelperText);
  const hasMultipleFieldErrors = hasNameError && Boolean(descriptionError);
  const fieldErrorSummary = hasMultipleFieldErrors ? LABELS.projectCreateFieldsInvalid : undefined;
  const errorDetail = failureDetail ?? fieldErrorSummary;
  const submitLabel = isPending ? LABELS.projectCreatePending : LABELS.projectCreate;
  const inputSlotProps = { input: { readOnly: isPending } };

  const handleNameChange = (event: ChangeEvent<HTMLInputElement>) => {
    const updatedRequest = {
      ...createProjectRequest,
      name: event.target.value,
    };
    onChange(updatedRequest);
  };
  const handleDescriptionChange = (event: ChangeEvent<HTMLInputElement>) => {
    const updatedRequest = {
      ...createProjectRequest,
      description: event.target.value,
    };
    onChange(updatedRequest);
  };
  const handleClose = () => {
    if (isPending) {
      return;
    }

    onClose();
  };
  const handleExited = () => setHasSubmitted(false);
  const handleEntered = () => {
    const isDialogFocused = document.activeElement === dialogPaperRef.current;
    if (!isDialogFocused) {
      return;
    }

    const firstInputRef = descriptionError && !nameError ? descriptionInputRef : nameInputRef;
    firstInputRef.current?.focus();
  };
  const dialogSlotProps = {
    paper: { ref: dialogPaperRef },
    transition: { onEntered: handleEntered },
  };
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isPending) {
      return;
    }

    setHasSubmitted(true);
    if (isNameMissing) {
      nameInputRef.current?.focus();
      return;
    }

    onSubmit(createProjectRequest);
  };

  useEffect(() => {
    if (!isOpen || isPending) {
      return;
    }

    if (nameError) {
      nameInputRef.current?.focus();
    } else if (descriptionError) {
      descriptionInputRef.current?.focus();
    }
  }, [isOpen, isPending, nameError, descriptionError]);

  return (
    <Dialog
      open={isOpen}
      onClose={handleClose}
      onTransitionExited={handleExited}
      slotProps={dialogSlotProps}
      aria-labelledby={titleId}
      fullWidth
      maxWidth="sm"
    >
      <DialogTitle id={titleId}>{LABELS.projectCreate}</DialogTitle>
      <DialogContent>
        <Box component="form" id={formId} noValidate onSubmit={handleSubmit} sx={FORM_STYLE}>
          <TextField
            required
            autoFocus
            fullWidth
            id={`${formId}-name`}
            label={LABELS.projectName}
            value={createProjectRequest.name}
            inputRef={nameInputRef}
            slotProps={inputSlotProps}
            error={hasNameError}
            helperText={nameHelperText}
            onChange={handleNameChange}
          />
          <TextField
            multiline
            fullWidth
            minRows={DESCRIPTION_MIN_ROWS}
            id={`${formId}-description`}
            label={LABELS.projectDescriptionOptional}
            value={createProjectRequest.description ?? ''}
            inputRef={descriptionInputRef}
            slotProps={inputSlotProps}
            error={Boolean(descriptionError)}
            helperText={descriptionError}
            onChange={handleDescriptionChange}
          />
          {errorDetail && <Alert severity="error">{errorDetail}</Alert>}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={isPending} sx={ACTION_STYLE}>
          {LABELS.projectCreateCancel}
        </Button>
        <Button
          type="submit"
          form={formId}
          variant="contained"
          disabled={isPending}
          aria-busy={isPending}
          aria-label={submitLabel}
          sx={SUBMIT_STYLE}
        >
          <Box component="span" role="status">
            {submitLabel}
          </Box>
        </Button>
      </DialogActions>
    </Dialog>
  );
};
