import type { GraphDependencyNode } from './graphLayout';

/**
 * Checks whether a dependency would create a cycle.
 */
export const wouldCreateDependencyCycle = (
  graphNodes: GraphDependencyNode[],
  sourceId: string,
  targetId: string,
): boolean => {
  const pendingNodeIds = [sourceId];
  const visitedNodeIds = new Set<string>();

  while (pendingNodeIds.length > 0) {
    const nodeId = pendingNodeIds.pop();
    const isVisited = nodeId === undefined || visitedNodeIds.has(nodeId);

    if (isVisited) {
      continue;
    }

    if (nodeId === targetId) {
      return true;
    }

    visitedNodeIds.add(nodeId);

    const graphNode = graphNodes.find((candidate) => candidate.id === nodeId);
    pendingNodeIds.push(...(graphNode?.dependsOn ?? []));
  }

  return false;
};

/**
 * Validates a connection that adds a dependency to its target.
 */
export const canConnectPlanNodes = (
  graphNodes: GraphDependencyNode[],
  sourceId: string,
  targetId: string,
): boolean => {
  if (sourceId === targetId) {
    return false;
  }

  const targetNode = graphNodes.find((graphNode) => graphNode.id === targetId);
  const isDuplicate = targetNode?.dependsOn.includes(sourceId) ?? false;

  if (isDuplicate) {
    return false;
  }

  const createsCycle = wouldCreateDependencyCycle(
    graphNodes,
    sourceId,
    targetId,
  );

  return !createsCycle;
};
