import type { ProjectSummary } from '@/entities/catalog/project';
import { RepositoryPresentationStatusEnum } from '@/entities/catalog/repository';

import type { ProjectSelectionRepository } from './types';

/**
 * Returns active projects eligible for selection.
 */
export const getActiveProjects = (projects: ProjectSummary[] | null) =>
  projects?.filter((project) => project.archivedAt === null) ?? [];

/**
 * Returns ready repositories associated with the selected project.
 */
export const getReadyRepositories = (repositories: ProjectSelectionRepository[] | null, projectId: string | null) =>
  repositories?.filter((repository) => {
    const isAssociated = repository.projects.some((project) => project.id === projectId);
    return isAssociated && repository.presentationStatus === RepositoryPresentationStatusEnum.READY;
  }) ?? [];
