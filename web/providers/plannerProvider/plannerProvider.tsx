'use client';

import { useState } from 'react';
import type { ReactNode } from 'react';

import { PlannerContext } from '@/contexts/plannerContext';
import { createPlannerStore } from '@/stores/plannerStore/plannerStore';

interface PlannerProviderProps {
  children: ReactNode;
}

/**
 * Provides the shared planner store to planner pages.
 */
export const PlannerProvider = ({ children }: PlannerProviderProps) => {
  const [plannerStore] = useState(createPlannerStore);

  return <PlannerContext value={plannerStore}>{children}</PlannerContext>;
};
