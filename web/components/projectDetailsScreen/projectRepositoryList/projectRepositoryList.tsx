import List from '@mui/material/List';

import { ProjectRepositoryRow } from '@/components/projectDetailsScreen/projectRepositoryList/projectRepositoryRow/projectRepositoryRow';
import type { Repository } from '@/entities/catalog/repository';

interface ProjectRepositoryListProps {
  repositories: Repository[];
  projectId: string;
  isReadOnly: boolean;
  onRemove: (repository: Repository) => void;
}

/**
 * Displays repositories assigned to a project.
 */
export const ProjectRepositoryList = ({
  repositories,
  ...projectRepositoryRowProps
}: ProjectRepositoryListProps) => (
  <List disablePadding>
    {repositories.map((repository) => (
      <ProjectRepositoryRow
        key={repository.id}
        repository={repository}
        {...projectRepositoryRowProps}
      />
    ))}
  </List>
);
