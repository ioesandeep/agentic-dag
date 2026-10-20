import { expect, test } from 'vitest';
import type { Repository } from '@/entities/catalog/repository';
import { RepositoryPresentationStatusEnum } from '@/entities/catalog/repository';
import {
  MOCK_PROJECTS,
  MOCK_REPOSITORIES,
  MOCK_REPOSITORY_IMPORTS,
  MOCK_REPOSITORY_INSPECTION,
} from './catalogMocks';

const countRepositoriesByStatus = (
  repositories: Repository[],
  status: RepositoryPresentationStatusEnum,
) => {
  const matchingRepositories = repositories.filter(
    (repository) => repository.presentationStatus === status,
  );

  return matchingRepositories.length;
};

const getRepositoryCounts = (repositories: Repository[]) => {
  const ready = countRepositoriesByStatus(
    repositories,
    RepositoryPresentationStatusEnum.READY,
  );

  const importing = countRepositoriesByStatus(
    repositories,
    RepositoryPresentationStatusEnum.CLONING,
  );

  const failed = countRepositoriesByStatus(
    repositories,
    RepositoryPresentationStatusEnum.FAILED,
  );

  const unavailable = repositories.length - ready - importing - failed;

  return { total: repositories.length, ready, importing, failed, unavailable };
};

test.each(MOCK_REPOSITORIES)(
  'catalog memberships reference a mock project when the repository is $fullName',
  (repository) => {
    for (const membership of repository.memberships) {
      const project = MOCK_PROJECTS.find(
        (project) => project.id === membership.project.id,
      );

      expect(project).toMatchObject(membership.project);
      expect(repository.branches).toContain(membership.branch);
    }
  },
);

test.each(MOCK_REPOSITORY_IMPORTS)(
  'catalog imports reference a mock repository when the import is $id',
  (repositoryImport) => {
    const repositoryIds = MOCK_REPOSITORIES.map((repository) => repository.id);

    expect(repositoryIds).toContain(repositoryImport.repositoryId);
  },
);

test.each(MOCK_REPOSITORIES)(
  'catalog latest imports resolve when the repository is $fullName',
  (repository) => {
    const repositoryImports = MOCK_REPOSITORY_IMPORTS.filter(
      (repositoryImport) => repositoryImport.repositoryId === repository.id,
    );

    const latestImport = repositoryImports.at(-1) ?? null;

    expect(repository.latestImport).toBe(latestImport);
  },
);

test('catalog inspection references the registered local repository when the inspected clone is already registered', () => {
  const existingRepository = MOCK_REPOSITORY_INSPECTION.existingRepository;

  expect(MOCK_REPOSITORIES).toContain(existingRepository);
  expect(existingRepository?.checkoutPath).toBe(
    MOCK_REPOSITORY_INSPECTION.canonicalPath,
  );
});

test.each(MOCK_PROJECTS)(
  'catalog repository counts match memberships when the project is $name',
  (project) => {
    const repositories = MOCK_REPOSITORIES.filter((repository) => {
      const hasMembership = repository.memberships.some(
        (membership) => membership.project.id === project.id,
      );

      return hasMembership;
    });

    const repositoryCounts = getRepositoryCounts(repositories);

    expect(project.repositoryCounts).toEqual(repositoryCounts);
  },
);
