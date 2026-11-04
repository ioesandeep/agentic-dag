export const DAGS_ROUTE = '/dags';

export const PROJECTS_ROUTE = '/projects';

export const REPOSITORIES_ROUTE = '/repositories';

/**
 * Returns the route of a repository's screen.
 */
export const getRepositoryRoute = (repositoryId: string): string => {
  const encodedRepositoryId = encodeURIComponent(repositoryId);

  return `${REPOSITORIES_ROUTE}/${encodedRepositoryId}`;
};

/**
 * Returns the route of a dag's screen.
 */
export const getDagRoute = (dagName: string): string =>
  `${DAGS_ROUTE}/${dagName}`;

/**
 * Returns the route of a node's screen.
 */
export const getNodeRoute = (dagName: string, nodeId: string): string => {
  const dagRoute = getDagRoute(dagName);

  return `${dagRoute}/${nodeId}`;
};
