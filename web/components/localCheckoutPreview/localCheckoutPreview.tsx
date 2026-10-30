import Alert from '@mui/material/Alert';
import Link from '@mui/material/Link';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import type { Repository } from '@/entities/catalog/repository';
import type { RepositoryInspection } from '@/entities/catalog/repositoryInspection';
import type { LocalCheckoutPreviewContent } from './types';
import { isRepositoryMismatch } from './utils';

const PREVIEW_STYLE = { overflowWrap: 'anywhere', minWidth: 0 };

interface LocalCheckoutPreviewProps {
  inspection: RepositoryInspection | null;
  repairRepository?: Repository;
  showExistingRegistration?: boolean;
  content: LocalCheckoutPreviewContent;
}

/**
 * Displays a local checkout inspection and the repository required for repair.
 */
export const LocalCheckoutPreview = ({ inspection, repairRepository, showExistingRegistration = true, content }: LocalCheckoutPreviewProps) => {
  const identity = inspection?.identity;
  const existingRepository = inspection?.existingRepository;
  const hasMismatch = isRepositoryMismatch(inspection, repairRepository);

  return (
    <Stack spacing={2} sx={PREVIEW_STYLE}>
      {repairRepository !== undefined && (
        <Stack spacing={0.5}>
          <Typography variant="subtitle2">{content.expected}</Typography>
          <Typography variant="body2" color="text.secondary">{content.projects}</Typography>
          <List disablePadding aria-label={content.projects}>
            {repairRepository.memberships.map(({ project }) => <ListItem disablePadding key={project.id}><Typography variant="body2">{project.name}</Typography></ListItem>)}
          </List>
          {repairRepository.memberships.length === 0 && <Typography variant="body2">{content.noProjects}</Typography>}
        </Stack>
      )}
      {hasMismatch && <Alert severity="warning">{content.mismatch}</Alert>}
      {inspection !== null && (
        <Stack spacing={0.5}>
          <Typography variant="subtitle2">{content.gitRoot}</Typography>
          <Typography variant="body2">{inspection.canonicalPath}</Typography>
        </Stack>
      )}
      {identity == null && <Typography variant="body2" color="text.secondary">{content.identityRequired}</Typography>}
      {identity != null && (
        <Stack spacing={0.5}>
          <Typography variant="subtitle2">{content.githubRepository}</Typography>
          <Link href={identity.webUrl} target="_blank" rel="noreferrer">{identity.fullName}</Link>
          <Typography variant="body2">{content.branches}</Typography>
        </Stack>
      )}
      {inspection?.dirty && <Typography variant="body2" color="text.secondary">{content.uncommitted}</Typography>}
      {showExistingRegistration && existingRepository != null && (
        <Stack spacing={0.5} role="group" aria-label={content.existing}>
          <Typography variant="subtitle2">{content.existing}</Typography>
          <Typography variant="body2">{existingRepository.fullName}</Typography>
          <Typography variant="body2">{existingRepository.checkoutPath}</Typography>
        </Stack>
      )}
    </Stack>
  );
};
