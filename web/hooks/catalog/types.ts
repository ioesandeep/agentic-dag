import type { ProjectSummary } from '@/entities/catalog/project';
import type { Repository } from '@/entities/catalog/repository';

/**
 * Provides repository identity and readiness for selection.
 */
export type ProjectSelectionRepository = Pick<Repository, 'id' | 'fullName' | 'projects' | 'presentationStatus'>;

/**
 * Supplies catalog records for project and repository selection.
 */
export interface ProjectSelectionCatalog {
  projects: ProjectSummary[] | null;
  repositories: ProjectSelectionRepository[] | null;
}

/**
 * Exposes selected catalog IDs and selection actions.
 */
export interface ProjectSelection {
  projectId: string | null;
  repositoryId: string | null;
  setProjectId: (projectId: string) => void;
  setRepositoryId: (repositoryId: string) => void;
}
