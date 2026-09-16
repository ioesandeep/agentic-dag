import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';

import { LABELS } from '@/labels/en';

interface PullRequestLinkProps {
  // The pull request url, empty when the node has none.
  url: string;
}

/**
 * Renders a link to the node's pull request, or a message when it has none.
 */
export const PullRequestLink = ({ url }: PullRequestLinkProps) => {
  if (url === '') {
    return (
      <Typography variant="body2" color="text.secondary">
        {LABELS.nodeNoPullRequest}
      </Typography>
    );
  }

  return (
    <Button
      size="small"
      variant="outlined"
      href={url}
      target="_blank"
      rel="noreferrer"
      startIcon={<OpenInNewIcon fontSize="small" />}
    >
      {LABELS.nodePullRequestLink}
    </Button>
  );
};
