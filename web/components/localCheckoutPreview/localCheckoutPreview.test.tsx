import { render, screen, within } from '@testing-library/react';
import { expect, test } from 'vitest';

import { getLocalCheckoutPreviewContent } from '@/components/localCheckoutForm/utils';
import { LABELS } from '@/labels/en';
import { MOCK_REPOSITORIES, MOCK_REPOSITORY_INSPECTION } from '@/mocks/catalogMocks';
import { LocalCheckoutPreview } from './localCheckoutPreview';

test('LocalCheckoutPreview displays identity guidance when the inspection has no identity', () => {
  const inspection = { ...MOCK_REPOSITORY_INSPECTION, identity: null, existingRepository: null };
  const content = getLocalCheckoutPreviewContent(inspection);

  render(<LocalCheckoutPreview inspection={inspection} content={content} />);

  const gitRoot = screen.getByText(inspection.canonicalPath);
  const guidance = screen.getByText(content.identityRequired);
  const repositoryLink = screen.queryByRole('link');
  expect(gitRoot).toBeVisible();

  expect(guidance).toBeVisible();
  expect(repositoryLink).not.toBeInTheDocument();
});

test('LocalCheckoutPreview displays observations when the folder has changes and an existing registration', () => {
  const inspection = MOCK_REPOSITORY_INSPECTION;
  const content = getLocalCheckoutPreviewContent(inspection);

  render(<LocalCheckoutPreview inspection={inspection} content={content} />);

  const repositoryLink = screen.getByRole('link', { name: 'virgo/console' });
  const observation = screen.getByText(content.uncommitted);
  const alert = screen.queryByRole('alert');
  expect(repositoryLink).toHaveAttribute('href', 'https://github.com/virgo/console');

  expect(observation).toBeVisible();
  expect(alert).not.toBeInTheDocument();

  const existingRegistration = screen.getByRole('group', { name: content.existing });
  const registrationQueries = within(existingRegistration);
  const name = registrationQueries.getByText('virgo/console');
  const folder = registrationQueries.getByText('/Users/sandeep/work/console');

  expect(name).toBeVisible();
  expect(folder).toBeVisible();
});

test('LocalCheckoutPreview warns about a mismatch when repair expects a different repository', () => {
  const repairRepository = MOCK_REPOSITORIES[0];
  const content = getLocalCheckoutPreviewContent(MOCK_REPOSITORY_INSPECTION, repairRepository);

  render(<LocalCheckoutPreview inspection={MOCK_REPOSITORY_INSPECTION} repairRepository={repairRepository} content={content} />);

  const expectedRepository = screen.getByText(content.expected);
  const defaultProject = screen.getByText('Default');
  const platformProject = screen.getByText('Platform');
  expect(expectedRepository).toBeVisible();

  expect(defaultProject).toBeVisible();
  expect(platformProject).toBeVisible();

  const projectList = screen.getByRole('list', { name: LABELS.repositoryProjects });
  const projectQueries = within(projectList);
  const projects = projectQueries.getAllByRole('listitem');
  expect(projects).toHaveLength(2);

  const warning = screen.getByRole('alert');
  expect(warning).toHaveTextContent(content.mismatch);
});
