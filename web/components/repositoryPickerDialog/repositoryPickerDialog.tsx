'use client';

import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import List from '@mui/material/List';
import Typography from '@mui/material/Typography';
import { useId, useState } from 'react';

import { REPOSITORY_OPTION_HEIGHT_REM } from '@/components/repositoryOption/constants';
import { RepositoryOption } from '@/components/repositoryOption/repositoryOption';
import type { ProjectSummary } from '@/entities/catalog/project';
import type { Repository } from '@/entities/catalog/repository';
import { LABELS } from '@/labels/en';
import { MOCK_REPOSITORIES } from '@/mocks/catalogMocks';

const MAX_VISIBLE_REPOSITORIES = 5;
const LIST_STYLE = { maxHeight: `${REPOSITORY_OPTION_HEIGHT_REM * MAX_VISIBLE_REPOSITORIES}rem`, overflowY: 'auto' };
const ACTIONS_STYLE = { px: 3, pb: 2 };

interface RepositoryPickerDialogProps {
  isOpen: boolean;
  onClose: () => void;
  project: ProjectSummary;
  repositories?: readonly Repository[];
}

/**
 * Selects catalog repositories and their project branches.
 */
export const RepositoryPickerDialog = ({ isOpen, onClose, project, repositories = MOCK_REPOSITORIES }: RepositoryPickerDialogProps) => {
  const [selectedRepositoryIds, setSelectedRepositoryIds] = useState<ReadonlySet<string>>(() => new Set());
  const [branchOverrides, setBranchOverrides] = useState<Record<string, string>>({});
  const titleId = useId();

  const activeRepositories = repositories.filter((repository) => repository.archivedAt === null);
  const firstAvailableRepository = activeRepositories.find((repository) => !repository.memberships.some((membership) => membership.project.id === project.id));
  const hasSelection = selectedRepositoryIds.size > 0;
  const handleSelectionChange = (repositoryId: string, isSelected: boolean) => {
    const updatedRepositoryIds = new Set(selectedRepositoryIds);
    if (isSelected) {
      updatedRepositoryIds.add(repositoryId);
    } else {
      updatedRepositoryIds.delete(repositoryId);
    }

    setSelectedRepositoryIds(updatedRepositoryIds);
  };

  const handleBranchChange = (repositoryId: string, branch: string) => {
    const updatedBranches = { ...branchOverrides, [repositoryId]: branch };
    setBranchOverrides(updatedBranches);
  };

  return (
    <Dialog open={isOpen} onClose={onClose} fullWidth maxWidth="sm" aria-labelledby={titleId}>
      <DialogTitle id={titleId}>{LABELS.repositoryPickerTitle}</DialogTitle>
      <DialogContent>
        <List disablePadding aria-label={LABELS.projectRepositories} sx={LIST_STYLE}>
          {activeRepositories.map((repository) => {
            const membership = repository.memberships.find((membership) => membership.project.id === project.id);
            const disabledReason = membership === undefined ? undefined : LABELS.repositoryAlreadyInProject;
            const branch = branchOverrides[repository.id] ?? membership?.branch ?? repository.defaultBranch ?? repository.branches[0] ?? '';
            const isSelected = selectedRepositoryIds.has(repository.id);

            return (
              <RepositoryOption
                key={repository.id} repository={repository} branch={branch} isSelected={isSelected}
                disabledReason={disabledReason} autoFocus={repository.id === firstAvailableRepository?.id}
                onSelectionChange={(isSelected) => handleSelectionChange(repository.id, isSelected)}
                onBranchChange={(branch) => handleBranchChange(repository.id, branch)}
              />
            );
          })}
        </List>
        {activeRepositories.length === 0 && <Typography color="text.secondary">{LABELS.repositoryPickerEmpty}</Typography>}
      </DialogContent>
      <DialogActions sx={ACTIONS_STYLE}>
        <Button autoFocus={firstAvailableRepository === undefined} onClick={onClose}>{LABELS.repositoryActionCancel}</Button>
        <Button onClick={onClose} variant="contained" disabled={!hasSelection}>
          {LABELS.projectRepositoryAdd}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
