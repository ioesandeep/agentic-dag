'use client';

import Box from '@mui/material/Box';
import ButtonBase from '@mui/material/ButtonBase';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import type { NodeProps } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import Link from 'next/link';
import type { MouseEvent } from 'react';

import {
  NODE_HEIGHT,
  NODE_WIDTH,
  STATE_BORDER_WIDTH,
} from '@/components/dagPanel/dagGraph/constants';
import { PullRequestBadge } from '@/components/dagPanel/dagGraph/pullRequestBadge/pullRequestBadge';
import type { DagFlowNode } from '@/components/dagPanel/dagGraph/types';
import { SoftChip } from '@/components/softChip/softChip';
import { NODE_STATE_LABELS } from '@/labels/en';
import { createEntryFromDagPage } from '@/utils/dagPageEntry';
import { getStateColor } from '@/utils/getStateColor';
import { isSameTabClick } from '@/utils/isSameTabClick';

/**
 * Renders one node of the DagGraph.
 */
export const DagGraphNode = ({ data }: NodeProps<DagFlowNode>) => {
  const { node, dagName } = data;

  const handleOpen = (event: MouseEvent<HTMLElement>) => {
    if (!isSameTabClick(event)) {
      return;
    }

    createEntryFromDagPage();
  };

  return (
    <>
      <Handle type="target" position={Position.Left} isConnectable={false} />
      <Paper
        variant="outlined"
        sx={{
          width: NODE_WIDTH,
          height: NODE_HEIGHT,
          overflow: 'hidden',
          borderLeft: STATE_BORDER_WIDTH,
          borderLeftColor: getStateColor(node.state),
          transition: 'box-shadow 200ms ease',
          '&:hover': { boxShadow: 3 },
        }}
      >
        <ButtonBase
          component={Link}
          href={`/dags/${dagName}/${node.id}`}
          onClick={handleOpen}
          sx={{
            width: '100%',
            height: '100%',
            p: 1.25,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'stretch',
            justifyContent: 'center',
            gap: 0.75,
            textAlign: 'left',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
            <Typography
              variant="body2"
              noWrap
              sx={{ flexGrow: 1, minWidth: 0, fontWeight: 500 }}
            >
              {node.title}
            </Typography>
            <PullRequestBadge prUrl={node.prUrl} />
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
            <SoftChip
              color={getStateColor(node.state)}
              label={NODE_STATE_LABELS[node.state]}
            />
            <Typography variant="caption" color="text.secondary" noWrap>
              {node.agentName}
            </Typography>
          </Box>
        </ButtonBase>
      </Paper>
      <Handle type="source" position={Position.Right} isConnectable={false} />
    </>
  );
};
