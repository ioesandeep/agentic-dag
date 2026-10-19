import type { Repository, RepositoryIdentity } from './repository';

/**
 * Describes a remote available for local repository registration.
 */
export interface RepositoryRemoteChoice {
  name: string;
  url: string;
  supported: boolean;
}

/**
 * Describes a local clone before repository registration.
 */
export interface RepositoryInspection {
  canonicalPath: string;
  remotes: RepositoryRemoteChoice[];
  selectedRemoteName: string | null;
  dirty: boolean;
  identity: RepositoryIdentity | null;
  branches: string[];
  existingRepository: Repository | null;
}
