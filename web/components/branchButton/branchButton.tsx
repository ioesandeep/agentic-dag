'use client';

import ButtonBase from '@mui/material/ButtonBase';
import Tooltip from '@mui/material/Tooltip';
import { useState } from 'react';

import { BranchDialog } from '@/components/branchButton/branchDialog/branchDialog';
import { SoftChip } from '@/components/softChip/softChip';
import type { Repository } from '@/entities/catalog/repository';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

const BUTTON_STYLE = {
  borderRadius: 1,
  minWidth: 0,
  maxWidth: '100%',
  '&.Mui-disabled': { opacity: 'var(--mui-palette-action-disabledOpacity)' },
  '&.Mui-focusVisible': {
    outline: '0.125rem solid',
    outlineColor: 'primary.main',
    outlineOffset: '0.125rem',
  },
};

interface BranchButtonProps {
  repository: Repository;
  branch: string;
  disabled?: boolean;
  onChange: (branch: string) => void;
}

/**
 * Opens branch selection and creation for a repository.
 */
export const BranchButton = ({
  repository,
  branch,
  disabled = false,
  onChange,
}: BranchButtonProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [createdBranches, setCreatedBranches] = useState<string[]>([]);
  const branchRepository = {
    ...repository,
    branches: [...repository.branches, ...createdBranches],
  };

  const buttonValues = { branch };
  const label = formatLabel(LABELS.repositoryBranchButton, buttonValues);
  const titleValues = { repository: repository.fullName, branch };
  const title = formatLabel(LABELS.repositoryBranchAction, titleValues);

  const handleOpen = () => setIsOpen(true);
  const handleClose = () => setIsOpen(false);
  const handleChange = (branch: string) => {
    const isExistingBranch = branchRepository.branches.includes(branch);
    if (!isExistingBranch) {
      setCreatedBranches([...createdBranches, branch]);
    }

    onChange(branch);
    setIsOpen(false);
  };

  return (
    <>
      <Tooltip title={title}>
        <ButtonBase aria-label={title} onClick={handleOpen} disabled={disabled} sx={BUTTON_STYLE}>
          <SoftChip label={label} color="var(--mui-palette-primary-main)" />
        </ButtonBase>
      </Tooltip>
      {isOpen && (
        <BranchDialog
          repository={branchRepository}
          branch={branch}
          onClose={handleClose}
          onChange={handleChange}
        />
      )}
    </>
  );
};
