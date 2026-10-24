import type { SvgIconComponent } from '@mui/icons-material';

import type { ProjectSummary } from '@/entities/catalog/project';
import type { Repository } from '@/entities/catalog/repository';

/**
 * Specifies the repository membership display.
 */
export enum RepositoryListVariantEnum {
  PROJECT = 'project',
  GLOBAL = 'global',
}

interface RepositoryListBaseProps {
  repositories: Repository[];
  onOpenDetails: (repository: Repository) => void;
  onRetryClone: (repository: Repository) => void;
}

interface ProjectRepositoryListProps extends RepositoryListBaseProps {
  variant: RepositoryListVariantEnum.PROJECT;
  project: ProjectSummary;
  onChangeBranch: (repository: Repository) => void;
  onRemoveFromProject: (repository: Repository) => void;
}

interface GlobalRepositoryListProps extends RepositoryListBaseProps {
  variant: RepositoryListVariantEnum.GLOBAL;
}

/**
 * Specifies the repositories and available list actions.
 */
export type RepositoryListProps = ProjectRepositoryListProps | GlobalRepositoryListProps;

/**
 * Specifies a repository and its list context.
 */
export type RepositoryRowProps = (
  Omit<ProjectRepositoryListProps, 'repositories'> | Omit<GlobalRepositoryListProps, 'repositories'>
) & { repository: Repository };

/**
 * Specifies an available repository action.
 */
export interface RepositoryAction {
  label: string;
  ariaLabel?: string;
  icon: SvgIconComponent;
  onClick: () => void;
}

/**
 * Identifies the project branch displayed for a repository.
 */
export interface RepositoryBranchLabel {
  projectId: string;
  label: string;
  color: string;
}
