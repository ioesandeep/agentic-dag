'use client';

import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import { Fragment, useState } from 'react';

import {
  DISABLED_BUTTON_STYLE,
  FAILURE_STYLE,
} from '@/components/nodeDialog/nodeStatus/nodeActionByState/constants';
import { RetryDialog } from '@/components/nodeDialog/nodeStatus/nodeActionByState/retryAction/retryDialog/retryDialog';
import type { RetryRequest } from '@/entities/retryRequest';
import { useNodeAction } from '@/hooks/useNodeAction';
import { LABELS } from '@/labels/en';
import { getNodeActionPath, NodeActionEnum } from '@/utils/apiPath';

interface RetryActionProps {
  dagName: string;
  nodeId: string;
  onNodeActionSuccess: () => void;
}

/**
 * Renders the retry button of a node with its confirmation dialog and the failure of its last request.
 */
export const RetryAction = ({
  dagName,
  nodeId,
  onNodeActionSuccess,
}: RetryActionProps) => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [dialogOpenCount, setDialogOpenCount] = useState(0);
  const retryPath = getNodeActionPath(dagName, nodeId, NodeActionEnum.RETRY);
  const { isPending, failureDetail, postNodeAction } = useNodeAction(
    retryPath,
    onNodeActionSuccess,
  );

  const retryLabel = isPending ? LABELS.nodeRetryPending : LABELS.nodeRetry;

  const handleOpenDialog = () => {
    setDialogOpenCount((count) => count + 1);
    setIsDialogOpen(true);
  };

  const handleCloseDialog = () => setIsDialogOpen(false);

  const handleConfirmRetry = (retryRequest: RetryRequest) => {
    setIsDialogOpen(false);
    postNodeAction(retryRequest);
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
        {retryLabel}
      </Button>
      {failureDetail !== null && (
        <Alert severity="error" sx={FAILURE_STYLE}>
          {failureDetail}
        </Alert>
      )}
      <RetryDialog
        key={dialogOpenCount}
        nodeId={nodeId}
        isOpen={isDialogOpen}
        isPending={isPending}
        onClose={handleCloseDialog}
        onConfirm={handleConfirmRetry}
      />
    </Fragment>
  );
};
