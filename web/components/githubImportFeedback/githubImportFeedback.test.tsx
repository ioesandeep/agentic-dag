import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';

import { LABELS } from '@/labels/en';
import { MOCK_GITHUB_ACCOUNT_STATUS } from '@/mocks/catalogMocks';
import { formatLabel } from '@/utils/formatLabel';
import { GithubImportFeedback } from './githubImportFeedback';

test('GithubImportFeedback displays the login and host when GitHub is signed in', () => {
  const accountValues = { login: 'sandeep', host: 'github.com' };
  const signedInLabel = formatLabel(LABELS.githubAccountSignedIn, accountValues);

  render(<GithubImportFeedback accountStatus={MOCK_GITHUB_ACCOUNT_STATUS} />);

  expect(screen.getByText(signedInLabel)).toBeVisible();
  expect(screen.queryByText(LABELS.githubLoginCommand)).not.toBeInTheDocument();
  expect(screen.getByText(LABELS.githubSwitchCommand)).toBeVisible();
});

test('GithubImportFeedback displays host login commands when GitHub is signed out', () => {
  const accountStatus = { ...MOCK_GITHUB_ACCOUNT_STATUS, authenticated: false, login: null };

  render(<GithubImportFeedback accountStatus={accountStatus} />);

  expect(screen.getByRole('alert')).toHaveTextContent(LABELS.githubAccountSignedOut);
  expect(screen.getByText(LABELS.githubLoginInstruction)).toBeVisible();
  expect(screen.getByText(LABELS.githubLoginCommand)).toBeVisible();

  expect(screen.getByText(LABELS.githubSwitchInstruction)).toBeVisible();
  expect(screen.getByText(LABELS.githubSwitchCommand)).toBeVisible();
});
