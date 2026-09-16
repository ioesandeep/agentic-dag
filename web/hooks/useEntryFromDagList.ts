'use client';

import { useEffect, useState } from 'react';

import type { DagSummary } from '@/entities/dagSummary';
import {
  deleteEntryFromDagList,
  findEntryFromDagList,
} from '@/utils/dagListEntry';

/**
 * Returns the dags the dag list handed over to this page.
 */
export const useEntryFromDagList = (): DagSummary[] | null => {
  const [dagsFromList] = useState(findEntryFromDagList);

  useEffect(() => {
    deleteEntryFromDagList();
  }, []);

  return dagsFromList;
};
