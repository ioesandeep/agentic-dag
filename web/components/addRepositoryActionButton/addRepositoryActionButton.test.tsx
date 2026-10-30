import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test } from 'vitest';

import { LABELS } from '@/labels/en';
import { MOCK_PROJECTS } from '@/mocks/catalogMocks';
import { AddRepositoryActionButton } from './addRepositoryActionButton';

const [PROJECT] = MOCK_PROJECTS;
if (PROJECT === undefined) {
  throw new Error('The project fixture is missing.');
}

test('AddRepositoryActionButton opens GitHub and restores focus when operated by keyboard', async () => {
  const user = userEvent.setup();
  render(<AddRepositoryActionButton project={PROJECT} />);

  const button = screen.getByRole('button', { name: LABELS.repositoryAdd });
  await user.tab();
  await user.keyboard('{Enter}');

  const githubItem = screen.getByRole('menuitem', { name: LABELS.repositoryAddGithub });
  expect(button).toHaveAttribute('aria-expanded', 'true');
  await waitFor(() => expect(githubItem).toHaveFocus());

  await user.keyboard('{Escape}');
  await waitFor(() => expect(button).toHaveFocus());
  await user.keyboard(' {Enter}');

  const repositoryInput = screen.getByRole('combobox', { name: LABELS.githubRepository });
  await waitFor(() => expect(repositoryInput).toHaveFocus());
  expect(screen.getByRole('dialog', { name: LABELS.githubCloneTitle })).toBeVisible();

  await user.keyboard('{Escape}');

  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(button).toHaveFocus();
});

test('AddRepositoryActionButton disables repository actions when isDisabled is true', () => {
  render(<AddRepositoryActionButton project={PROJECT} isDisabled />);

  expect(screen.getByRole('button', { name: LABELS.repositoryAdd })).toBeDisabled();
  expect(screen.queryByRole('menu')).not.toBeInTheDocument();
});
