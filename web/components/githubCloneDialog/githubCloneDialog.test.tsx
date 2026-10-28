import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';

import { LABELS, REPOSITORY_STATUS_LABELS } from '@/labels/en';
import { MOCK_GITHUB_BRANCHES, MOCK_GITHUB_DEFAULT_BRANCH, MOCK_PROJECTS, MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { GithubCloneDialog } from './githubCloneDialog';

const CLONE_COMPLETION_WAIT_MS = 2000;

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

test.each(['api', 'virgo/api', 'https://github.com/virgo/api.git', 'git@github.com:virgo/api.git', 'ssh://git@github.com/virgo/api.git'])(
  'GithubCloneDialog fills an editable clone folder when the repository is %s', async (repositoryInput) => {
    const user = userEvent.setup();
    render(<GithubCloneDialog isOpen onClose={vi.fn()} />);

    await user.type(screen.getByRole('combobox', { name: LABELS.githubRepository }), repositoryInput);
    expect(screen.getByRole('option', { name: 'virgo/api' })).toBeVisible();
    await user.keyboard('{ArrowDown}{Enter}');

    const folderInput = screen.getByRole('textbox', { name: LABELS.githubCloneFolder });
    expect(folderInput).toHaveValue('~/.virgo-dag/repositories/virgo/api');

    await user.clear(folderInput);
    await user.type(folderInput, '/work/virgo/api');

    expect(folderInput).toHaveValue('/work/virgo/api');
  },
);

test.each([true, false])('GithubCloneDialog completes the clone when project context is %s', async (hasProject) => {
  vi.useFakeTimers({ shouldAdvanceTime: true });

  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
  const onClose = vi.fn();
  const project = hasProject ? MOCK_PROJECTS[1] : undefined;
  render(<GithubCloneDialog isOpen onClose={onClose} project={project} />);

  const repositoryInput = screen.getByRole('combobox', { name: LABELS.githubRepository });
  await waitFor(() => expect(repositoryInput).toHaveFocus());
  await user.keyboard('virgo/api');
  await user.tab();

  const folderInput = screen.getByRole('textbox', { name: LABELS.githubCloneFolder });
  expect(folderInput).toHaveFocus();
  await user.keyboard('{End}/checkout');
  expect(folderInput).toHaveValue('~/.virgo-dag/repositories/virgo/api/checkout');

  await user.tab();
  expect(screen.getByRole('button', { name: LABELS.githubFolderBrowse })).toHaveFocus();

  await user.tab();
  await user.tab();
  await user.keyboard('{Enter}');

  expect(screen.getByRole('progressbar', { name: LABELS.githubCloneProgress })).toBeVisible();
  expect(screen.getByRole('button', { name: LABELS.githubCloning })).toBeDisabled();
  expect(screen.queryByRole('combobox', { name: LABELS.repositoryBranch })).not.toBeInTheDocument();
  act(() => vi.advanceTimersByTime(CLONE_COMPLETION_WAIT_MS));

  const footer = screen.getByRole('group', { name: LABELS.githubCloneFooter });
  expect(within(footer).getByRole('status')).toHaveTextContent(LABELS.githubCloneComplete);
  expect(within(footer).getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');

  if (hasProject) {
    const branchInput = screen.getByRole('combobox', { name: LABELS.repositoryBranch });
    expect(branchInput).toHaveFocus();
    expect(branchInput).toHaveTextContent(MOCK_GITHUB_DEFAULT_BRANCH);
    await user.keyboard('{Enter}');

    expect(screen.getAllByRole('option')).toHaveLength(MOCK_GITHUB_BRANCHES.length + 1);
    await user.keyboard('{End}{ArrowUp}{Enter}');
    expect(branchInput).toHaveTextContent('release/1.0');

    await user.tab();
    await user.tab();
  } else {
    expect(screen.queryByRole('combobox', { name: LABELS.repositoryBranch })).not.toBeInTheDocument();
  }

  expect(screen.getByRole('button', { name: LABELS.githubDone })).toHaveFocus();
  await user.keyboard('{Enter}');

  expect(onClose).toHaveBeenCalledOnce();
  expect(MOCK_REPOSITORIES.some((repository) => repository.fullName === 'virgo/api')).toBe(false);
});

test('GithubCloneDialog completes the clone when the dialog closes during progress', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });

  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
  const onClose = vi.fn();
  const { rerender } = render(<GithubCloneDialog isOpen onClose={onClose} />);

  await user.type(screen.getByRole('combobox', { name: LABELS.githubRepository }), 'virgo/api');
  await user.click(screen.getByRole('button', { name: LABELS.githubClone }));
  await user.click(screen.getByRole('button', { name: LABELS.githubCloneClose }));

  expect(onClose).toHaveBeenCalledOnce();
  rerender(<GithubCloneDialog isOpen={false} onClose={onClose} />);
  act(() => vi.advanceTimersByTime(CLONE_COMPLETION_WAIT_MS));
  rerender(<GithubCloneDialog isOpen onClose={onClose} />);

  expect(screen.getByRole('status')).toHaveTextContent(LABELS.githubCloneComplete);
  expect(screen.getByRole('button', { name: LABELS.githubDone })).toBeEnabled();
});

