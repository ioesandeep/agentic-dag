import type { ProjectSummary } from './project';
import type { RepositoryImport } from './repositoryImport';

/**
 * Identifies who creates a repository checkout.
 */
export enum CheckoutKindEnum {
  MANAGED = 'managed',
  EXTERNAL = 'external',
}

/**
 * Identifies the availability of a repository checkout.
 */
export enum CheckoutStateEnum {
  PENDING = 'pending',
  READY = 'ready',
  MISSING = 'missing',
  INVALID = 'invalid',
}

/**
 * Identifies the catalog status displayed for a repository.
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
 * Identifies a repository at its provider.
 */
export interface RepositoryIdentity {
  providerRepositoryId: string;
  fullName: string;
  webUrl: string;
  defaultBranch: string | null;
}

/**
 * Specifies the branch a project uses for a repository.
 */
export interface ProjectMembership {
  project: ProjectSummary;
  branch: string;
}

/**
 * Describes a registered repository and its local checkout.
 */
export interface Repository extends RepositoryIdentity {
  id: string;
  host: string;
  checkoutKind: CheckoutKindEnum;
  checkoutPath: string;
  remoteName: string;
  branches: string[];
  checkoutState: CheckoutStateEnum;
  lastCheckedAt: string | null;
  validationMessage: string | null;
  version: number;
  createdAt: string;
  updatedAt: string;
  archivedAt: string | null;
  memberships: ProjectMembership[];
  latestImport: RepositoryImport | null;
  presentationStatus: RepositoryPresentationStatusEnum;
}
