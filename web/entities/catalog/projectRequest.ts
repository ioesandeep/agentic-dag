import type { CatalogVersionRequest } from './catalogVersionRequest';

/**
 * Defines the metadata for creating a project.
 */
export interface CreateProjectRequest {
  name: string;
  description?: string;
}

/**
 * Defines a versioned replacement of project metadata.
 */
export interface UpdateProjectRequest extends CatalogVersionRequest {
  name: string;
  description: string;
}
