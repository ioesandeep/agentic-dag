'use client';

import CheckIcon from '@mui/icons-material/Check';
import Box from '@mui/material/Box';
import Checkbox from '@mui/material/Checkbox';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { useId } from 'react';

import { BranchButton } from '@/components/branchButton/branchButton';
import type { Repository } from '@/entities/catalog/repository';
import { REPOSITORY_OPTION_HEIGHT_REM } from './constants';

const ROW_STYLE = {
  height: `${REPOSITORY_OPTION_HEIGHT_REM}rem`,
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr) auto 2rem',
  columnGap: 1,
  px: 1,
};

const SELECTION_STYLE = {
  gridColumn: '1 / -1', gridRow: 1, display: 'grid', gridTemplateColumns: 'subgrid',
  alignItems: 'center', height: '100%', p: 0,
  '&.Mui-disabled': { opacity: 1 },
  '&.Mui-focusVisible': { bgcolor: 'transparent' },
};

const DISABLED_STYLE = { color: 'text.disabled' };
const CONTENT_STYLE = { gridColumn: 1, minWidth: 0 };
const NAME_STYLE = { fontWeight: 'fontWeightMedium', 'label:has(:focus-visible) &': { textDecoration: 'underline' } };
const BRANCH_STYLE = { minWidth: 0, maxWidth: { xs: '5rem', sm: '10rem' }, gridColumn: 2, gridRow: 1, alignSelf: 'center', zIndex: 1 };
const CHECKBOX_STYLE = { gridColumn: 3, p: 0, justifySelf: 'center' };
const EMPTY_MARK_STYLE = { width: '1.5rem', height: '1.5rem' };

interface RepositoryOptionProps {
  repository: Repository;
  branch: string;
  isSelected: boolean;
  onSelectionChange: (isSelected: boolean) => void;
  onBranchChange: (branch: string) => void;
  disabledReason?: string;
  autoFocus?: boolean;
}

/**
 * Displays a selectable repository and its project branch.
 */
export const RepositoryOption = ({ repository, branch, isSelected, onSelectionChange, onBranchChange, disabledReason, autoFocus = false }: RepositoryOptionProps) => {
  const checkboxId = useId();
  const folderId = useId();
  const disabledReasonId = useId();

  const isDisabled = disabledReason !== undefined;
  const descriptionIds = isDisabled ? `${folderId} ${disabledReasonId}` : folderId;
  const checkboxSlotProps = { input: { id: checkboxId, 'aria-label': repository.fullName, 'aria-describedby': descriptionIds } };
  const handleSelectionChange = (_: unknown, isSelected: boolean) => onSelectionChange(isSelected);

  return (
    <ListItem divider disablePadding sx={[ROW_STYLE, isDisabled && DISABLED_STYLE]}>
      <ListItemButton component="label" htmlFor={checkboxId} role={undefined} tabIndex={-1} disabled={isDisabled} sx={SELECTION_STYLE}>
        <Stack spacing={0.25} sx={CONTENT_STYLE}>
          <Typography noWrap variant="body1" title={repository.fullName} sx={NAME_STYLE}>{repository.fullName}</Typography>
          <Typography noWrap id={folderId} variant="caption" color="text.secondary" title={repository.checkoutPath}>{repository.checkoutPath}</Typography>
          {disabledReason && <Typography noWrap id={disabledReasonId} variant="caption" color="text.secondary">{disabledReason}</Typography>}
        </Stack>
        <Checkbox
          checked={isSelected} disabled={isDisabled} onChange={handleSelectionChange} disableRipple
          autoFocus={autoFocus} icon={<Box component="span" sx={EMPTY_MARK_STYLE} />} checkedIcon={<CheckIcon />}
          slotProps={checkboxSlotProps} sx={CHECKBOX_STYLE}
        />
      </ListItemButton>
      <Box sx={BRANCH_STYLE}>
        <BranchButton repository={repository} branch={branch} disabled={isDisabled} onChange={onBranchChange} />
      </Box>
    </ListItem>
  );
};
