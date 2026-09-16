import LinkIcon from '@mui/icons-material/Link';
import Box from '@mui/material/Box';
import { buttonBaseClasses } from '@mui/material/ButtonBase';
import IconButton from '@mui/material/IconButton';
import TableCell from '@mui/material/TableCell';
import TableRow, { tableRowClasses } from '@mui/material/TableRow';
import Tooltip from '@mui/material/Tooltip';
import Link from 'next/link';
import type { MouseEvent } from 'react';

import { LastActivity } from '@/components/dagList/dagCard/lastActivity/lastActivity';
import { SoftChip } from '@/components/softChip/softChip';
import type { DagNode } from '@/entities/dagDetail';
import { LABELS, NODE_STATE_LABELS } from '@/labels/en';
import { createEntryFromDagPage } from '@/utils/dagPageEntry';
import { getStateColor } from '@/utils/getStateColor';
import { isSameTabClick } from '@/utils/isSameTabClick';

interface NodeTableRowProps {
  dagName: string;
  node: DagNode;
}

/**
 * Renders one row of the NodeTable.
 */
export const NodeTableRow = ({ dagName, node }: NodeTableRowProps) => {
  const handleOpen = (event: MouseEvent<HTMLElement>) => {
    if (!isSameTabClick(event)) {
      return;
    }

    createEntryFromDagPage();
  };

  return (
    <TableRow hover>
      <TableCell>
        <SoftChip
          color={getStateColor(node.state)}
          label={NODE_STATE_LABELS[node.state]}
        />
      </TableCell>
      <TableCell
        sx={{ fontFamily: (theme) => theme.typography.fontFamilyMono }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {node.id}
          <Tooltip title={LABELS.nodeOpen}>
            <IconButton
              component={Link}
              href={`/dags/${dagName}/${node.id}`}
              onClick={handleOpen}
              size="small"
              aria-label={LABELS.nodeOpen}
              sx={{
                opacity: 0,
                [`.${tableRowClasses.root}:hover &`]: { opacity: 1 },
                [`&.${buttonBaseClasses.focusVisible}`]: { opacity: 1 },
              }}
            >
              <LinkIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </TableCell>
      <TableCell>{node.title}</TableCell>
      <TableCell>{node.agentName}</TableCell>
      <TableCell>
        <LastActivity at={node.updatedAt} />
      </TableCell>
    </TableRow>
  );
};
