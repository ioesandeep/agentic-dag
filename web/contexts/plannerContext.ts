'use client';

import { createContext } from 'react';
import type { StoreApi } from 'zustand/vanilla';

import type { Plan } from '@/entities/plan/plan';
import type { PlanNodeChange, PlanRevision } from '@/entities/plan/planMessage';
import type { PlanProject } from '@/entities/plan/planProject';
import type {
  PlannerAction,
  PlannerStoreState,
} from '@/stores/plannerStore/types';

/**
 * Provides shared plans and their editing operations.
 */
export interface PlannerContextData extends PlannerAction {
  projects: PlanProject[];
  plans: Plan[];
  canUndo: Record<string, boolean>;
  canRedo: Record<string, boolean>;
  lastUndoneRevision: Record<string, PlanRevision | null>;
  highlightedNodes: Record<string, PlanNodeChange[]>;
}

/**
 * Shares the planner store across planner pages.
 */
export const PlannerContext = createContext<StoreApi<PlannerStoreState> | null>(
  null,
);
