import { AuditList } from '@/components/dagPanel/dagTabs/auditList/auditList';
import { DagSettings } from '@/components/dagPanel/dagTabs/dagSettings/dagSettings';
import { NodeTable } from '@/components/dagPanel/dagTabs/nodeTable/nodeTable';
import { DagTab } from '@/components/dagPanel/dagTabs/types';
import type { DagDetail } from '@/entities/dagDetail';

interface DagTabPanelProps {
  dag: DagDetail;
  tab: DagTab;
}

/**
 * Renders the panel below the DagTabs tab bar.
 */
export const DagTabPanel = ({ dag, tab }: DagTabPanelProps) => {
  switch (tab) {
    case DagTab.NODES:
      return <NodeTable dagName={dag.name} nodes={dag.nodes} />;
    case DagTab.SETTINGS:
      return <DagSettings dag={dag} />;
    case DagTab.AUDIT:
      return <AuditList audit={dag.audit} />;
  }
};
