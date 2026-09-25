'use client';

import Box from '@mui/material/Box';
import MuiLink from '@mui/material/Link';
import ListItem from '@mui/material/ListItem';
import type { SxProps, Theme } from '@mui/material/styles';
import Link from 'next/link';
import type { MouseEvent } from 'react';

import { NODE_IDS_MIN_WIDTH } from '@/components/dagPanel/dagTabs/recoverySessionList/recoverySessionRow/constants';
import { RelativeTime } from '@/components/relativeTime/relativeTime';
import { SoftChip } from '@/components/softChip/softChip';
import type { RecoverySession } from '@/entities/recoverySession';
import { LABELS, RECOVERY_SESSION_STATE_LABELS } from '@/labels/en';
import { createEntryFromDagPage } from '@/utils/dagPageEntry';
import { isSameTabClick } from '@/utils/isSameTabClick';
import {
  getRecoverySessionState,
  getRecoverySessionStateColor,
} from '@/utils/recoverySessionState';
import { getNodeRoute } from '@/utils/route';

const ROW_STYLE = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'baseline',
  columnGap: 1.5,
  rowGap: 0.5,
  px: 2,
  py: 1,
};

const NODE_IDS_STYLE = {
  display: 'flex',
  flexWrap: 'wrap',
  columnGap: 1,
  flex: 1,
  minWidth: NODE_IDS_MIN_WIDTH,
};

const NODE_ID_STYLE: SxProps<Theme> = {
  fontFamily: (theme) => theme.typography.fontFamilyMono,
  overflowWrap: 'anywhere',
};

interface RecoverySessionRowProps {
  dagName: string;
  recoverySession: RecoverySession;
}

/**
 * Renders a recovery session in the RecoverySessionList.
 */
export const RecoverySessionRow = ({
  dagName,
  recoverySession,
}: RecoverySessionRowProps) => {
  const recoverySessionState = getRecoverySessionState(recoverySession);

  const handleOpen = (event: MouseEvent<HTMLElement>) => {
    const isSameTab = isSameTabClick(event);

    if (!isSameTab) {
      return;
    }

    createEntryFromDagPage();
  };

  return (
    <ListItem divider sx={ROW_STYLE}>
      <SoftChip
        color={getRecoverySessionStateColor(recoverySessionState)}
        label={RECOVERY_SESSION_STATE_LABELS[recoverySessionState]}
      />
      <Box sx={NODE_IDS_STYLE}>
        {recoverySession.nodeIds.map((nodeId) => (
          <MuiLink
            key={nodeId}
            component={Link}
            href={getNodeRoute(dagName, nodeId)}
            onClick={handleOpen}
            variant="body2"
            sx={NODE_ID_STYLE}
          >
            {nodeId}
          </MuiLink>
        ))}
      </Box>
      <RelativeTime
        at={recoverySession.startedAt}
        template={LABELS.sessionStartedAt}
      />
      {recoverySession.endedAt !== null && (
        <RelativeTime
          at={recoverySession.endedAt}
          template={LABELS.sessionEndedAt}
        />
      )}
    </ListItem>
  );
};
