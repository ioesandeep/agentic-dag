'use client';

import ButtonBase from '@mui/material/ButtonBase';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import type { NodeProps } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';

import {
  NODE_BUTTON_STYLE,
  NODE_HEIGHT,
  NODE_WIDTH,
  OUTLINE_WIDTH,
  PRIMARY_COLOR,
  REM_PIXELS,
  SECONDARY_COLOR,
  SELECTION_RING_WIDTH,
} from '@/components/planGraph/constants';
import type { PlanFlowNode } from '@/components/planGraph/types';
import { SoftChip } from '@/components/softChip/softChip';

/**
 * Displays a plan node's title and execution settings.
 */
export const PlanGraphNode = ({
  data,
  selected,
  isConnectable,
}: NodeProps<PlanFlowNode>) => (
  <>
    <Handle
      type="target"
      position={Position.Left}
      isConnectable={isConnectable}
    />
    <Paper
      variant="outlined"
      sx={{
        position: 'relative',
        width: `${NODE_WIDTH / REM_PIXELS}rem`,
        height: `${NODE_HEIGHT / REM_PIXELS}rem`,
        p: 1.25,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        gap: 0.75,
        ...(data.changeLabel !== null && {
          outline: `${OUTLINE_WIDTH} solid ${PRIMARY_COLOR}`,
        }),
        ...(selected && {
          borderColor: 'primary.main',
          boxShadow: `0 0 0 ${SELECTION_RING_WIDTH} color-mix(in srgb, ${PRIMARY_COLOR} 30%, transparent)`,
        }),
      }}
    >
      {data.changeLabel !== null && (
        <Typography
          variant="caption"
          sx={(theme) => ({
            position: 'absolute',
            top: 0,
            left: theme.spacing(1.25),
            transform: 'translateY(-50%)',
            px: 1,
            borderRadius: theme.shape.borderRadius,
            bgcolor: 'primary.main',
            color: (theme.vars ?? theme).palette.primary.contrastText,
            fontWeight: 500,
          })}
        >
          {data.changeLabel}
        </Typography>
      )}
      <ButtonBase
        onClick={() => data.onSelectNode(data.nodeId)}
        sx={NODE_BUTTON_STYLE}
      >
        <Typography variant="body2" noWrap sx={{ fontWeight: 500 }}>
          {data.title}
        </Typography>
      </ButtonBase>
      <Stack direction="row" spacing={0.75} sx={{ minWidth: 0 }}>
        <SoftChip label={data.nodeId} color={PRIMARY_COLOR} mono />
        <SoftChip label={data.executorLabel} color={SECONDARY_COLOR} />
        <SoftChip label={data.repositoryName} color={SECONDARY_COLOR} />
      </Stack>
    </Paper>
    <Handle
      type="source"
      position={Position.Right}
      isConnectable={isConnectable}
    />
  </>
);
