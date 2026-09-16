import List from '@mui/material/List';

import { AuditRow } from '@/components/dagPanel/dagTabs/auditList/auditRow/auditRow';
import {
  getAuditLineKey,
  compareByNewest,
} from '@/components/dagPanel/dagTabs/auditList/utils';
import { EmptyState } from '@/components/emptyState/emptyState';
import type { AuditLine } from '@/entities/dagDetail';
import { LABELS } from '@/labels/en';

interface AuditListProps {
  audit: AuditLine[];
}

/**
 * Renders the Activity tab of the DagTabs.
 */
export const AuditList = ({ audit }: AuditListProps) => {
  if (audit.length === 0) {
    return (
      <EmptyState
        title={LABELS.dagAuditEmpty}
        body={LABELS.dagAuditEmptyHint}
      />
    );
  }

  return (
    <List dense disablePadding>
      {[...audit].sort(compareByNewest).map((line) => (
        <AuditRow key={getAuditLineKey(line)} line={line} />
      ))}
    </List>
  );
};
