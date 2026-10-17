import type { CatalogVersionRequest } from './catalogVersionRequest';

/**
 * Identifies a local checkout for inspection.
 */
export interface InspectLocalRepositoryRequest {
  path: string;
  remoteName?: string;
}

/**
 * Defines a local checkout registration with an optional project association.
 */
export interface RegisterLocalRepositoryRequest extends InspectLocalRepositoryRequest {
  projectId?: string;
}

/**
 * Defines an idempotent managed import with an optional project association.
 */
export interface ImportRepositoryRequest {
  reference: string;
  requestId: string;
  projectId?: string;
}

/**
 * Identifies an idempotent request to retry a managed import.
 */
export interface RetryRepositoryImportRequest {
  requestId: string;
}

/**
 * Defines a versioned path replacement for an external checkout.
 */
export interface RelinkRepositoryRequest extends CatalogVersionRequest {
  path: string;
  remoteName: string;
}
