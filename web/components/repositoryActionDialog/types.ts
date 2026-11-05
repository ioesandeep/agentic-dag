import type { Repository } from '@/entities/catalog/repository';
import type { RepositoryActionEnum } from '@/entities/catalog/repositoryAction';
import type { RepositoryInspection } from '@/entities/catalog/repositoryInspection';

/**
 * Identifies repository actions that require confirmation.
 */
export type RepositoryConfirmationAction =
  RepositoryActionEnum.CANCEL | RepositoryActionEnum.REPAIR;

interface RepositoryDialogControlProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

interface RepositoryRemovalDialogProps extends RepositoryDialogControlProps {
  variant?: RepositoryActionEnum.REMOVE;
  projectName: string;
  repositoryName: string;
}

interface RepositoryCatalogDialogProps extends RepositoryDialogControlProps {
  variant: RepositoryConfirmationAction;
  repository: Repository;
  inspections?: readonly RepositoryInspection[];
}

/**
 * Specifies a repository action confirmation.
 */
export type RepositoryActionDialogProps =
  RepositoryRemovalDialogProps | RepositoryCatalogDialogProps;
