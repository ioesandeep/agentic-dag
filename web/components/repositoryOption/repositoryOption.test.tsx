import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';

import { LABELS } from '@/labels/en';
import { MOCK_REPOSITORIES } from '@/mocks/catalogMocks';
import { RepositoryOption } from './repositoryOption';

const [REPOSITORY] = MOCK_REPOSITORIES;
if (REPOSITORY === undefined) {
  throw new Error('The service repository fixture is missing.');
}

afterEach(cleanup);

test('RepositoryOption changes selection when Space is pressed', async () => {
  const user = userEvent.setup();
  const onSelectionChange = vi.fn();
  render(<RepositoryOption repository={REPOSITORY} branch="main" isSelected={false} onSelectionChange={onSelectionChange} onBranchChange={vi.fn()} autoFocus />);

  await user.keyboard(' ');

  expect(onSelectionChange).toHaveBeenCalledExactlyOnceWith(true);
  expect(screen.getByText(REPOSITORY.checkoutPath)).toBeVisible();
  expect(screen.getByRole('checkbox', { name: REPOSITORY.fullName })).toHaveFocus();
});

test('RepositoryOption disables selection when disabledReason is defined', () => {
  render(<RepositoryOption repository={REPOSITORY} branch="main" isSelected={false} onSelectionChange={vi.fn()} onBranchChange={vi.fn()} disabledReason={LABELS.repositoryAlreadyInProject} />);

  const checkbox = screen.getByRole('checkbox', { name: REPOSITORY.fullName });
  expect(checkbox).toBeDisabled();
  expect(checkbox).toHaveAccessibleDescription(expect.stringContaining(LABELS.repositoryAlreadyInProject));
});
