import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';

import { LABELS } from '@/labels/en';
import { MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { formatLabel } from '@/utils/formatLabel';
import { BranchButton } from './branchButton';

const getRepository = () => {
  const repository = MOCK_REPOSITORIES.find((repository) => repository.id === 'repository-service');
  if (repository === undefined) {
    throw new Error('The repository fixture is missing.');
  }

  return repository;
};

test('BranchButton creates a reusable branch option when the name is valid', async () => {
  const repository = getRepository();
  const user = userEvent.setup();
  const onChange = vi.fn();
  const titleValues = { repository: repository.fullName, branch: 'release/1.0' };
  const title = formatLabel(LABELS.repositoryBranchAction, titleValues);
  render(<BranchButton repository={repository} branch="release/1.0" onChange={onChange} />);

  await user.tab();
  await user.keyboard('{Enter}');

  const branchInput = screen.getByRole('combobox', { name: LABELS.repositoryBranch });
  await user.clear(branchInput);
  await user.type(branchInput, 'feature/review');
  await user.click(screen.getByRole('button', { name: LABELS.repositoryCreateBranch }));

  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(onChange).toHaveBeenCalledExactlyOnceWith('feature/review');
  expect(screen.getByRole('button', { name: title })).toHaveFocus();

  await user.keyboard('{Enter}');
  await user.click(screen.getByRole('button', { name: LABELS.repositoryBranchesOpen }));

  expect(screen.getByRole('option', { name: 'feature/review' })).toBeVisible();
  expect(repository.branches).not.toContain('feature/review');
});

test.each(['', 'feature invalid'])(
  'BranchButton preserves invalid branch input when the name is "%s"',
  async (branch) => {
    const repository = getRepository();
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<BranchButton repository={repository} branch="main" onChange={onChange} />);

    await user.tab();
    await user.keyboard('{Enter}');

    const branchInput = screen.getByRole('combobox', { name: LABELS.repositoryBranch });
    await user.clear(branchInput);
    await user.paste(branch);
    await user.click(screen.getByRole('button', { name: LABELS.repositoryCreateBranch }));

    expect(branchInput).toBeInvalid();
    expect(branchInput).toHaveFocus();
    expect(branchInput).toHaveAccessibleDescription(LABELS.repositoryBranchInvalid);
    expect(onChange).not.toHaveBeenCalled();

    await user.keyboard('{Escape}');

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  },
);
