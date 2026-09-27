'use client';

import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import type { ChangeEvent } from 'react';
import { useState } from 'react';

import { DISABLED_BUTTON_STYLE } from '@/components/nodeDialog/nodeStatus/nodeActionByState/constants';
import type { RetryRequest } from '@/entities/retryRequest';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

const SWITCH_STYLE = { mt: 2 };

interface RetryDialogProps {
  nodeId: string;
  isOpen: boolean;
  // True while the retry request is in flight.
  isPending: boolean;
  onClose: () => void;
  onConfirm: (retryRequest: RetryRequest) => void;
}

/**
 * Renders a dialog that lets a person confirm a node retry and choose whether it resets the current session.
 */
export const RetryDialog = ({
  nodeId,
  isOpen,
  isPending,
  onClose,
  onConfirm,
}: RetryDialogProps) => {
  const [isSessionReset, setIsSessionReset] = useState(false);

  const titleValues = { node: nodeId };

  const handleSessionResetChange = (event: ChangeEvent<HTMLInputElement>) =>
    setIsSessionReset(event.target.checked);

  const handleConfirm = () => {
    const retryRequest = { reset: isSessionReset };
    onConfirm(retryRequest);
  };

  return (
    <Dialog open={isOpen} onClose={onClose}>
      <DialogTitle>
        {formatLabel(LABELS.nodeRetryDialogTitle, titleValues)}
      </DialogTitle>
      <DialogContent>
        <DialogContentText>
          {LABELS.nodeRetryDialogDescription}
        </DialogContentText>
        <FormControlLabel
          label={LABELS.nodeRetryResetSession}
          sx={SWITCH_STYLE}
          control={
            <Switch
              checked={isSessionReset}
              onChange={handleSessionResetChange}
            />
          }
        />
      </DialogContent>
      <DialogActions>
        <Button autoFocus onClick={onClose}>
          {LABELS.nodeActionCancel}
        </Button>
        <Button
          variant="contained"
          disabled={isPending}
          aria-busy={isPending}
          sx={DISABLED_BUTTON_STYLE}
          onClick={handleConfirm}
        >
          {LABELS.nodeRetrySubmit}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
