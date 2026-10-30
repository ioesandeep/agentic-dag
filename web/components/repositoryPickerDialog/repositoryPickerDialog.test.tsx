import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';

import { AddRepositoryActionButton } from '@/components/addRepositoryActionButton/addRepositoryActionButton';
import { LABELS } from '@/labels/en';
import { MOCK_PROJECTS, MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { formatLabel } from '@/utils/formatLabel';
import { RepositoryPickerDialog } from './repositoryPickerDialog';

const [DEFAULT_PROJECT, PLATFORM_PROJECT, RESEARCH_PROJECT] = MOCK_PROJECTS;
if (DEFAULT_PROJECT === undefined || PLATFORM_PROJECT === undefined || RESEARCH_PROJECT === undefined) {
  throw new Error('The project fixtures are missing.');
}

afterEach(cleanup);

test('RepositoryPickerDialog disables project members when the catalog lists active repositories', () => {
  const branchValues = { repository: 'virgo/console', branch: 'develop' };
  const branchLabel = formatLabel(LABELS.repositoryBranchAction, branchValues);
  render(<RepositoryPickerDialog isOpen onClose={vi.fn()} project={PLATFORM_PROJECT} />);

  expect(screen.getAllByRole('checkbox')).toHaveLength(5);
  expect(screen.queryByRole('checkbox', { name: 'virgo/legacy' })).not.toBeInTheDocument();

  expect(screen.getByRole('checkbox', { name: 'virgo/service' })).toBeDisabled();
  expect(screen.getByRole('checkbox', { name: 'virgo/console' })).toBeDisabled();
  expect(screen.getByRole('checkbox', { name: 'virgo/tools' })).toBeDisabled();
  expect(screen.getByRole('button', { name: branchLabel })).toBeDisabled();

  expect(screen.getAllByText(LABELS.repositoryAlreadyInProject)).toHaveLength(3);
  expect(screen.getByRole('button', { name: LABELS.projectRepositoryAdd })).toBeDisabled();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
});

test('RepositoryPickerDialog closes without changing catalog records when multiple repositories are selected by keyboard', async () => {
  const user = userEvent.setup();
  const repositoryReferences = [...MOCK_REPOSITORIES];
  const membershipCounts = MOCK_REPOSITORIES.map((repository) => repository.memberships.length);

  const projectRepositoryCount = PLATFORM_PROJECT.repositoryCounts.total;
  render(<AddRepositoryActionButton project={PLATFORM_PROJECT} />);

  await user.tab();
  await user.keyboard('{Enter}');

  const menuItem = screen.getByRole('menuitem', { name: LABELS.repositoryAddFromList });
  await user.keyboard('{ArrowDown}');
  await waitFor(() => expect(menuItem).toHaveFocus());
  await user.keyboard('{Enter}');

  const workerCheckbox = screen.getByRole('checkbox', { name: 'virgo/worker' });
  await waitFor(() => expect(workerCheckbox).toHaveFocus());
  await user.keyboard(' {Tab}{Tab} ');

  expect(workerCheckbox).toBeChecked();
  expect(screen.getByRole('checkbox', { name: 'virgo/connector' })).toBeChecked();

  await user.keyboard(' {Shift>}{Tab}{Tab}{/Shift} ');
  expect(screen.getByRole('button', { name: LABELS.projectRepositoryAdd })).toBeDisabled();

  await user.keyboard(' {Tab}{Tab} ');
  await user.keyboard('{Tab}{Tab}{Tab}');
  expect(screen.getByRole('button', { name: LABELS.projectRepositoryAdd })).toHaveFocus();
  await user.keyboard('{Enter}');

  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(screen.getByRole('button', { name: LABELS.repositoryAdd })).toHaveFocus();

  expect(MOCK_REPOSITORIES.every((repository, index) => repository === repositoryReferences[index])).toBe(true);
  expect(MOCK_REPOSITORIES.map((repository) => repository.memberships.length)).toEqual(membershipCounts);
  expect(PLATFORM_PROJECT.repositoryCounts.total).toBe(projectRepositoryCount);
});

test('RepositoryPickerDialog preserves each branch when another repository branch changes', async () => {
  const user = userEvent.setup();
  const workerValues = { repository: 'virgo/worker', branch: 'main' };
  const consoleValues = { repository: 'virgo/console', branch: 'main' };

  const workerLabel = formatLabel(LABELS.repositoryBranchAction, workerValues);
  const consoleLabel = formatLabel(LABELS.repositoryBranchAction, consoleValues);
  const onClose = vi.fn();
  render(<RepositoryPickerDialog isOpen onClose={onClose} project={RESEARCH_PROJECT} />);

  await user.click(screen.getByRole('checkbox', { name: 'virgo/worker' }));
  await user.click(screen.getByRole('checkbox', { name: 'virgo/console' }));
  await user.click(screen.getByRole('button', { name: workerLabel }));

  const branchInput = screen.getByRole('combobox', { name: LABELS.repositoryBranch });
  expect(branchInput).toHaveValue('main');
  await user.click(screen.getByRole('button', { name: LABELS.repositoryBranchesOpen }));
  await user.click(screen.getByRole('option', { name: 'develop' }));

  await user.click(screen.getByRole('button', { name: LABELS.repositoryUseBranch }));
  await user.click(screen.getByRole('button', { name: consoleLabel }));

  const newBranchInput = screen.getByRole('combobox', { name: LABELS.repositoryBranch });
  expect(newBranchInput).toHaveValue('main');
  await user.clear(newBranchInput);
  await user.type(newBranchInput, 'invalid branch');

  await user.click(screen.getByRole('button', { name: LABELS.repositoryCreateBranch }));
  expect(newBranchInput).toBeInvalid();
  expect(onClose).not.toHaveBeenCalled();

  await user.clear(newBranchInput);
  await user.type(newBranchInput, 'feature/catalog');
  await user.click(screen.getByRole('button', { name: LABELS.repositoryCreateBranch }));

  const changedWorkerValues = { ...workerValues, branch: 'develop' };
  const changedConsoleValues = { ...consoleValues, branch: 'feature/catalog' };
  expect(screen.getByRole('button', { name: formatLabel(LABELS.repositoryBranchAction, changedWorkerValues) })).toBeVisible();
  expect(screen.getByRole('button', { name: formatLabel(LABELS.repositoryBranchAction, changedConsoleValues) })).toBeVisible();

  expect(screen.getByRole('checkbox', { name: 'virgo/worker' })).toBeChecked();
  expect(screen.getByRole('checkbox', { name: 'virgo/console' })).toBeChecked();
  expect(onClose).not.toHaveBeenCalled();
});

test('RepositoryPickerDialog lists every repository when the catalog exceeds five records', async () => {
  const repository = MOCK_REPOSITORIES[0];
  if (repository === undefined) {
    throw new Error('The service repository fixture is missing.');
  }

  const repositories = Array.from({ length: 12 }, (_, index) => ({ ...repository, id: `repository-${index}`, fullName: `virgo/service-${index}`, memberships: [] }));
  const user = userEvent.setup();
  render(<RepositoryPickerDialog isOpen onClose={vi.fn()} project={RESEARCH_PROJECT} repositories={repositories} />);

  await user.click(screen.getByRole('checkbox', { name: 'virgo/service-11' }));

  expect(screen.getAllByRole('checkbox')).toHaveLength(12);
  expect(screen.getByRole('checkbox', { name: 'virgo/service-11' })).toBeChecked();
});

test('RepositoryPickerDialog shows an empty message when the catalog has no active repositories', () => {
  const archivedRepositories = MOCK_REPOSITORIES.filter((repository) => repository.archivedAt !== null);
  render(<RepositoryPickerDialog isOpen onClose={vi.fn()} project={DEFAULT_PROJECT} repositories={archivedRepositories} />);

  expect(screen.getByText(LABELS.repositoryPickerEmpty)).toBeVisible();
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: LABELS.projectRepositoryAdd })).toBeDisabled();
  expect(screen.getByRole('button', { name: LABELS.repositoryActionCancel })).toHaveFocus();
});
