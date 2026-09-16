export const DAGS_PATH = '/api/dags';

/**
 * Returns the api path of a dag.
 */
export const getDagPath = (dagName: string): string =>
  `${DAGS_PATH}/${dagName}`;

/**
 * Returns the api path of a node of a dag.
 */
export const getNodePath = (dagName: string, nodeId: string): string => {
  const dagPath = getDagPath(dagName);

  return `${dagPath}/${nodeId}`;
};
