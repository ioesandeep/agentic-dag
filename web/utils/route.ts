export const DAGS_ROUTE = '/dags';

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
