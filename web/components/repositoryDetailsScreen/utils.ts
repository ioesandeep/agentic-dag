import type { Repository } from '@/entities/catalog/repository';
import type { RepositoryInspection } from '@/entities/catalog/repositoryInspection';
import { MOCK_REPOSITORY_INSPECTION } from '@/mocks/catalogMocks';

/**
 * Provides a matching mock inspection for repository repair.
 */
export const getMockRepairInspections = (
  repository: Repository,
): RepositoryInspection[] => [
  {
    ...MOCK_REPOSITORY_INSPECTION,
    canonicalPath: repository.checkoutPath,
    identity: repository,
    branches: repository.branches,
    existingRepository: null,
    selectedRemoteName: repository.remoteName,
    remotes: [
      { name: repository.remoteName, url: repository.webUrl, supported: true },
    ],
  },
];
