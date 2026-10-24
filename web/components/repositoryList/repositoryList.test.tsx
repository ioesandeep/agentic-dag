import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';

import type { ProjectSummary } from '@/entities/catalog/project';
import { CheckoutKindEnum } from '@/entities/catalog/repository';
import type { Repository } from '@/entities/catalog/repository';
import { ImportStatusEnum } from '@/entities/catalog/repositoryImport';
import { LABELS } from '@/labels/en';
import { MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { RUNNING_WORKER_IMPORT } from '@/mocks/catalogRepositoryImports';
import { theme } from '@/theme/theme';
import { formatLabel } from '@/utils/formatLabel';
import { RepositoryList } from './repositoryList';
import { RepositoryListVariantEnum } from './types';

const createRepository = (overrides: Partial<Repository> = {}): Repository => {
  const [repository] = MOCK_REPOSITORIES;
  if (repository === undefined) {
    throw new Error('The repository fixture is missing.');
  }

  return { ...repository, ...overrides };
};

test('RepositoryList displays each project branch when the variant is global', () => {
  const repositories = MOCK_REPOSITORIES;
  const branchValues = { branch: 'main' };
  const dateValues = { date: 'Oct 1, 2026' };

  render(
    <RepositoryList
      variant={RepositoryListVariantEnum.GLOBAL}
      repositories={repositories}
      onOpenDetails={vi.fn()}
      onRetryClone={vi.fn()}
    />,
  );

  for (const repository of repositories) {
    const repositoryItem = screen.getByRole('listitem', { name: repository.fullName });
    const repositoryContent = within(repositoryItem);
    expect(repositoryContent.getByText(repository.checkoutPath)).toBeVisible();

    expect(repositoryContent.getByRole('link', { name: repository.fullName })).toHaveAttribute(
      'href',
      repository.webUrl,
    );

    for (const { project, branch } of repository.memberships) {
      const branchValues = { project: project.name, branch };
      expect(
        repositoryContent.getByText(formatLabel(LABELS.repositoryProjectBranch, branchValues)),
      ).toBeVisible();
    }
  }

  expect(screen.queryByText(/Cloned by/)).not.toBeInTheDocument();
  expect(screen.getAllByText(LABELS.repositoryExternal)).toHaveLength(2);

  expect(
    screen.getAllByText(formatLabel(LABELS.repositoryDefaultBranch, branchValues)),
  ).toHaveLength(6);

  expect(screen.getAllByText(formatLabel(LABELS.repositoryClonedDate, dateValues))).toHaveLength(2);
  expect(screen.queryByText(/Clone date unavailable/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Used in projects|Cloned folder/)).not.toBeInTheDocument();
  expect(
    screen.queryByRole('button', { name: LABELS.repositoryChangeBranch }),
  ).not.toBeInTheDocument();

  expect(
    screen.queryByRole('button', { name: LABELS.repositoryRemoveFromProject }),
  ).not.toBeInTheDocument();
});

test.each([null, '2026-10-15T12:00:00Z'])(
  'RepositoryList offers project actions only when archivedAt is %s',
  async (archivedAt) => {
    const project: ProjectSummary = {
      id: 'project-platform',
      name: 'Platform',
      isDefault: false,
      archivedAt,
    };

    const repository = createRepository();
    const repositories = [repository];
    const onOpenDetails = vi.fn();
    const onChangeBranch = vi.fn();
    const onRemoveFromProject = vi.fn();
    const user = userEvent.setup();
    const branchValues = { project: project.name, branch: 'release/1.0' };

    render(
      <RepositoryList
        variant={RepositoryListVariantEnum.PROJECT}
        project={project}
        repositories={repositories}
        onOpenDetails={onOpenDetails}
        onRetryClone={vi.fn()}
        onChangeBranch={onChangeBranch}
        onRemoveFromProject={onRemoveFromProject}
      />,
    );

    expect(
      screen.getByText(formatLabel(LABELS.repositoryProjectBranch, branchValues)),
    ).toBeVisible();

    if (archivedAt !== null) {
      expect(
        screen.queryByRole('button', { name: LABELS.repositoryChangeBranch }),
      ).not.toBeInTheDocument();

      expect(
        screen.queryByRole('button', { name: LABELS.repositoryRemoveFromProject }),
      ).not.toBeInTheDocument();

      return;
    }

    await user.tab();
    await user.tab();
    await user.keyboard('{Enter}');
    await user.tab();
    await user.keyboard(' ');
    await user.tab();
    await user.keyboard('{Enter}');

    expect(onOpenDetails).toHaveBeenCalledWith(repository);
    expect(onChangeBranch).toHaveBeenCalledWith(repository);
    expect(onRemoveFromProject).toHaveBeenCalledWith(repository);
  },
);

test('RepositoryList preserves project colors when membership positions differ', () => {
  render(
    <RepositoryList
      variant={RepositoryListVariantEnum.GLOBAL}
      repositories={MOCK_REPOSITORIES}
      onOpenDetails={vi.fn()}
      onRetryClone={vi.fn()}
    />,
  );

  const serviceBranchValues = { project: 'Platform', branch: 'release/1.0' };
  const consoleBranchValues = { project: 'Platform', branch: 'develop' };
  const defaultBranchValues = { project: 'Default', branch: 'main' };

  const serviceSegment = screen.getByRole('img', {
    name: formatLabel(LABELS.repositoryProjectBranch, serviceBranchValues),
  });

  const consoleSegment = screen.getByRole('img', {
    name: formatLabel(LABELS.repositoryProjectBranch, consoleBranchValues),
  });

  const [defaultSegment] = screen.getAllByRole('img', {
    name: formatLabel(LABELS.repositoryProjectBranch, defaultBranchValues),
  });

  const serviceColor = getComputedStyle(serviceSegment).backgroundColor;
  const consoleColor = getComputedStyle(consoleSegment).backgroundColor;
  const defaultColor = defaultSegment && getComputedStyle(defaultSegment).backgroundColor;

  expect(serviceColor).toBe(consoleColor);
  expect(serviceColor).not.toBe(defaultColor);
});

test('RepositoryList displays an empty project bar when a repository has no projects', () => {
  const repository = createRepository({ memberships: [] });
  const repositories = [repository];

  render(
    <RepositoryList
      variant={RepositoryListVariantEnum.GLOBAL}
      repositories={repositories}
      onOpenDetails={vi.fn()}
      onRetryClone={vi.fn()}
    />,
  );

  const projectBar = screen.getByRole('group', { name: LABELS.repositoryProjects });
  const projectSegments = within(projectBar).queryAllByRole('img');

  expect(projectBar).toHaveStyle({ backgroundColor: theme.palette.grey[500] });
  expect(projectSegments).toHaveLength(0);
  expect(screen.getByText(LABELS.repositoryNoProjects)).toBeVisible();
  expect(screen.getByText(repository.checkoutPath)).toBeVisible();
});

test.each([
  { checkoutKind: CheckoutKindEnum.MANAGED, status: ImportStatusEnum.FAILED, canRetry: true },
  { checkoutKind: CheckoutKindEnum.MANAGED, status: ImportStatusEnum.CANCELLED, canRetry: true },
  { checkoutKind: CheckoutKindEnum.MANAGED, status: ImportStatusEnum.INTERRUPTED, canRetry: true },
  { checkoutKind: CheckoutKindEnum.MANAGED, status: ImportStatusEnum.RUNNING, canRetry: false },
  { checkoutKind: CheckoutKindEnum.MANAGED, status: ImportStatusEnum.QUEUED, canRetry: false },
  { checkoutKind: CheckoutKindEnum.MANAGED, status: ImportStatusEnum.SUCCEEDED, canRetry: false },
  { checkoutKind: CheckoutKindEnum.MANAGED, status: null, canRetry: false },
  { checkoutKind: CheckoutKindEnum.EXTERNAL, status: ImportStatusEnum.FAILED, canRetry: false },
])(
  'RepositoryList offers retry for $checkoutKind clones when the latest attempt is $status',
  async ({ checkoutKind, status, canRetry }) => {
    const latestImport = status === null ? null : { ...RUNNING_WORKER_IMPORT, status };
    const repository = createRepository({ checkoutKind, latestImport });
    const repositories = [repository];
    const onRetryClone = vi.fn();
    const user = userEvent.setup();

    render(
      <RepositoryList
        variant={RepositoryListVariantEnum.GLOBAL}
        repositories={repositories}
        onOpenDetails={vi.fn()}
        onRetryClone={onRetryClone}
      />,
    );

    if (!canRetry) {
      expect(
        screen.queryByRole('button', { name: LABELS.repositoryRetryClone }),
      ).not.toBeInTheDocument();

      return;
    }

    await user.tab();
    await user.tab();
    await user.tab();
    await user.keyboard('{Enter}');

    expect(onRetryClone).toHaveBeenCalledWith(repository);
  },
);

test('RepositoryList displays the empty state when there are no repositories', () => {
  render(
    <RepositoryList
      variant={RepositoryListVariantEnum.GLOBAL}
      repositories={[]}
      onOpenDetails={vi.fn()}
      onRetryClone={vi.fn()}
    />,
  );

  expect(screen.getByText(LABELS.repositoriesEmpty)).toBeVisible();
  expect(screen.getByText(LABELS.repositoriesEmptyHint)).toBeVisible();
  expect(screen.queryByRole('list')).not.toBeInTheDocument();
});
