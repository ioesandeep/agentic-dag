/**
 * Reports repository availability totals for a project.
 */
export interface ProjectRepositoryCount {
  total: number;
  ready: number;
  importing: number;
  failed: number;
  unavailable: number;
}

/**
 * Identifies a project associated with a repository.
 */
export interface ProjectSummary {
  id: string;
  name: string;
  isDefault: boolean;
  archivedAt: string | null;
}

/**
 * Provides project metadata and repository availability.
 */
export interface Project extends ProjectSummary {
  description: string;
  version: number;
  createdAt: string;
  updatedAt: string;
  repositoryCounts: ProjectRepositoryCount;
}

/**
 * Describes a response containing catalog projects.
 */
export interface ProjectListResponse {
  projects: Project[];
}
