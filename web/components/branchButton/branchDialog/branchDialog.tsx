'use client';

import Autocomplete from '@mui/material/Autocomplete';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import TextField from '@mui/material/TextField';
import type { FormEvent } from 'react';
import { useId, useRef, useState } from 'react';

import { isValidBranchName } from '@/components/branchButton/utils';
import type { Repository } from '@/entities/catalog/repository';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

const INPUT_STYLE = { mt: 1 };

interface BranchDialogProps {
  repository: Repository;
  branch: string;
  onClose: () => void;
  onChange: (branch: string) => void;
}

/**
 * Selects an existing repository branch or creates a new branch.
 */
export const BranchDialog = ({
  repository,
  branch: currentBranch,
  onClose,
  onChange,
}: BranchDialogProps) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [branch, setBranch] = useState(currentBranch);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const titleId = useId();

  const titleValues = { repository: repository.fullName };
  const title = formatLabel(LABELS.repositoryBranchesTitle, titleValues);
  const isExistingBranch = repository.branches.includes(branch);
  const submitLabel = isExistingBranch ? LABELS.repositoryUseBranch : LABELS.repositoryCreateBranch;

  const isValid = isValidBranchName(branch);
  const hasError = hasSubmitted && !isValid;
  const helperText = hasError ? LABELS.repositoryBranchInvalid : LABELS.repositoryBranchHint;
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setHasSubmitted(true);
    if (!isValid) {
      inputRef.current?.focus();

      return;
    }

    onChange(branch);
  };

  return (
    <Dialog open fullWidth maxWidth="sm" onClose={onClose} aria-labelledby={titleId}>
      <Box component="form" noValidate onSubmit={handleSubmit}>
        <DialogTitle id={titleId}>{title}</DialogTitle>
        <DialogContent>
          <Autocomplete
            freeSolo
            forcePopupIcon
            clearText={LABELS.repositoryBranchClear}
            openText={LABELS.repositoryBranchesOpen}
            closeText={LABELS.repositoryBranchesClose}
            selectOnFocus
            handleHomeEndKeys
            options={repository.branches}
            value={branch}
            inputValue={branch}
            onChange={(_, branch) => setBranch(branch ?? '')}
            onInputChange={(_, branch) => setBranch(branch)}
            sx={INPUT_STYLE}
            renderOption={(optionProps, option) => {
              const { key, ...listItemProps } = optionProps;
              const branchValues = { branch: option };
              const defaultLabel = formatLabel(LABELS.repositoryBranchDefault, branchValues);
              const isDefault = option === repository.defaultBranch;
              const label = isDefault ? defaultLabel : option;

              return (
                <Box component="li" key={key} {...listItemProps}>
                  {label}
                </Box>
              );
            }}
            renderInput={(autocompleteInput) => (
              <TextField
                {...autocompleteInput}
                autoFocus
                required
                inputRef={inputRef}
                label={LABELS.repositoryBranch}
                error={hasError}
                helperText={helperText}
              />
            )}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>{LABELS.repositoryActionCancel}</Button>
          <Button variant="contained" type="submit">
            {submitLabel}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
};
