'use client';

import { useContext } from 'react';
import { useStore } from 'zustand';

import { getPlannerValue } from '@/stores/plannerStore/selectors/plannerSelectors';
import type { PlannerContextData } from '@/contexts/plannerContext';
import { PlannerContext } from '@/contexts/plannerContext';

/**
 * Reports a planner consumer outside its provider.
 */
class PlannerProviderError extends Error {
  constructor() {
    super('usePlanner requires PlannerProvider.');
    this.name = 'PlannerProviderError';
  }
}

/**
 * Returns shared plans and their editing operations.
 * @throws {PlannerProviderError} When the planner provider is absent.
 */
export const usePlanner = (): PlannerContextData => {
  const plannerStore = useContext(PlannerContext);

  if (!plannerStore) {
    throw new PlannerProviderError();
  }

  const plannerState = useStore(plannerStore);

  return { ...getPlannerValue(plannerState), ...plannerState.actions };
};
