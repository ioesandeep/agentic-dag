'use client';

import { useContext } from 'react';

import type { DagContextValue } from '@/contexts/dagContext';
import { DagContext } from '@/contexts/dagContext';

/**
 * Returns the current dag, the dags beside it, and whether its last request failed.
 */
export const useDag = (): DagContextValue => useContext(DagContext);
