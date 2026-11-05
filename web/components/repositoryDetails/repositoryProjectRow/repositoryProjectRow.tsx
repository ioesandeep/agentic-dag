'use client';

import DeleteOutlinedIcon from '@mui/icons-material/DeleteOutlined';
import IconButton from '@mui/material/IconButton';
import Link from '@mui/material/Link';
import ListItem from '@mui/material/ListItem';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import NextLink from 'next/link';

import { BranchButton } from '@/components/branchButton/branchButton';
import type {
  ProjectMembership,
  Repository,
} from '@/entities/catalog/repository';
import { LABELS } from '@/labels/en';

const ROW_STYLE = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr) auto minmax(0, 1fr)',
  columnGap: 1,
  py: 1.5,
  borderTop: 1,
  borderColor: 'divider',
};

const NAME_STYLE = { fontWeight: 600, minWidth: 0, overflowWrap: 'anywhere' };
const ACTION_STYLE = { justifySelf: 'end' };

interface RepositoryProjectRowProps {
  repository: Repository;
  membership: ProjectMembership;
  onRemove: (membership: ProjectMembership) => void;
}

/**
 * Displays a repository's project membership and branch.
 */
export const RepositoryProjectRow = ({
  repository,
  membership,
  onRemove,
}: RepositoryProjectRowProps) => {
  const { project, branch } = membership;
  const isReadOnly = project.archivedAt !== null;
  const handleBranchChange = () => {};
  const handleRemove = () => onRemove(membership);

  return (
    <ListItem disableGutters aria-label={project.name} sx={ROW_STYLE}>
      <Stack sx={NAME_STYLE}>
        <Link
          component={NextLink}
          href={`/projects/${project.id}`}
          color="inherit"
          underline="hover"
        >
          {project.name}
        </Link>
        {isReadOnly && (
          <Typography variant="caption" color="text.secondary">
            {LABELS.projectStateArchived}
          </Typography>
        )}
      </Stack>
      <BranchButton
        repository={repository}
        branch={branch}
        disabled={isReadOnly}
        onChange={handleBranchChange}
      />
      <Tooltip title={LABELS.repositoryRemoveFromProject}>
        <Stack component="span" sx={ACTION_STYLE}>
          <IconButton
            size="small"
            color="error"
            aria-label={LABELS.repositoryRemoveFromProject}
            disabled={isReadOnly}
            onClick={handleRemove}
          >
            <DeleteOutlinedIcon fontSize="small" />
          </IconButton>
        </Stack>
      </Tooltip>
    </ListItem>
  );
};
