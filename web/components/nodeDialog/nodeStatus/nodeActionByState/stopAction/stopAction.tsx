'use client';

import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import { Fragment, useState } from 'react';

import {
  DISABLED_BUTTON_STYLE,
  FAILURE_STYLE,
} from '@/components/nodeDialog/nodeStatus/nodeActionByState/constants';
import { StopDialog } from '@/components/nodeDialog/nodeStatus/nodeActionByState/stopAction/stopDialog/stopDialog';
import { useNodeAction } from '@/hooks/useNodeAction';
import { LABELS } from '@/labels/en';
import { getNodeActionPath, NodeActionEnum } from '@/utils/apiPath';

interface StopActionProps {
  dagName: string;
  nodeId: string;
  onNodeActionSuccess: () => void;
}

/**
 * Renders the stop button of a node with its confirmation dialog and the failure of its last request.
 */
export const StopAction = ({
  dagName,
  nodeId,
  onNodeActionSuccess,
}: StopActionProps) => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const stopPath = getNodeActionPath(dagName, nodeId, NodeActionEnum.STOP);
  const { isPending, failureDetail, postNodeAction } = useNodeAction(
    stopPath,
    onNodeActionSuccess,
  );

  const stopLabel = isPending ? LABELS.nodeStopPending : LABELS.nodeStop;

  const handleOpenDialog = () => setIsDialogOpen(true);
  const handleCloseDialog = () => setIsDialogOpen(false);

  const handleConfirmStop = () => {
    setIsDialogOpen(false);
    postNodeAction(null);
  };

  return (
    <Fragment>
      <Button
        size="small"
        variant="outlined"
        disabled={isPending}
        aria-busy={isPending}
        sx={DISABLED_BUTTON_STYLE}
        onClick={handleOpenDialog}
      >
        {stopLabel}
      </Button>
      {failureDetail !== null && (
        <Alert severity="error" sx={FAILURE_STYLE}>
          {failureDetail}
        </Alert>
      )}
      <StopDialog
        nodeId={nodeId}
        isOpen={isDialogOpen}
        isPending={isPending}
        onClose={handleCloseDialog}
        onConfirm={handleConfirmStop}
      />
    </Fragment>
  );
};
