import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';

import { RepositoryDetailsScreen } from '@/components/repositoryDetailsScreen/repositoryDetailsScreen';
import {
  LABELS,
  REPOSITORY_DETAILS_ACTION_LABELS,
  REPOSITORY_STATUS_LABELS,
} from '@/labels/en';
import { MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { formatCatalogTime } from '@/utils/formatCatalogTime';
import { RepositoryDetails } from './repositoryDetails';

const [READY_REPOSITORY] = MOCK_REPOSITORIES;
if (READY_REPOSITORY === undefined) {
  throw new Error('The ready repository fixture is missing.');
}

test.each<[string, string[]]>([
  ['repository-service', [LABELS.repositoryCheck]],
  [
    'repository-connector',
    [LABELS.repositoryCheck, LABELS.repositoryRetryClone],
  ],
  ['repository-tools', [LABELS.repositoryCheck, LABELS.localCheckoutRepair]],
  ['repository-worker', [LABELS.repositoryCancelClone]],
  ['repository-legacy', [LABELS.repositoryCheck]],
])(
  'RepositoryDetails displays applicable actions when the repository is %s',
  (repositoryId, expectedActions) => {
    const repository = MOCK_REPOSITORIES.find(
      (repository) => repository.id === repositoryId,
    );

    if (repository === undefined) {
      throw new Error('The repository fixture is missing.');
    }

    render(
      <RepositoryDetails
        repository={repository}
        onAction={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    const status = screen.getByRole('status');
    const details = screen.getByRole('region', {
      name: LABELS.repositoryDetails,
    });

    const detailQueries = within(details);
    expect(status).toHaveTextContent(
      REPOSITORY_STATUS_LABELS[repository.presentationStatus],
    );

    for (const label of Object.values(REPOSITORY_DETAILS_ACTION_LABELS)) {
      const action = detailQueries.queryByRole('button', { name: label });
      const isExpectedAction = expectedActions.includes(label);
      if (isExpectedAction) {
        expect(action).toBeEnabled();
      } else {
        expect(action).not.toBeInTheDocument();
      }
    }

    const progress = detailQueries.queryByRole('progressbar');
    const isCloning = repositoryId === 'repository-worker';
    if (isCloning) {
      expect(progress).toBeVisible();
    } else {
      expect(progress).not.toBeInTheDocument();
    }
  },
);

test('RepositoryDetails displays metadata and project branches when a ready clone has two memberships', () => {
  render(
    <RepositoryDetails
      repository={READY_REPOSITORY}
      onAction={vi.fn()}
      onRemove={vi.fn()}
    />,
  );

  const repositoryLink = screen.getByRole('link', {
    name: READY_REPOSITORY.fullName,
  });

  const fields = screen.getAllByRole('term');
  const folder = screen.getByText(READY_REPOSITORY.checkoutPath);
  expect(repositoryLink).toHaveAttribute('href', READY_REPOSITORY.webUrl);

  expect(fields).toHaveLength(5);
  expect(folder).toBeVisible();

  const remote = screen.getByText(READY_REPOSITORY.remoteName);
  const clonedAt = formatCatalogTime(
    READY_REPOSITORY.latestImport?.finishedAt ?? null,
  );

  const clonedDate = screen.getByText(clonedAt);
  expect(remote).toBeVisible();

  const headings = screen.getAllByRole('heading', { level: 2 });
  expect(clonedDate).toBeVisible();
  expect(headings).toHaveLength(2);

  const projects = screen.getByRole('list', {
    name: LABELS.repositoryProjects,
  });

  const projectQueries = within(projects);
  const projectRows = projectQueries.getAllByRole('listitem');
  expect(projectRows).toHaveLength(2);

  const defaultProjectLink = projectQueries.getByRole('link', {
    name: 'Default',
  });

  const platformProjectLink = projectQueries.getByRole('link', {
    name: 'Platform',
  });

  expect(defaultProjectLink).toHaveAttribute(
    'href',
    '/projects/project-default',
  );

  expect(platformProjectLink).toHaveAttribute(
    'href',
    '/projects/project-platform',
  );

  const defaultBranch = projectQueries.getByRole('button', {
    name: /current branch main/,
  });

  const platformBranch = projectQueries.getByRole('button', {
    name: /current branch release\/1.0/,
  });

  expect(defaultBranch).toBeVisible();
  expect(platformBranch).toBeVisible();

  const removeButtons = projectQueries.getAllByRole('button', {
    name: LABELS.repositoryRemoveFromProject,
  });

  expect(removeButtons).toHaveLength(2);
});

test('RepositoryDetails displays empty repository metadata when GitHub has no default branch', () => {
  const repository = {
    ...READY_REPOSITORY,
    defaultBranch: null,
    memberships: [],
    latestImport: null,
  };

  render(
    <RepositoryDetails
      repository={repository}
      onAction={vi.fn()}
      onRemove={vi.fn()}
    />,
  );

  const emptyRepository = screen.getByText(LABELS.repositoryEmpty);
  const noProjects = screen.getByText(LABELS.repositoryNoProjects);
  const noCloneDate = screen.getByText(LABELS.repositoryTimeUnavailable);
  expect(emptyRepository).toBeVisible();

  expect(noProjects).toBeVisible();
  expect(noCloneDate).toBeVisible();
});

test('RepositoryDetailsScreen preserves mock data when Check or Retry is activated by keyboard', async () => {
  const user = userEvent.setup();
  const repositorySnapshot = structuredClone(MOCK_REPOSITORIES);
  render(<RepositoryDetailsScreen repositoryId="repository-connector" />);

  const checkButton = screen.getByRole('button', {
    name: LABELS.repositoryCheck,
  });

  checkButton.focus();
  await user.keyboard('{Enter}{Tab}{Enter}');

  const status = screen.getByRole('status');
  const dialog = screen.queryByRole('dialog');
  expect(status).toHaveTextContent(REPOSITORY_STATUS_LABELS.failed);
  expect(MOCK_REPOSITORIES).toEqual(repositorySnapshot);
  expect(dialog).not.toBeInTheDocument();
});
