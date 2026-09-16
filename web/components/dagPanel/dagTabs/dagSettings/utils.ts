import type { DagSetting } from '@/components/dagPanel/dagTabs/dagSettings/types';
import type { DagDetail } from '@/entities/dagDetail';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

const SECONDS_PER_MINUTE = 60;

const formatDuration = (seconds: number): string => {
  if (seconds % SECONDS_PER_MINUTE !== 0) {
    const secondValues = { count: seconds };

    return formatLabel(LABELS.durationSeconds, secondValues);
  }

  const minuteValues = { count: seconds / SECONDS_PER_MINUTE };

  return formatLabel(LABELS.durationMinutes, minuteValues);
};

// TODO: list the project root, workspace path, executor agent, agent account,
// max workers, wake cap, session timeout and Slack channel once the read api
// sends them.
/**
 * Returns the displayable settings of a dag.
 */
export const getSettings = (dag: DagDetail): DagSetting[] => [
  { name: LABELS.dagBaseBranch, value: dag.baseBranch },
  {
    name: LABELS.dagTickInterval,
    value: formatDuration(dag.tickIntervalSeconds),
  },
];
