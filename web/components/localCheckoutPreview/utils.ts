import type { Repository } from '@/entities/catalog/repository';
import type { RepositoryInspection } from '@/entities/catalog/repositoryInspection';

/**
 * Checks whether an inspection identifies a different repository for repair.
 */
export const isRepositoryMismatch = (inspection: RepositoryInspection | null, repository?: Repository): boolean =>
  repository !== undefined && inspection?.identity != null &&
  inspection.identity.providerRepositoryId !== repository.providerRepositoryId;
