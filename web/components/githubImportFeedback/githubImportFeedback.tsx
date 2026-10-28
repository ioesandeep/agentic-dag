'use client';

import Alert from '@mui/material/Alert';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import type { GithubAccountStatus } from '@/entities/catalog/githubAccountStatus';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

const COMMAND_STYLE = { display: 'block', overflowWrap: 'anywhere' };

interface GithubImportFeedbackProps {
  accountStatus: GithubAccountStatus;
}

/**
 * Displays the GitHub account and host authentication instructions.
 */
export const GithubImportFeedback = ({ accountStatus }: GithubImportFeedbackProps) => {
  const accountValues = { login: accountStatus.login ?? '', host: accountStatus.host };
  const signedInLabel = formatLabel(LABELS.githubAccountSignedIn, accountValues);
  const accountLabel = accountStatus.authenticated ? signedInLabel : LABELS.githubAccountSignedOut;
  const severity = accountStatus.authenticated ? 'info' : 'warning';

  return (
    <Alert severity={severity}>
      <Stack spacing={1}>
        <Typography variant="body2">{accountLabel}</Typography>
        {!accountStatus.authenticated && (
          <>
            <Typography variant="body2">{LABELS.githubLoginInstruction}</Typography>
            <Typography component="code" variant="body2" sx={COMMAND_STYLE}>
              {LABELS.githubLoginCommand}
            </Typography>
          </>
        )}
        <Typography variant="body2">{LABELS.githubSwitchInstruction}</Typography>
        <Typography component="code" variant="body2" sx={COMMAND_STYLE}>
          {LABELS.githubSwitchCommand}
        </Typography>
      </Stack>
    </Alert>
  );
};
