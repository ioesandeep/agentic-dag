export const DAGS_PATH = '/api/dags';
const MEMORY_SEGMENT = 'memory';
const RECOVERY_SESSIONS_SEGMENT = 'recovery-sessions';

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

/**
 * Returns the api path of a dag's memory file.
 */
export const getMemoryPath = (dagName: string): string => {
  const dagPath = getDagPath(dagName);

  return `${dagPath}/${MEMORY_SEGMENT}`;
};

/**
 * Returns the api path of a dag's recovery sessions.
 */
export const getRecoverySessionsPath = (dagName: string): string => {
  const dagPath = getDagPath(dagName);

  return `${dagPath}/${RECOVERY_SESSIONS_SEGMENT}`;
};
