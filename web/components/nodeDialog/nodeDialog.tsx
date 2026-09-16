'use client';

import Dialog from '@mui/material/Dialog';
import { useRouter } from 'next/navigation';

import { BackButton } from '@/components/backButton/backButton';
import { ColorSchemeToggle } from '@/components/colorSchemeToggle/colorSchemeToggle';
import { NodeDialogBody } from '@/components/nodeDialog/nodeDialogBody/nodeDialogBody';
import { RequestFailureAlert } from '@/components/requestFailureAlert/requestFailureAlert';
import { TopAppBar } from '@/components/topAppBar/topAppBar';
import type { NodeDetail, NodeLink } from '@/entities/nodeDetail';
import { LABELS } from '@/labels/en';
import { getDagRoute } from '@/utils/route';

const PAPER_STYLE = { bgcolor: 'background.default', backgroundImage: 'none' };
const NO_DIALOG_TRANSITION = 0;

interface NodeDialogProps {
  dagName: string;
  nodeId: string;
  // Every node of the dag.
  nodes: NodeLink[];
  // The node's record, null until the api sends it.
  detail: NodeDetail | null;
  // True where the dag records no node with this id.
  isMissing: boolean;
  // True where the last request to the api failed.
  hasFailed: boolean;
}

/**
 * Renders one node's screen as a fullscreen dialog over the dag page.
 */
export const NodeDialog = ({
  dagName,
  nodeId,
  nodes,
  detail,
  isMissing,
  hasFailed,
}: NodeDialogProps) => {
  const router = useRouter();
  const dagRoute = getDagRoute(dagName);
  const title = detail?.title ?? nodeId;
  const dialogSlotProps = { paper: { sx: PAPER_STYLE, 'aria-label': title } };

  const handleClose = () => router.push(dagRoute);

  return (
    <Dialog
      fullScreen
      open
      onClose={handleClose}
      transitionDuration={NO_DIALOG_TRANSITION}
      slotProps={dialogSlotProps}
    >
      <TopAppBar
        backButton={<BackButton href={dagRoute} label={LABELS.nodeBack} />}
        title={title}
        actions={<ColorSchemeToggle />}
      />
      <RequestFailureAlert hasFailed={hasFailed} />
      <NodeDialogBody
        dagName={dagName}
        nodeId={nodeId}
        nodes={nodes}
        detail={detail}
        isMissing={isMissing}
      />
    </Dialog>
  );
};
