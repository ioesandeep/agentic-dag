import type { Repository } from './repository';
import type { RepositoryImport } from './repositoryImport';

/**
 * Distinguishes a new local registration from an existing registration.
 */
export enum RepositoryRegistrationOutcomeEnum {
  CREATED = 'created',
  EXISTING = 'existing',
}

/**
 * Distinguishes an accepted import from an existing registration.
 */
export enum RepositoryImportOutcomeEnum {
  ACCEPTED = 'accepted',
  EXISTING = 'existing',
}

/**
 * Provides the repository returned by local checkout registration.
 */
export interface RepositoryRegistrationResult {
  outcome: RepositoryRegistrationOutcomeEnum;
  repository: Repository;
}

interface AcceptedRepositoryImportResult {
  outcome: RepositoryImportOutcomeEnum.ACCEPTED;
  repository: Repository;
  import: RepositoryImport;
}

interface ExistingRepositoryImportResult {
  outcome: RepositoryImportOutcomeEnum.EXISTING;
  repository: Repository;
}

/**
 * Provides the accepted import or existing registration returned by import submission.
 */
export type RepositoryImportResult =
  AcceptedRepositoryImportResult | ExistingRepositoryImportResult;
