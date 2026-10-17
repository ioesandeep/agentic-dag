import type { CatalogErrorCodeEnum } from './catalogError';

/**
 * Defines the lifecycle states of a managed import attempt.
 */
export enum ImportStatusEnum {
  QUEUED = 'queued',
  RUNNING = 'running',
  SUCCEEDED = 'succeeded',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  INTERRUPTED = 'interrupted',
}

/**
 * Records a managed import attempt and its diagnostics.
 */
export interface RepositoryImport {
  id: string;
  repositoryId: string;
  requestId: string;
  status: ImportStatusEnum;
  cancelRequestedAt: string | null;
  errorCode: CatalogErrorCodeEnum | null;
  errorMessage: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}

/**
 * Describes a response containing a repository's import history.
 */
export interface RepositoryImportListResponse {
  imports: RepositoryImport[];
}
