import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import { SlackNotificationLine } from '@/components/nodeDialog/nodeSidebar/slackNotificationList/slackNotificationLine/slackNotificationLine';
import type { SlackNotification } from '@/entities/nodeDetail';
import { LABELS } from '@/labels/en';

interface SlackNotificationListProps {
  slackNotifications: SlackNotification[];
}

/**
 * Renders every Slack thread opened about a node, oldest first.
 */
export const SlackNotificationList = ({
  slackNotifications,
}: SlackNotificationListProps) => {
  if (slackNotifications.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        {LABELS.slackNotificationsEmpty}
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      {slackNotifications.map((slackNotification) => (
        <SlackNotificationLine
          key={slackNotification.id}
          slackNotification={slackNotification}
        />
      ))}
    </Box>
  );
};
