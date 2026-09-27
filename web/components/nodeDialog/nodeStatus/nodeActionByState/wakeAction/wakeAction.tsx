'use client';

import Button from '@mui/material/Button';
import { Fragment, useState } from 'react';

import { WakeDialog } from '@/components/nodeDialog/nodeStatus/nodeActionByState/wakeAction/wakeDialog/wakeDialog';
import { LABELS } from '@/labels/en';

interface WakeActionProps {
  dagName: string;
  nodeId: string;
  onNodeActionSuccess: () => void;
}

/**
 * Renders the wake button of a resting node with the dialog it opens.
 */
export const WakeAction = ({
  dagName,
  nodeId,
  onNodeActionSuccess,
}: WakeActionProps) => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [dialogOpenCount, setDialogOpenCount] = useState(0);

  const handleOpenDialog = () => {
    setDialogOpenCount((count) => count + 1);
    setIsDialogOpen(true);
  };

  const handleCloseDialog = () => setIsDialogOpen(false);

  const handleWake = () => {
    setIsDialogOpen(false);
    onNodeActionSuccess();
  };

  return (
    <Fragment>
      <Button size="small" variant="outlined" onClick={handleOpenDialog}>
        {LABELS.nodeWake}
      </Button>
      <WakeDialog
        key={dialogOpenCount}
        dagName={dagName}
        nodeId={nodeId}
        isOpen={isDialogOpen}
        onClose={handleCloseDialog}
        onWake={handleWake}
      />
    </Fragment>
  );
};
