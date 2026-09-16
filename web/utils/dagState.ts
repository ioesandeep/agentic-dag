import type { DagSummary } from '@/entities/dagSummary';
import type { NodeState } from '@/entities/nodeState';
import { getStateColor } from '@/utils/getStateColor';
import { isNull } from '@/utils/typeGuards';

/**
 * The states the dag list filters by.
 */
export enum DagState {
  ANY = 'any',
  ACTIVE = 'active',
  COMPLETE = 'complete',
  ERRORED = 'errored',
}

export const DAG_STATES: readonly DagState[] = Object.values(DagState);

const ANY_STATE_COLOR = 'var(--mui-palette-primary-main)';

// The colour each dag state carries in the filter.
const DAG_STATE_COLORS: Record<DagState, string> = {
  [DagState.ANY]: ANY_STATE_COLOR,
  [DagState.ACTIVE]: getStateColor('in_progress'),
  [DagState.COMPLETE]: getStateColor('merged'),
  [DagState.ERRORED]: getStateColor('needs_human'),
};

const ACTIVE_NODE_STATES: readonly NodeState[] = [
  'in_progress',
  'resting',
  'pending',
];
const ERRORED_NODE_STATES: readonly NodeState[] = ['needs_human', 'errored'];
const COMPLETE_NODE_STATE: NodeState = 'merged';
const NO_CURRENT_DAG_NAME = '';

const hasNodeInStates = (
  dag: DagSummary,
  nodeStates: readonly NodeState[],
): boolean => dag.nodes.some((node) => nodeStates.includes(node.state));

const isCompleteDag = (dag: DagSummary): boolean =>
  dag.nodes.length > 0 &&
  dag.nodes.every((node) => node.state === COMPLETE_NODE_STATE);

const isDagInState = (dag: DagSummary, dagState: DagState): boolean => {
  switch (dagState) {
    case DagState.ANY:
      return true;
    case DagState.ACTIVE:
      return hasNodeInStates(dag, ACTIVE_NODE_STATES);
    case DagState.COMPLETE:
      return isCompleteDag(dag);
    case DagState.ERRORED:
      return hasNodeInStates(dag, ERRORED_NODE_STATES);
  }
};

/**
 * Returns the dags in the selected state, keeping the dag whose page is open.
 */
export const getDagsInStateWithCurrentDag = (
  dags: DagSummary[] | null,
  dagState: DagState,
  currentName: string,
): DagSummary[] | null => {
  if (isNull(dags)) {
    return dags;
  }

  return dags.filter(
    (dag) => dag.name === currentName || isDagInState(dag, dagState),
  );
};

/**
 * Returns the dags in the selected state.
 */
export const getDagsInState = (
  dags: DagSummary[] | null,
  dagState: DagState,
): DagSummary[] | null =>
  getDagsInStateWithCurrentDag(dags, dagState, NO_CURRENT_DAG_NAME);

/**
 * Returns the theme colour of a dag state.
 */
export const getDagStateColor = (dagState: DagState): string =>
  DAG_STATE_COLORS[dagState];
