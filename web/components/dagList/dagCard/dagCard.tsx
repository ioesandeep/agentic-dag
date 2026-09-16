'use client';

import { DagFlexibleCard } from '@/components/dagList/dagCard/dagFlexibleCard/dagFlexibleCard';
import { DagFullCard } from '@/components/dagList/dagCard/dagFullCard/dagFullCard';
import { DagMinimalCard } from '@/components/dagList/dagCard/dagMinimalCard/dagMinimalCard';
import type { DagCardSelect } from '@/components/dagList/dagCard/types';
import { DagCardVariant } from '@/components/dagList/dagCard/types';
import type { DagSummary } from '@/entities/dagSummary';

interface DagCardProps {
  dag: DagSummary;
  variant: DagCardVariant;
  isCurrent?: boolean;
  onSelect?: DagCardSelect;
}

/**
 * Renders the card for one dag in the requested variant.
 */
export const DagCard = ({
  dag,
  variant,
  isCurrent = false,
  onSelect,
}: DagCardProps) => {
  if (variant === DagCardVariant.MINIMAL) {
    return (
      <DagMinimalCard dag={dag} isCurrent={isCurrent} onSelect={onSelect} />
    );
  }

  if (variant === DagCardVariant.FLEXIBLE) {
    return (
      <DagFlexibleCard dag={dag} isCurrent={isCurrent} onSelect={onSelect} />
    );
  }

  return <DagFullCard dag={dag} onSelect={onSelect} />;
};
