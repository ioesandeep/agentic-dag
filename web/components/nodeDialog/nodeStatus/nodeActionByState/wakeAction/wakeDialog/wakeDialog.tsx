'use client';

import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import type { ChangeEvent, FormEvent } from 'react';
import { useId, useRef, useState } from 'react';

import { DISABLED_BUTTON_STYLE } from '@/components/nodeDialog/nodeStatus/nodeActionByState/constants';
import { RECOVERY_CAUSES } from '@/entities/nodeDetail';
import { useNodeAction } from '@/hooks/useNodeAction';
import { LABELS, RECOVERY_CAUSE_LABELS } from '@/labels/en';
import { getNodeActionPath, NodeActionEnum } from '@/utils/apiPath';
import { formatLabel } from '@/utils/formatLabel';

import type { FocusableInput } from './types';
import { getRequiredHelperText, getWakeRequest, isBlank } from './utils';

const FORM_STYLE = { display: 'flex', flexDirection: 'column', gap: 2, pt: 2 };
const MESSAGE_MIN_ROWS = 3;
const SUMMARY_MIN_FIELD_COUNT = 2;

interface WakeDialogProps {
  dagName: string;
  nodeId: string;
  isOpen: boolean;
  onClose: () => void;
  onWake: () => void;
}

/**
 * Renders the dialog that requests a resting node's wake with a recovery cause, an action, and a message.
 */
export const WakeDialog = ({
  dagName,
  nodeId,
  isOpen,
  onClose,
  onWake,
}: WakeDialogProps) => {
  const causeInputRef = useRef<FocusableInput>(null);
  const actionInputRef = useRef<FocusableInput>(null);
  const messageInputRef = useRef<FocusableInput>(null);

  const [cause, setCause] = useState('');
  const [action, setAction] = useState('');
  const [message, setMessage] = useState('');
  const [hasSubmitted, setHasSubmitted] = useState(false);

  const formId = useId();
  const wakePath = getNodeActionPath(dagName, nodeId, NodeActionEnum.WAKE);
  const { isPending, failureDetail, postNodeAction } = useNodeAction(
    wakePath,
    onWake,
  );

  const isCauseMissing = cause === '';
  const isActionMissing = isBlank(action);
  const isMessageMissing = isBlank(message);

  const hasCauseError = hasSubmitted && isCauseMissing;
  const hasActionError = hasSubmitted && isActionMissing;
  const hasMessageError = hasSubmitted && isMessageMissing;

  const missingFieldCount = [
    isCauseMissing,
    isActionMissing,
    isMessageMissing,
  ].filter((isMissing) => isMissing).length;
  const hasSummary =
    hasSubmitted && missingFieldCount >= SUMMARY_MIN_FIELD_COUNT;
  const hasFailureAlert = failureDetail !== null && missingFieldCount === 0;

  const titleValues = { node: nodeId };
  const submitLabel = isPending ? LABELS.nodeWakePending : LABELS.nodeWakeSubmit;

  const handleCauseChange = (event: ChangeEvent<HTMLInputElement>) =>
    setCause(event.target.value);
  const handleActionChange = (event: ChangeEvent<HTMLInputElement>) =>
    setAction(event.target.value);
  const handleMessageChange = (event: ChangeEvent<HTMLInputElement>) =>
    setMessage(event.target.value);

  const handleClose = () => {
    if (isPending) {
      return;
    }

    onClose();
  };

  const focusFirstMissingField = () => {
    const wakeFields = [
      { isMissing: isCauseMissing, inputRef: causeInputRef },
      { isMissing: isActionMissing, inputRef: actionInputRef },
      { isMissing: isMessageMissing, inputRef: messageInputRef },
    ];
    const firstMissingField = wakeFields.find(
      (wakeField) => wakeField.isMissing,
    );

    firstMissingField?.inputRef.current?.focus();
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setHasSubmitted(true);

    const wakeRequest = getWakeRequest(cause, action, message);

    if (wakeRequest === null) {
      focusFirstMissingField();
      return;
    }

    postNodeAction(wakeRequest);
  };

  return (
    <Dialog open={isOpen} onClose={handleClose} fullWidth>
      <DialogTitle>
        {formatLabel(LABELS.nodeWakeDialogTitle, titleValues)}
      </DialogTitle>
      <DialogContent>
        <DialogContentText>{LABELS.nodeWakeDialogDescription}</DialogContentText>
        <Box
          component="form"
          id={formId}
          noValidate
          onSubmit={handleSubmit}
          sx={FORM_STYLE}
        >
          {hasSummary && (
            <Alert severity="error">{LABELS.nodeWakeFieldsRequired}</Alert>
          )}
          <TextField
            select
            required
            autoFocus
            label={LABELS.nodeWakeCause}
            value={cause}
            inputRef={causeInputRef}
            error={hasCauseError}
            helperText={getRequiredHelperText(
              hasCauseError,
              LABELS.nodeWakeCauseRequired,
            )}
            onChange={handleCauseChange}
          >
            {RECOVERY_CAUSES.map((recoveryCause) => (
              <MenuItem key={recoveryCause} value={recoveryCause}>
                {RECOVERY_CAUSE_LABELS[recoveryCause]}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            required
            label={LABELS.nodeWakeAction}
            value={action}
            inputRef={actionInputRef}
            error={hasActionError}
            helperText={getRequiredHelperText(
              hasActionError,
              LABELS.nodeWakeActionRequired,
            )}
            onChange={handleActionChange}
          />
          <TextField
            required
            multiline
            minRows={MESSAGE_MIN_ROWS}
            label={LABELS.nodeWakeMessage}
            value={message}
            inputRef={messageInputRef}
            error={hasMessageError}
            helperText={getRequiredHelperText(
              hasMessageError,
              LABELS.nodeWakeMessageRequired,
            )}
            onChange={handleMessageChange}
          />
          {hasFailureAlert && <Alert severity="error">{failureDetail}</Alert>}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button
          disabled={isPending}
          sx={DISABLED_BUTTON_STYLE}
          onClick={onClose}
        >
          {LABELS.nodeActionCancel}
        </Button>
        <Button
          type="submit"
          form={formId}
          variant="contained"
          disabled={isPending}
          aria-busy={isPending}
          sx={DISABLED_BUTTON_STYLE}
        >
          {submitLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
