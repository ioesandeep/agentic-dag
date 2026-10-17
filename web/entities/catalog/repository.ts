import type { ProjectSummary } from './project';
import type { RepositoryImport } from './repositoryImport';

/**
 * Identifies the supported repository provider.
 */
export enum RepositoryProviderEnum {
  GITHUB = 'github',
}

/**
 * Distinguishes managed clones from external checkouts.
 */
export enum CheckoutKindEnum {
  MANAGED = 'managed',
  EXTERNAL = 'external',
}

/**
 * Reports the last observed checkout condition.
 */
export enum CheckoutStateEnum {
  PENDING = 'pending',
  READY = 'ready',
  MISSING = 'missing',
  INVALID = 'invalid',
}

/**
 * Represents repository availability and import progress.
 */
export enum RepositoryPresentationStatusEnum {
  QUEUED = 'queued',
  CLONING = 'cloning',
  READY = 'ready',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  INTERRUPTED = 'interrupted',
  MISSING = 'missing',
  INVALID = 'invalid',
  PENDING = 'pending',
  ARCHIVED = 'archived',
}

/**
 * Records a repository's GitHub identity and metadata.
 */
export interface RepositoryIdentity {
  providerRepositoryId: string;
  fullName: string;
  webUrl: string;
  defaultBranch: string | null;
}

/**
 * Provides a registered checkout's availability and project associations.
 */
export interface Repository extends RepositoryIdentity {
  id: string;
  provider: RepositoryProviderEnum;
  host: string;
  checkoutKind: CheckoutKindEnum;
  checkoutPath: string;
  remoteName: string;
  checkoutState: CheckoutStateEnum;
  lastCheckedAt: string | null;
  validationMessage: string | null;
  version: number;
  createdAt: string;
  updatedAt: string;
  archivedAt: string | null;
  projects: ProjectSummary[];
  latestImport: RepositoryImport | null;
  presentationStatus: RepositoryPresentationStatusEnum;
}

/**
 * Describes a response containing registered repositories.
 */
export interface RepositoryListResponse {
  repositories: Repository[];
}
