'use client';

import List from '@mui/material/List';

import { DAG_GRID_COLUMNS } from '@/components/dagList/constants';
import { EmptyState } from '@/components/emptyState/emptyState';
import { RepositoryRow } from '@/components/repositoryList/repositoryRow/repositoryRow';
import type { RepositoryListProps } from './types';
import { LABELS } from '@/labels/en';

const LIST_STYLE = { display: 'grid', gap: 2, gridTemplateColumns: DAG_GRID_COLUMNS };

/**
 * Displays repository checkouts in a project or the global catalog.
 */
export const RepositoryList = ({ repositories, ...repositoryListProps }: RepositoryListProps) => {
  if (repositories.length === 0) {
    return <EmptyState title={LABELS.repositoriesEmpty} body={LABELS.repositoriesEmptyHint} />;
  }

  return (
    <List disablePadding sx={LIST_STYLE}>
      {repositories.map((repository) => (
        <RepositoryRow key={repository.id} repository={repository} {...repositoryListProps} />
      ))}
    </List>
  );
};
