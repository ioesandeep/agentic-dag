import type { ApiErrorResponse } from '@/entities/apiErrorResponse';
import type { Project } from './project';
import type { Repository } from './repository';

/**
 * Identifies catalog request failures and import diagnostics.
 */
export enum CatalogErrorCodeEnum {
  INVALID_INPUT = 'invalid_input',
  UNSUPPORTED_REMOTE = 'unsupported_remote',
  REMOTE_REQUIRED = 'remote_required',
  IDENTITY_MISMATCH = 'identity_mismatch',
  PROJECT_NOT_FOUND = 'project_not_found',
  REPOSITORY_NOT_FOUND = 'repository_not_found',
  IMPORT_NOT_FOUND = 'import_not_found',
  DUPLICATE_PROJECT_NAME = 'duplicate_project_name',
  PROTECTED_PROJECT = 'protected_project',
  PROJECT_ARCHIVED = 'project_archived',
  REPOSITORY_ARCHIVED = 'repository_archived',
  REPOSITORY_IN_USE = 'repository_in_use',
  PATH_CONFLICT = 'path_conflict',
  MANAGED_PATH_IMMUTABLE = 'managed_path_immutable',
  CATALOG_PATH_CONFLICT = 'catalog_path_conflict',
  VERSION_CONFLICT = 'version_conflict',
  IMPORT_ACTIVE = 'import_active',
  INVALID_IMPORT_STATE = 'invalid_import_state',
  GITHUB_CLI_MISSING = 'github_cli_missing',
  GITHUB_AUTH_REQUIRED = 'github_auth_required',
  GITHUB_NOT_FOUND = 'github_not_found',
  GITHUB_UNAVAILABLE = 'github_unavailable',
  CHECKOUT_MISSING = 'checkout_missing',
  CHECKOUT_INVALID = 'checkout_invalid',
  IMPORT_FAILED = 'import_failed',
  IMPORT_TIMEOUT = 'import_timeout',
  IMPORT_CANCELLED = 'import_cancelled',
  IMPORT_INTERRUPTED = 'import_interrupted',
}

interface CatalogErrorContext extends ApiErrorResponse {
  field?: string;
  existingProjectId?: string;
  existingRepositoryId?: string;
  projectIds?: string[];
  importId?: string;
}

interface CatalogRequestErrorResponse extends CatalogErrorContext {
  code: Exclude<CatalogErrorCodeEnum, CatalogErrorCodeEnum.VERSION_CONFLICT>;
}

interface CatalogVersionConflictResponse extends CatalogErrorContext {
  code: CatalogErrorCodeEnum.VERSION_CONFLICT;
  current: Project | Repository;
}

/**
 * Provides catalog failure details and conflict context.
 */
export type CatalogErrorResponse =
  CatalogRequestErrorResponse | CatalogVersionConflictResponse;
