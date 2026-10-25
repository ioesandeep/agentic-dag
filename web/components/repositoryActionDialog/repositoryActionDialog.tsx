'use client';

import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import { useId } from 'react';

import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

interface RepositoryActionDialogProps {
  projectName: string;
  repositoryName: string;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

/**
 * Confirms removal of a repository from a project.
 */
export const RepositoryActionDialog = ({
  projectName,
  repositoryName,
  isOpen,
  onClose,
  onConfirm,
}: RepositoryActionDialogProps) => {
  const titleId = useId();
  const descriptionId = useId();
  const titleValues = { project: projectName, repository: repositoryName };
  const title = formatLabel(
    LABELS.repositoryRemoveFromProjectTitle,
    titleValues,
  );

  return (
    <Dialog
      open={isOpen}
      onClose={onClose}
      fullWidth
      maxWidth="sm"
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
    >
      <DialogTitle id={titleId}>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText id={descriptionId}>
          {LABELS.repositoryRemoveFromProjectDescription}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button autoFocus onClick={onClose}>
          {LABELS.repositoryActionCancel}
        </Button>
        <Button variant="contained" color="error" onClick={onConfirm}>
          {LABELS.repositoryRemoveFromProject}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
