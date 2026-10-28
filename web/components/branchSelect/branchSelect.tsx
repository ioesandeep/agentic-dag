'use client';

import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import type { RefObject } from 'react';
import { useRef, useState } from 'react';

import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

const NEW_BRANCH_VALUE = '\u0000new-branch';

interface BranchSelectProps {
  branches: string[];
  defaultBranch: string | null;
  branch: string;
  autoFocus?: boolean;
  inputRef?: RefObject<HTMLInputElement | null>;
  hasError?: boolean;
  onChange: (branch: string) => void;
}

/**
 * Selects a cloned repository branch.
 */
export const BranchSelect = ({ branches, defaultBranch, branch, autoFocus = false, inputRef, hasError = false, onChange }: BranchSelectProps) => {
  const newBranchInputRef = useRef<HTMLInputElement>(null);
  const [isCreatingBranch, setIsCreatingBranch] = useState(false);
  const selectedValue = isCreatingBranch ? NEW_BRANCH_VALUE : branch;
  const helperText = hasError ? LABELS.repositoryBranchInvalid : undefined;

  const branchInputRef = inputRef ?? newBranchInputRef;
  const handleChange = (selectedBranch: string) => {
    const isNewBranch = selectedBranch === NEW_BRANCH_VALUE;
    setIsCreatingBranch(isNewBranch);
    onChange(isNewBranch ? '' : selectedBranch);
  };

  const handleMenuExited = () => {
    if (isCreatingBranch) {
      branchInputRef.current?.focus();
    }
  };

  const selectSlotProps = { select: { MenuProps: { slotProps: { transition: { onExited: handleMenuExited } } } } };

  return (
    <Stack spacing={2}>
      <TextField
        select fullWidth autoFocus={autoFocus} label={LABELS.repositoryBranch}
        value={selectedValue} onChange={(event) => handleChange(event.target.value)}
        slotProps={selectSlotProps}
      >
        {branches.map((branch) => {
          const branchValues = { branch };
          const defaultLabel = formatLabel(LABELS.repositoryBranchDefault, branchValues);
          const label = branch === defaultBranch ? defaultLabel : branch;

          return <MenuItem key={branch} value={branch}>{label}</MenuItem>;
        })}
        <MenuItem value={NEW_BRANCH_VALUE}>{LABELS.repositoryAddBranch}</MenuItem>
      </TextField>
      {isCreatingBranch && (
        <TextField
          required fullWidth label={LABELS.repositoryNewBranch}
          value={branch} onChange={(event) => onChange(event.target.value)}
          inputRef={branchInputRef} error={hasError} helperText={helperText}
        />
      )}
    </Stack>
  );
};
