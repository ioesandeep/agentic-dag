import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';

import { DISABLED_BUTTON_STYLE } from '@/components/nodeDialog/nodeStatus/nodeActionByState/constants';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

interface StopDialogProps {
  nodeId: string;
  isOpen: boolean;
  // True while the stop request is in flight.
  isPending: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

/**
 * Renders the dialog that confirms a stop of a node's running session.
 */
export const StopDialog = ({
  nodeId,
  isOpen,
  isPending,
  onClose,
  onConfirm,
}: StopDialogProps) => {
  const titleValues = { node: nodeId };

  return (
    <Dialog open={isOpen} onClose={onClose}>
      <DialogTitle>
        {formatLabel(LABELS.nodeStopDialogTitle, titleValues)}
      </DialogTitle>
      <DialogContent>
        <DialogContentText>{LABELS.nodeStopDialogDescription}</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button autoFocus onClick={onClose}>
          {LABELS.nodeActionCancel}
        </Button>
        <Button
          variant="contained"
          color="error"
          disabled={isPending}
          aria-busy={isPending}
          sx={DISABLED_BUTTON_STYLE}
          onClick={onConfirm}
        >
          {LABELS.nodeStopSubmit}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
