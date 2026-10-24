'use client';

import LinearProgress from '@mui/material/LinearProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { SoftChip } from '@/components/softChip/softChip';
import type { Repository } from '@/entities/catalog/repository';
import { RepositoryPresentationStatusEnum } from '@/entities/catalog/repository';
import { ImportStatusEnum } from '@/entities/catalog/repositoryImport';
import { useRepositoryImportElapsedTime } from '@/hooks/useRepositoryImportElapsedTime';
import { LABELS, REPOSITORY_STATUS_LABELS } from '@/labels/en';
import { RepositoryStatusVariantEnum } from './types';

interface RepositoryStatusProps {
  repository: Repository;
  variant?: RepositoryStatusVariantEnum;
}

/**
 * Displays repository availability and clone progress.
 */
export const RepositoryStatus = ({
  repository,
  variant = RepositoryStatusVariantEnum.FULL,
}: RepositoryStatusProps) => {
  const isActive =
    repository.presentationStatus === RepositoryPresentationStatusEnum.QUEUED ||
    repository.presentationStatus === RepositoryPresentationStatusEnum.CLONING;

  const showsProgress = isActive && variant !== RepositoryStatusVariantEnum.STATUS;
  const elapsedTime = useRepositoryImportElapsedTime(
    showsProgress ? repository.latestImport : null,
  );

  const label = REPOSITORY_STATUS_LABELS[repository.presentationStatus];
  const isCancellationRequested =
    isActive &&
    repository.latestImport?.status === ImportStatusEnum.RUNNING &&
    repository.latestImport.cancelRequestedAt !== null;

  if (variant === RepositoryStatusVariantEnum.PROGRESS && !isActive) {
    return null;
  }

  return (
    <Stack spacing={1} sx={{ minWidth: 0 }}>
      {variant !== RepositoryStatusVariantEnum.PROGRESS && (
        <Stack spacing={1} direction="row" useFlexGap sx={{ flexWrap: 'wrap' }} role="status">
          <SoftChip label={label} color="var(--mui-palette-text-primary)" />
          {isCancellationRequested && (
            <Typography variant="body2">{LABELS.repositoryCancellationRequested}</Typography>
          )}
        </Stack>
      )}
      {showsProgress && <LinearProgress aria-label={label} />}
      {elapsedTime && (
        <Typography variant="caption" color="text.secondary" aria-live="off">
          {elapsedTime}
        </Typography>
      )}
    </Stack>
  );
};
