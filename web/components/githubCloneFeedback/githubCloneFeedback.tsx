import LinearProgress from '@mui/material/LinearProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { GithubCloneStageEnum } from '@/components/githubCloneDialog/types';
import { RepositoryStatus } from '@/components/repositoryStatus/repositoryStatus';
import type { Repository } from '@/entities/catalog/repository';
import { LABELS } from '@/labels/en';

const PROGRESS_STYLE = { '@media (prefers-reduced-motion: reduce)': { '& .MuiLinearProgress-bar': { animation: 'none' } } };
const STATUS_STYLE = { flex: 1, minWidth: 0, width: '100%' };
const COMPLETE_PERCENT = 100;

interface GithubCloneFeedbackProps {
  stage: GithubCloneStageEnum;
  registeredRepository: Repository | undefined;
}

/**
 * Displays repository clone status in the dialog footer.
 */
export const GithubCloneFeedback = ({ stage, registeredRepository }: GithubCloneFeedbackProps) => {
  const isCloning = stage === GithubCloneStageEnum.CLONING;
  const hasCloneStatus = stage !== GithubCloneStageEnum.INPUT;
  const label = isCloning ? LABELS.githubCloneProgress : LABELS.githubCloneComplete;
  const progressVariant = isCloning ? 'indeterminate' : 'determinate';

  return (
    <Stack spacing={1} sx={STATUS_STYLE}>
      {registeredRepository !== undefined && <RepositoryStatus repository={registeredRepository} />}
      {hasCloneStatus && (
        <Stack spacing={1} role="status">
          <Typography variant="body2">{label}</Typography>
          <LinearProgress variant={progressVariant} value={COMPLETE_PERCENT} aria-label={label} sx={PROGRESS_STYLE} />
          {isCloning && <Typography variant="caption" color="text.secondary">{LABELS.githubCloneCloseHint}</Typography>}
        </Stack>
      )}
    </Stack>
  );
};
