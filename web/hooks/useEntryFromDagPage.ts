'use client';

import { useEffect, useState } from 'react';

import {
  deleteEntryFromDagPage,
  isEntryFromDagPage,
} from '@/utils/dagPageEntry';

/**
 * Returns true where the dag page opened this node.
 */
export const useEntryFromDagPage = (): boolean => {
  const [isEntering] = useState(isEntryFromDagPage);

  useEffect(() => {
    deleteEntryFromDagPage();
  }, []);

  return isEntering;
};
