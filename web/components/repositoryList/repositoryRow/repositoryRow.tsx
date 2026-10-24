'use client';

import GitHubIcon from '@mui/icons-material/GitHub';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';

import type { RepositoryRowProps } from '@/components/repositoryList/types';
import {
  getRepositoryActions,
  getRepositoryBranchLabels,
  getRepositoryClonedDateLabel,
  getRepositoryDefaultBranchLabel,
  getRepositoryKindLabel,
} from '@/components/repositoryList/utils';
import { RepositoryStatus } from '@/components/repositoryStatus/repositoryStatus';
import { RepositoryStatusVariantEnum } from '@/components/repositoryStatus/types';
import { SoftChip } from '@/components/softChip/softChip';
import { VirgoCard } from '@/components/virgoCard/virgoCard';
import { VirgoCardBody } from '@/components/virgoCard/virgoCardBody/virgoCardBody';
import { VirgoCardFooter } from '@/components/virgoCard/virgoCardFooter/virgoCardFooter';
import { VirgoCardHeader } from '@/components/virgoCard/virgoCardHeader/virgoCardHeader';
import { LABELS } from '@/labels/en';

const ITEM_STYLE = { p: 0, display: 'block', minWidth: 0 };
const WRAP_STYLE = { minWidth: 0, overflowWrap: 'anywhere' };
const ACTION_STYLE = { flexWrap: 'wrap', maxWidth: { xs: '4rem', md: 'none' } };
const PROJECT_LIST_STYLE = {
  p: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 0.5,
};

const PROJECT_ROW_STYLE = { gap: 1, minWidth: 0 };
const PROJECT_DOT_STYLE = {
  width: '0.5rem',
  height: '0.5rem',
  borderRadius: '50%',
  flexShrink: 0,
};

const PROJECT_BAR_STYLE = {
  display: 'flex',
  height: '0.5rem',
  borderRadius: 1,
  overflow: 'hidden',
  bgcolor: 'grey.500',
};

/**
 * Displays a repository checkout and its available actions.
 */
export const RepositoryRow = (repositoryRowProps: RepositoryRowProps) => {
  const { repository } = repositoryRowProps;
  const branchLabels = getRepositoryBranchLabels(repositoryRowProps);
  const actions = getRepositoryActions(repositoryRowProps);
  const kindLabel = getRepositoryKindLabel(repository);

  const defaultBranchLabel = getRepositoryDefaultBranchLabel(repository);
  const clonedDateLabel = getRepositoryClonedDateLabel(repository);
  const hasNoProjects = branchLabels.length === 0;

  const header = (
    <VirgoCardHeader
      title={repository.fullName}
      actions={
        <Stack direction="row" sx={ACTION_STYLE}>
          <Tooltip title={repository.fullName}>
            <IconButton
              component="a"
              href={repository.webUrl}
              target="_blank"
              rel="noreferrer"
              size="small"
              aria-label={repository.fullName}
            >
              <GitHubIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          {actions.map(({ label, ariaLabel, icon: Icon, onClick }) => (
            <Tooltip key={label} title={label}>
              <IconButton size="small" onClick={onClick} aria-label={ariaLabel ?? label}>
                <Icon fontSize="small" />
              </IconButton>
            </Tooltip>
          ))}
        </Stack>
      }
    />
  );

  const body = (
    <VirgoCardBody
      content={
        <>
          <Box role="group" aria-label={LABELS.repositoryProjects} sx={PROJECT_BAR_STYLE}>
            {branchLabels.map(({ projectId, label, color }) => (
              <Box
                key={projectId}
                role="img"
                aria-label={label}
                sx={{ flexGrow: 1, bgcolor: color }}
              />
            ))}
          </Box>
          <Typography variant="body1" sx={WRAP_STYLE}>
            {repository.checkoutPath}
          </Typography>
          <RepositoryStatus
            repository={repository}
            variant={RepositoryStatusVariantEnum.PROGRESS}
          />
          <List aria-label={LABELS.repositoryProjects} sx={PROJECT_LIST_STYLE}>
            {branchLabels.map(({ projectId, label, color }) => (
              <ListItem key={projectId} disablePadding sx={PROJECT_ROW_STYLE}>
                <Box aria-hidden sx={{ ...PROJECT_DOT_STYLE, bgcolor: color }} />
                <Typography variant="body1" sx={WRAP_STYLE}>
                  {label}
                </Typography>
              </ListItem>
            ))}
          </List>
          {hasNoProjects && (
            <Typography variant="body1" color="text.secondary">
              {LABELS.repositoryNoProjects}
            </Typography>
          )}
        </>
      }
    />
  );

  const footer = (
    <VirgoCardFooter
      chips={
        <>
          <RepositoryStatus repository={repository} variant={RepositoryStatusVariantEnum.STATUS} />
          {kindLabel !== null && (
            <SoftChip color="var(--mui-palette-text-primary)" label={kindLabel} />
          )}
          <SoftChip color="var(--mui-palette-primary-main)" label={defaultBranchLabel} />
          {clonedDateLabel !== null && (
            <SoftChip color="var(--mui-palette-text-secondary)" label={clonedDateLabel} />
          )}
        </>
      }
    />
  );

  return (
    <ListItem sx={ITEM_STYLE} aria-label={repository.fullName}>
      <VirgoCard ariaLabel={repository.fullName} header={header} body={body} footer={footer} />
    </ListItem>
  );
};
