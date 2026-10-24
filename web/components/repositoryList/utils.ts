import AccountTreeOutlinedIcon from '@mui/icons-material/AccountTreeOutlined';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import LinkOffOutlinedIcon from '@mui/icons-material/LinkOffOutlined';
import RefreshOutlinedIcon from '@mui/icons-material/RefreshOutlined';

import type { ProjectSummary } from '@/entities/catalog/project';
import { CheckoutKindEnum } from '@/entities/catalog/repository';
import type { Repository } from '@/entities/catalog/repository';
import { ImportStatusEnum } from '@/entities/catalog/repositoryImport';
import { LABELS, LOCALE } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';
import { RepositoryListVariantEnum } from './types';
import type { RepositoryAction, RepositoryBranchLabel, RepositoryRowProps } from './types';

const RETRYABLE_IMPORT_STATUSES = [
  ImportStatusEnum.FAILED,
  ImportStatusEnum.CANCELLED,
  ImportStatusEnum.INTERRUPTED,
];

const DEFAULT_PROJECT_COLOR = 'primary.main';
const PROJECT_COLORS = [
  DEFAULT_PROJECT_COLOR,
  'info.main',
  'success.main',
  'warning.main',
  'error.main',
  'secondary.main',
];

const CLONED_DATE_CONFIG: Intl.DateTimeFormatOptions = { dateStyle: 'medium', timeZone: 'UTC' };
const CLONED_DATE_FORMAT = new Intl.DateTimeFormat(LOCALE, CLONED_DATE_CONFIG);

const getProjectColor = (project: ProjectSummary): string => {
  const projectIdCharacters = Array.from(project.id);
  const colorIndex = projectIdCharacters.reduce((index, character) => {
    const characterCode = character.charCodeAt(0);

    return (index + characterCode) % PROJECT_COLORS.length;
  }, 0);

  return PROJECT_COLORS[colorIndex] ?? DEFAULT_PROJECT_COLOR;
};

/**
 * Returns the recorded clone date for a repository.
 */
export const getRepositoryClonedDateLabel = (repository: Repository): string | null => {
  const latestImport = repository.latestImport;
  if (latestImport?.status !== ImportStatusEnum.SUCCEEDED || latestImport.finishedAt === null) {
    return null;
  }

  const finishedAt = new Date(latestImport.finishedAt);
  const date = CLONED_DATE_FORMAT.format(finishedAt);
  const dateValues = { date };

  return formatLabel(LABELS.repositoryClonedDate, dateValues);
};

/**
 * Returns the default branch label for a repository.
 */
export const getRepositoryDefaultBranchLabel = (repository: Repository): string => {
  if (repository.defaultBranch === null) {
    return LABELS.repositoryDefaultBranchUnknown;
  }

  const branchValues = { branch: repository.defaultBranch };

  return formatLabel(LABELS.repositoryDefaultBranch, branchValues);
};

/**
 * Returns the checkout kind label for a repository.
 */
export const getRepositoryKindLabel = (repository: Repository): string | null => {
  if (repository.checkoutKind === CheckoutKindEnum.MANAGED) {
    return null;
  }

  return LABELS.repositoryExternal;
};

const getRetryCloneActions = (repositoryRowProps: RepositoryRowProps): RepositoryAction[] => {
  const { repository, onRetryClone } = repositoryRowProps;
  const latestImportStatus = repository.latestImport?.status;
  const canRetry =
    repository.checkoutKind === CheckoutKindEnum.MANAGED &&
    latestImportStatus !== undefined &&
    RETRYABLE_IMPORT_STATUSES.includes(latestImportStatus);

  if (!canRetry) {
    return [];
  }

  return [
    {
      label: LABELS.repositoryRetryClone,
      icon: RefreshOutlinedIcon,
      onClick: () => onRetryClone(repository),
    },
  ];
};

const getProjectActions = (repositoryRowProps: RepositoryRowProps): RepositoryAction[] => {
  if (
    repositoryRowProps.variant !== RepositoryListVariantEnum.PROJECT ||
    repositoryRowProps.project.archivedAt !== null
  ) {
    return [];
  }

  const { repository, onChangeBranch, onRemoveFromProject } = repositoryRowProps;

  return [
    {
      label: LABELS.repositoryChangeBranch,
      icon: AccountTreeOutlinedIcon,
      onClick: () => onChangeBranch(repository),
    },
    {
      label: LABELS.repositoryRemoveFromProject,
      icon: LinkOffOutlinedIcon,
      onClick: () => onRemoveFromProject(repository),
    },
  ];
};

/**
 * Returns the actions available for a repository.
 */
export const getRepositoryActions = (
  repositoryRowProps: RepositoryRowProps,
): RepositoryAction[] => {
  const { repository, onOpenDetails } = repositoryRowProps;
  const retryCloneActions = getRetryCloneActions(repositoryRowProps);
  const projectActions = getProjectActions(repositoryRowProps);

  const repositoryValues = { repository: repository.fullName };
  const ariaLabel = formatLabel(LABELS.repositoryDetailsOpen, repositoryValues);

  return [
    {
      label: LABELS.repositoryDetails,
      ariaLabel,
      icon: InfoOutlinedIcon,
      onClick: () => onOpenDetails(repository),
    },
    ...retryCloneActions,
    ...projectActions,
  ];
};

/**
 * Returns the project branches displayed for a repository.
 */
export const getRepositoryBranchLabels = (
  repositoryRowProps: RepositoryRowProps,
): RepositoryBranchLabel[] => {
  const memberships = repositoryRowProps.repository.memberships.filter(
    ({ project }) =>
      repositoryRowProps.variant === RepositoryListVariantEnum.GLOBAL ||
      project.id === repositoryRowProps.project.id,
  );

  return memberships.map(({ project, branch }) => {
    const membershipValues = { project: project.name, branch };
    const label = formatLabel(LABELS.repositoryProjectBranch, membershipValues);

    const color = getProjectColor(project);

    return { projectId: project.id, label, color };
  });
};
