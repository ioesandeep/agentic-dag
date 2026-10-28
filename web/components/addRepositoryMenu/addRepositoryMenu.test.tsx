import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test } from 'vitest';

import { LABELS } from '@/labels/en';
import { AddRepositoryMenu } from './addRepositoryMenu';
import { AddRepositoryMethodEnum } from './types';

const GITHUB_METHODS = [AddRepositoryMethodEnum.GITHUB];

test('AddRepositoryMenu opens GitHub and restores focus when operated by keyboard', async () => {
  const user = userEvent.setup();
  render(<AddRepositoryMenu methods={GITHUB_METHODS} />);

  const button = screen.getByRole('button', { name: LABELS.repositoryAdd });
  await user.tab();
  await user.keyboard('{Enter}');

  const githubItem = screen.getByRole('menuitem', { name: LABELS.repositoryAddGithub });
  expect(button).toHaveAttribute('aria-expanded', 'true');
  await waitFor(() => expect(githubItem).toHaveFocus());

  await user.keyboard('{Escape}');
  await waitFor(() => expect(button).toHaveFocus());
  await user.keyboard(' {ArrowDown}{Enter}');

  const repositoryInput = screen.getByRole('combobox', { name: LABELS.githubRepository });
  await waitFor(() => expect(repositoryInput).toHaveFocus());
  expect(screen.getByRole('dialog', { name: LABELS.githubCloneTitle })).toBeVisible();

  await user.keyboard('{Escape}');

  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(button).toHaveFocus();
});

test('AddRepositoryMenu excludes GitHub when the page omits that method', async () => {
  const user = userEvent.setup();
  render(<AddRepositoryMenu methods={[]} />);

  await user.click(screen.getByRole('button', { name: LABELS.repositoryAdd }));

  expect(screen.getByRole('menu')).toBeVisible();
  expect(screen.queryByRole('menuitem', { name: LABELS.repositoryAddGithub })).not.toBeInTheDocument();
});
