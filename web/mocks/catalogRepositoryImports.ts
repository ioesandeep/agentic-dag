/**
 * Provides fixed repository clone attempts for the catalog.
 */
import { ImportStatusEnum } from '@/entities/catalog/repositoryImport';
import type { RepositoryImport } from '@/entities/catalog/repositoryImport';

const CREATED_AT = '2026-10-01T09:00:00Z';
const UPDATED_AT = '2026-10-15T12:00:00Z';

/**
 * Provides an import fixture for a clone attempt that fails before a retry.
 */
export const FAILED_SERVICE_IMPORT: RepositoryImport = {
  id: 'import-service-1',
  repositoryId: 'repository-service',
  requestId: 'request-service-1',
  status: ImportStatusEnum.FAILED,
  cancelRequestedAt: null,
  errorMessage: 'The connection to GitHub timed out.',
  createdAt: CREATED_AT,
  startedAt: CREATED_AT,
  finishedAt: '2026-10-01T09:02:00Z',
};
/**
 * Provides an import fixture for a successful clone retry.
 */
export const SUCCEEDED_SERVICE_IMPORT: RepositoryImport = {
  id: 'import-service-2',
  repositoryId: FAILED_SERVICE_IMPORT.repositoryId,
  requestId: 'request-service-2',
  status: ImportStatusEnum.SUCCEEDED,
  cancelRequestedAt: null,
  errorMessage: null,
  createdAt: '2026-10-01T09:05:00Z',
  startedAt: '2026-10-01T09:05:00Z',
  finishedAt: '2026-10-01T09:06:00Z',
};
/**
 * Provides an import fixture for a clone attempt in progress.
 */
export const RUNNING_WORKER_IMPORT: RepositoryImport = {
  id: 'import-worker-1',
  repositoryId: 'repository-worker',
  requestId: 'request-worker-1',
  status: ImportStatusEnum.RUNNING,
  cancelRequestedAt: null,
  errorMessage: null,
  createdAt: UPDATED_AT,
  startedAt: UPDATED_AT,
  finishedAt: null,
};
/**
 * Provides an import fixture for a clone attempt that fails because GitHub denies access.
 */
export const FAILED_CONNECTOR_IMPORT: RepositoryImport = {
  id: 'import-connector-1',
  repositoryId: 'repository-connector',
  requestId: 'request-connector-1',
  status: ImportStatusEnum.FAILED,
  cancelRequestedAt: null,
  errorMessage: 'GitHub denied access to virgo/connector.',
  createdAt: '2026-10-15T11:00:00Z',
  startedAt: '2026-10-15T11:00:00Z',
  finishedAt: '2026-10-15T11:01:00Z',
};
/**
 * Provides a successful clone fixture for repository import history.
 */
export const SUCCEEDED_LEGACY_IMPORT: RepositoryImport = {
  id: 'import-legacy-1',
  repositoryId: 'repository-legacy',
  requestId: 'request-legacy-1',
  status: ImportStatusEnum.SUCCEEDED,
  cancelRequestedAt: null,
  errorMessage: null,
  createdAt: CREATED_AT,
  startedAt: CREATED_AT,
  finishedAt: '2026-10-01T09:01:00Z',
};

/**
 * Provides import history fixtures for repository clone attempts.
 */
export const MOCK_REPOSITORY_IMPORTS: RepositoryImport[] = [
  FAILED_SERVICE_IMPORT,
  SUCCEEDED_SERVICE_IMPORT,
  RUNNING_WORKER_IMPORT,
  FAILED_CONNECTOR_IMPORT,
  SUCCEEDED_LEGACY_IMPORT,
];
