import ScheduleOutlinedIcon from '@mui/icons-material/ScheduleOutlined';
import SensorsOutlinedIcon from '@mui/icons-material/SensorsOutlined';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import Link from 'next/link';

import { DagCardBody } from '@/components/dagList/dagCard/dagCardBody/dagCardBody';
import { DagCardFooter } from '@/components/dagList/dagCard/dagCardFooter/dagCardFooter';
import { DagCardHeader } from '@/components/dagList/dagCard/dagCardHeader/dagCardHeader';
import type { DagCardAction } from '@/components/dagList/dagCard/dagCardHeader/types';
import type { DagCardSelect } from '@/components/dagList/dagCard/types';
import {
  getAriaCurrent,
  getCardBorderColor,
  getFlagIconColor,
  getScheduleTooltip,
  getWatchTooltip,
} from '@/components/dagList/dagCard/utils';
import type { DagSummary } from '@/entities/dagSummary';

interface DagFlexibleCardProps {
  dag: DagSummary;
  isCurrent: boolean;
  onSelect?: DagCardSelect;
}

/**
 * Renders the DagCard when the dag list is displayed in split view.
 */
export const DagFlexibleCard = ({
  dag,
  isCurrent,
  onSelect,
}: DagFlexibleCardProps) => {
  const actions: DagCardAction[] = [
    {
      title: getScheduleTooltip(dag.isScheduled),
      icon: (
        <ScheduleOutlinedIcon
          fontSize="small"
          sx={{ color: getFlagIconColor(dag.isScheduled) }}
        />
      ),
    },
    {
      title: getWatchTooltip(dag.isWatching),
      icon: (
        <SensorsOutlinedIcon
          fontSize="small"
          sx={{ color: getFlagIconColor(dag.isWatching) }}
        />
      ),
    },
  ];

  return (
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
        sx={{ display: 'flex', flexDirection: 'column', alignItems: 'stretch' }}
      >
        <Box
          sx={{
            p: 2,
            pb: 1.5,
            display: 'flex',
            flexDirection: 'column',
            gap: 1.25,
          }}
        >
          <DagCardHeader title={dag.name} actions={actions} />
          <DagCardBody dag={dag} hasNodeHighlights={false} />
        </Box>
        <DagCardFooter dag={dag} />
      </CardActionArea>
    </Card>
  );
};
