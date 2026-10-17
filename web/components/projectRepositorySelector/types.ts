import type { ProjectSelectionCatalog } from '@/hooks/catalog/types';

/**
 * Defines controlled catalog selection and repository management actions.
 */
export interface ProjectRepositorySelectorProps extends ProjectSelectionCatalog {
  projectId: string | null;
  repositoryId: string | null;
  hasFailed: boolean;
  onProjectSelect: (projectId: string) => void;
  onRepositorySelect: (repositoryId: string) => void;
  onAddRepository: () => void;
  onRetry: () => void;
}
