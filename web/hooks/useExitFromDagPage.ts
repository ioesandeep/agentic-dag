'use client';

import { useEffect, useState } from 'react';

import {
  deleteExitFromDagPage,
  isExitFromDagPage,
} from '@/utils/dagPageExit';

/**
 * Returns true when the dag page closes before the dag list mounts.
 */
export const useExitFromDagPage = (): boolean => {
  const [isReturning] = useState(isExitFromDagPage);

  useEffect(() => {
    deleteExitFromDagPage();
  }, []);

  return isReturning;
};
