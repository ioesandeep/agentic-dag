/**
 * Groups a project's repositories by availability.
 */
export interface ProjectRepositoryCount {
  total: number;
  ready: number;
  importing: number;
  failed: number;
  unavailable: number;
}

/**
 * Identifies a project in repository memberships.
 */
export interface ProjectSummary {
  id: string;
  name: string;
  isDefault: boolean;
  archivedAt: string | null;
}

/**
 * Describes a project in the repository catalog.
 */
export interface Project extends ProjectSummary {
  description: string;
  version: number;
  createdAt: string;
  updatedAt: string;
  repositoryCounts: ProjectRepositoryCount;
}
