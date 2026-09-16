import { DagGraph } from '@/components/dagPanel/dagGraph/dagGraph';
import { INITIAL_SPLIT } from '@/components/dagPanel/dagPanelBody/constants';
import { DagPanelBodySkeleton } from '@/components/dagPanel/dagPanelBody/dagPanelBodySkeleton/dagPanelBodySkeleton';
import { DagTabs } from '@/components/dagPanel/dagTabs/dagTabs';
import { EmptyState } from '@/components/emptyState/emptyState';
import { SplitPanel } from '@/components/splitPanel/splitPanel';
import type { DagDetail } from '@/entities/dagDetail';
import { LABELS } from '@/labels/en';

interface DagPanelBodyProps {
  // The dag's detail, null until the api sends it.
  dag: DagDetail | null;
  // False until the panel's entrance finishes.
  hasSettled: boolean;
}

/**
 * Renders the right column of the DagPanel.
 */
export const DagPanelBody = ({ dag, hasSettled }: DagPanelBodyProps) => {
  if (!hasSettled || dag === null) {
    return <DagPanelBodySkeleton />;
  }

  if (!dag.isReadable) {
    return (
      <EmptyState
        title={LABELS.dagUnreadableTitle}
        body={LABELS.dagUnreadableHint}
      />
    );
  }

  const panels = [
    <DagGraph key="graph" dag={dag} />,
    <DagTabs key="tabs" dag={dag} />,
  ];

  return <SplitPanel panels={panels} initialSplit={INITIAL_SPLIT} />;
};
