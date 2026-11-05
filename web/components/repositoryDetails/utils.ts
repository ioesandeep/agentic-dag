import {
  CheckoutKindEnum,
  CheckoutStateEnum,
} from '@/entities/catalog/repository';
import type { Repository } from '@/entities/catalog/repository';
import { ImportStatusEnum } from '@/entities/catalog/repositoryImport';
import { LABELS } from '@/labels/en';
import { formatCatalogTime } from '@/utils/formatCatalogTime';
import { RepositoryActionEnum } from '@/entities/catalog/repositoryAction';

const RETRY_STATUSES = [
  ImportStatusEnum.FAILED,
  ImportStatusEnum.CANCELLED,
  ImportStatusEnum.INTERRUPTED,
];

const ACTIVE_STATUSES = [ImportStatusEnum.QUEUED, ImportStatusEnum.RUNNING];

/**
 * Returns the actions available for a repository checkout.
 */
export const getRepositoryDetailsActions = (
  repository: Repository,
): RepositoryActionEnum[] => {
  const importStatus = repository.latestImport?.status;
  const isActive =
    importStatus !== undefined && ACTIVE_STATUSES.includes(importStatus);

  if (isActive) {
    return repository.latestImport?.cancelRequestedAt === null
      ? [RepositoryActionEnum.CANCEL]
      : [];
  }

  const needsRepair =
    repository.checkoutKind === CheckoutKindEnum.EXTERNAL &&
    (repository.checkoutState === CheckoutStateEnum.MISSING ||
      repository.checkoutState === CheckoutStateEnum.INVALID);

  const canRetry =
    repository.checkoutKind === CheckoutKindEnum.MANAGED &&
    importStatus !== undefined &&
    RETRY_STATUSES.includes(importStatus);

  return [
    RepositoryActionEnum.CHECK,
    ...(needsRepair ? [RepositoryActionEnum.REPAIR] : []),
    ...(canRetry ? [RepositoryActionEnum.RETRY] : []),
  ];
};

/**
 * Returns repository metadata for the details page.
 */
export const getRepositoryDetailsFields = (repository: Repository) => {
  const clonedAt =
    repository.latestImport?.status === ImportStatusEnum.SUCCEEDED
      ? repository.latestImport.finishedAt
      : null;

  return [
    {
      label: LABELS.repositoryName,
      value: repository.fullName,
      href: repository.webUrl,
    },
    { label: LABELS.repositoryRemote, value: repository.remoteName },
    {
      label: LABELS.repositoryGithubDefaultBranch,
      value: repository.defaultBranch ?? LABELS.repositoryEmpty,
    },
    { label: LABELS.repositoryFolder, value: repository.checkoutPath },
    { label: LABELS.repositoryCloneDate, value: formatCatalogTime(clonedAt) },
  ];
};
