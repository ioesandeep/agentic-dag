import { expect, test } from 'vitest';

import {
  getProjectActionPath,
  getProjectPath,
  getProjectRepositoriesPath,
  getProjectRepositoryPath,
  getProjectsPath,
  getRepositoriesPath,
  getRepositoryActionPath,
  getRepositoryCatalogPath,
  getRepositoryImportActionPath,
  getRepositoryImportPath,
  getRepositoryImportsPath,
  getRepositoryPath,
  ProjectActionEnum,
  RepositoryActionEnum,
  RepositoryCatalogEndpointEnum,
  RepositoryImportActionEnum,
} from './catalogApiPath';

const PROJECT_ID = 'project /?#%&=+雪';
const REPOSITORY_ID = 'repository /?#%&=+雪';
const IMPORT_ID = 'import /?#%&=+雪';
const PROJECT_PATH = '/api/projects/project%20%2F%3F%23%25%26%3D%2B%E9%9B%AA';
const REPOSITORY_PATH =
  '/api/repositories/repository%20%2F%3F%23%25%26%3D%2B%E9%9B%AA';
const IMPORT_PATH =
  '/api/repository-imports/import%20%2F%3F%23%25%26%3D%2B%E9%9B%AA';
const EXPECTED_CATALOG_PATHS = [
  '/api/projects',
  PROJECT_PATH,
  `${PROJECT_PATH}/archive`,
  `${PROJECT_PATH}/restore`,
  `${PROJECT_PATH}/repositories`,
  '/api/projects/project%20%2F%3F%23%25%26%3D%2B%E9%9B%AA/repositories/repository%20%2F%3F%23%25%26%3D%2B%E9%9B%AA',
  '/api/repositories',
  REPOSITORY_PATH,
  '/api/repositories/inspect-local',
  '/api/repositories/register-local',
  '/api/repositories/github/status',
  '/api/repositories/import',
  `${REPOSITORY_PATH}/check`,
  `${REPOSITORY_PATH}/relink`,
  `${REPOSITORY_PATH}/archive`,
  `${REPOSITORY_PATH}/restore`,
  `${REPOSITORY_PATH}/imports`,
  IMPORT_PATH,
  `${IMPORT_PATH}/retry`,
  `${IMPORT_PATH}/cancel`,
];

test('Catalog paths match every approved endpoint when no DAG is selected', () => {
  const catalogPaths = [
    getProjectsPath(),
    getProjectPath(PROJECT_ID),
    getProjectActionPath(PROJECT_ID, ProjectActionEnum.ARCHIVE),
    getProjectActionPath(PROJECT_ID, ProjectActionEnum.RESTORE),
    getProjectRepositoriesPath(PROJECT_ID),
    getProjectRepositoryPath(PROJECT_ID, REPOSITORY_ID),
    getRepositoriesPath(),
    getRepositoryPath(REPOSITORY_ID),
    getRepositoryCatalogPath(RepositoryCatalogEndpointEnum.INSPECT_LOCAL),
    getRepositoryCatalogPath(RepositoryCatalogEndpointEnum.REGISTER_LOCAL),
    getRepositoryCatalogPath(RepositoryCatalogEndpointEnum.GITHUB_STATUS),
    getRepositoryCatalogPath(RepositoryCatalogEndpointEnum.IMPORT),
    getRepositoryActionPath(REPOSITORY_ID, RepositoryActionEnum.CHECK),
    getRepositoryActionPath(REPOSITORY_ID, RepositoryActionEnum.RELINK),
    getRepositoryActionPath(REPOSITORY_ID, RepositoryActionEnum.ARCHIVE),
    getRepositoryActionPath(REPOSITORY_ID, RepositoryActionEnum.RESTORE),
    getRepositoryImportsPath(REPOSITORY_ID),
    getRepositoryImportPath(IMPORT_ID),
    getRepositoryImportActionPath(IMPORT_ID, RepositoryImportActionEnum.RETRY),
    getRepositoryImportActionPath(IMPORT_ID, RepositoryImportActionEnum.CANCEL),
  ];

  expect(catalogPaths).toEqual(EXPECTED_CATALOG_PATHS);
});

const ARCHIVE_VISIBILITY = [undefined, false, true];

test.each(ARCHIVE_VISIBILITY)(
  'Catalog lists add includeArchived only when archive visibility is %s',
  (includeArchived) => {
    const expectedSuffix = includeArchived ? '?includeArchived=true' : '';

    const projectsPath = getProjectsPath(includeArchived);
    const repositoriesPath = getRepositoriesPath(includeArchived);

    expect(projectsPath).toBe(`/api/projects${expectedSuffix}`);
    expect(repositoriesPath).toBe(`/api/repositories${expectedSuffix}`);
  },
);
