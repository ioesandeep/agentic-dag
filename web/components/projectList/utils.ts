import type {
  Project,
  ProjectRepositoryCount,
} from '@/entities/catalog/project';
import type { Repository } from '@/entities/catalog/repository';
import { LABELS, LOCALE } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

const PROJECT_NAME_COLLATOR = new Intl.Collator(LOCALE);
const REPOSITORY_COUNT_FORMATTER = new Intl.NumberFormat(LOCALE);
const SINGLE_REPOSITORY_COUNT = 1;

/**
 * Orders projects with Default first and the remaining projects by name.
 */
export const compareProjects = (
  firstProject: Project,
  secondProject: Project,
) => {
  const defaultOrder =
    Number(secondProject.isDefault) - Number(firstProject.isDefault);

  if (defaultOrder !== 0) {
    return defaultOrder;
  }

  return PROJECT_NAME_COLLATOR.compare(firstProject.name, secondProject.name);
};

/**
 * Returns the catalog status of a project.
 */
export const getProjectStatusLabel = (project: Project): string => {
  if (project.archivedAt !== null) {
    return LABELS.projectArchived;
  }

  return LABELS.projectActive;
};

/**
 * Formats the total repository count for a project.
 */
export const getProjectRepositoryCountLabel = (
  repositoryCounts: ProjectRepositoryCount,
): string => {
  const countLabel =
    repositoryCounts.total === SINGLE_REPOSITORY_COUNT
      ? LABELS.projectRepositoryCountSingular
      : LABELS.projectRepositoryCountPlural;

  const countValues = {
    count: REPOSITORY_COUNT_FORMATTER.format(repositoryCounts.total),
  };

  return formatLabel(countLabel, countValues);
};

/**
 * Returns the repositories assigned to a project.
 */
export const getProjectRepositories = (
  project: Project,
  repositories: Repository[],
): Repository[] => {
  return repositories.filter((repository) => {
    const hasMembership = repository.memberships.some(
      (membership) => membership.project.id === project.id,
    );

    return hasMembership;
  });
};
