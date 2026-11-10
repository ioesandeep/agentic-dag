export const DAGS_ROUTE = '/dags';

export const PROJECTS_ROUTE = '/projects';

export const REPOSITORIES_ROUTE = '/repositories';

/**
 * Identifies the plans list route.
 */
export const PLANS_ROUTE = '/plans';

/**
 * Identifies the plan creation route.
 */
export const NEW_PLAN_ROUTE = '/plans/new';

/**
 * Returns the route of a plan's screen.
 */
export const getPlanRoute = (planId: string): string => {
  const encodedPlanId = encodeURIComponent(planId);

  return `${PLANS_ROUTE}/${encodedPlanId}`;
};

/**
 * Returns the route of a plan node's screen.
 */
export const getPlanNodeRoute = (planId: string, nodeId: string): string => {
  const planRoute = getPlanRoute(planId);
  const encodedNodeId = encodeURIComponent(nodeId);

  return `${planRoute}/${encodedNodeId}`;
};

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
