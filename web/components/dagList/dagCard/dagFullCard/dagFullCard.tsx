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
  getFlagIconColor,
  getScheduleTooltip,
  getWatchTooltip,
} from '@/components/dagList/dagCard/utils';
import type { DagSummary } from '@/entities/dagSummary';

interface DagFullCardProps {
  dag: DagSummary;
  onSelect?: DagCardSelect;
}

/**
 * Renders the DagCard on the dags listing page.
 */
export const DagFullCard = ({ dag, onSelect }: DagFullCardProps) => {
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
        height: '100%',
        transition: 'border-color 200ms ease, box-shadow 200ms ease',
        '&:hover': { borderColor: 'primary.main', boxShadow: 3 },
      }}
    >
      <CardActionArea
        component={Link}
        href={`/dags/${dag.name}`}
        onClick={onSelect}
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'stretch',
        }}
      >
        <Box
          sx={{
            p: 2.5,
            pb: 2,
            flexGrow: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: 1.5,
          }}
        >
          <DagCardHeader title={dag.name} actions={actions} />
          <DagCardBody dag={dag} hasNodeHighlights />
        </Box>
        <DagCardFooter dag={dag} />
      </CardActionArea>
    </Card>
  );
};
