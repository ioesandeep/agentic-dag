import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import { PRIMARY_MAIN_COLOR } from '@/components/nodeDialog/constants';
import { RelativeTime } from '@/components/relativeTime/relativeTime';
import { SoftChip } from '@/components/softChip/softChip';
import type { SlackNotification } from '@/entities/nodeDetail';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

interface SlackNotificationLineProps {
  slackNotification: SlackNotification;
}

/**
 * Renders a single Slack thread with its channel and the time it opens.
 */
export const SlackNotificationLine = ({
  slackNotification,
}: SlackNotificationLineProps) => {
  const threadValues = { threadId: slackNotification.threadId };

  return (
    <Box
      sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, minWidth: 0 }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.75,
          flexWrap: 'wrap',
        }}
      >
        <SoftChip
          mono
          color={PRIMARY_MAIN_COLOR}
          label={slackNotification.channel}
        />
        <Box sx={{ flexGrow: 1 }} />
        <RelativeTime at={slackNotification.createdAt} />
      </Box>
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ wordBreak: 'break-all' }}
      >
        {formatLabel(LABELS.slackNotificationThread, threadValues)}
      </Typography>
    </Box>
  );
};
