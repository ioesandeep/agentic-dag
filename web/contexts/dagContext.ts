'use client';

import { createContext } from 'react';

import type { DagDetail } from '@/entities/dagDetail';
import type { DagSummary } from '@/entities/dagSummary';

export interface DagContextValue {
  // The dags of this host, null until the api sends them.
  dagSummaries: DagSummary[] | null;
  // The current dag's detail, null until the api sends it.
  dagDetail: DagDetail | null;
  // True where the last request to the api failed.
  hasFailed: boolean;
}

const NO_DAG: DagContextValue = {
  dagSummaries: null,
  dagDetail: null,
  hasFailed: false,
};

export const DagContext = createContext<DagContextValue>(NO_DAG);
