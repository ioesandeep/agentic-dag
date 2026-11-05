'use client';

import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import { useId } from 'react';

import { LocalCheckoutForm } from '@/components/localCheckoutForm/localCheckoutForm';
import { RepositoryActionEnum } from '@/entities/catalog/repositoryAction';
import { LABELS } from '@/labels/en';
import type { RepositoryActionDialogProps } from './types';
import { getRepositoryActionContent } from './utils';

/**
 * Confirms repository actions and local folder repair.
 */
export const RepositoryActionDialog = (
  repositoryActionDialogProps: RepositoryActionDialogProps,
) => {
  const titleId = useId();
  const descriptionId = useId();

  const { isOpen, onClose, onConfirm } = repositoryActionDialogProps;
  const content = getRepositoryActionContent(repositoryActionDialogProps);
  const repairSlotProps = {
    paper: { 'aria-label': content.title, 'aria-labelledby': undefined },
  };

  if (repositoryActionDialogProps.variant === RepositoryActionEnum.REPAIR) {
    return (
      <Dialog
        open={isOpen}
        onClose={onClose}
        fullWidth
        maxWidth="sm"
        slotProps={repairSlotProps}
      >
        <LocalCheckoutForm
          repairRepository={repositoryActionDialogProps.repository}
          inspections={repositoryActionDialogProps.inspections}
          onClose={onClose}
        />
      </Dialog>
    );
  }

  return (
    <Dialog
      open={isOpen}
      onClose={onClose}
      fullWidth
      maxWidth="sm"
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
    >
      <DialogTitle id={titleId}>{content.title}</DialogTitle>
      <DialogContent>
        <DialogContentText id={descriptionId}>
          {content.description}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button autoFocus onClick={onClose}>
          {LABELS.repositoryActionCancel}
        </Button>
        <Button variant="contained" color="error" onClick={onConfirm}>
          {content.confirm}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
