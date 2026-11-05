import { RepositoryActionEnum } from '@/entities/catalog/repositoryAction';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';
import type { RepositoryActionDialogProps } from './types';

/**
 * Returns the confirmation text for a repository action.
 */
export const getRepositoryActionContent = (
  repositoryActionDialogProps: RepositoryActionDialogProps,
) => {
  if ('repositoryName' in repositoryActionDialogProps) {
    const titleValues = {
      project: repositoryActionDialogProps.projectName,
      repository: repositoryActionDialogProps.repositoryName,
    };

    return {
      title: formatLabel(LABELS.repositoryRemoveFromProjectTitle, titleValues),
      description: LABELS.repositoryRemoveFromProjectDescription,
      confirm: LABELS.repositoryRemoveFromProject,
    };
  }

  const titleValues = {
    repository: repositoryActionDialogProps.repository.fullName,
  };

  const content = {
    [RepositoryActionEnum.CANCEL]: {
      title: LABELS.repositoryCancelTitle,
      description: LABELS.repositoryCancelDescription,
      confirm: LABELS.repositoryCancelClone,
    },
    [RepositoryActionEnum.REPAIR]: {
      title: LABELS.repositoryRepairTitle,
      description: LABELS.localCheckoutHint,
      confirm: LABELS.localCheckoutRepair,
    },
  }[repositoryActionDialogProps.variant];

  return { ...content, title: formatLabel(content.title, titleValues) };
};
