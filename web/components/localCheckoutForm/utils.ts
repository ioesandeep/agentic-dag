import type { LocalCheckoutPreviewContent } from '@/components/localCheckoutPreview/types';
import type { Repository } from '@/entities/catalog/repository';
import type { RepositoryInspection } from '@/entities/catalog/repositoryInspection';
import { LABELS } from '@/labels/en';
import { formatLabel } from '@/utils/formatLabel';

/**
 * Provides the display text for a local checkout inspection.
 */
export const getLocalCheckoutPreviewContent = (inspection: RepositoryInspection | null, repairRepository?: Repository): LocalCheckoutPreviewContent => {
  const branchValues = { branches: inspection?.branches.join(', ') ?? '' };
  const branches = formatLabel(LABELS.localCheckoutBranches, branchValues);
  const expectedValues = { repository: repairRepository?.fullName ?? '' };
  const expected = formatLabel(LABELS.localCheckoutExpected, expectedValues);

  return {
    gitRoot: LABELS.localCheckoutGitRoot,
    githubRepository: LABELS.localCheckoutGithubRepository,
    identityRequired: LABELS.localCheckoutIdentityRequired,
    branches,
    uncommitted: LABELS.localCheckoutUncommitted,
    existing: LABELS.localCheckoutExisting,
    expected,
    projects: LABELS.repositoryProjects,
    noProjects: LABELS.repositoryNoProjects,
    mismatch: LABELS.localCheckoutMismatch,
  };
};