test.each([true, false])('GithubCloneDialog offers an existing registration when project context is %s', async (hasProject) => {
  const repository = MOCK_REPOSITORIES[0];
  if (repository === undefined) {
    throw new Error('The service repository fixture is missing.');
  }

  const user = userEvent.setup();
  const onClose = vi.fn();
  const project = hasProject ? MOCK_PROJECTS[1] : undefined;
  render(<GithubCloneDialog isOpen onClose={onClose} project={project} />);

  await user.type(screen.getByRole('combobox', { name: LABELS.githubRepository }), 'git@github.com:VIRGO/service.git');

  expect(screen.getByRole('textbox', { name: LABELS.githubCloneFolder })).toHaveValue(repository.checkoutPath);

  const footer = screen.getByRole('group', { name: LABELS.githubCloneFooter });
  expect(within(footer).getByRole('status')).toHaveTextContent(REPOSITORY_STATUS_LABELS[repository.presentationStatus]);
  expect(screen.queryByRole('button', { name: LABELS.githubClone })).not.toBeInTheDocument();
  expect(screen.queryByRole('combobox', { name: LABELS.repositoryBranch }) !== null).toBe(hasProject);

  await user.click(screen.getByRole('button', { name: LABELS.githubAddExisting }));

  expect(onClose).toHaveBeenCalledOnce();
  expect(repository.memberships).toHaveLength(2);
});

test('GithubCloneDialog focuses invalid input when a required value is missing', async () => {
  const user = userEvent.setup();
  render(<GithubCloneDialog isOpen onClose={vi.fn()} />);

  await user.click(screen.getByRole('button', { name: LABELS.githubClone }));
  expect(screen.getByText(LABELS.githubCloneRequired)).toBeVisible();

  const repositoryInput = screen.getByRole('combobox', { name: LABELS.githubRepository });
  expect(repositoryInput).toBeInvalid();
  expect(repositoryInput).toHaveFocus();
  expect(repositoryInput).toHaveAccessibleDescription(LABELS.githubRepositoryInvalid);

  await user.type(repositoryInput, 'virgo/api');

  const folderInput = screen.getByRole('textbox', { name: LABELS.githubCloneFolder });
  await user.clear(folderInput);
  await user.click(screen.getByRole('button', { name: LABELS.githubClone }));

  await waitFor(() => expect(folderInput).toHaveFocus());
  expect(folderInput).toBeInvalid();
  expect(folderInput).toHaveAccessibleDescription(LABELS.githubCloneFolderRequired);
});

test('GithubCloneDialog limits repository suggestions when the catalog exceeds ten names', async () => {
  const user = userEvent.setup();
  render(<GithubCloneDialog isOpen onClose={vi.fn()} />);

  const repositoryInput = screen.getByRole('combobox', { name: LABELS.githubRepository });
  await waitFor(() => expect(repositoryInput).toHaveFocus());
  await user.keyboard('{ArrowDown}');

  expect(repositoryInput).toHaveAttribute('aria-expanded', 'true');
  expect(screen.getAllByRole('option')).toHaveLength(10);
  expect(screen.queryByRole('option', { name: 'virgo/infra' })).not.toBeInTheDocument();

  await user.keyboard('infra{ArrowDown}{Enter}');

  expect(repositoryInput).toHaveValue('virgo/infra');
  expect(repositoryInput).toHaveAttribute('aria-expanded', 'false');
  expect(screen.getByRole('textbox', { name: LABELS.githubCloneFolder })).toHaveValue('~/.virgo-dag/repositories/virgo/infra');
});

test('GithubCloneDialog validates a new branch when Add new branch is selected', async () => {
  const user = userEvent.setup();
  const onClose = vi.fn();
  render(<GithubCloneDialog isOpen onClose={onClose} project={MOCK_PROJECTS[1]} />);

  await user.type(screen.getByRole('combobox', { name: LABELS.githubRepository }), 'virgo/service');
  await user.keyboard('{Escape}');
  await user.click(screen.getByRole('combobox', { name: LABELS.repositoryBranch }));
  await user.click(screen.getByRole('option', { name: LABELS.repositoryAddBranch }));

  const branchInput = screen.getByRole('textbox', { name: LABELS.repositoryNewBranch });
  await waitFor(() => expect(branchInput).toHaveFocus());
  await user.keyboard('feature invalid{Enter}');

  expect(branchInput).toBeInvalid();
  expect(branchInput).toHaveAccessibleDescription(LABELS.repositoryBranchInvalid);
  expect(branchInput).toHaveFocus();
  expect(onClose).not.toHaveBeenCalled();

  await user.clear(branchInput);
  await user.keyboard('feature/review{Enter}');

  expect(onClose).toHaveBeenCalledOnce();
  expect(MOCK_GITHUB_BRANCHES).not.toContain('feature/review');
});

test('GithubCloneDialog resets branch creation when a different repository is pasted', async () => {
  const user = userEvent.setup();
  render(<GithubCloneDialog isOpen onClose={vi.fn()} project={MOCK_PROJECTS[1]} />);

  const repositoryInput = screen.getByRole('combobox', { name: LABELS.githubRepository });
  await user.type(repositoryInput, 'virgo/service');
  await user.keyboard('{Escape}');

  await user.click(screen.getByRole('combobox', { name: LABELS.repositoryBranch }));
  await user.click(screen.getByRole('option', { name: LABELS.repositoryAddBranch }));

  const branchInput = screen.getByRole('textbox', { name: LABELS.repositoryNewBranch });
  await user.type(branchInput, 'feature/review');
  await user.tripleClick(repositoryInput);
  await user.paste('virgo/console');

  expect(repositoryInput).toHaveValue('virgo/console');
  expect(screen.queryByRole('textbox', { name: LABELS.repositoryNewBranch })).not.toBeInTheDocument();
  expect(screen.getByRole('combobox', { name: LABELS.repositoryBranch })).toHaveTextContent('main (default)');
});
