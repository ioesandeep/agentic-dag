import Alert from '@mui/material/Alert';

import { LABELS } from '@/labels/en';

const ALERT_STYLE = { flexShrink: 0 };

interface RequestFailureAlertProps {
  // True where the last request to the api failed.
  hasFailed: boolean;
}

/**
 * Renders a warning that the data on screen is older than the api.
 */
export const RequestFailureAlert = ({
  hasFailed,
}: RequestFailureAlertProps) => {
  if (!hasFailed) {
    return null;
  }

  return (
    <Alert severity="warning" sx={ALERT_STYLE}>
      {LABELS.apiRequestFailed}
    </Alert>
  );
};
