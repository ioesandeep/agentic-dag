/**
 * Identifies the state of a repository clone attempt.
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
 * Describes a repository clone attempt.
 */
export interface RepositoryImport {
  id: string;
  repositoryId: string;
  requestId: string;
  status: ImportStatusEnum;
  cancelRequestedAt: string | null;
  errorMessage: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}
