const PROJECTS_PATH = '/api/projects';
const REPOSITORIES_PATH = '/api/repositories';
const REPOSITORY_IMPORTS_PATH = '/api/repository-imports';
const REPOSITORIES_SEGMENT = 'repositories';
const IMPORTS_SEGMENT = 'imports';
const INCLUDE_ARCHIVED_PARAMETER = 'includeArchived';

/**
 * Identifies project archive operations.
 */
export enum ProjectActionEnum {
  ARCHIVE = 'archive',
  RESTORE = 'restore',
}

/**
 * Identifies repository catalog operations.
 */
export enum RepositoryCatalogEndpointEnum {
  INSPECT_LOCAL = 'inspect-local',
  REGISTER_LOCAL = 'register-local',
  GITHUB_STATUS = 'github/status',
  IMPORT = 'import',
}

/**
 * Identifies repository maintenance operations.
 */
export enum RepositoryActionEnum {
  CHECK = 'check',
  RELINK = 'relink',
  ARCHIVE = 'archive',
  RESTORE = 'restore',
}

/**
 * Identifies import control operations.
 */
export enum RepositoryImportActionEnum {
  RETRY = 'retry',
  CANCEL = 'cancel',
}

/**
 * Returns the API path for the project catalog list.
 */
export const getProjectsPath = (includeArchived = false): string => {
  if (!includeArchived) {
    return PROJECTS_PATH;
  }

  return `${PROJECTS_PATH}?${INCLUDE_ARCHIVED_PARAMETER}=true`;
};

/**
 * Returns the API path for a project record.
 */
export const getProjectPath = (projectId: string): string => {
  const encodedProjectId = encodeURIComponent(projectId);
  return `${PROJECTS_PATH}/${encodedProjectId}`;
};

/**
 * Returns the API path for a project archive operation.
 */
export const getProjectActionPath = (
  projectId: string,
  projectAction: ProjectActionEnum,
): string => {
  const projectPath = getProjectPath(projectId);
  return `${projectPath}/${projectAction}`;
};

/**
 * Returns the API path for a project's repository list.
 */
export const getProjectRepositoriesPath = (projectId: string): string => {
  const projectPath = getProjectPath(projectId);
  return `${projectPath}/${REPOSITORIES_SEGMENT}`;
};

/**
 * Returns the API path for a project repository association.
 */
export const getProjectRepositoryPath = (
  projectId: string,
  repositoryId: string,
): string => {
  const projectRepositoriesPath = getProjectRepositoriesPath(projectId);
  const encodedRepositoryId = encodeURIComponent(repositoryId);
  return `${projectRepositoriesPath}/${encodedRepositoryId}`;
};

/**
 * Returns the API path for the repository catalog list.
 */
export const getRepositoriesPath = (includeArchived = false): string => {
  if (!includeArchived) {
    return REPOSITORIES_PATH;
  }

  return `${REPOSITORIES_PATH}?${INCLUDE_ARCHIVED_PARAMETER}=true`;
};

/**
 * Returns the API path for a repository catalog operation.
 */
export const getRepositoryCatalogPath = (
  repositoryCatalogEndpoint: RepositoryCatalogEndpointEnum,
): string => `${REPOSITORIES_PATH}/${repositoryCatalogEndpoint}`;

/**
 * Returns the API path for a repository record.
 */
export const getRepositoryPath = (repositoryId: string): string => {
  const encodedRepositoryId = encodeURIComponent(repositoryId);
  return `${REPOSITORIES_PATH}/${encodedRepositoryId}`;
};

/**
 * Returns the API path for a repository maintenance operation.
 */
export const getRepositoryActionPath = (
  repositoryId: string,
  repositoryAction: RepositoryActionEnum,
): string => {
  const repositoryPath = getRepositoryPath(repositoryId);
  return `${repositoryPath}/${repositoryAction}`;
};

/**
 * Returns the API path for a repository's import history.
 */
export const getRepositoryImportsPath = (repositoryId: string): string => {
  const repositoryPath = getRepositoryPath(repositoryId);
  return `${repositoryPath}/${IMPORTS_SEGMENT}`;
};

/**
 * Returns the API path for an import attempt.
 */
export const getRepositoryImportPath = (importId: string): string => {
  const encodedImportId = encodeURIComponent(importId);
  return `${REPOSITORY_IMPORTS_PATH}/${encodedImportId}`;
};

/**
 * Returns the API path for an import control operation.
 */
export const getRepositoryImportActionPath = (
  importId: string,
  repositoryImportAction: RepositoryImportActionEnum,
): string => {
  const repositoryImportPath = getRepositoryImportPath(importId);
  return `${repositoryImportPath}/${repositoryImportAction}`;
};
