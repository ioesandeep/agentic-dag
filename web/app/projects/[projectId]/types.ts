/**
 * Specifies the project route parameter.
 */
export interface ProjectRouteParameter {
  projectId: string;
}

/**
 * Specifies the project page parameters.
 */
export interface ProjectPageProps {
  params: Promise<ProjectRouteParameter>;
}
