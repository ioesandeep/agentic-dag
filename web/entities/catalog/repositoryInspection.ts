import type { Repository, RepositoryIdentity } from './repository';

/**
 * Describes a remote choice without exposing credentials in its URL.
 */
export interface RepositoryRemoteChoice {
  name: string;
  url: string;
  supported: boolean;
}

/**
 * Provides a local checkout preview before registration or repair.
 */
export interface RepositoryInspection {
  canonicalPath: string;
  remotes: RepositoryRemoteChoice[];
  selectedRemoteName: string | null;
  dirty: boolean;
  identity: RepositoryIdentity | null;
  existingRepository: Repository | null;
}
