'use client';

import { DagPanel } from '@/components/dagPanel/dagPanel';
import { useDag } from '@/hooks/useDag';

interface DagScreenProps {
  dagName: string;
}

/**
 * Renders a single dag's split panel.
 */
export const DagScreen = ({ dagName }: DagScreenProps) => {
  const { dagSummaries, dagDetail, hasFailed } = useDag();

  return (
    <DagPanel
      dags={dagSummaries}
      currentName={dagName}
      dag={dagDetail}
      hasFailed={hasFailed}
    />
  );
};
