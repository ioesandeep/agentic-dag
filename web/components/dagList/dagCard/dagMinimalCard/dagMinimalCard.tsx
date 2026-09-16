import Avatar from '@mui/material/Avatar';
import Badge from '@mui/material/Badge';
import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import Tooltip from '@mui/material/Tooltip';
import Link from 'next/link';

import {
  MINIMAL_AVATAR_FONT_SIZE,
  MINIMAL_AVATAR_SIZE,
} from '@/components/dagList/dagCard/constants';
import type { DagCardSelect } from '@/components/dagList/dagCard/types';
import {
  getAriaCurrent,
  getCardBorderColor,
  getLatestStateColor,
} from '@/components/dagList/dagCard/utils';
import type { DagSummary } from '@/entities/dagSummary';
import { getLatestNodeState } from '@/utils/dagNodes';

interface DagMinimalCardProps {
  dag: DagSummary;
  isCurrent: boolean;
  onSelect?: DagCardSelect;
}

/**
 * Renders the DagCard when the dag list is collapsed.
 */
export const DagMinimalCard = ({
  dag,
  isCurrent,
  onSelect,
}: DagMinimalCardProps) => {
  const latestState = getLatestNodeState(dag.nodes);

  return (
    <Tooltip title={dag.name} placement="right">
      <Card
        sx={{
          flexShrink: 0,
          transition: 'border-color 200ms ease',
          borderColor: getCardBorderColor(isCurrent),
          '&:hover': { borderColor: 'primary.main' },
        }}
      >
        <CardActionArea
          component={Link}
          href={`/dags/${dag.name}`}
          aria-current={getAriaCurrent(isCurrent)}
          onClick={onSelect}
          sx={{ display: 'flex', justifyContent: 'center', p: 1 }}
        >
          <Badge
            overlap="circular"
            variant="dot"
            invisible={latestState === null}
            sx={{
              '& .MuiBadge-badge': {
                bgcolor: getLatestStateColor(latestState),
              },
            }}
          >
            <Avatar
              variant="rounded"
              sx={{
                width: MINIMAL_AVATAR_SIZE,
                height: MINIMAL_AVATAR_SIZE,
                fontSize: MINIMAL_AVATAR_FONT_SIZE,
                bgcolor: 'action.selected',
                color: 'text.primary',
              }}
            >
              {dag.name.charAt(0).toUpperCase()}
            </Avatar>
          </Badge>
        </CardActionArea>
      </Card>
    </Tooltip>
  );
};
