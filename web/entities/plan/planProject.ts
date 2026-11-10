/**
 * Specifies the repository branches available to a plan.
 */
export interface PlanRepository {
  id: string;
  fullName: string;
  branch: string;
  branches: string[];
}

/**
 * Describes a project available for plan creation.
 */
export interface PlanProject {
  id: string;
  name: string;
  repositories: PlanRepository[];
}
