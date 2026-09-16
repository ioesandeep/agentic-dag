export const DAGS_ROUTE = '/dags';

/**
 * Returns the route of a dag's screen.
 */
export const getDagRoute = (dagName: string): string =>
  `${DAGS_ROUTE}/${dagName}`;
