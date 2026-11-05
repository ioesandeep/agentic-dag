'use client';

import CancelOutlinedIcon from '@mui/icons-material/CancelOutlined';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Link from '@mui/material/Link';
import List from '@mui/material/List';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { Fragment } from 'react';

import { RepositoryStatus } from '@/components/repositoryStatus/repositoryStatus';
import type {
  ProjectMembership,
  Repository,
} from '@/entities/catalog/repository';
import { LABELS, REPOSITORY_DETAILS_ACTION_LABELS } from '@/labels/en';
import { RepositoryActionEnum } from '@/entities/catalog/repositoryAction';
import { RepositoryProjectRow } from './repositoryProjectRow/repositoryProjectRow';
import {
  getRepositoryDetailsActions,
  getRepositoryDetailsFields,
} from './utils';

const SECTION_STYLE = { p: { xs: 2, sm: 2.5 }, minWidth: 0 };
const FIELD_STYLE = { m: 0, overflowWrap: 'anywhere' };
const METADATA_STYLE = {
  ...FIELD_STYLE,
  display: 'grid',
  gridTemplateColumns: {
    xs: 'minmax(0, 1fr)',
    sm: 'minmax(0, 1fr) minmax(0, 2fr)',
  },
  columnGap: 3,
  rowGap: 1.5,
};

const FIELD_LABEL_STYLE = { fontWeight: 600 };
const ACTION_STYLE = { flexWrap: 'wrap' };
const PROJECT_HEADING_STYLE = { mb: 1.5 };

interface RepositoryDetailsProps {
  repository: Repository;
  onAction: (action: RepositoryActionEnum) => void;
  onRemove: (membership: ProjectMembership) => void;
}

/**
 * Displays repository metadata, availability, and project branches.
 */
export const RepositoryDetails = ({
  repository,
  onAction,
  onRemove,
}: RepositoryDetailsProps) => {
  const actions = getRepositoryDetailsActions(repository);
  const detailActions = actions.filter(
    (action) => action !== RepositoryActionEnum.CANCEL,
  );

  const canCancel = actions.includes(RepositoryActionEnum.CANCEL);

  const metadataFields = getRepositoryDetailsFields(repository);
  const errorMessage =
    repository.validationMessage ?? repository.latestImport?.errorMessage;

  const handleCancel = () => onAction(RepositoryActionEnum.CANCEL);

  return (
    <Stack spacing={3}>
      <Paper
        variant="outlined"
        component="section"
        aria-label={LABELS.repositoryDetails}
        sx={SECTION_STYLE}
      >
        <Stack spacing={2}>
          <Typography variant="h6" component="h2">
            {LABELS.repositoryDetails}
          </Typography>
          <Stack component="dl" sx={METADATA_STYLE}>
            {metadataFields.map(({ label, value, href }) => (
              <Fragment key={label}>
                <Typography
                  component="dt"
                  variant="body1"
                  sx={FIELD_LABEL_STYLE}
                >
                  {label}
                </Typography>
                <Typography component="dd" variant="body1" sx={FIELD_STYLE}>
                  {href !== undefined && (
                    <Link href={href} target="_blank" rel="noreferrer">
                      {value}
                    </Link>
                  )}
                  {href === undefined && value}
                </Typography>
              </Fragment>
            ))}
          </Stack>
          <RepositoryStatus
            repository={repository}
            progressAction={
              canCancel && (
                <Tooltip title={LABELS.repositoryCancelClone}>
                  <IconButton
                    size="small"
                    aria-label={LABELS.repositoryCancelClone}
                    onClick={handleCancel}
                  >
                    <CancelOutlinedIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )
            }
          />
          {errorMessage && (
            <Typography color="error">{errorMessage}</Typography>
          )}
          {detailActions.length > 0 && (
            <Stack direction="row" spacing={1} useFlexGap sx={ACTION_STYLE}>
              {detailActions.map((action) => (
                <Button key={action} onClick={() => onAction(action)}>
                  {REPOSITORY_DETAILS_ACTION_LABELS[action]}
                </Button>
              ))}
            </Stack>
          )}
        </Stack>
      </Paper>
      <Paper
        variant="outlined"
        component="section"
        aria-label={LABELS.repositoryProjects}
        sx={SECTION_STYLE}
      >
        <Typography variant="h6" component="h2" sx={PROJECT_HEADING_STYLE}>
          {LABELS.repositoryProjects}
        </Typography>
        <List aria-label={LABELS.repositoryProjects} disablePadding>
          {repository.memberships.map((membership) => (
            <RepositoryProjectRow
              key={membership.project.id}
              repository={repository}
              membership={membership}
              onRemove={onRemove}
            />
          ))}
        </List>
        {repository.memberships.length === 0 && (
          <Typography color="text.secondary">
            {LABELS.repositoryNoProjects}
          </Typography>
        )}
      </Paper>
    </Stack>
  );
};
