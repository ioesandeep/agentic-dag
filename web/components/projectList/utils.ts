import type { Project, ProjectRepositoryCount } from '@/entities/catalog/project';
import { LABELS, LOCALE } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

const NAME_COLLATOR_CONFIG: Intl.CollatorOptions = { sensitivity: 'base' };
const NAME_COLLATOR = new Intl.Collator(LOCALE, NAME_COLLATOR_CONFIG);
const COUNT_FORMATTER = new Intl.NumberFormat(LOCALE);

const compareProjects = (leftProject: Project, rightProject: Project) => {
  if (leftProject.isDefault !== rightProject.isDefault) {
    return leftProject.isDefault ? -1 : 1;
  }
  return NAME_COLLATOR.compare(leftProject.name, rightProject.name);
};

/**
 * Orders the visible projects with Default first.
 */
export const getVisibleProjects = (projects: Project[] | null, showArchived: boolean) => {
  if (projects === null) {
    return null;
  }
  const visibleProjects = projects.filter((project) => showArchived || project.archivedAt === null);
  return visibleProjects.sort(compareProjects);
};

/**
 * Describes a project's archive or Default status.
 */
export const getProjectStatus = (project: Project) => {
  if (project.isDefault) {
    return LABELS.projectDefault;
  }
  return project.archivedAt === null ? LABELS.projectActive : LABELS.projectArchived;
};

/**
 * Formats repository counts by readiness.
 */
export const getRepositoryCountLabel = (projectRepositoryCount: ProjectRepositoryCount) => {
  const countValues = {
    total: COUNT_FORMATTER.format(projectRepositoryCount.total),
    ready: COUNT_FORMATTER.format(projectRepositoryCount.ready),
    importing: COUNT_FORMATTER.format(projectRepositoryCount.importing),
    failed: COUNT_FORMATTER.format(projectRepositoryCount.failed),
    unavailable: COUNT_FORMATTER.format(projectRepositoryCount.unavailable),
  };
  return formatLabel(LABELS.projectRepositoryCounts, countValues);
};
